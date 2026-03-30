"""Command-line bootstrap script for loading CSVs into the configured database."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import get_settings
from src.database.client import build_database_manager
from src.services.rag_pipeline import ChatWithDatabaseService


def main() -> None:
    """Bootstrap the configured database and build the vector store."""

    settings = get_settings()
    if not settings.vector_store_path.is_absolute():
        settings.vector_store_path = PROJECT_ROOT / settings.vector_store_path
    db = build_database_manager(settings)
    service = ChatWithDatabaseService(settings=settings, db=db, data_dir=PROJECT_ROOT / "csv")
    result = service.ensure_bootstrap(replace_existing=False)
    print(result)


if __name__ == "__main__":
    main()
