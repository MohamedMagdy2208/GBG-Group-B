import asyncio
import logging
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import mask_sensitive_text
from app.models import FoundItem, FoundItemStatus, LostReport, LostReportStatus


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
        try:
            await asyncio.to_thread(self._create_or_update_index_sync)
            logger.info("Azure AI Search index ready", extra={"event": "search_index_ready"})
        except Exception as exc:
            # Fields whose vector dimension changed cannot be updated in-place — recreate as a fallback.
            message = str(exc).lower()
            if "cannot be changed" in message or "cannotchangeexistingfield" in message:
                logger.warning(
                    "Search index field schema changed — recreating index",
                    extra={"event": "search_index_recreate_required"},
                )
                await asyncio.to_thread(self._delete_index_if_exists_sync)
                await asyncio.to_thread(self._create_or_update_index_sync)
                logger.info("Azure AI Search index recreated", extra={"event": "search_index_ready"})
            else:
                logger.exception("Search index update failed; continuing with local fallback", extra={"event": "search_index_failed"})

    async def recreate_index(self) -> None:
        if not self._enabled():
            logger.info("local search fallback index reset", extra={"event": "search_index_reset"})
            return
        await asyncio.to_thread(self._delete_index_if_exists_sync)
        await asyncio.to_thread(self._create_or_update_index_sync)
        logger.info("Azure AI Search index recreated", extra={"event": "search_index_recreated"})

    def _delete_index_if_exists_sync(self) -> None:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            self._index_client().delete_index(self.settings.azure_search_index_name)
        except ResourceNotFoundError:
            return

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
            SearchField(
                name="image_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                # Azure AI Vision multimodal embeddings are fixed at 1024 dimensions.
                vector_search_dimensions=1024,
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
        query_text = self._lost_text(report)
        if self._enabled():
            results = await self._azure_hybrid_search(
                query_text=query_text,
                filter_expression="source_type eq 'found_item' and status ne 'released' and status ne 'disposed'",
                limit=limit,
                image_blob_url=report.proof_blob_url,
            )
            azure_items = self._materialize_found_items(db, results)
            rule_items = self._rule_recall_found_items(db, report, query_text, limit)
            return self._merge_candidates(azure_items, rule_items, limit)
        items = self._candidate_found_items(db)
        scored = [
            (item, self._local_score(query_text, self._found_text(item), report.proof_phash, item.image_phash))
            for item in items
        ]
        return sorted(scored, key=lambda pair: pair[1], reverse=True)[:limit]

    async def hybrid_search_lost_reports(self, db: Session, item: FoundItem, limit: int = 10) -> list[tuple[LostReport, float]]:
        query_text = self._found_text(item)
        if self._enabled():
            results = await self._azure_hybrid_search(
                query_text=query_text,
                filter_expression="source_type eq 'lost_report' and status ne 'resolved' and status ne 'rejected'",
                limit=limit,
                image_blob_url=item.image_blob_url,
            )
            azure_reports = self._materialize_lost_reports(db, results)
            rule_reports = self._rule_recall_lost_reports(db, item, query_text, limit)
            return self._merge_candidates(azure_reports, rule_reports, limit)
        reports = self._candidate_lost_reports(db)
        scored = [
            (report, self._local_score(query_text, self._lost_text(report), item.image_phash, report.proof_phash))
            for report in reports
        ]
        return sorted(scored, key=lambda pair: pair[1], reverse=True)[:limit]

    def _local_score(self, query_text: str, candidate_text: str, query_phash: str | None, candidate_phash: str | None) -> float:
        from app.services.image_similarity_service import image_similarity_service

        text_score = self._similarity(query_text, candidate_text)
        image_score = image_similarity_service.phash_similarity(query_phash, candidate_phash) if query_phash and candidate_phash else 0
        if image_score:
            return round(text_score * 0.7 + image_score * 0.3, 2)
        return text_score

    async def vector_search(self, documents: list[Any], query_text: str, limit: int = 10) -> list[tuple[Any, float]]:
        scored = [(doc, self._similarity(query_text, str(doc))) for doc in documents]
        return sorted(scored, key=lambda pair: pair[1], reverse=True)[:limit]

    async def _azure_hybrid_search(
        self,
        query_text: str,
        filter_expression: str,
        limit: int,
        image_blob_url: str | None = None,
    ) -> list[dict[str, Any]]:
        from azure.search.documents.models import VectorizedQuery

        from app.services.azure_openai_service import azure_openai_service
        from app.services.image_similarity_service import image_similarity_service

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
        vector_queries = [
            VectorizedQuery(
                vector=embedding,
                k_nearest_neighbors=max(limit, 10),
                fields="content_vector",
            )
        ]
        if image_blob_url:
            try:
                pair = await image_similarity_service.compute_image_vector(image_blob_url)
                if pair:
                    image_vector = pair[1]
                    if len(image_vector) == 1024:
                        vector_queries.append(
                            VectorizedQuery(
                                vector=image_vector,
                                k_nearest_neighbors=max(limit, 10),
                                fields="image_vector",
                            )
                        )
            except Exception:
                logger.exception("image vector query skipped", extra={"event": "search_image_vector_query_failed"})
        client = self._search_client()

        def run_search():
            return list(
                client.search(
                    search_text=query_text or "*",
                    vector_queries=vector_queries,
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

    def _rule_recall_found_items(self, db: Session, report: LostReport, query_text: str, limit: int) -> list[tuple[FoundItem, float]]:
        scored = [
            (item, self._rule_recall_score(query_text, self._found_text(item), report.category, item.category, report.color, item.color, report.lost_location, item.found_location))
            for item in self._candidate_found_items(db)
        ]
        return sorted(scored, key=lambda pair: pair[1], reverse=True)[: max(limit, 10)]

    def _rule_recall_lost_reports(self, db: Session, item: FoundItem, query_text: str, limit: int) -> list[tuple[LostReport, float]]:
        scored = [
            (report, self._rule_recall_score(query_text, self._lost_text(report), item.category, report.category, item.color, report.color, item.found_location, report.lost_location))
            for report in self._candidate_lost_reports(db)
        ]
        return sorted(scored, key=lambda pair: pair[1], reverse=True)[: max(limit, 10)]

    def _candidate_found_items(self, db: Session) -> list[FoundItem]:
        return (
            db.query(FoundItem)
            .filter(FoundItem.status.notin_([FoundItemStatus.released, FoundItemStatus.disposed]))
            .all()
        )

    def _candidate_lost_reports(self, db: Session) -> list[LostReport]:
        return (
            db.query(LostReport)
            .filter(LostReport.status.notin_([LostReportStatus.resolved, LostReportStatus.rejected]))
            .all()
        )

    def _merge_candidates(self, primary: list[tuple[Any, float]], recall: list[tuple[Any, float]], limit: int) -> list[tuple[Any, float]]:
        merged: dict[int, tuple[Any, float]] = {}
        for entity, score in [*primary, *recall]:
            entity_id = int(entity.id)
            current = merged.get(entity_id)
            if current is None or score > current[1]:
                merged[entity_id] = (entity, score)
        return sorted(merged.values(), key=lambda pair: pair[1], reverse=True)[:limit]

    def _rule_recall_score(
        self,
        query_text: str,
        candidate_text: str,
        query_category: str | None,
        candidate_category: str | None,
        query_color: str | None,
        candidate_color: str | None,
        query_location: str | None,
        candidate_location: str | None,
    ) -> float:
        score = self._similarity(query_text, candidate_text)
        if self._same(query_category, candidate_category):
            score += 12
        if self._same(query_color, candidate_color):
            score += 8
        if self._same(query_location, candidate_location):
            score += 12
        return round(min(score, 100), 2)

    async def _lost_report_document(self, report: LostReport) -> dict[str, Any]:
        from app.services.azure_openai_service import azure_openai_service
        from app.services.image_similarity_service import image_similarity_service

        content = mask_sensitive_text(self._lost_text(report)) or ""
        _, embedding = await azure_openai_service.generate_embedding(content)
        image_vector = await self._image_vector_for(report.proof_blob_url, image_similarity_service)
        return {
            "document_id": f"lost-{report.id}",
            "source_type": "lost_report",
            "source_id": report.id,
            "item_title": report.item_title,
            "category": report.category,
            "description": mask_sensitive_text(report.ai_clean_description or report.raw_description),
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
            "image_vector": image_vector,
        }

    async def _found_item_document(self, item: FoundItem) -> dict[str, Any]:
        from app.services.azure_openai_service import azure_openai_service
        from app.services.image_similarity_service import image_similarity_service

        content = mask_sensitive_text(self._found_text(item)) or ""
        _, embedding = await azure_openai_service.generate_embedding(content)
        image_vector = await self._image_vector_for(item.image_blob_url, image_similarity_service)
        return {
            "document_id": f"found-{item.id}",
            "source_type": "found_item",
            "source_id": item.id,
            "item_title": item.item_title,
            "category": item.category,
            "description": mask_sensitive_text(item.ai_clean_description or item.raw_description),
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
            "image_vector": image_vector,
        }

    async def _image_vector_for(self, blob_url: str | None, image_similarity_service: Any) -> list[float]:
        """Return the image vector or a zero-vector placeholder so Azure Search accepts the doc.

        The image_vector field is fixed at 1024 dimensions (Azure Vision multimodal output),
        independent of the text embedding dimension.
        """
        if blob_url:
            try:
                vector_pair = await image_similarity_service.compute_image_vector(blob_url)
                if vector_pair and len(vector_pair[1]) == 1024:
                    return vector_pair[1]
            except Exception:
                logger.exception("image vector failed during indexing", extra={"event": "search_image_vector_failed"})
        return [0.0] * 1024

    def _similarity(self, left: str, right: str) -> float:
        return round(SequenceMatcher(None, left.lower(), right.lower()).ratio() * 100, 2)

    def _same(self, left: str | None, right: str | None) -> bool:
        return bool(left and right and left.strip().lower() == right.strip().lower())

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
