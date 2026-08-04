"""
告警处理服务 - 核心业务逻辑

流程:
1. 扫描告警目录，对比 processed_alerts.json 去重
2. 解析 JSON 提取关键字段
3. 调用 CMDB Tool 查询环境
4. 三维度风险判定
5. 生成分析报告 + 处理建议
6. 输出结果文件
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.schemas.alert import (
    RawAlert,
    AlertResult,
    EnrichedAlert,
    RiskDetails,
    AlertListItem,
    AlertDetail,
    TokenUsage,
    ProcessTokenUsage,
)
from app.schemas.cmdb import CmdbLookupResult
from app.core.risk_assessor import assess_risk
from app.tools.cmdb_tool import _lookup_by_resource_id, _lookup_by_hostname

logger = logging.getLogger("aiops.alert_service")


async def process_new_alerts() -> dict:
    """
    扫描告警目录，处理所有新告警

    Returns:
        {"new": N, "processed": N, "errors": N}
    """
    settings = get_settings()
    input_dir = settings.alert_input_path
    index_path = settings.processed_index_path

    # 加载已处理索引
    index = _load_index(index_path)

    # 扫描 JSON 文件
    json_files = sorted(input_dir.glob("*.json"))
    new_count = 0
    processed_count = 0
    error_count = 0

    for fpath in json_files:
        fname = fpath.name
        if fname in index.get("processed_files", {}):
            continue  # 已处理过，跳过

        try:
            result = await process_single_alert(fpath)
            if result:
                # 标记为已处理
                index.setdefault("processed_files", {})[fname] = {
                    "processed_at": datetime.now().isoformat(),
                    "risk_level": result.risk_level,
                    "output_dir": datetime.now().strftime("%Y-%m-%d"),
                }
                processed_count += 1
            else:
                error_count += 1
        except Exception as e:
            logger.error(f"[ALERT] Process failed [{fname}]: {e}", exc_info=True)
            error_count += 1

        new_count += 1

    # 更新索引
    index["last_scan_time"] = datetime.now().isoformat()
    _save_index(index_path, index)

    return {"new": new_count, "processed": processed_count, "errors": error_count}


async def process_single_alert(file_path: Path) -> Optional[EnrichedAlert]:
    """
    处理单个告警文件

    Args:
        file_path: 告警 JSON 文件路径

    Returns:
        EnrichedAlert 或 None
    """
    settings = get_settings()

    # 1. 解析告警 JSON
    raw_data = json.loads(file_path.read_text(encoding="utf-8"))
    alert = RawAlert(**raw_data)

    if not alert.results:
        logger.warning(f"[ALERT] No results: {file_path.name}")
        return None

    # 取第一个 result（通常只有一个）
    first_result = alert.results[0]
    resource_id = first_result.id
    hostname = first_result.properties_hostname
    request_uri = first_result.properties_requestUri
    count = first_result.count_int

    logger.info(f"[ALERT] Processing: {alert.alert_name} | id={resource_id} | hostname={hostname} | count={count}")

    # 2. CMDB 查询
    cmdb_result = _lookup_by_resource_id(resource_id)
    if not cmdb_result or not cmdb_result.found:
        cmdb_result = _lookup_by_hostname(hostname)
    if not cmdb_result:
        cmdb_result = CmdbLookupResult(
            found=False, match_type="none", environment=_infer_env_from_id(resource_id)
        )

    # 3. 三维度风险判定
    risk = assess_risk(
        environment=cmdb_result.environment,
        count=count,
        request_uri=request_uri,
    )

    # 4. 构造带风险等级的告警
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
    )

    # 5. 生成分析报告和处理建议（先于写输出，确保 token_usage 被写入）
    today_str = datetime.now().strftime("%Y-%m-%d")
    base_name = file_path.stem  # 如: alert_test-waf_20260713_144409
    await _generate_report_and_suggestion(enriched, cmdb_result, risk, today_str, base_name)

    # 6. 写入输出目录（此时 token_usage 已填充）
    output_dir = settings.alert_output_path / today_str
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_path.name
    output_path.write_text(
        json.dumps(enriched.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"[ALERT] Enriched output: {output_path}")

    return enriched


async def _generate_report_and_suggestion(
    alert: EnrichedAlert,
    cmdb: CmdbLookupResult,
    risk,
    date_str: str,
    base_name: str,
):
    """生成分析报告和处理建议"""
    from app.services.report_service import generate_analysis_report, generate_suggestion

    report_usage = TokenUsage()
    sug_usage = TokenUsage()

    try:
        # 生成分析报告
        report, report_usage = await generate_analysis_report(alert, cmdb, risk)
        settings = get_settings()
        report_dir = settings.reports_path / date_str
        report_dir.mkdir(parents=True, exist_ok=True)
        report_name = f"{base_name}_analysis.md"
        if report and report.strip():
            (report_dir / report_name).write_text(report, encoding="utf-8")
        else:
            logger.warning(f"[REPORT] Empty analysis report for {base_name}")

        # 生成处理建议
        suggestion, sug_usage = await generate_suggestion(alert, cmdb, risk)
        sug_dir = settings.suggestions_path / date_str
        sug_dir.mkdir(parents=True, exist_ok=True)
        sug_name = f"{base_name}_suggestion.md"
        if suggestion and suggestion.strip():
            (sug_dir / sug_name).write_text(suggestion, encoding="utf-8")
        else:
            logger.warning(f"[REPORT] Empty suggestion for {base_name}")

        logger.info(
            f"[REPORT] Generated: analysis={report_name} suggestion={sug_name} "
            f"tokens report={report_usage.total_tokens} sug={sug_usage.total_tokens}"
        )
    except Exception as e:
        logger.error(f"[REPORT] Generation failed: {e}", exc_info=True)

    # 将 token 用量写入 alert
    alert.token_usage = ProcessTokenUsage(
        analysis_report=report_usage,
        suggestion=sug_usage,
        total=TokenUsage(
            prompt_tokens=(report_usage.prompt_tokens + sug_usage.prompt_tokens),
            completion_tokens=(report_usage.completion_tokens + sug_usage.completion_tokens),
            total_tokens=(report_usage.total_tokens + sug_usage.total_tokens),
        ),
    )


def _infer_env_from_id(resource_id: str) -> str:
    """从 resource_id 名称推断环境"""
    if not resource_id:
        return "Unknown"
    upper = resource_id.upper()
    if "PRD" in upper or "PROD" in upper:
        return "Production"
    if "TST" in upper or "DEV" in upper:
        return "Non-Production"
    return "Unknown"


def _safe_timestamp() -> str:
    """生成安全的文件名时间戳"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ==========================================
