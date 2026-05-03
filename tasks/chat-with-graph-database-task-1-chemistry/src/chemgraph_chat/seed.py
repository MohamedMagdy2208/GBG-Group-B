from __future__ import annotations

from pathlib import Path

import neo4j


DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "chemistry_seed.cypher"


def load_seed_statements(path: Path = DEFAULT_SEED_PATH) -> list[str]:
    text = path.read_text(encoding="utf-8")
    statements = [statement.strip() for statement in text.split(";")]
    return [statement for statement in statements if statement]


def run_seed(
    driver: neo4j.Driver,
    database: str,
    *,
    path: Path = DEFAULT_SEED_PATH,
) -> int:
    statements = load_seed_statements(path)

    def work(tx: neo4j.ManagedTransaction) -> None:
        for statement in statements:
            tx.run(statement)

    with driver.session(database=database) as session:
        session.execute_write(work)
    return len(statements)

