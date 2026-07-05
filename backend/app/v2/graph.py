"""Lightweight relationship graph for MiroFish v2."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List

from .schemas import Entity, Relationship


class RelationshipGraphService:
    def build_graph(self, entities: Iterable[Entity], relationships: Iterable[Relationship]) -> Dict[str, Any]:
        nodes = [
            {
                "id": entity.entity_id,
                "name": entity.name,
                "type": entity.type,
                "source_ids": entity.source_ids,
                "citations": [c.model_dump(mode="json") for c in entity.citations],
            }
            for entity in entities
        ]
        edges = [
            {
                "id": rel.relationship_id,
                "source": rel.source_entity_id,
                "target": rel.target_entity_id,
                "type": rel.type,
                "description": rel.description,
                "citations": [c.model_dump(mode="json") for c in rel.citations],
            }
            for rel in relationships
        ]
        by_entity: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        by_source: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for edge in edges:
            by_entity[edge["source"]].append(edge)
            by_entity[edge["target"]].append(edge)
            by_type[edge["type"]].append(edge)
            for citation in edge.get("citations", []):
                by_source[citation.get("source_id", "")].append(edge)

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "indexes": {
                "by_entity": dict(by_entity),
                "by_type": dict(by_type),
                "by_source": dict(by_source),
            },
        }
