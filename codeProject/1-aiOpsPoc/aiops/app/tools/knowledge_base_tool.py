"""Agent 查询 SOP 文档与结构化 CMDB 事实的统一 Tool。"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Callable

from langchain.tools import tool

logger = logging.getLogger("aiops.knowledge_base_tool")
VALID_TYPES = {"auto", "document", "asset"}


class KnowledgeBaseSearchService:
    def __init__(self, *, document_search: Callable, asset_search: Callable):
        self.document_search = document_search
        self.asset_search = asset_search

    def search(self, query: str, knowledge_type: str = "auto", resource_id: str = "",
               hostname: str = "", top_k: int = 5) -> dict:
        query, mode = str(query or "").strip(), str(knowledge_type or "auto").strip().lower()
        resource_id, hostname = str(resource_id or "").strip(), str(hostname or "").strip()
        if mode not in VALID_TYPES:
            return _error(mode, query, "invalid_knowledge_type", "knowledge_type 无效")
        try:
            limit = max(1, min(int(top_k), 10))
        except (TypeError, ValueError):
            return _error(mode, query, "invalid_top_k", "top_k 必须是 1 到 10 之间的整数")
        if mode in {"auto", "document"} and not query:
            return _error(mode, query, "query_required", "文档检索词不能为空")
        if mode == "asset" and not (resource_id or hostname):
            return _error(mode, query, "asset_identifier_required", "CMDB 查询需要 resource_id 或 hostname")

        evidence, warnings, requested, succeeded = {"assets": [], "documents": []}, [], 0, 0
        if mode == "asset" or (mode == "auto" and (resource_id or hostname)):
            requested += 1
            try:
                asset = self.asset_search(resource_id, hostname)
                if asset:
                    evidence["assets"].append(_asset_evidence(asset))
                succeeded += 1
            except Exception as exc:
                logger.warning("CMDB search failed: %s", exc)
                warnings.append("asset_search_unavailable")
        if mode in {"auto", "document"}:
            requested += 1
            try:
                evidence["documents"] = [_document_evidence(item) for item in self.document_search(query, limit)]
                succeeded += 1
            except Exception as exc:
                logger.warning("Document search failed: %s", exc)
                warnings.append("document_search_unavailable")
        return {"success": succeeded > 0 or requested == 0, "knowledge_type": mode, "query": query,
                "evidence": evidence, "warnings": warnings,
                **({"error_code": "knowledge_search_unavailable"} if requested and not succeeded else {})}


def _document_evidence(item: dict) -> dict:
    text = " ".join(str(item.get("text", "")).split())
    return {"evidence_type": "document", "source": str(item.get("source", "")),
            "chunk_index": int(item.get("chunk_index", 0) or 0),
            "score": float(item.get("score", 0) or 0),
            "text": text[:1199].rstrip() + "…" if len(text) > 1200 else text}


def _asset_evidence(item) -> dict:
    if hasattr(item, "model_dump"):
        item = item.model_dump()
    allowed = ("found", "match_type", "resource_name", "resource_type", "environment",
               "subscription", "source_sheet", "source_row")
    return {**{key: item.get(key) for key in allowed}, "evidence_type": "asset"}


def _error(mode: str, query: str, code: str, message: str) -> dict:
    return {"success": False, "knowledge_type": mode, "query": query, "error_code": code,
            "message": message, "evidence": {"assets": [], "documents": []}, "warnings": []}


def _default_document_search(query: str, top_k: int) -> list[dict]:
    from app.services.document_service import search_documents
    return search_documents(query, top_k=top_k, raise_on_error=True)


def _default_asset_search(resource_id: str, hostname: str):
    from app.tools.cmdb_tool import lookup_cmdb_record
    return lookup_cmdb_record(resource_id=resource_id, hostname=hostname)


@lru_cache(maxsize=1)
def _get_default_service() -> KnowledgeBaseSearchService:
    return KnowledgeBaseSearchService(document_search=_default_document_search,
                                      asset_search=_default_asset_search)


@tool
def search_knowledge_base(query: str, knowledge_type: str = "auto", resource_id: str = "",
                          hostname: str = "", top_k: int = 5) -> str:
    """查询运维文档和 CMDB。knowledge_type 支持 auto、document、asset。"""
    return json.dumps(_get_default_service().search(query, knowledge_type, resource_id, hostname, top_k),
                      ensure_ascii=False)
