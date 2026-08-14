"""有限告警分类库的本地语义复用判定流程。

分类结果仍按“告警类别 × 风险等级”有限保存，但复用时会基于
``classification_signature`` 计算相似度；只有达到配置阈值（默认 85%）的
候选才能复用。它不是历史实例库，不调用 LLM、CMDB、RAG 或 Agent。
历史实例由 historical_alert_service 单独保存。
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.core.attack_classifier import get_attack_type_summary

logger = logging.getLogger("aiops.alert_classification")

_RISK_ORDER = {"低": 0, "中": 1, "高": 2, "特高": 3, "未知": 1}
_RISK_CODE = {"低": "low", "中": "medium", "高": "high", "特高": "critical", "未知": "medium"}

# 这些字段是告警分类库的可审计特征签名。
# 告警名称、触发原因和请求内容最能刻画告警类型；主机和备注只用于细化，
# 因而权重较低，避免同一类告警因资产或人工备注不同而无法复用。
_SIGNATURE_WEIGHTS = {
    "alert_name": 30,
    "trigger_reason": 20,
    "search_terms": 15,
    "request_uri": 20,
    "action": 10,
    "hostname": 3,
    "operator_notes": 2,
}
_TOKEN_RE = re.compile(r"[a-z0-9_./:-]+|[\u4e00-\u9fff]+", re.IGNORECASE)


def build_classification_key(alert: Any) -> tuple[str, str, str]:
    """根据告警自身字段得到确定性分类键，不依赖 CMDB 或模型。

    当前类别来自已有攻击规则的主攻击类型；风险由输入风险等级（若有）或
    告警次数与攻击规则的最高等级决定。未来接入完整 70 类词典时，仅需替换此函数。
    """
    data = _to_dict(alert)
    results = data.get("results") or []
    first = results[0] if results else {}
    if hasattr(first, "model_dump"):
        first = first.model_dump()
    request_uri = str(first.get("properties_requestUri", "")) if isinstance(first, dict) else ""
    attack = get_attack_type_summary(request_uri)
    category = str((attack.get("types") or ["unknown"])[0] or "unknown")

    # 分类键必须在进入 Agent 之前得到，因此不能依赖 CMDB 环境风险。
    # 若上游已经带有等级则直接使用；否则仅用告警严重度、次数和攻击规则判定。
    supplied_risk = str(data.get("risk_level") or data.get("severity") or "").strip()
    count = _as_int(first.get("count", 0) if isinstance(first, dict) else 0)
    count_risk = "高" if count >= get_settings().RISK_COUNT_HIGH_THRESHOLD else (
        "中" if count >= get_settings().RISK_COUNT_MEDIUM_THRESHOLD else "低"
    )
    if supplied_risk not in _RISK_ORDER:
        supplied_risk = max((count_risk, str(attack.get("highest_risk", "低"))),
                            key=lambda value: _RISK_ORDER.get(value, 0))
    risk_code = _RISK_CODE.get(supplied_risk, "medium")
    return category, risk_code, f"{category}:{risk_code}"


class AlertClassificationRepository:
    """单文件、至多 280 条的分类库；命中需通过签名相似度阈值。"""

    def __init__(self, path: Path | None = None, max_records: int | None = None):
        settings = get_settings()
        self.path = Path(path or settings.alert_classification_store_path)
        self.max_records = max(1, int(max_records or settings.ALERT_CLASSIFICATION_MAX_RECORDS))
        self.match_threshold = max(0, min(100, int(settings.SEMANTIC_MATCH_THRESHOLD)))
        self.max_candidates = max(1, int(settings.ALERT_CLASSIFICATION_MAX_CANDIDATES))
        self.max_field_chars = max(1, int(settings.ALERT_CLASSIFICATION_MAX_FIELD_CHARS))

    def find(self, alert: Any) -> dict | None:
        if not get_settings().ALERT_CLASSIFICATION_ENABLED:
            return None
        signature = build_classification_signature(alert, self.max_field_chars)
        records = self._load()["records"]
        candidates: list[tuple[int, str, dict]] = []
        for key, record in records.items():
            if not str(record.get("report", "")).strip() or not str(record.get("suggestion", "")).strip():
                logger.warning("Classification record %s is incomplete and will not be reused", key)
                continue
            stored_signature = record.get("classification_signature")
            if not isinstance(stored_signature, dict):
                # 旧的固定键记录没有可比对的特征，不能错误地按 100% 复用。
                logger.info("Classification record %s has no signature; skip semantic reuse", key)
                continue
            score = calculate_signature_similarity(signature, stored_signature)
            candidates.append((score, key, record))

        # 固定上限与原配置 ALERT_CLASSIFICATION_MAX_CANDIDATES 保持一致，
        # 先取最高分候选再按阈值判断，确保不会因字典插入顺序影响结果。
        candidates.sort(key=lambda item: (-item[0], item[1]))
        candidates = candidates[:self.max_candidates]
        if not candidates:
            return None
        score, key, record = candidates[0]
        if score < self.match_threshold:
            logger.info("[CLASSIFICATION MISS] best key=%s score=%s threshold=%s", key, score, self.match_threshold)
            return None

        result = dict(record)
        result["key"] = key
        result["match_score"] = score
        self._record_hit(records, key)
        logger.info("[CLASSIFICATION HIT] key=%s score=%s threshold=%s", key, score, self.match_threshold)
        return result

    def upsert(
        self,
        alert: Any,
        *,
        report: str,
        suggestion: str,
        risk_level: str,
        risk_details: dict | None,
        evidence: dict | None = None,
    ) -> dict | None:
        if not (
            get_settings().ALERT_CLASSIFICATION_ENABLED
            and get_settings().ALERT_CLASSIFICATION_AUTO_ENROLL
            and report.strip()
            and suggestion.strip()
        ):
            return None
        category, routing_risk, key = build_classification_key(alert)
        payload = self._load()
        records = payload["records"]
        if key not in records and len(records) >= self.max_records:
            logger.warning("Classification library reached capacity=%s; skip new key=%s", self.max_records, key)
            return None
        timestamp = datetime.now().isoformat()
        record = {
            "key": key,
            "category": category,
            "routing_risk": routing_risk,
            "risk_level": risk_level,
            "risk_details": risk_details or {},
            "classification_signature": build_classification_signature(alert, self.max_field_chars),
            "report": report,
            "suggestion": suggestion,
            "source_alert_name": _to_dict(alert).get("alert_name", ""),
            "source_application_code": _to_dict(alert).get("application_code", ""),
            "created_at": records.get(key, {}).get("created_at", timestamp),
            "updated_at": timestamp,
            "evidence_summary": _compact_evidence(evidence),
        }
        records[key] = record
        self._save(payload)
        return record

    def stats(self) -> dict[str, int]:
        return {"records": len(self._load()["records"]), "max_records": self.max_records}

    def _load(self) -> dict:
        if not self.path.exists():
            return {"version": 1, "records": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            records = payload.get("records", {})
            return {"version": 1, "records": records if isinstance(records, dict) else {}}
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Unable to read classification store %s: %s", self.path, exc)
            return {"version": 1, "records": {}}

    def _save(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, self.path)
        finally:
            if temp.exists():
                temp.unlink(missing_ok=True)

    def _record_hit(self, records: dict, key: str) -> None:
        """记录复用次数；匹配分数仅属于本次实例，不写回分类模板。"""
        record = records.get(key)
        if not record:
            return
        record["hit_count"] = _as_int(record.get("hit_count")) + 1
        record["last_hit_at"] = datetime.now().isoformat()
        self._save({"version": 2, "records": records})


def _to_dict(alert: Any) -> dict:
    if hasattr(alert, "model_dump"):
        return alert.model_dump()
    return alert if isinstance(alert, dict) else {}


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_classification_signature(alert: Any, max_field_chars: int | None = None) -> dict[str, str]:
    """提取可审计的告警签名，兼容 RawAlert、字典和旧语义样本字段。"""
    data = _to_dict(alert)
    results = data.get("results") or []
    first = results[0] if results else {}
    if hasattr(first, "model_dump"):
        first = first.model_dump()
    first = first if isinstance(first, dict) else {}
    limit = max(1, int(max_field_chars or get_settings().ALERT_CLASSIFICATION_MAX_FIELD_CHARS))
    values = {
        "alert_name": data.get("alert_name", ""),
        "trigger_reason": data.get("trigger_reason", ""),
        "search_terms": data.get("search_terms", ""),
        "operator_notes": data.get("operator_notes", ""),
        "hostname": first.get("properties_hostname", data.get("hostname", "")),
        "request_uri": first.get("properties_requestUri", data.get("request_uri", "")),
        "action": first.get("properties_action", data.get("action", "")),
    }
    return {name: str(value or "")[:limit] for name, value in values.items()}


def calculate_signature_similarity(current: dict[str, Any], candidate: dict[str, Any]) -> int:
    """返回 0--100 的确定性告警特征相似度。

    每个非空字段使用字符序列相似度与 token Jaccard 的混合分数，再按字段
    权重加权。相同签名为 100；任一关键字段明显变化会拉低总分，低于 85
    必须进入 Agent 分支。该计算不依赖网络或模型，便于测试与审计。
    """
    weighted_score = 0.0
    total_weight = 0
    for field, weight in _SIGNATURE_WEIGHTS.items():
        left = _normalize_signature_value(current.get(field, ""))
        right = _normalize_signature_value(candidate.get(field, ""))
        if not left and not right:
            continue
        total_weight += weight
        if not left or not right:
            continue
        if left == right:
            field_score = 1.0
        else:
            sequence_score = SequenceMatcher(None, left, right, autojunk=False).ratio()
            left_tokens, right_tokens = set(_TOKEN_RE.findall(left)), set(_TOKEN_RE.findall(right))
            union = left_tokens | right_tokens
            token_score = len(left_tokens & right_tokens) / len(union) if union else sequence_score
            field_score = 0.65 * sequence_score + 0.35 * token_score
        weighted_score += weight * field_score
    return round(100 * weighted_score / total_weight) if total_weight else 0


def _normalize_signature_value(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _compact_evidence(evidence: dict | None) -> dict:
    if not evidence:
        return {}
    return {
        "history_result_count": len(evidence.get("historical", {}).get("results", [])),
        "document_count": len(evidence.get("knowledge", {}).get("evidence", {}).get("documents", [])),
        "asset_count": len(evidence.get("knowledge", {}).get("evidence", {}).get("assets", [])),
    }
