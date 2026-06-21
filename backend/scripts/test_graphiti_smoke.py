#!/usr/bin/env python3
"""Smoke test for the Graphiti/FalkorDB memory layer."""

import os
import sys

from dotenv import load_dotenv

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

from app.services.graphiti_graph_service import (  # noqa: E402
    FALKOR_UNREACHABLE_ERROR,
    OPENAI_KEY_ERROR,
    GraphitiGraphService,
)


def main() -> int:
    try:
        service = GraphitiGraphService()
        graph_id = service.create_graph("MiroFish Graphiti Smoke Test")
        try:
            service.set_ontology(
                graph_id,
                {
                    "entity_types": [
                        {
                            "name": "Person",
                            "description": "A person involved in the scenario.",
                            "attributes": [
                                {"name": "role", "description": "Role in the scenario"}
                            ],
                        },
                        {
                            "name": "Organization",
                            "description": "An organization involved in the scenario.",
                            "attributes": [
                                {"name": "org_type", "description": "Organization type"}
                            ],
                        },
                    ],
                    "edge_types": [
                        {
                            "name": "WORKS_WITH",
                            "description": "Works with another entity.",
                            "source_targets": [
                                {"source": "Person", "target": "Organization"}
                            ],
                            "attributes": [],
                        }
                    ],
                },
            )
            service.add_text_batches(
                graph_id,
                [
                    "Alice is a student organizer at Miro University.",
                    "Bob works with Alice on a campus public opinion survey.",
                    "Miro University responds to Alice and Bob with a public statement.",
                ],
                batch_size=2,
            )
            result = service.search_graph(graph_id, "Who is involved with Miro University?", limit=5)
            print(f"graph_id={graph_id}")
            print(f"facts_found={len(result.get('facts', []))}")
            for fact in result.get("facts", [])[:5]:
                print(f"- {fact}")
            return 0 if result.get("facts") or result.get("nodes") else 2
        finally:
            service.delete_graph(graph_id)
    except Exception as exc:
        message = str(exc)
        if OPENAI_KEY_ERROR in message:
            print(OPENAI_KEY_ERROR, file=sys.stderr)
        elif FALKOR_UNREACHABLE_ERROR in message:
            print(FALKOR_UNREACHABLE_ERROR, file=sys.stderr)
        else:
            print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
