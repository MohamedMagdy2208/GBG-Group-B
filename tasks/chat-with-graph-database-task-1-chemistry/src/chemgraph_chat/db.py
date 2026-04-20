from __future__ import annotations

from collections.abc import Callable
from typing import Any

import neo4j
from neo4j import GraphDatabase

from .config import Settings
from .serialization import serialize_record


def create_driver(settings: Settings) -> neo4j.Driver:
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )


def verify_connectivity(driver: neo4j.Driver, database: str) -> None:
    try:
        driver.verify_connectivity(database=database)
    except TypeError:
        driver.verify_connectivity()


def run_read_query(
    driver: neo4j.Driver,
    database: str,
    query: str,
    parameters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    params = parameters or {}

    def work(tx: neo4j.ManagedTransaction) -> list[dict[str, Any]]:
        result = tx.run(query, **params)
        return [serialize_record(record) for record in result]

    with driver.session(database=database, default_access_mode=neo4j.READ_ACCESS) as session:
        return session.execute_read(work)


def make_query_runner(
    driver: neo4j.Driver,
    database: str,
) -> Callable[[str, dict[str, Any]], list[dict[str, Any]]]:
    def runner(query: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        return run_read_query(driver, database, query, parameters)

    return runner