# 索引文件管理
# ==========================================

def _load_index(path: Path) -> dict:
    """加载已处理告警索引"""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"processed_files": {}, "last_scan_time": None}


def _save_index(path: Path, index: dict):
    """保存已处理告警索引"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


# ==========================================
# 查询接口
# ==========================================

def get_alert_list(
    risk_filter: str = "all",
    search: str = "",
) -> list[AlertListItem]:
    """获取已处理的告警列表"""
    settings = get_settings()
    index = _load_index(settings.processed_index_path)
    items = []

    output_base = settings.alert_output_path
    for fname, info in index.get("processed_files", {}).items():
        # 尝试读取输出文件获取详细信息
        date_dir = info.get("output_dir", "")
        output_file = output_base / date_dir / fname
        hostname = ""
        alert_name = ""
        trigger_time = ""
        risk_level = info.get("risk_level", "?")

        if output_file.exists():
            try:
                data = json.loads(output_file.read_text(encoding="utf-8"))
                alert_name = data.get("alert_name", "")
                trigger_time = data.get("trigger_time", "")
                risk_level = data.get("risk_level", risk_level)
                results = data.get("results", [])
                if results:
                    hostname = results[0].get("properties_hostname", "")
            except Exception:
                pass

        if risk_filter != "all" and risk_level != risk_filter:
            continue
        if search:
            s = search.lower()
            if s not in hostname.lower() and s not in alert_name.lower():
                continue

        # 用文件名生成稳定 ID
        alert_id = fname.replace(".json", "").replace(" ", "_")
        items.append(AlertListItem(
            id=alert_id,
            alert_name=alert_name,
            hostname=hostname,
            trigger_time=trigger_time,
            risk_level=risk_level,
            processed_at=info.get("processed_at", ""),
        ))

    # 按处理时间倒序
    items.sort(key=lambda x: x.processed_at, reverse=True)
    return items


def get_alert_detail(alert_id: str) -> Optional[AlertDetail]:
    """获取单个告警详情"""
    settings = get_settings()
    index = _load_index(settings.processed_index_path)

    # 从索引中找到文件
    for fname, info in index.get("processed_files", {}).items():
        fid = fname.replace(".json", "").replace(" ", "_")
        if fid != alert_id:
            continue

        date_dir = info.get("output_dir", "")
        output_file = settings.alert_output_path / date_dir / fname

        alert_data = None
        if output_file.exists():
            try:
                alert_data = json.loads(output_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # 查找对应的报告和建议
        base_name = fname.replace(".json", "")
        analysis_report = _read_md_file(
            settings.reports_path / date_dir / f"{base_name}_analysis.md"
        )
        suggestion = _read_md_file(
            settings.suggestions_path / date_dir / f"{base_name}_suggestion.md"
        )

        return AlertDetail(
            alert=alert_data,
            risk_details=alert_data.get("risk_details") if alert_data else None,
            analysis_report=analysis_report,
            suggestion=suggestion,
            token_usage=alert_data.get("token_usage") if alert_data else None,
        )

    return None


def _read_md_file(path: Path) -> Optional[str]:
    """读取 Markdown 文件内容"""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None
