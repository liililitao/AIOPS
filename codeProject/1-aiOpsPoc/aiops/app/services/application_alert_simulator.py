"""模拟应用日志并把对应应用告警写入本地 AIOps 告警列表。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import get_settings
from app.services.alert_service import _load_index, _save_index


def _load_log_generator():
    """加载项目根目录已有的 16 条应用规则日志生成器。"""
    path = get_settings().project_root.parent / "app_log_gen.py"
    spec = importlib.util.spec_from_file_location("aiops_app_log_generator", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"无法加载应用日志生成器: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def list_application_alert_rules() -> list[dict[str, Any]]:
    generator = _load_log_generator()
    return [{
        "id": item["id"], "system": item["system"], "sn": item["sn"],
        "alert_name": item["alert_name"], "spl": item["raw_spl"],
    } for item in generator.RULE_CONFIGS]


def generate_application_alert(rule_id: int, count: int = 10) -> dict[str, Any]:
    if not 1 <= count <= 1000:
        raise ValueError("生成条数必须在 1 到 1000 之间")
    generator = _load_log_generator()
    try:
        rule_index = next(i for i, item in enumerate(generator.RULE_CONFIGS) if item["id"] == rule_id)
    except StopIteration as exc:
        raise ValueError("未找到指定的应用告警规则") from exc

    config = generator.RULE_CONFIGS[rule_index]
    csv_path, records = generator.run_generation(rule_index, count, return_records=True)
    now = datetime.now(timezone(timedelta(hours=8)))
    alert_id = "appsim_" + hashlib.sha256(
        f"{rule_id}|{now.isoformat()}|{count}".encode("utf-8")
    ).hexdigest()[:20]
    filename = f"{alert_id}.json"
    resource_name = f"{config['system']}-APP-SIM"
    first = records[0] if records else {}
    event_time = first.get("_time") or first.get("OperateTime") or now.isoformat()
    result = {
        "id": resource_name,
        "properties_hostname": f"{config['system'].lower().replace(' ', '-')}.simulated.local",
        "properties_requestUri": _summary(records, config["output_fields"]),
        "properties_action": "应用异常",
        "count": str(count),
    }
    alert = {
        "alert_name": config["alert_name"],
        "application_code": config["system"],
        "trigger_time": event_time,
        "trigger_time_utc": now.isoformat(),
        "event_count": count,
        "trigger_reason": f"模拟应用日志命中规则 #{config['id']}：{config['alert_name']}",
        "search_terms": config["raw_spl"],
        "full_spl": config["raw_spl"],
        "results": [result],
        "operator_notes": f"模拟应用告警；日志已写入 {csv_path}",
        # 生成日志只创建待分析告警；风险等级和风险详情必须由 AI 分析接口写入。
        "risk_level": "待分析",
        "risk_details": None,
        "from_sample": None,
    }
    settings = get_settings()
    output_dir = now.strftime("%Y-%m-%d")
    raw_path = settings.application_alert_path / output_dir / filename
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(alert, ensure_ascii=False, indent=2), encoding="utf-8")
    index = _load_index(settings.processed_index_path)
    index.setdefault("processed_files", {})[filename] = {
        "processed_at": now.isoformat(), "risk_level": alert["risk_level"],
        "raw_dir": output_dir, "source": "application_simulator", "analysis_status": "pending",
    }
    _save_index(settings.processed_index_path, index)
    return {"alert_id": alert_id, "alert": alert, "log_path": str(csv_path), "generated_logs": count}


def _summary(records: list[dict[str, Any]], fields: list[str]) -> str:
    if not records:
        return "模拟应用异常日志"
    row = records[0]
    values = [f"{field}={row[field]}" for field in fields if field not in {"_time", "OperateTime"} and row.get(field) not in (None, "")]
    return "; ".join(values)[:500] or "模拟应用异常日志"


async def analyze_application_alert(alert_id: str) -> dict[str, Any] | None:
    """复用标准告警编排完成分类、Agent、报告、建议和历史归档。"""
    settings = get_settings()
    index = _load_index(settings.processed_index_path)
    filename = f"{alert_id}.json"
    info = index.get("processed_files", {}).get(filename)
    if not info or info.get("source") != "application_simulator":
        return None
    raw_path = settings.application_alert_path / str(info.get("raw_dir", "")) / filename
    try:
        raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("无法读取模拟应用原始告警") from exc
    # ``待分析`` 只是页面状态，不是标准 RawAlert 字段。标准处理器会提供
    # 真正的 risk_level/risk_details，因此这里必须移除占位字段，避免重复传参。
    raw_payload.pop("risk_level", None)
    raw_payload.pop("risk_details", None)
    raw_payload.pop("token_usage", None)
    raw_payload.pop("from_sample", None)
    raw_payload.pop("match_sample_id", None)
    raw_payload.pop("match_score", None)
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # 标准函数依次执行：分类库命中判断；未命中时调用历史告警 Tool 和
    # 知识库/CMDB Tool；生成报告/建议；类别×风险等级 upsert；归档历史案例。
    from app.services.alert_service import process_single_alert

    result = await process_single_alert(raw_path, classification_alert_id=alert_id)
    if not result:
        raise RuntimeError("标准告警处理未生成增强结果")
    enriched = result.model_dump()
    output_dir = str(info.get("raw_dir", ""))
    enriched_path = settings.application_enriched_alert_path / output_dir / filename
    enriched_path.parent.mkdir(parents=True, exist_ok=True)
    enriched_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")

    # 标准编排的报告/建议已落在原位置；确认它们真实存在且非空，再允许展示。
    _normalize_required_outputs(output_dir, alert_id)
    # 标准函数为兼容旧前端还会写一个重复结果到旧输出目录；应用告警只保留
    # output/application_alerts 这份增强数据，其余历史归档仍由标准流程保留。
    (settings.alert_output_path / output_dir / filename).unlink(missing_ok=True)
    info["risk_level"] = result.risk_level
    info["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    info["analysis_status"] = "completed"
    info["enriched_dir"] = output_dir
    _save_index(settings.processed_index_path, index)
    return enriched


def delete_application_alert(alert_id: str) -> bool:
    """删除一条模拟应用告警及其 AI 输出；不删除共享的原始 CSV 日志。"""
    if not alert_id.startswith("appsim_"):
        return False
    settings = get_settings()
    index = _load_index(settings.processed_index_path)
    filename = f"{alert_id}.json"
    info = index.get("processed_files", {}).get(filename)
    if not info or info.get("source") != "application_simulator":
        return False
    date = str(info.get("raw_dir") or info.get("output_dir", ""))
    paths = [
        settings.application_alert_path / date / filename,
        settings.application_enriched_alert_path / str(info.get("enriched_dir", date)) / filename,
        # 兼容目录调整前写入旧“带风险等级”目录的模拟告警。
        settings.alert_output_path / date / filename,
        settings.reports_path / date / f"{alert_id}_analysis.md",
        settings.suggestions_path / date / f"{alert_id}_suggestion.md",
    ]
    for path in paths:
        path.unlink(missing_ok=True)
    del index["processed_files"][filename]
    _save_index(settings.processed_index_path, index)
    return True


def _normalize_required_outputs(date: str, alert_id: str) -> None:
    settings = get_settings()
    report_path = settings.reports_path / date / f"{alert_id}_analysis.md"
    suggestion_path = settings.suggestions_path / date / f"{alert_id}_suggestion.md"
    for path, label in ((report_path, "分析报告"), (suggestion_path, "处理建议")):
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"标准流程未生成{label}")
        path.write_text(_strip_markdown_fence(path.read_text(encoding="utf-8")), encoding="utf-8")


def _strip_markdown_fence(content: str) -> str:
    """模型偶尔会把整份 Markdown 包成代码块；落盘前还原为正文。"""
    text = content.strip()
    if text.startswith("```markdown") or text.startswith("```md"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()
