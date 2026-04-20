from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.pipeline import IngestionPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the sample research PDF.")
    parser.add_argument("--pdf", type=Path, default=None, help="Optional PDF path.")
    parser.add_argument("--rebuild", action="store_true", help="Delete this PDF's graph/vector data first.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    settings = get_settings()
    pdf_path = args.pdf or settings.sample_pdf_path
    pipeline = IngestionPipeline(settings)
    result = pipeline.run(pdf_path, rebuild=args.rebuild)

    entity_count = sum(len(item.entities) for item in result.extractions)
    relationship_count = sum(len(item.relationships) for item in result.extractions)
    print(f"Ingested: {result.metadata.source_pdf}")
    print(f"Document ID: {result.metadata.document_id}")
    print(f"Chunks: {len(result.chunks)}")
    print(f"Entities extracted: {entity_count}")
    print(f"Relationships extracted: {relationship_count}")
    print(f"Raw text JSON: {result.raw_path}")
    print(f"Chunks JSON: {result.chunks_path}")
    print(f"Extraction JSON: {result.extractions_path}")


if __name__ == "__main__":
    main()

