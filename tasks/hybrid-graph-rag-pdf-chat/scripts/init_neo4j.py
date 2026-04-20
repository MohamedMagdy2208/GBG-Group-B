from __future__ import annotations

import logging
import sys
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.graph_store import SCHEMA_PATH, Neo4jGraphStore, load_cypher_statements


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize Neo4j constraints and indexes.")
    parser.add_argument(
        "--print-schema",
        action="store_true",
        help="Print the Cypher schema statements without connecting to Neo4j.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    if args.print_schema:
        for statement in load_cypher_statements(SCHEMA_PATH):
            print(f"{statement};\n")
        return

    settings = get_settings()
    store = Neo4jGraphStore(settings)
    try:
        store.verify_connectivity()
        store.init_schema()
        print(f"Neo4j constraints and indexes are ready in database '{settings.neo4j_database}'.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
