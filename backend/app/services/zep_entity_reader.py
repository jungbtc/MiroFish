"""
Graphiti entity reader compatibility layer.

The filename/class names are retained because simulation code imports them
directly, but the implementation reads from Graphiti.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..utils.logger import get_logger
from .graphiti_graph_service import GraphitiGraphService

logger = get_logger('mirofish.graphiti_entity_reader')


@dataclass
class EntityNode:
    """Entity node structure expected by the simulation pipeline."""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }

    def get_entity_type(self) -> Optional[str]:
        """Return the first non-default label."""
        for label in self.labels:
            if label not in ["Entity", "Node"]:
                return label
        return None


@dataclass
class FilteredEntities:
    """Filtered entity collection."""
    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [entity.to_dict() for entity in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


class ZepEntityReader:
    """
    Compatibility reader backed by Graphiti.

    `api_key` is retained as a compatibility parameter and is interpreted as an
    OpenAI-compatible API key.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.graph_service = GraphitiGraphService(openai_api_key=api_key)

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        logger.info(f"Fetching Graphiti nodes for graph {graph_id}...")
        return self.graph_service.get_graph_data(graph_id).get("nodes", [])

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        logger.info(f"Fetching Graphiti edges for graph {graph_id}...")
        return self.graph_service.get_graph_data(graph_id).get("edges", [])

    def get_node_edges(self, node_uuid: str, graph_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not graph_id:
            logger.debug("get_node_edges called without graph_id; returning empty result")
            return []
        all_edges = self.get_all_edges(graph_id)
        return [
            edge for edge in all_edges
            if edge.get("source_node_uuid") == node_uuid or edge.get("target_node_uuid") == node_uuid
        ]

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
    ) -> FilteredEntities:
        logger.info(f"Filtering Graphiti entities for graph {graph_id}...")
        data = self.graph_service.get_entities(
            graph_id=graph_id,
            defined_entity_types=defined_entity_types,
            enrich_with_edges=enrich_with_edges,
        )
        entities = [
            EntityNode(
                uuid=item.get("uuid", ""),
                name=item.get("name", ""),
                labels=item.get("labels", []) or ["Entity"],
                summary=item.get("summary", ""),
                attributes=item.get("attributes", {}) or {},
                related_edges=item.get("related_edges", []) or [],
                related_nodes=item.get("related_nodes", []) or [],
            )
            for item in data.get("entities", [])
        ]
        entity_types = set(data.get("entity_types", []))
        logger.info(
            "Graphiti entity filtering complete: total=%s filtered=%s types=%s",
            data.get("total_count", 0),
            len(entities),
            entity_types,
        )
        return FilteredEntities(
            entities=entities,
            entity_types=entity_types,
            total_count=data.get("total_count", 0),
            filtered_count=len(entities),
        )

    def get_entity_with_context(self, graph_id: str, entity_uuid: str) -> Optional[EntityNode]:
        filtered = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=None,
            enrich_with_edges=True,
        )
        for entity in filtered.entities:
            if entity.uuid == entity_uuid:
                return entity
        return None

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str,
        enrich_with_edges: bool = True,
    ) -> List[EntityNode]:
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges,
        )
        return result.entities
