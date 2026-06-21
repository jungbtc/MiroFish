"""
Graph build service.

The public class name is kept for compatibility with existing API routes and
frontend expectations. Internally it delegates to Graphiti.
"""

import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ..models.task import TaskManager, TaskStatus
from ..utils.locale import get_locale, set_locale, t
from .graphiti_graph_service import GraphitiGraphService
from .text_processor import TextProcessor


@dataclass
class GraphInfo:
    """Graph summary."""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuilderService:
    """
    Graph construction service backed by Graphiti.

    `api_key` is retained as a compatibility parameter and is interpreted as an
    OpenAI-compatible API key.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.graph_service = GraphitiGraphService(openai_api_key=api_key)
        self.task_manager = TaskManager()

    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "MiroFish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 3,
    ) -> str:
        """Build a graph in a background thread and return the task id."""
        task_id = self.task_manager.create_task(
            task_type="graph_build",
            metadata={
                "graph_name": graph_name,
                "chunk_size": chunk_size,
                "text_length": len(text),
            },
        )
        current_locale = get_locale()
        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(
                task_id,
                text,
                ontology,
                graph_name,
                chunk_size,
                chunk_overlap,
                batch_size,
                current_locale,
            ),
            daemon=True,
        )
        thread.start()
        return task_id

    def _build_graph_worker(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int,
        locale: str = 'zh',
    ):
        """Background graph build worker."""
        set_locale(locale)
        try:
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                progress=5,
                message=t('progress.startBuildingGraph'),
            )

            graph_id = self.create_graph(graph_name)
            self.task_manager.update_task(
                task_id,
                progress=10,
                message=t('progress.graphCreated', graphId=graph_id),
            )

            self.set_ontology(graph_id, ontology)
            self.task_manager.update_task(
                task_id,
                progress=15,
                message=t('progress.ontologySet'),
            )

            chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
            total_chunks = len(chunks)
            self.task_manager.update_task(
                task_id,
                progress=20,
                message=t('progress.textSplit', count=total_chunks),
            )

            episode_uuids = self.add_text_batches(
                graph_id,
                chunks,
                batch_size,
                lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=20 + int(prog * 0.7),
                    message=msg,
                ),
            )

            self._wait_for_episodes(
                episode_uuids,
                lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=90 + int(prog * 5),
                    message=msg,
                ),
            )

            graph_info = self._get_graph_info(graph_id)
            self.task_manager.complete_task(task_id, {
                "graph_id": graph_id,
                "graph_info": graph_info.to_dict(),
                "chunks_processed": total_chunks,
            })
        except Exception as e:
            import traceback

            self.task_manager.fail_task(task_id, f"{str(e)}\n{traceback.format_exc()}")

    def create_graph(self, name: str) -> str:
        """Create a logical Graphiti graph."""
        return self.graph_service.create_graph(name)

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """Persist ontology metadata for Graphiti episode extraction."""
        self.graph_service.set_ontology(graph_id, ontology)

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[str]:
        """Add document chunks as Graphiti text episodes."""
        return self.graph_service.add_text_batches(
            graph_id=graph_id,
            chunks=chunks,
            batch_size=batch_size,
            progress_callback=progress_callback,
        )

    def _wait_for_episodes(
        self,
        episode_uuids: List[str],
        progress_callback: Optional[Callable[[str, float], None]] = None,
        timeout: int = 600,
    ):
        """
        Graphiti processes an episode before `add_episode` returns.

        This no-op keeps the old task/progress contract intact.
        """
        if progress_callback:
            progress_callback(t('progress.processingComplete', completed=len(episode_uuids), total=len(episode_uuids)), 1.0)

    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        graph_data = self.get_graph_data(graph_id)
        entity_types = set()
        for node in graph_data.get("nodes", []):
            for label in node.get("labels", []):
                if label not in ["Entity", "Node"]:
                    entity_types.add(label)
        return GraphInfo(
            graph_id=graph_id,
            node_count=graph_data.get("node_count", 0),
            edge_count=graph_data.get("edge_count", 0),
            entity_types=list(entity_types),
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """Return nodes/edges in the existing frontend-compatible shape."""
        return self.graph_service.get_graph_data(graph_id)

    def search_graph(self, graph_id: str, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search Graphiti using hybrid retrieval."""
        return self.graph_service.search_graph(graph_id, query, limit)

    def delete_graph(self, graph_id: str):
        """Delete the logical Graphiti graph."""
        self.graph_service.delete_graph(graph_id)
