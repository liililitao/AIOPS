"""告警处理服务。

确定性顶层 Graph 先比对有限告警分类库；语义命中后复用报告与建议并重新计算
本次风险；未命中才进入 Tool-calling Agent 子图，由模型按需选择历史告警、
知识库/CMDB 与受控 Splunk 日志能力，再生成报告与建议并保存 Agent 运行记录。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.agents.alert_processing_graph import create_alert_processing_graph
from app.config import get_settings
from app.core.llm import call_llm_with_retry, get_router_llm
from app.core.risk_assessor import assess_risk
from app.schemas.alert import (
    AlertDetail, AlertListItem, EnrichedAlert, ProcessTokenUsage, RawAlert,
    RiskDetails, TokenUsage,
)
from app.schemas.cmdb import CmdbLookupResult
from app.services.alert_classification_service import (
    AlertClassificationRepository, build_classification_key, build_classification_signature,
)
from app.services.historical_alert_service import (
    HistoricalCaseRepository, archive_raw_alert, best_effort_index_case,
)
from app.services.splunk_alert_service import (
    get_cached_remote_alert_detail, get_cached_remote_alerts,
)

logger = logging.getLogger("aiops.alert_service")


def _load_semantic_candidates(alert: RawAlert, current_risk_level: str) -> list[dict]:
    """载入同一应用、同一告警名称、同一风险等级的分类结果。

    告警名称、应用代码和风险等级是复用的硬性条件，不能交给模型用“语义相近”
    来猜测。Router 只负责在同一告警定义的候选之间判定细节是否足够相似。
    """
    settings = get_settings()
    candidates: list[dict] = []
    # 旧固定键记录没有 signature，不能参与匹配，避免误复用。
    for key, record in AlertClassificationRepository()._load().get("records", {}).items():
        signature = record.get("classification_signature")
        report, suggestion = str(record.get("report") or ""), str(record.get("suggestion") or "")
        if not (isinstance(signature, dict) and report.strip() and suggestion.strip()):
            continue
        candidate_name = str(record.get("source_alert_name") or signature.get("alert_name") or "")
        candidate_app = str(record.get("source_application_code") or "")
        # application_code、告警名称和风险等级均为硬性边界。旧记录若缺少应用
        # 标识，宁可不复用、重新走 Agent，也绝不能跨应用误复用。
        if candidate_name != alert.alert_name:
            continue
        if not candidate_app or candidate_app != alert.application_code:
            continue
        if str(record.get("risk_level") or "") != current_risk_level:
            continue
        candidates.append({
            "sample_id": str(key), "signature": signature, "report": report,
            "suggestion": suggestion, "source": "classification_library",
            "display_name": candidate_name,
            "application_code": candidate_app,
        })

    # 同一个 ID 只保留一个候选，再受配置上限约束。
    unique: dict[str, dict] = {}
    for item in candidates:
        unique.setdefault(item["sample_id"], item)
    return list(unique.values())[:max(1, settings.ALERT_CLASSIFICATION_MAX_CANDIDATES)]


def _signature_block(signature: dict) -> str:
    fields = ("alert_name", "trigger_reason", "search_terms", "operator_notes", "hostname", "request_uri", "action")
    limit = max(1, get_settings().ALERT_CLASSIFICATION_MAX_FIELD_CHARS)
    return "\n".join(f"{field}:{str(signature.get(field, '') or '')[:limit]}" for field in fields)


async def _llm_semantic_match(alert: RawAlert, candidates: list[dict]) -> tuple[dict | None, int | None, TokenUsage]:
    """调用同事提供的 Router LLM 语义匹配协议。

    模型只能返回 ``sample_id:ID,score:XX`` 或 ``no_match``。任何异常、格式
    不合法或低于阈值都安全降级为未命中，并继续 Agent 全流程。
    """
    usage = TokenUsage()
    if not candidates:
        return None, None, usage
    threshold = get_settings().SEMANTIC_MATCH_THRESHOLD
    sample_blocks = [
        f"[sample_id:{item['sample_id']}]\n{_signature_block(item['signature'])}"
        for item in candidates
    ]
    candidates_text = "\n\n".join(sample_blocks)
    prompt = f"""
