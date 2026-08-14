"""Milvus 中可重建的历史告警索引。"""

from __future__ import annotations

from typing import Callable, Iterable

from app.services.historical_alert_service import HistoricalAlertCase

SEARCH_FIELDS = [
    "case_id", "alert_name", "trigger_time", "hostname", "resource_id", "risk_level",
    "alert_summary", "analysis_summary", "suggestion_summary",
]


class HistoricalAlertIndex:
    def __init__(self, *, client=None, embedder: Callable | None = None,
                 collection: str = "historical_alerts", dimension: int = 1536):
        self._client = client
        self._embedder = embedder
        self.collection = collection
        self.dimension = dimension

    @property
    def client(self):
        if self._client is None:
            from app.core.milvus import get_client
            self._client = get_client()
        if self._client is None:
            raise RuntimeError("milvus_unavailable")
        return self._client

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if self._embedder is None:
            from app.core.embedding import embed
            self._embedder = embed
        return self._embedder(texts)

    def ensure_collection(self) -> None:
        if self.client.has_collection(self.collection):
            return
        self.client.create_collection(
            collection_name=self.collection, dimension=self.dimension,
            primary_field_name="case_id", id_type="string", metric_type="COSINE",
            auto_id=False, max_length=512, enable_dynamic_field=True,
        )

    def upsert(self, case: HistoricalAlertCase) -> str:
        self.ensure_collection()
        escaped = case.case_id.replace("\\", "\\\\").replace('"', '\\"')
        existing = self.client.query(self.collection, filter=f'case_id == "{escaped}"',
                                     output_fields=["case_id", "content_hash"], limit=1)
        if existing and existing[0].get("content_hash") == case.content_hash:
            return "unchanged"
        record = case.to_index_record()
        record["vector"] = self._embed([case.case_summary])[0]
        if hasattr(self.client, "upsert"):
            self.client.upsert(self.collection, data=[record])
        else:
            if existing:
                self.client.delete(self.collection, filter=f'case_id == "{escaped}"')
            self.client.insert(self.collection, data=[record])
        return "updated" if existing else "inserted"

    def rebuild(self, cases: Iterable[HistoricalAlertCase]) -> dict[str, int]:
        counts = {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 0}
        for case in cases:
            try:
                counts[self.upsert(case)] += 1
            except Exception:
                counts["errors"] += 1
        return counts

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        query = query.strip()
        if not query:
            raise ValueError("query_required")
        self.ensure_collection()
        batches = self.client.search(self.collection, data=[self._embed([query])[0]],
                                     limit=max(1, min(int(top_k), 10)), output_fields=SEARCH_FIELDS)
        results = []
        for hit in batches[0] if batches else []:
            entity = hit.get("entity", {})
            item = {field: entity.get(field, "") for field in SEARCH_FIELDS}
            item["similarity"] = float(hit.get("distance", 0.0))
            results.append(item)
        return results
