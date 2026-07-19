"""
Graphiti-backed knowledge graph adapter.

This module is the replacement for the former managed graph service.  The rest
of the backend still uses the old public service names, so this class keeps the
graph operations concentrated in one place.
"""

import asyncio
import json
import os
import re
import socket
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, create_model

from ..config import Config
from ..llm_settings import (
    reasoning_request_kwargs,
    structured_output_reasoning_effort,
    temperature_request_kwargs,
    token_limit_request_kwargs,
    usage_to_log_dict,
    uses_completion_token_param,
    validate_model,
    validate_reasoning_effort,
)
from ..utils.logger import get_logger
from ..utils.locale import t

logger = get_logger('mirofish.graphiti')

OPENAI_KEY_ERROR = "OPENAI_API_KEY or LLM_API_KEY is required."
FALKOR_UNREACHABLE_ERROR = "Graphiti backend is not reachable. Start FalkorDB on localhost:6379."
GRAPHITI_IMPORT_ERROR = (
    "Graphiti is not installed. Run `pip install -r backend/requirements.txt` "
    "or `uv sync` in the backend directory."
)


def run_async_safely(coro):
    """
    Run an async Graphiti coroutine from Flask's synchronous call sites.

    If a loop is already running in the current thread, run the coroutine on a
    short-lived worker thread with its own loop. This avoids nested event-loop
    failures in notebooks, debug tooling, or future async route contexts.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    if not loop.is_running():
        return loop.run_until_complete(coro)

    result: Dict[str, Any] = {}

    def runner():
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001 - re-raised in caller thread
            result["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]
    return result.get("value")


class GraphitiGraphService:
    """Sync facade over Graphiti's async temporal graph API."""

    DEFAULT_LABELS = {"Entity", "Node"}
    MAPPING_DIR = os.path.abspath(os.path.join(Config.UPLOAD_FOLDER, "graphiti_graphs"))

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
    ):
        self.openai_api_key = openai_api_key or Config.OPENAI_API_KEY or Config.LLM_API_KEY
        self.model_name = validate_model(model_name or Config.LLM_MODEL_NAME)
        self.reasoning_effort = validate_reasoning_effort(
            reasoning_effort or Config.LLM_REASONING_EFFORT
        )
        if Config._is_placeholder_secret(self.openai_api_key):
            raise ValueError(OPENAI_KEY_ERROR)

        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        os.environ.setdefault("LLM_API_KEY", self.openai_api_key)
        os.environ.setdefault("SEMAPHORE_LIMIT", str(Config.SEMAPHORE_LIMIT))
        os.environ.setdefault(
            "GRAPHITI_TELEMETRY_ENABLED",
            "true" if Config.GRAPHITI_TELEMETRY_ENABLED else "false",
        )
        os.makedirs(self.MAPPING_DIR, exist_ok=True)

    @classmethod
    def validate_configuration(cls) -> List[str]:
        """Return configuration errors without opening a graph connection."""
        return Config.validate_graph_settings()

    def create_graph(self, name: str) -> str:
        graph_id = f"graphiti_{uuid.uuid4().hex[:16]}"
        metadata = {
            "graph_id": graph_id,
            "name": name,
            "backend": Config.GRAPH_BACKEND,
            "driver": Config.GRAPHITI_DRIVER,
            "database": graph_id,
            "ontology": {},
            "episode_uuids": [],
            "llm_model": self.model_name,
            "llm_reasoning_effort": self.reasoning_effort,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_metadata(graph_id, metadata)
        try:
            run_async_safely(self._initialize_graph(graph_id))
        except Exception:
            path = self._metadata_path(graph_id)
            if os.path.exists(path):
                os.remove(path)
            raise
        return graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        metadata = self._load_metadata(graph_id)
        metadata["ontology"] = ontology or {}
        metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_metadata(graph_id, metadata)
        run_async_safely(self._initialize_graph(graph_id))

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[str]:
        return run_async_safely(
            self._add_text_batches(
                graph_id=graph_id,
                chunks=chunks,
                batch_size=max(1, batch_size),
                progress_callback=progress_callback,
            )
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        return run_async_safely(self._get_graph_data(graph_id))

    def delete_graph(self, graph_id: str) -> None:
        run_async_safely(self._delete_graph(graph_id))
        path = self._metadata_path(graph_id)
        if os.path.exists(path):
            os.remove(path)

    def search_graph(self, graph_id: str, query: str, limit: int = 10) -> Dict[str, Any]:
        return run_async_safely(self._search_graph(graph_id, query, limit))

    def get_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
    ) -> Dict[str, Any]:
        graph_data = self.get_graph_data(graph_id)
        metadata = self._load_metadata(graph_id)
        ontology_types = [
            item.get("name")
            for item in metadata.get("ontology", {}).get("entity_types", [])
            if item.get("name")
        ]
        preferred_types = defined_entity_types or ontology_types

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", []) if enrich_with_edges else []
        node_map = {node.get("uuid"): node for node in nodes}

        filtered = []
        entity_types_found = set()

        for node in nodes:
            labels = self._labels_with_inference(node, preferred_types)
            custom_labels = [label for label in labels if label not in self.DEFAULT_LABELS]

            if defined_entity_types:
                matching = [label for label in custom_labels if label in defined_entity_types]
                if not matching:
                    continue
                entity_type = matching[0]
            elif custom_labels:
                entity_type = custom_labels[0]
            else:
                entity_type = "Entity"

            entity_types_found.add(entity_type)
            related_edges = []
            related_node_uuids = set()

            if enrich_with_edges:
                for edge in edges:
                    if edge.get("source_node_uuid") == node.get("uuid"):
                        related_edges.append({
                            "direction": "outgoing",
                            "edge_name": edge.get("name", ""),
                            "fact": edge.get("fact", ""),
                            "target_node_uuid": edge.get("target_node_uuid", ""),
                        })
                        related_node_uuids.add(edge.get("target_node_uuid", ""))
                    elif edge.get("target_node_uuid") == node.get("uuid"):
                        related_edges.append({
                            "direction": "incoming",
                            "edge_name": edge.get("name", ""),
                            "fact": edge.get("fact", ""),
                            "source_node_uuid": edge.get("source_node_uuid", ""),
                        })
                        related_node_uuids.add(edge.get("source_node_uuid", ""))

            related_nodes = []
            for related_uuid in related_node_uuids:
                related = node_map.get(related_uuid)
                if related:
                    related_nodes.append({
                        "uuid": related.get("uuid", ""),
                        "name": related.get("name", ""),
                        "labels": related.get("labels", []),
                        "summary": related.get("summary", ""),
                    })

            filtered.append({
                "uuid": node.get("uuid", ""),
                "name": node.get("name", ""),
                "labels": labels,
                "summary": node.get("summary", ""),
                "attributes": node.get("attributes", {}),
                "related_edges": related_edges,
                "related_nodes": related_nodes,
            })

        return {
            "entities": filtered,
            "entity_types": list(entity_types_found),
            "total_count": len(nodes),
            "filtered_count": len(filtered),
        }

    def add_agent_activity(
        self,
        graph_id: str,
        activity_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        run_async_safely(self._add_agent_activity(graph_id, activity_text, metadata or {}))

    async def _initialize_graph(self, graph_id: str) -> None:
        graphiti = self._make_graphiti(graph_id)
        try:
            await graphiti.build_indices_and_constraints()
        finally:
            await graphiti.close()

    async def _add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int,
        progress_callback: Optional[Callable[[str, float], None]],
    ) -> List[str]:
        if not chunks:
            if progress_callback:
                progress_callback(t('progress.noEpisodesWait'), 1.0)
            return []

        metadata = self._load_metadata(graph_id)
        entity_types, edge_types, edge_type_map, instructions = self._build_ontology_models(
            metadata.get("ontology", {})
        )
        graphiti = self._make_graphiti(graph_id)
        episode_uuids: List[str] = []
        total_chunks = len(chunks)
        total_batches = (total_chunks + batch_size - 1) // batch_size

        try:
            for start in range(0, total_chunks, batch_size):
                batch_chunks = chunks[start:start + batch_size]
                batch_num = start // batch_size + 1
                if progress_callback:
                    progress_callback(
                        t(
                            'progress.sendingBatch',
                            current=batch_num,
                            total=total_batches,
                            chunks=len(batch_chunks),
                        ),
                        min((start + len(batch_chunks)) / total_chunks, 1.0),
                    )

                for offset, chunk in enumerate(batch_chunks):
                    chunk_index = start + offset
                    result = await graphiti.add_episode(
                        name=f"{metadata.get('name', 'FOREFOLD Graph')} chunk {chunk_index + 1}",
                        episode_body=chunk,
                        source=self._episode_type().text,
                        source_description=(
                            f"FOREFOLD upload chunk {chunk_index + 1}/{total_chunks}; "
                            f"graph={graph_id}"
                        ),
                        reference_time=datetime.now(timezone.utc),
                        group_id=graph_id,
                        entity_types=entity_types or None,
                        edge_types=edge_types or None,
                        edge_type_map=edge_type_map or None,
                        custom_extraction_instructions=instructions,
                    )
                    stored_uuid = getattr(getattr(result, "episode", None), "uuid", None)
                    if stored_uuid:
                        episode_uuids.append(stored_uuid)
        finally:
            await graphiti.close()

        metadata["episode_uuids"] = list({
            *(metadata.get("episode_uuids") or []),
            *episode_uuids,
        })
        metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_metadata(graph_id, metadata)
        return episode_uuids

    async def _get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        graphiti = self._make_graphiti(graph_id)
        try:
            nodes = await self._fetch_nodes(graphiti, graph_id)
            edges = await self._fetch_edges(graphiti, graph_id)
        finally:
            await graphiti.close()

        node_map = {node["uuid"]: node.get("name", "") for node in nodes}
        for edge in edges:
            edge["source_node_name"] = node_map.get(edge.get("source_node_uuid"), "")
            edge["target_node_name"] = node_map.get(edge.get("target_node_uuid"), "")

        return {
            "graph_id": graph_id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    async def _delete_graph(self, graph_id: str) -> None:
        graphiti = self._make_graphiti(graph_id)
        try:
            await graphiti.driver.execute_query("MATCH (n) DETACH DELETE n")
        finally:
            await graphiti.close()

    async def _search_graph(self, graph_id: str, query: str, limit: int) -> Dict[str, Any]:
        graphiti = self._make_graphiti(graph_id)
        try:
            edge_results = await graphiti.search(
                query=query,
                group_ids=[graph_id],
                num_results=limit,
            )

            edges = [self._edge_to_dict(edge) for edge in edge_results]
            facts = [edge.get("fact", "") for edge in edges if edge.get("fact")]
            nodes = []

            try:
                from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

                node_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
                node_config.limit = limit
                if hasattr(graphiti, "search_"):
                    node_results = await graphiti.search_(
                        query=query,
                        config=node_config,
                        group_ids=[graph_id],
                    )
                else:
                    node_results = await graphiti._search(
                        query=query,
                        config=node_config,
                        group_ids=[graph_id],
                    )
                nodes = [self._node_to_dict(node) for node in getattr(node_results, "nodes", [])]
            except Exception as exc:
                logger.debug(f"Graphiti node search skipped: {exc}")

            return {
                "facts": facts,
                "edges": edges,
                "nodes": nodes,
                "query": query,
                "total_count": len(facts) + len(nodes),
            }
        finally:
            await graphiti.close()

    async def _add_agent_activity(
        self,
        graph_id: str,
        activity_text: str,
        metadata: Dict[str, Any],
    ) -> None:
        graphiti = self._make_graphiti(graph_id)
        try:
            description = "FOREFOLD agent activity"
            if metadata:
                description += f"; metadata={json.dumps(metadata, ensure_ascii=False)[:500]}"
            await graphiti.add_episode(
                name=f"agent_activity_{datetime.now(timezone.utc).isoformat()}",
                episode_body=activity_text,
                source=self._episode_type().text,
                source_description=description,
                reference_time=datetime.now(timezone.utc),
                group_id=graph_id,
                saga="agent_activity",
            )
        finally:
            await graphiti.close()

    async def _fetch_nodes(self, graphiti, graph_id: str) -> List[Dict[str, Any]]:
        try:
            from graphiti_core.nodes import EntityNode as GraphitiEntityNode

            nodes = await GraphitiEntityNode.get_by_group_ids(graphiti.driver, [graph_id])
            return [self._node_to_dict(node) for node in nodes]
        except AttributeError:
            return await self._fetch_nodes_via_query(graphiti)
        except Exception as exc:
            if "not found" in str(exc).lower():
                return []
            try:
                return await self._fetch_nodes_via_query(graphiti)
            except Exception:
                raise exc

    async def _fetch_edges(self, graphiti, graph_id: str) -> List[Dict[str, Any]]:
        try:
            from graphiti_core.edges import EntityEdge as GraphitiEntityEdge

            edges = await GraphitiEntityEdge.get_by_group_ids(graphiti.driver, [graph_id])
            return [self._edge_to_dict(edge) for edge in edges]
        except AttributeError:
            return await self._fetch_edges_via_query(graphiti)
        except Exception as exc:
            if "not found" in str(exc).lower():
                return []
            try:
                return await self._fetch_edges_via_query(graphiti)
            except Exception:
                raise exc

    async def _fetch_nodes_via_query(self, graphiti) -> List[Dict[str, Any]]:
        records, _, _ = await graphiti.driver.execute_query(
            """
            MATCH (n:Entity)
            RETURN n.uuid AS uuid,
                   n.name AS name,
                   labels(n) AS labels,
                   n.summary AS summary,
                   properties(n) AS attributes,
                   n.created_at AS created_at
            """,
            routing_='r',
        )
        return [self._node_record_to_dict(record) for record in records]

    async def _fetch_edges_via_query(self, graphiti) -> List[Dict[str, Any]]:
        records, _, _ = await graphiti.driver.execute_query(
            """
            MATCH (source:Entity)-[edge:RELATES_TO]->(target:Entity)
            RETURN edge.uuid AS uuid,
                   edge.name AS name,
                   edge.fact AS fact,
                   source.uuid AS source_node_uuid,
                   target.uuid AS target_node_uuid,
                   properties(edge) AS attributes,
                   edge.created_at AS created_at,
                   edge.valid_at AS valid_at,
                   edge.invalid_at AS invalid_at,
                   edge.expired_at AS expired_at,
                   edge.episodes AS episodes
            """,
            routing_='r',
        )
        return [self._edge_record_to_dict(record) for record in records]

    def _make_graphiti(self, graph_id: str):
        self._ensure_graphiti_installed()
        self._check_backend_reachable()

        metadata = self._load_metadata(graph_id)
        model_name = metadata.get("llm_model", self.model_name)
        reasoning_effort = metadata.get("llm_reasoning_effort", self.reasoning_effort)

        from graphiti_core import Graphiti
        from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.llm_client.openai_client import OpenAIClient

        llm_config = LLMConfig(
            api_key=self.openai_api_key,
            model=model_name,
            small_model=model_name,
            base_url=Config.LLM_BASE_URL,
        )
        selected_reasoning_effort = validate_reasoning_effort(reasoning_effort)
        effective_reasoning_effort = structured_output_reasoning_effort(
            selected_reasoning_effort
        )

        class MiroFishOpenAIClient(OpenAIClient):
            async def _create_completion(
                self,
                model,
                messages,
                temperature,
                max_tokens,
                response_model=None,
                reasoning=None,
                verbosity=None,
            ):
                if not model.startswith("gpt-5"):
                    return await super()._create_completion(
                        model,
                        messages,
                        temperature,
                        max_tokens,
                        response_model,
                        reasoning,
                        verbosity,
                    )

                request_kwargs = {
                    "model": model,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    **reasoning_request_kwargs(
                        effective_reasoning_effort,
                        model,
                        Config.LLM_BASE_URL,
                    ),
                    **temperature_request_kwargs(model, temperature, Config.LLM_BASE_URL),
                    **token_limit_request_kwargs(
                        model,
                        effective_reasoning_effort,
                        max_tokens,
                        uses_completion_token_param(model, Config.LLM_BASE_URL),
                    ),
                }
                logger.info(
                    "LLM request start: model=%s, reasoning_effort=%s, effective_reasoning_effort=%s, component=graphiti",
                    model,
                    selected_reasoning_effort,
                    effective_reasoning_effort,
                )
                try:
                    response = await self.client.chat.completions.create(**request_kwargs)
                except Exception as exc:
                    logger.error(
                        "LLM request error: model=%s, reasoning_effort=%s, effective_reasoning_effort=%s, component=graphiti, error=%s",
                        model,
                        selected_reasoning_effort,
                        effective_reasoning_effort,
                        exc,
                    )
                    raise
                logger.info(
                    "LLM request complete: model=%s, reasoning_effort=%s, effective_reasoning_effort=%s, component=graphiti, usage=%s",
                    model,
                    selected_reasoning_effort,
                    effective_reasoning_effort,
                    usage_to_log_dict(response),
                )
                return response

        graphiti_reasoning = effective_reasoning_effort
        llm_client = MiroFishOpenAIClient(config=llm_config, reasoning=graphiti_reasoning)
        embedder = OpenAIEmbedder(
            config=OpenAIEmbedderConfig(
                api_key=self.openai_api_key,
                base_url=Config.LLM_BASE_URL,
            )
        )
        reranker_config = LLMConfig(
            api_key=self.openai_api_key,
            model=validate_model(Config.GRAPHITI_RERANKER_MODEL),
            base_url=Config.LLM_BASE_URL,
        )
        reranker = OpenAIRerankerClient(config=reranker_config)

        if Config.GRAPHITI_DRIVER == "neo4j":
            from graphiti_core.driver.neo4j_driver import Neo4jDriver

            driver = Neo4jDriver(
                uri=Config.NEO4J_URI,
                user=Config.NEO4J_USER,
                password=Config.NEO4J_PASSWORD,
                database=graph_id,
            )
        else:
            from graphiti_core.driver.falkordb_driver import (
                FalkorDriver,
                get_fulltext_indices,
                get_range_indices,
            )

            class MiroFishFalkorDriver(FalkorDriver):
                async def build_indices_and_constraints(self, delete_existing=False):
                    if delete_existing:
                        await self.delete_all_indexes()

                    graph = self._get_graph(self._database)
                    for query in get_range_indices(self.provider) + get_fulltext_indices(self.provider):
                        try:
                            await graph.query(query, {})
                        except Exception as exc:
                            message = str(exc).lower()
                            if "already indexed" in message or "connection closed by server" in message:
                                logger.debug(f"Skipping FalkorDB index statement: {exc}")
                                continue
                            raise

            driver = MiroFishFalkorDriver(
                host=Config.FALKORDB_HOST,
                port=Config.FALKORDB_PORT,
                username=Config.FALKORDB_USERNAME,
                password=Config.FALKORDB_PASSWORD,
                database=graph_id,
            )

        return Graphiti(
            graph_driver=driver,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=reranker,
            max_coroutines=Config.SEMAPHORE_LIMIT,
        )

    def _check_backend_reachable(self) -> None:
        if Config.GRAPHITI_DRIVER != "falkordb":
            return
        try:
            with socket.create_connection(
                (Config.FALKORDB_HOST, Config.FALKORDB_PORT),
                timeout=2,
            ):
                return
        except OSError as exc:
            raise ConnectionError(FALKOR_UNREACHABLE_ERROR) from exc

    @staticmethod
    def _ensure_graphiti_installed() -> None:
        try:
            import graphiti_core  # noqa: F401
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(GRAPHITI_IMPORT_ERROR) from exc

    @staticmethod
    def _episode_type():
        from graphiti_core.nodes import EpisodeType

        return EpisodeType

    def _build_ontology_models(
        self,
        ontology: Dict[str, Any],
    ) -> tuple[Dict[str, type[BaseModel]], Dict[str, type[BaseModel]], Dict[tuple[str, str], List[str]], Optional[str]]:
        entity_models: Dict[str, type[BaseModel]] = {}
        edge_models: Dict[str, type[BaseModel]] = {}
        edge_type_map: Dict[tuple[str, str], List[str]] = {}

        for entity in ontology.get("entity_types", []) or []:
            name = self._safe_entity_type(entity.get("name") or "Entity")
            fields = self._model_fields(entity.get("attributes", []))
            model = create_model(name, __base__=BaseModel, **fields)
            model.__doc__ = entity.get("description", f"A {name} entity.")
            entity_models[name] = model

        for edge in ontology.get("edge_types", []) or []:
            name = self._safe_edge_type(edge.get("name") or "RELATED_TO")
            fields = self._model_fields(edge.get("attributes", []))
            model = create_model(name, __base__=BaseModel, **fields)
            model.__doc__ = edge.get("description", f"A {name} relationship.")
            edge_models[name] = model

            source_targets = edge.get("source_targets") or []
            if source_targets:
                for source_target in source_targets:
                    source = self._safe_entity_type(source_target.get("source") or "Entity")
                    target = self._safe_entity_type(source_target.get("target") or "Entity")
                    edge_type_map.setdefault((source, target), []).append(name)

        if edge_models and not edge_type_map:
            edge_type_map[("Entity", "Entity")] = list(edge_models.keys())

        instructions = self._ontology_instructions(ontology)
        return entity_models, edge_models, edge_type_map, instructions

    def _model_fields(self, attributes: List[Dict[str, Any]]) -> Dict[str, Any]:
        fields = {}
        for attr in attributes or []:
            name = self._safe_attr_name(attr.get("name") or "value")
            description = attr.get("description") or name
            fields[name] = (Optional[str], Field(default=None, description=description))
        return fields

    @staticmethod
    def _ontology_instructions(ontology: Dict[str, Any]) -> Optional[str]:
        entity_names = [item.get("name") for item in ontology.get("entity_types", []) if item.get("name")]
        edge_names = [item.get("name") for item in ontology.get("edge_types", []) if item.get("name")]
        if not entity_names and not edge_names:
            return None
        return (
            "Use the prescribed ontology where possible. Entity types: "
            f"{', '.join(entity_names) or 'Entity'}. Relationship types: "
            f"{', '.join(edge_names) or 'RELATED_TO'}. Preserve real people, "
            "organizations, media accounts, platforms, and groups as entities."
        )

    @staticmethod
    def _safe_entity_type(value: str) -> str:
        words = re.split(r'[^A-Za-z0-9]+', value or "")
        name = ''.join(word[:1].upper() + word[1:] for word in words if word)
        if not name:
            name = "Entity"
        if not re.match(r'^[A-Za-z_]', name):
            name = f"Entity{name}"
        return re.sub(r'[^A-Za-z0-9_]', '', name)

    @staticmethod
    def _safe_edge_type(value: str) -> str:
        words = re.split(r'[^A-Za-z0-9]+', value or "")
        name = '_'.join(word.upper() for word in words if word)
        if not name:
            name = "RELATED_TO"
        if not re.match(r'^[A-Za-z_]', name):
            name = f"REL_{name}"
        return re.sub(r'[^A-Za-z0-9_]', '', name)

    @staticmethod
    def _safe_attr_name(value: str) -> str:
        name = re.sub(r'[^A-Za-z0-9_]', '_', value or "value").strip('_').lower()
        if not name:
            name = "value"
        if not re.match(r'^[A-Za-z_]', name):
            name = f"attr_{name}"
        if name in {"uuid", "name", "group_id", "name_embedding", "summary", "created_at", "labels"}:
            name = f"entity_{name}"
        return name

    def _labels_with_inference(self, node: Dict[str, Any], preferred_types: Optional[List[str]]) -> List[str]:
        labels = list(node.get("labels") or [])
        if "Entity" not in labels:
            labels.append("Entity")

        custom_labels = [label for label in labels if label not in self.DEFAULT_LABELS]
        if custom_labels:
            return labels

        inferred = self._infer_entity_type(node, preferred_types or [])
        if inferred and inferred not in labels:
            labels.insert(0, inferred)
        return labels

    @staticmethod
    def _infer_entity_type(node: Dict[str, Any], preferred_types: List[str]) -> str:
        text = " ".join([
            str(node.get("name", "")),
            str(node.get("summary", "")),
            json.dumps(node.get("attributes", {}), ensure_ascii=False),
        ]).lower()

        for entity_type in preferred_types:
            if entity_type and entity_type.lower() in text:
                return entity_type

        if preferred_types:
            return preferred_types[0]

        organization_words = ["company", "university", "agency", "school", "media", "organization", "group"]
        if any(word in text for word in organization_words):
            return "Organization"
        if len(str(node.get("name", "")).split()) <= 4:
            return "Person"
        return "Entity"

    def _node_to_dict(self, node: Any) -> Dict[str, Any]:
        labels = list(getattr(node, "labels", []) or [])
        if "Entity" not in labels:
            labels.append("Entity")
        attributes = dict(getattr(node, "attributes", {}) or {})
        return {
            "uuid": str(getattr(node, "uuid", "") or ""),
            "name": getattr(node, "name", "") or "",
            "labels": labels,
            "summary": getattr(node, "summary", "") or "",
            "attributes": self._clean_attributes(attributes),
            "created_at": self._format_datetime(getattr(node, "created_at", None)),
        }

    def _edge_to_dict(self, edge: Any) -> Dict[str, Any]:
        attributes = dict(getattr(edge, "attributes", {}) or {})
        episodes = getattr(edge, "episodes", None) or getattr(edge, "episode_ids", None) or []
        if episodes and not isinstance(episodes, list):
            episodes = [episodes]
        return {
            "uuid": str(getattr(edge, "uuid", "") or ""),
            "name": getattr(edge, "name", "") or "",
            "fact": getattr(edge, "fact", "") or "",
            "fact_type": getattr(edge, "fact_type", None) or getattr(edge, "name", "") or "",
            "source_node_uuid": getattr(edge, "source_node_uuid", "") or "",
            "target_node_uuid": getattr(edge, "target_node_uuid", "") or "",
            "attributes": self._clean_attributes(attributes),
            "created_at": self._format_datetime(getattr(edge, "created_at", None)),
            "valid_at": self._format_datetime(getattr(edge, "valid_at", None)),
            "invalid_at": self._format_datetime(getattr(edge, "invalid_at", None)),
            "expired_at": self._format_datetime(getattr(edge, "expired_at", None)),
            "episodes": [str(item) for item in episodes],
        }

    def _node_record_to_dict(self, record: Dict[str, Any]) -> Dict[str, Any]:
        labels = list(record.get("labels") or [])
        if "Entity" not in labels:
            labels.append("Entity")
        return {
            "uuid": str(record.get("uuid", "") or ""),
            "name": record.get("name", "") or "",
            "labels": labels,
            "summary": record.get("summary", "") or "",
            "attributes": self._clean_attributes(dict(record.get("attributes") or {})),
            "created_at": self._format_datetime(record.get("created_at")),
        }

    def _edge_record_to_dict(self, record: Dict[str, Any]) -> Dict[str, Any]:
        episodes = record.get("episodes") or []
        if episodes and not isinstance(episodes, list):
            episodes = [episodes]
        return {
            "uuid": str(record.get("uuid", "") or ""),
            "name": record.get("name", "") or "",
            "fact": record.get("fact", "") or "",
            "fact_type": record.get("name", "") or "",
            "source_node_uuid": record.get("source_node_uuid", "") or "",
            "target_node_uuid": record.get("target_node_uuid", "") or "",
            "attributes": self._clean_attributes(dict(record.get("attributes") or {})),
            "created_at": self._format_datetime(record.get("created_at")),
            "valid_at": self._format_datetime(record.get("valid_at")),
            "invalid_at": self._format_datetime(record.get("invalid_at")),
            "expired_at": self._format_datetime(record.get("expired_at")),
            "episodes": [str(item) for item in episodes],
        }

    @staticmethod
    def _clean_attributes(attributes: Dict[str, Any]) -> Dict[str, Any]:
        for key in [
            "uuid",
            "name",
            "group_id",
            "name_embedding",
            "fact_embedding",
            "summary",
            "created_at",
            "labels",
            "fact",
            "valid_at",
            "invalid_at",
            "expired_at",
            "episodes",
        ]:
            attributes.pop(key, None)
        return attributes

    @staticmethod
    def _format_datetime(value: Any) -> Optional[str]:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    def _metadata_path(self, graph_id: str) -> str:
        safe_id = re.sub(r'[^A-Za-z0-9_-]', '_', graph_id)
        return os.path.join(self.MAPPING_DIR, f"{safe_id}.json")

    def _load_metadata(self, graph_id: str) -> Dict[str, Any]:
        path = self._metadata_path(graph_id)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as file:
                return json.load(file)
        return {
            "graph_id": graph_id,
            "name": graph_id,
            "backend": Config.GRAPH_BACKEND,
            "driver": Config.GRAPHITI_DRIVER,
            "database": graph_id,
            "ontology": {},
            "episode_uuids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _save_metadata(self, graph_id: str, metadata: Dict[str, Any]) -> None:
        metadata["graph_id"] = graph_id
        os.makedirs(self.MAPPING_DIR, exist_ok=True)
        with open(self._metadata_path(graph_id), 'w', encoding='utf-8') as file:
            json.dump(metadata, file, ensure_ascii=False, indent=2)
