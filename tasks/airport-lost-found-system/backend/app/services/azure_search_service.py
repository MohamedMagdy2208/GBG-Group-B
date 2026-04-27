import asyncio
import logging
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import FoundItem, LostReport


logger = logging.getLogger(__name__)


class AzureSearchService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _enabled(self) -> bool:
        return bool(
            self.settings.use_azure_services
            and self.settings.azure_search_endpoint
            and self.settings.azure_search_index_name
        )

    def _credential(self):
        if self.settings.azure_search_key:
            from azure.core.credentials import AzureKeyCredential

            return AzureKeyCredential(self.settings.azure_search_key)
        from azure.identity import DefaultAzureCredential

        return DefaultAzureCredential()

    def _search_client(self):
        from azure.search.documents import SearchClient

        return SearchClient(
            endpoint=self.settings.azure_search_endpoint,
            index_name=self.settings.azure_search_index_name,
            credential=self._credential(),
        )

    def _index_client(self):
        from azure.search.documents.indexes import SearchIndexClient

        return SearchIndexClient(endpoint=self.settings.azure_search_endpoint, credential=self._credential())

    async def create_or_update_index(self) -> None:
        if not self._enabled():
            logger.info("local search fallback ready", extra={"event": "search_index_ready"})
            return
        await asyncio.to_thread(self._create_or_update_index_sync)
        logger.info("Azure AI Search index ready", extra={"event": "search_index_ready"})

    def _create_or_update_index_sync(self) -> None:
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration,
            SearchableField,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        fields = [
            SimpleField(name="document_id", type=SearchFieldDataType.String, key=True, filterable=True),
            SimpleField(name="source_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="source_id", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
            SearchableField(name="item_title", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="description", type=SearchFieldDataType.String),
            SearchableField(name="brand", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="model", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="color", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="location", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="item_datetime", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SearchableField(name="flight_number", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="status", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="risk_level", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.settings.azure_search_vector_dimensions,
                vector_search_profile_name="lost-found-vector-profile",
            ),
        ]
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="lost-found-hnsw")],
            profiles=[
                VectorSearchProfile(
                    name="lost-found-vector-profile",
                    algorithm_configuration_name="lost-found-hnsw",
                )
            ],
        )
        index = SearchIndex(name=self.settings.azure_search_index_name, fields=fields, vector_search=vector_search)
        self._index_client().create_or_update_index(index)

    async def index_lost_report(self, report: LostReport) -> str:
        document_id = f"lost-{report.id}"
        if self._enabled():
            document = await self._lost_report_document(report)
            await asyncio.to_thread(self._search_client().merge_or_upload_documents, [document])
        return document_id

    async def index_found_item(self, item: FoundItem) -> str:
        document_id = f"found-{item.id}"
        if self._enabled():
            document = await self._found_item_document(item)
            await asyncio.to_thread(self._search_client().merge_or_upload_documents, [document])
        return document_id

    async def delete_document(self, document_id: str) -> None:
        if not self._enabled():
            return
        await asyncio.to_thread(self._search_client().delete_documents, [{"document_id": document_id}])

    async def hybrid_search_found_items(self, db: Session, report: LostReport, limit: int = 10) -> list[tuple[FoundItem, float]]:
        if self._enabled():
            query_text = self._lost_text(report)
            results = await self._azure_hybrid_search(
                query_text=query_text,
                filter_expression="source_type eq 'found_item' and status ne 'released' and status ne 'disposed'",
                limit=limit,
            )
            return self._materialize_found_items(db, results)
        items = db.query(FoundItem).all()
        query_text = self._lost_text(report)
        scored = [(item, self._similarity(query_text, self._found_text(item))) for item in items]
        return sorted(scored, key=lambda pair: pair[1], reverse=True)[:limit]

    async def hybrid_search_lost_reports(self, db: Session, item: FoundItem, limit: int = 10) -> list[tuple[LostReport, float]]:
        if self._enabled():
            query_text = self._found_text(item)
            results = await self._azure_hybrid_search(
                query_text=query_text,
                filter_expression="source_type eq 'lost_report' and status ne 'resolved' and status ne 'rejected'",
                limit=limit,
            )
            return self._materialize_lost_reports(db, results)
        reports = db.query(LostReport).all()
        query_text = self._found_text(item)
        scored = [(report, self._similarity(query_text, self._lost_text(report))) for report in reports]
        return sorted(scored, key=lambda pair: pair[1], reverse=True)[:limit]

    async def vector_search(self, documents: list[Any], query_text: str, limit: int = 10) -> list[tuple[Any, float]]:
        scored = [(doc, self._similarity(query_text, str(doc))) for doc in documents]
        return sorted(scored, key=lambda pair: pair[1], reverse=True)[:limit]

    async def _azure_hybrid_search(self, query_text: str, filter_expression: str, limit: int) -> list[dict[str, Any]]:
        from azure.search.documents.models import VectorizedQuery

        from app.services.azure_openai_service import azure_openai_service

        _, embedding = await azure_openai_service.generate_embedding(query_text)
        if len(embedding) != self.settings.azure_search_vector_dimensions:
            logger.warning(
                "embedding dimension mismatch for Azure AI Search",
                extra={
                    "event": "search_embedding_dimension_mismatch",
                    "actual_dimensions": len(embedding),
                    "expected_dimensions": self.settings.azure_search_vector_dimensions,
                },
            )
        vector_query = VectorizedQuery(
            vector=embedding,
            k_nearest_neighbors=max(limit, 10),
            fields="content_vector",
        )
        client = self._search_client()

        def run_search():
            return list(
                client.search(
                    search_text=query_text or "*",
                    vector_queries=[vector_query],
                    filter=filter_expression,
                    select=[
                        "document_id",
                        "source_type",
                        "source_id",
                        "item_title",
                        "category",
                        "location",
                        "status",
                    ],
                    top=limit,
                )
            )

        raw_results = await asyncio.to_thread(run_search)
        max_score = max((float(result.get("@search.score", 0) or 0) for result in raw_results), default=1) or 1
        return [
            {
                "source_id": int(result["source_id"]),
                "score": round((float(result.get("@search.score", 0) or 0) / max_score) * 100, 2),
            }
            for result in raw_results
            if result.get("source_id") is not None
        ]

    def _materialize_found_items(self, db: Session, results: list[dict[str, Any]]) -> list[tuple[FoundItem, float]]:
        items = []
        for result in results:
            item = db.get(FoundItem, result["source_id"])
            if item:
                items.append((item, result["score"]))
        return items

    def _materialize_lost_reports(self, db: Session, results: list[dict[str, Any]]) -> list[tuple[LostReport, float]]:
        reports = []
        for result in results:
            report = db.get(LostReport, result["source_id"])
            if report:
                reports.append((report, result["score"]))
        return reports

    async def _lost_report_document(self, report: LostReport) -> dict[str, Any]:
        from app.services.azure_openai_service import azure_openai_service

        content = self._lost_text(report)
        _, embedding = await azure_openai_service.generate_embedding(content)
        return {
            "document_id": f"lost-{report.id}",
            "source_type": "lost_report",
            "source_id": report.id,
            "item_title": report.item_title,
            "category": report.category,
            "description": report.ai_clean_description or report.raw_description,
            "brand": report.brand,
            "model": report.model,
            "color": report.color,
            "location": report.lost_location,
            "item_datetime": self._format_datetime(report.lost_datetime),
            "flight_number": report.flight_number,
            "status": report.status.value,
            "risk_level": None,
            "content": content,
            "content_vector": embedding,
        }

    async def _found_item_document(self, item: FoundItem) -> dict[str, Any]:
        from app.services.azure_openai_service import azure_openai_service

        content = self._found_text(item)
        _, embedding = await azure_openai_service.generate_embedding(content)
        return {
            "document_id": f"found-{item.id}",
            "source_type": "found_item",
            "source_id": item.id,
            "item_title": item.item_title,
            "category": item.category,
            "description": item.ai_clean_description or item.raw_description,
            "brand": item.brand,
            "model": item.model,
            "color": item.color,
            "location": item.found_location,
            "item_datetime": self._format_datetime(item.found_datetime),
            "flight_number": (item.ai_extracted_attributes_json or {}).get("flight_number"),
            "status": item.status.value,
            "risk_level": item.risk_level.value,
            "content": content,
            "content_vector": embedding,
        }

    def _similarity(self, left: str, right: str) -> float:
        return round(SequenceMatcher(None, left.lower(), right.lower()).ratio() * 100, 2)

    def _lost_text(self, report: LostReport) -> str:
        return " ".join(
            filter(
                None,
                [
                    report.item_title,
                    report.category,
                    report.raw_description,
                    report.ai_clean_description,
                    report.brand,
                    report.model,
                    report.color,
                    report.lost_location,
                    report.flight_number,
                ],
            )
        )

    def _found_text(self, item: FoundItem) -> str:
        return " ".join(
            filter(
                None,
                [
                    item.item_title,
                    item.category,
                    item.raw_description,
                    item.ai_clean_description,
                    item.brand,
                    item.model,
                    item.color,
                    item.found_location,
                    item.vision_ocr_text,
                ],
            )
        )

    def _format_datetime(self, value: datetime | None) -> str | None:
        if not value:
            return None
        return value.isoformat()


azure_search_service = AzureSearchService()
