from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chemgraph_chat.config import ConfigError, load_settings
from chemgraph_chat.db import create_driver, verify_connectivity
from chemgraph_chat.seed import DEFAULT_SEED_PATH, run_seed


def main() -> int:
    try:
        settings = load_settings(require_openai=False)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    driver = create_driver(settings)
    try:
        verify_connectivity(driver, settings.neo4j_database)
        count = run_seed(driver, settings.neo4j_database, path=DEFAULT_SEED_PATH)
        print(f"Seeded chemistry graph with {count} idempotent Cypher statements.")
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())