你是告警语义匹配器。对比【新告警】与【告警分类库候选】，判断业务语义是否属于同一种告警事件。

规则：
1. 不要解释、不要分析理由，只能输出指定格式。
2. 候选已经保证是同一应用、同一告警名称、同一风险等级。若存在匹配得分大于等于 {threshold} 的候选，严格输出：sample_id:SAMPLE_ID,score:XX。
3. 若有多个候选达到阈值，必须返回得分最高的一个。
4. 若没有达到阈值的候选，严格输出：no_match。
5. score 必须是 0 到 100 的整数。

-----告警分类库候选-----
{candidates_text}
-----新告警-----
{_signature_block(build_classification_signature(alert))}
""".strip()
    try:
        text, message = await call_llm_with_retry(
            get_router_llm(),
            [{"role": "system", "content": prompt}, {"role": "user", "content": "执行告警语义匹配并严格按格式输出。"}],
            max_retries=2, base_delay=1, timeout=40,
        )
        metadata = getattr(message, "usage_metadata", {}) or {}
        usage.prompt_tokens = int(metadata.get("input_tokens", 0) or 0)
        usage.completion_tokens = int(metadata.get("output_tokens", 0) or 0)
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        normalized = str(text or "").strip()
        logger.info("[SEMANTIC-MATCH] Router output: %r", normalized)
        if normalized.lower().startswith("no_match"):
            return None, None, usage
        match = re.fullmatch(r"\s*sample_id\s*:\s*([^,\s]+)\s*,\s*score\s*:\s*(\d{1,3})\s*", normalized, re.I)
        if not match:
            logger.warning("[SEMANTIC-MATCH] Invalid Router response; fallback to Agent")
            return None, None, usage
        sample_id, score = match.group(1), int(match.group(2))
        candidate = next((item for item in candidates if item["sample_id"] == sample_id), None)
        if candidate is None or not 0 <= score <= 100 or score < threshold:
            logger.info("[SEMANTIC-MATCH] No usable match sample=%s score=%s threshold=%s", sample_id, score, threshold)
            return None, None, usage
        logger.info("[SEMANTIC-MATCH HIT] sample=%s score=%s", sample_id, score)
        return candidate, score, usage
    except Exception as exc:
        logger.warning("[SEMANTIC-MATCH] Router unavailable; fallback to Agent: %s", exc)
        return None, None, usage


async def process_new_alerts() -> dict:
    """扫描并处理未登记的本地输入告警。"""
    settings = get_settings()
    index = _load_index(settings.processed_index_path)
    counts = {"new": 0, "processed": 0, "errors": 0}
    for path in sorted(settings.alert_input_path.glob("*.json")):
        if path.name in index.get("processed_files", {}):
            continue
        counts["new"] += 1
        try:
            result = await process_single_alert(path)
            if not result:
                counts["errors"] += 1
                continue
            index.setdefault("processed_files", {})[path.name] = {
                "processed_at": datetime.now().isoformat(),
                "risk_level": result.risk_level,
                "output_dir": datetime.now().strftime("%Y-%m-%d"),
            }
            counts["processed"] += 1
        except Exception as exc:
            logger.exception("[ALERT] Process failed %s: %s", path.name, exc)
            counts["errors"] += 1
    index["last_scan_time"] = datetime.now().isoformat()
    _save_index(settings.processed_index_path, index)
    return counts


async def process_single_alert(
    file_path: Path,
    classification_alert_id: Optional[str] = None,
    *,
    force_new_agent_run: bool = False,
) -> Optional[EnrichedAlert]:
    """处理一条告警。

    首先由 Router 模型进行语义匹配；模型评分达到阈值时复用结果，且不会
    调用 Agent Tool 或报告/建议模型。否则才进入 Tool-calling Agent 子图。
    """
    settings = get_settings()
    file_path = Path(file_path)
    raw_data = json.loads(file_path.read_text(encoding="utf-8-sig"))
    alert = RawAlert(**raw_data)
    if not alert.results:
        logger.warning("[ALERT] No results: %s", file_path.name)
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    base_name = file_path.stem
    business_alert_id = classification_alert_id or f"{today}/{base_name}"
    formal_output_exists = force_new_agent_run or (
        settings.alert_output_path / today / file_path.name
    ).is_file()
    # 应用模拟资源的环境可本地确定；先计算本次风险，用它限制分类库候选，
    # 避免高风险模板被用于本次低风险告警，反之亦然。
    first = alert.results[0]
    preliminary_risk = assess_risk(
        environment=_infer_env(first.id, first.properties_hostname),
        count=first.count_int,
        request_uri=first.properties_requestUri,
    )
    async def classify_node(state):
        candidate, score, usage = await _llm_semantic_match(
            alert,
            _load_semantic_candidates(
                alert,
                preliminary_risk.overall_risk,
            ),
        )
        return {
            "classification_status": "hit" if candidate else "miss",
            "classification_result": candidate,
            "classification_score": score,
            "match_usage": usage,
        }

    async def reuse_node(state):
        semantic_candidate = state["classification_result"]
        semantic_score = state.get("classification_score")
        match_usage = state.get("match_usage") or TokenUsage()
        # 命中时不调用 Agent Tool。风险判定仍按当前告警重算，但只使用本地可判断
        # 的环境规则，避免在“分类已可用”分支额外触发 Agent/CMDB 查询。
        enriched = _build_semantic_reused_alert(
            raw_data, semantic_candidate, int(semantic_score or 0), preliminary_risk, match_usage,
        )
        _write_report_and_suggestion(today, base_name, semantic_candidate["report"], semantic_candidate["suggestion"])
        _write_enriched_alert(today, file_path.name, enriched)
        _archive_and_index_history(file_path, today, base_name)
        return {"result": enriched}

    async def analyze_node(state):
        # 分类未命中后才进入 Agent；模型按告警内容选择已注册 Tool。
        logger.info("[CLASSIFICATION MISS] Enter Agent for %s", alert.alert_name)
        from app.agents import AlertAnalysisAgent
        from app.agents.alert_analysis_agent import resolve_agent_run_id
        from app.services.agent_run_registry import AgentRunRegistry

        run_registry = None
        if settings.AGENT_CHECKPOINT_ENABLED:
            run_registry = AgentRunRegistry(settings.agent_checkpoint_db_path)
            agent_run_id = await run_registry.acquire(
                alert,
                alert_id=business_alert_id,
                formal_output_exists=formal_output_exists,
            )
        else:
            agent_run_id = resolve_agent_run_id(
                alert,
                alert_id=business_alert_id,
                formal_output_exists=formal_output_exists,
            )

        agent_result = await AlertAnalysisAgent().analyze(
            alert,
            alert_id=business_alert_id,
            run_id=agent_run_id,
        )
        evidence = agent_result.evidence
        cmdb = _cmdb_from_agent_evidence(evidence, alert)
        first = alert.results[0]
        risk = assess_risk(
            environment=cmdb.environment,
            count=first.count_int,
            request_uri=first.properties_requestUri,
        )
        enriched = EnrichedAlert(
            **raw_data,
            risk_level=risk.overall_risk,
            risk_details=RiskDetails(
                environment_risk=risk.environment_risk,
                environment=risk.environment,
                count_risk=risk.count_risk,
                count_value=risk.count_value,
                attack_type_risk=risk.attack_type_risk,
                attack_types=risk.attack_types,
                overall_risk=risk.overall_risk,
                assessed_at=risk.assessed_at,
            ),
            from_sample=False,
            agent_run_id=agent_result.run_id,
            agent_analysis=agent_result.analysis_result,
        )
        evidence_context = _format_agent_evidence(
            evidence,
            investigation_plan=agent_result.investigation_plan,
            agent_analysis=agent_result.analysis_result,
        )
        report, suggestion = await _generate_report_and_suggestion(
            enriched,
            cmdb,
            risk,
            today,
            base_name,
            evidence_context,
        )
        AlertClassificationRepository().upsert(
            enriched,
            report=report,
            suggestion=suggestion,
            risk_level=risk.overall_risk,
            risk_details=(
                enriched.risk_details.model_dump()
                if enriched.risk_details
                else {}
            ),
            evidence=evidence,
        )
        match_usage = state.get("match_usage") or TokenUsage()
        _add_token_usage(enriched, match_usage)
        _add_token_usage(enriched, agent_result.token_usage)
        if enriched.token_usage:
            enriched.token_usage.agent_planning = (
                agent_result.planning_token_usage
            )
            enriched.token_usage.agent_analysis = (
                agent_result.execution_token_usage
            )
        _write_enriched_alert(today, file_path.name, enriched)
        _write_agent_run(today, base_name, alert, agent_result)
        _archive_and_index_history(file_path, today, base_name)
        if run_registry is not None:
            await run_registry.mark_completed(business_alert_id, agent_run_id)
        return {"result": enriched}

    graph = create_alert_processing_graph(
        classify=classify_node,
        reuse=reuse_node,
        analyze=analyze_node,
    )
    graph_result = await graph.ainvoke({
        "alert_id": classification_alert_id or f"{today}/{base_name}",
        "alert": alert.model_dump(),
        "classification_status": "pending",
    })
    return graph_result["result"]


def _build_semantic_reused_alert(
    raw_data: dict, candidate: dict, score: int, risk, match_usage: TokenUsage,
) -> EnrichedAlert:
    """语义命中后复用报告建议，同时按本次告警重新计算本地风险。"""
    return EnrichedAlert(
        **raw_data,
        risk_level=risk.overall_risk,
        risk_details=RiskDetails(
            environment_risk=risk.environment_risk,
            environment=risk.environment,
            count_risk=risk.count_risk,
            count_value=risk.count_value,
            attack_type_risk=risk.attack_type_risk,
            attack_types=risk.attack_types,
            overall_risk=risk.overall_risk,
            assessed_at=risk.assessed_at,
        ),
        token_usage=ProcessTokenUsage(
            analysis_report=TokenUsage(), suggestion=TokenUsage(), total=match_usage,
        ),
        from_sample=True,
        # 页面展示业务可读的告警名称，不暴露 random_scan:high 等内部分类键。
        match_sample_id=str(candidate.get("display_name") or candidate.get("sample_id", "")),
        match_score=score,
    )


def _add_token_usage(alert: EnrichedAlert, extra: TokenUsage) -> None:
    """未命中时，语义匹配的 Router token 与报告/建议 token 一并保存。"""
    if not alert.token_usage:
        alert.token_usage = ProcessTokenUsage(total=TokenUsage())
    total = alert.token_usage.total
    total.prompt_tokens += extra.prompt_tokens
    total.completion_tokens += extra.completion_tokens
    total.total_tokens += extra.total_tokens


def _cmdb_from_agent_evidence(evidence: dict, alert: RawAlert) -> CmdbLookupResult:
    first = alert.results[0]
    # 模拟标识优先于 Tool 的占位未命中结果，避免 found=false/Unknown 覆盖规则。
    if _is_simulation_asset(first.id, first.properties_hostname):
        return CmdbLookupResult(found=False, match_type="simulation", environment="Non-Production")
    assets = evidence.get("knowledge", {}).get("evidence", {}).get("assets", [])
    if assets:
        asset = {key: value for key, value in assets[0].items() if key != "evidence_type"}
        return CmdbLookupResult(**asset)
    environment = _infer_env(first.id, first.properties_hostname)
    return CmdbLookupResult(
        found=False,
        match_type="simulation" if environment == "Non-Production" and _is_simulation_asset(first.id, first.properties_hostname) else "none",
        environment=environment,
    )


def _format_agent_evidence(
    evidence: dict, *, investigation_plan: str = "", agent_analysis: str = "",
) -> str:
    """把 Agent 已取得的压缩证据整理为报告模型可消费的有限上下文。"""
    history = evidence.get("historical", {})
    knowledge = evidence.get("knowledge", {})
    splunk = evidence.get("splunk", {})
    blocks = []
    if investigation_plan:
        blocks.append("【Agent 调查计划】\n" + investigation_plan)
    if agent_analysis:
        blocks.append("【Agent 证据研判】\n" + agent_analysis)
    for result in history.get("results", []):
        blocks.append(
            "【历史相似告警】\n"
            f"案例: {result.get('case_id', '')}\n"
            f"告警: {result.get('alert_summary', '')}\n"
            f"历史分析: {result.get('analysis_summary', '')}\n"
            f"历史建议: {result.get('suggestion_summary', '')}"
        )
    for asset in knowledge.get("evidence", {}).get("assets", []):
        blocks.append("【CMDB 资产事实】\n" + json.dumps(asset, ensure_ascii=False))
    for document in knowledge.get("evidence", {}).get("documents", []):
        blocks.append(
            f"【SOP/知识库：{document.get('source', '未知来源')}】\n{document.get('text', '')}"
        )
    if history.get("error_code"):
        blocks.append("【历史告警检索状态】历史检索暂不可用，不能据此推断不存在历史案例。")
    if knowledge.get("warnings"):
        blocks.append("【知识库检索状态】" + "、".join(knowledge["warnings"]))
    if splunk.get("success"):
        for item in splunk.get("evidence", []):
            blocks.append("【Splunk 日志调查：%s】\n%s" % (
                item.get("investigation", "未知"),
                json.dumps(item.get("summary", {}), ensure_ascii=False),
            ))
    elif splunk.get("error_code"):
        blocks.append("【Splunk 日志调查状态】本次受控 Splunk Tool 已调用，但未返回可用证据：%s。" % splunk["error_code"])
    context = "\n\n".join(blocks)
    return context[:max(1, get_settings().AGENT_EVIDENCE_MAX_CONTEXT_CHARS)]


async def _generate_report_and_suggestion(
    alert: EnrichedAlert, cmdb: CmdbLookupResult, risk, date_str: str, base_name: str,
    rag_context: str = "",
) -> tuple[str, str]:
    """唯一可能调用 LLM 的阶段，只在分类未命中后执行。"""
    from app.services.report_service import generate_analysis_report, generate_suggestion

    report_usage, suggestion_usage = TokenUsage(), TokenUsage()
    report, suggestion = "", ""
    try:
        report, report_usage = await generate_analysis_report(alert, cmdb, risk, rag_context=rag_context)
        suggestion, suggestion_usage = await generate_suggestion(alert, cmdb, risk, rag_context=rag_context)
        _write_report_and_suggestion(date_str, base_name, report, suggestion)
    except Exception as exc:
        logger.exception("[AGENT] Report generation failed: %s", exc)
    alert.token_usage = ProcessTokenUsage(
        analysis_report=report_usage,
        suggestion=suggestion_usage,
        total=TokenUsage(
            prompt_tokens=report_usage.prompt_tokens + suggestion_usage.prompt_tokens,
            completion_tokens=report_usage.completion_tokens + suggestion_usage.completion_tokens,
            total_tokens=report_usage.total_tokens + suggestion_usage.total_tokens,
        ),
    )
    return report, suggestion


def _write_report_and_suggestion(date_str: str, base_name: str, report: str, suggestion: str) -> None:
    settings = get_settings()
    report_path = settings.reports_path / date_str / f"{base_name}_analysis.md"
    suggestion_path = settings.suggestions_path / date_str / f"{base_name}_suggestion.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    suggestion_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report or "", encoding="utf-8")
    suggestion_path.write_text(suggestion or "", encoding="utf-8")


def _write_enriched_alert(date_str: str, filename: str, alert: EnrichedAlert) -> None:
    settings = get_settings()
    payload = json.dumps(alert.model_dump(), ensure_ascii=False, indent=2)
    # 保留此前前端依赖的输出位置，同时写规范历史告警归档。
    for target in (
        settings.alert_output_path / date_str / filename,
        settings.historical_enriched_alert_path / date_str / filename,
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")


def _write_agent_run(date_str: str, base_name: str, alert: RawAlert, result) -> None:
    """持久化分类未命中时的 Tool 调用轨迹和 Agent 研判，便于验证完整流程。"""
    settings = get_settings()
    path = settings.agent_runs_path / date_str / f"{base_name}_agent_run.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": result.run_id,
        "thread_id": result.thread_id,
        "status": result.status,
        "started_at": result.started_at,
        "completed_at": result.completed_at,
        "alert": {"alert_name": alert.alert_name, "application_code": alert.application_code},
        "steps": result.steps,
        "investigation_plan": result.investigation_plan,
        "analysis_result": result.analysis_result,
        "analysis": (
            result.analysis.model_dump(mode="json")
            if result.analysis is not None
            else None
        ),
        "degraded_reasons": result.degraded_reasons,
        "validation_repair_count": result.validation_repair_count,
        "evidence": result.evidence,
        "token_usage": {
            "agent_planning": result.planning_token_usage.model_dump(),
            "agent_analysis": result.execution_token_usage.model_dump(),
            "total": result.token_usage.model_dump(),
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _archive_and_index_history(file_path: Path, date_str: str, stem: str) -> None:
    settings = get_settings()
    try:
        archive_raw_alert(file_path, settings.raw_alert_path)
    except FileExistsError as exc:
        # 输出已经完成，归档冲突只记录，避免破坏现有处理结果。
        logger.warning("[HISTORY] Raw archive conflict: %s", exc)
        return
    if not (settings.HISTORICAL_ALERT_INDEX_ENABLED and settings.MILVUS_ENABLED):
        return
    from app.services.historical_alert_index import HistoricalAlertIndex
    best_effort_index_case(
        date_str, stem,
        HistoricalCaseRepository(settings.project_root),
        HistoricalAlertIndex(collection=settings.HISTORICAL_ALERT_COLLECTION,
                             dimension=settings.embedding_dimension),
        settings.project_root / "data" / "historical_alert_index_failures.json",
    )


def sync_existing_alerts_to_classification() -> dict[str, int]:
    """仅将已有的应用告警回填到分类库，重复键保留最新结果。

    WAF/Splunk 历史文件不得作为应用告警分类库候选，避免服务重启时把已
    清理的 WAF 分类重新写回。
    """
    settings = get_settings()
    repository = AlertClassificationRepository()
    created, updated, skipped = 0, 0, 0
    paths = list(settings.application_enriched_alert_path.glob("*/*.json"))
    for path in sorted({path.resolve() for path in paths}):
        date, stem = path.parent.name, path.stem
        report_path = settings.reports_path / date / f"{stem}_analysis.md"
        suggestion_path = settings.suggestions_path / date / f"{stem}_suggestion.md"
        if not report_path.exists() or not suggestion_path.exists():
            skipped += 1
            continue
        try:
            alert = EnrichedAlert(**json.loads(path.read_text(encoding="utf-8")))
            # 分类库的复用判断由 Router 模型完成；这里仅判断本地键是否已存在，
            # 用于回填统计，绝不能触发旧的本地字符串相似度匹配。
            key = build_classification_key(alert)[2]
            before = repository._load()["records"].get(key)
            record = repository.upsert(
                alert,
                report=report_path.read_text(encoding="utf-8"),
                suggestion=suggestion_path.read_text(encoding="utf-8"),
                risk_level=alert.risk_level,
                risk_details=alert.risk_details.model_dump() if alert.risk_details else {},
            )
            if not record:
                skipped += 1
            elif before:
                updated += 1
            else:
                created += 1
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("[CLASSIFICATION] Backfill skip %s: %s", path, exc)
            skipped += 1
    return {"created": created, "updated": updated, "skipped": skipped}


async def process_remote_alert(alert_id: str) -> Optional[EnrichedAlert]:
    remote_alert = get_cached_remote_alert_detail(alert_id)
    if not remote_alert:
        return None
    settings = get_settings()
    raw_data = {field: remote_alert.get(field) for field in RawAlert.model_fields if field in remote_alert}
    filename = f"remote_{hashlib.sha256(alert_id.encode()).hexdigest()[:16]}.json"
    input_path = settings.alert_input_path / filename
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8")
    index = _load_index(settings.processed_index_path)
    formal_output_exists = any(
        info.get("source_alert_id") == alert_id
        for info in index.get("processed_files", {}).values()
    )
    result = await process_single_alert(
        input_path,
        classification_alert_id=alert_id,
        force_new_agent_run=formal_output_exists,
    )
    if result:
        index = _load_index(settings.processed_index_path)
        index.setdefault("processed_files", {})[filename] = {
            "processed_at": datetime.now().isoformat(), "risk_level": result.risk_level,
            "output_dir": datetime.now().strftime("%Y-%m-%d"), "source": "splunk",
            "source_alert_id": alert_id,
        }
        _save_index(settings.processed_index_path, index)
    return result


def _is_simulation_asset(resource_id: str, hostname: str = "") -> bool:
    """模拟应用告警不依赖 CMDB，明确视作非生产环境。"""
    return str(resource_id or "").upper().endswith("-APP-SIM") or str(hostname or "").lower().endswith(".simulated.local")


def _is_stale_simulation_classification(alert: RawAlert, classification: dict) -> bool:
    """模拟资源必须使用非生产环境的分类结果，旧 Unknown 结果自动失效。"""
    first = alert.results[0] if alert.results else None
    if not first or not _is_simulation_asset(first.id, first.properties_hostname):
        return False
    details = classification.get("risk_details") or {}
    return details.get("environment") != "Non-Production"


def _infer_env(resource_id: str, hostname: str = "") -> str:
    if _is_simulation_asset(resource_id, hostname):
        return "Non-Production"
    upper = str(resource_id or "").upper()
    if "PRD" in upper or "PROD" in upper:
        return "Production"
    if "TST" in upper or "DEV" in upper:
        return "Non-Production"
    return "Unknown"


def _infer_env_from_id(resource_id: str) -> str:
    """兼容既有调用；新代码应同时提供 hostname。"""
    return _infer_env(resource_id)


def _load_index(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"processed_files": {}}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"processed_files": {}}


def _save_index(path: Path, index: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_frontend_alert_list_snapshot(items: list[AlertListItem]) -> None:
    settings = get_settings()
    target = settings.alert_input_path / "前端同步告警" / "前端告警列表快照.json"
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps({"source": "aiops_frontend_alert_list",
            "updated_at": datetime.now().isoformat(), "total": len(items),
            "alerts": [item.model_dump() for item in items]}, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def get_alert_list(risk_filter: str = "all", search: str = "") -> list[AlertListItem]:
    settings, index = get_settings(), _load_index(get_settings().processed_index_path)
    items = []
    for filename, info in index.get("processed_files", {}).items():
        # 当前页面仅展示应用告警。历史 WAF/Splunk 记录仍保留在本地，便于将来恢复。
        if info.get("source") != "application_simulator":
            continue
        # 模拟应用告警必须完成 AI 风险判定、报告和建议后才允许展示。
        if info.get("analysis_status") != "completed":
            continue
        if info.get("analysis_status") == "completed":
            date = str(info.get("enriched_dir") or info.get("raw_dir", ""))
            path = settings.application_enriched_alert_path / date / filename
        else:
            path = _application_raw_alert_path(settings, info, filename)
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        results = data.get("results") or [{}]
        item = AlertListItem(id=filename.removesuffix(".json").replace(" ", "_"),
            alert_name=data.get("alert_name", ""), hostname=results[0].get("properties_hostname", ""),
            trigger_time=data.get("trigger_time", ""), risk_level=data.get("risk_level", info.get("risk_level", "?")),
            processed_at=info.get("processed_at", ""), application_code=data.get("application_code", ""))
        if _matches_list_filter(item, risk_filter, search):
            items.append(item)
    items.sort(key=lambda item: item.processed_at, reverse=True)
    _save_frontend_alert_list_snapshot(items)
    return items


def _matches_list_filter(item: AlertListItem, risk_filter: str, search: str) -> bool:
    if risk_filter != "all" and item.risk_level != risk_filter:
        return False
    query = search.lower()
    return not query or query in item.hostname.lower() or query in item.alert_name.lower()


def get_alert_detail(alert_id: str) -> Optional[AlertDetail]:
    remote = get_cached_remote_alert_detail(alert_id)
    index = _load_index(get_settings().processed_index_path)
    if remote:
        for filename, info in index.get("processed_files", {}).items():
            if info.get("source_alert_id") == alert_id:
                return _build_processed_alert_detail(filename, info)
        return AlertDetail(alert=remote, risk_details=remote.get("risk_details"),
            analysis_report="此告警直接从 Splunk 同步；尚未生成本地 AI 分析报告。",
            suggestion="请根据告警详情和 Splunk 溯源链接进行初步处置。")
    for filename, info in index.get("processed_files", {}).items():
        if filename.removesuffix(".json").replace(" ", "_") == alert_id:
            if info.get("source") == "application_simulator":
                return _build_application_alert_detail(filename, info)
            return _build_processed_alert_detail(filename, info)
    return None


def _build_processed_alert_detail(filename: str, info: dict) -> AlertDetail:
    settings = get_settings()
    date = str(info.get("output_dir", ""))
    path = settings.alert_output_path / date / filename
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        data = None
    base = filename.removesuffix(".json")
    return AlertDetail(alert=data, risk_details=data.get("risk_details") if data else None,
        analysis_report=_read_md_file(settings.reports_path / date / f"{base}_analysis.md"),
        suggestion=_read_md_file(settings.suggestions_path / date / f"{base}_suggestion.md"),
        token_usage=data.get("token_usage") if data else None,
        from_sample=data.get("from_sample") if data else None,
        match_sample_id=data.get("match_sample_id") if data else None,
        match_score=data.get("match_score") if data else None)


def _build_application_alert_detail(filename: str, info: dict) -> AlertDetail:
    """待分析时读取 data 原始告警；AI 完成后读取 output 的独立增强结果。"""
    settings = get_settings()
    date = str(info.get("raw_dir") or info.get("output_dir", ""))
    if info.get("analysis_status") == "completed":
        path = settings.application_enriched_alert_path / str(info.get("enriched_dir", date)) / filename
    else:
        path = _application_raw_alert_path(settings, info, filename)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        data = None
    base = filename.removesuffix(".json")
    return AlertDetail(
        alert=data, risk_details=data.get("risk_details") if data else None,
        analysis_report=_read_md_file(settings.reports_path / date / f"{base}_analysis.md"),
        suggestion=_read_md_file(settings.suggestions_path / date / f"{base}_suggestion.md"),
        token_usage=data.get("token_usage") if data else None,
        from_sample=data.get("from_sample") if data else None,
        match_sample_id=data.get("match_sample_id") if data else None,
        match_score=data.get("match_score") if data else None,
    )


def _application_raw_alert_path(settings, info: dict, filename: str) -> Path:
    """兼容路径迁移前误写入旧增强目录的模拟原始告警。"""
    date = str(info.get("raw_dir") or info.get("output_dir", ""))
    preferred = settings.application_alert_path / date / filename
    if preferred.exists() or "raw_dir" in info:
        return preferred
    return settings.alert_output_path / date / filename


def _read_md_file(path: Path) -> Optional[str]:
    return path.read_text(encoding="utf-8") if path.exists() else None
