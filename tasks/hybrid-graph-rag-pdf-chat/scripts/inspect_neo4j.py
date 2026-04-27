from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.graph_store import Neo4jGraphStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the current Neo4j graph contents.")
    parser.add_argument("--source-pdf", default=None, help="Optional source PDF filter.")
    parser.add_argument("--limit", type=int, default=10, help="Number of sample entities/relationships.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    settings = get_settings()
    store = Neo4jGraphStore(settings)
    try:
        store.verify_connectivity()
        print("Summary")
        print(store.summary(source_pdf=args.source_pdf))
        print("\nSample entities")
        for row in store.list_entities(source_pdf=args.source_pdf, limit=args.limit):
            print(f"- {row.get('name')} [{row.get('type')}] pages={row.get('page_numbers')}")
        print("\nSample relationships")
        for row in store.list_relationships(source_pdf=args.source_pdf, limit=args.limit):
            print(
                f"- {row.get('source')} -[{row.get('type')}]-> {row.get('target')} "
                f"pages={row.get('page_numbers')}"
            )
    finally:
        store.close()


if __name__ == "__main__":
    main()
