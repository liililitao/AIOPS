"""告警新流程的本地 mock 测试：不会调用 LLM、Embedding、Milvus 或网络。"""

import json
from pathlib import Path

import pytest

from app.config import get_settings
from app.agents.alert_analysis_agent import AgentAnalysisResult, AlertAnalysisAgent
from app.schemas.alert import AlertResult, EnrichedAlert, RawAlert, TokenUsage
from app.schemas.cmdb import CmdbLookupResult
from app.schemas.risk import RiskAssessment
from app.services import alert_service
from app.services.alert_classification_service import AlertClassificationRepository


def _raw_alert() -> RawAlert:
    return RawAlert(
        alert_name="WAF suspicious path scan",
        application_code="Test Application",
        trigger_reason="blocked requests for sensitive paths",
        search_terms="index=waf blocked",
        results=[AlertResult(
            id="AGW-PRD-01", properties_hostname="api.example.internal",
            properties_requestUri="/.env /admin", properties_action="Blocked", count="15",
        )],
    )


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(settings, "MILVUS_ENABLED", False)
    monkeypatch.setattr(settings, "HISTORICAL_ALERT_INDEX_ENABLED", False)
    monkeypatch.setattr(settings, "ALERT_CLASSIFICATION_ENABLED", True)
    monkeypatch.setattr(settings, "ALERT_CLASSIFICATION_MAX_RECORDS", 280)
    monkeypatch.setattr(type(settings), "alert_classification_store_path", property(lambda _: tmp_path / "classifications.json"))
    monkeypatch.setattr(type(settings), "raw_alert_path", property(lambda _: tmp_path / "raw"))
    monkeypatch.setattr(type(settings), "historical_enriched_alert_path", property(lambda _: tmp_path / "history" / "enriched"))
    monkeypatch.setattr(type(settings), "alert_output_path", property(lambda _: tmp_path / "frontend-output"))
    monkeypatch.setattr(type(settings), "reports_path", property(lambda _: tmp_path / "reports"))
    monkeypatch.setattr(type(settings), "suggestions_path", property(lambda _: tmp_path / "suggestions"))
    monkeypatch.setattr(type(settings), "agent_runs_path", property(lambda _: tmp_path / "agent-runs"))
    return settings


def _write_input(tmp_path: Path, alert: RawAlert, name: str = "alert.json") -> Path:
    path = tmp_path / name
    path.write_text(alert.model_dump_json(), encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_router_llm_hit_reuses_without_agent_tools_or_report_llm(monkeypatch, tmp_path):
    raw = _raw_alert()
    repo = AlertClassificationRepository()
    record = repo.upsert(
        raw, report="# reused analysis", suggestion="# reused suggestion", risk_level="高",
        risk_details={"overall_risk": "高", "environment": "Production"},
    )
    # 主机变化时由 Router LLM 判断业务语义，而非本地文本分数。
    similar = raw.model_copy(deep=True)
    similar.results[0].properties_hostname = "api-dr.example.internal"

    def forbidden(*args, **kwargs):
        raise AssertionError("semantic hit must not enter Agent tools or report LLM")

    monkeypatch.setattr("app.agents.AlertAnalysisAgent.analyze", forbidden)
    class Message:
        usage_metadata = {"input_tokens": 12, "output_tokens": 3}
    async def router_match(*args, **kwargs):
        return f"sample_id:{record['key']},score:92", Message()
    monkeypatch.setattr(alert_service, "call_llm_with_retry", router_match)
    result = await alert_service.process_single_alert(_write_input(tmp_path, similar))

    assert result.from_sample is True
    assert result.match_sample_id == raw.alert_name
    assert result.match_score == 92
    assert result.token_usage.total.total_tokens == 15
    report_files = list(get_settings().reports_path.glob("*/*_analysis.md"))
    assert len(report_files) == 1
    assert report_files[0].read_text(encoding="utf-8") == "# reused analysis"
    assert (get_settings().raw_alert_path / "alert.json").exists()


@pytest.mark.asyncio
async def test_router_score_below_85_enters_tools_and_agent(monkeypatch, tmp_path):
    raw = _raw_alert()
    record = AlertClassificationRepository().upsert(raw, report="old report", suggestion="old suggestion", risk_level="高", risk_details={})
    class Message:
        usage_metadata = {"input_tokens": 9, "output_tokens": 2}
    async def router_no_match(*args, **kwargs):
        return f"sample_id:{record['key']},score:84", Message()
    monkeypatch.setattr(alert_service, "call_llm_with_retry", router_no_match)
    async def fake_agent(*args, **kwargs):
        return AgentAnalysisResult("test-agent", "", "", {"historical": {}, "knowledge": {"evidence": {"assets": []}}, "splunk": {}}, token_usage=TokenUsage())
    monkeypatch.setattr("app.agents.AlertAnalysisAgent.analyze", fake_agent)
    async def report(*args, **kwargs):
        return "# generated", TokenUsage(total_tokens=5)
    async def suggestion(*args, **kwargs):
        return "# suggested", TokenUsage(total_tokens=7)
    monkeypatch.setattr("app.services.report_service.generate_analysis_report", report)
    monkeypatch.setattr("app.services.report_service.generate_suggestion", suggestion)
    result = await alert_service.process_single_alert(_write_input(tmp_path, raw))
    assert result.from_sample is False
    assert result.match_score is None
    assert result.token_usage.total.total_tokens == 23


def test_semantic_candidates_require_same_application_name_and_risk(monkeypatch):
    current = RawAlert(
        alert_name="app_alert_rared_Add_Role", application_code="RareD NovoCare",
        results=[AlertResult(
            id="RareD NovoCare-APP-SIM", properties_hostname="rared-novocare.simulated.local",
            properties_requestUri="OperateDescription=新增角色", properties_action="应用异常", count="6",
        )],
    )
    records = {
        "random_scan:high": {
            "source_alert_name": "app_alert_novocare_diabetes_Change_of_Role_Privileges",
            "source_application_code": "NNRC Diabetes.com", "risk_level": "高",
            "classification_signature": {"alert_name": "app_alert_novocare_diabetes_Change_of_Role_Privileges"},
            "report": "report", "suggestion": "suggestion",
        },
        "legacy": {
            "source_alert_name": current.alert_name, "risk_level": "低",
            "classification_signature": {"alert_name": current.alert_name},
            "report": "report", "suggestion": "suggestion",
        },
    }
    monkeypatch.setattr(AlertClassificationRepository, "_load", lambda _: {"records": records})
    assert alert_service._load_semantic_candidates(current, "低") == []


@pytest.mark.asyncio
async def test_classification_miss_calls_both_tools_then_generates_and_upserts(monkeypatch, tmp_path):
    raw = _raw_alert()
    calls = []

    def fake_history(query, top_k):
        calls.append(("history", query, top_k))
        return {"success": True, "results": [{"case_id": "old/one", "alert_summary": "old alert",
                "analysis_summary": "old analysis", "suggestion_summary": "old suggestion"}]}

    class FakeKnowledgeService:
        def search(self, **kwargs):
            calls.append(("knowledge", kwargs))
            return {"success": True, "evidence": {"assets": [{"found": True, "match_type": "exact",
                    "resource_name": "AGW-PRD-01", "resource_type": "gateway", "environment": "Production",
                    "subscription": "prd", "source_sheet": "CMDB", "source_row": 1}],
                "documents": [{"source": "waf-sop.md", "text": "isolate source", "score": 0.9}]}, "warnings": []}

    async def fake_report(alert, cmdb, risk, rag_context=""):
        calls.append(("report", cmdb.environment, rag_context))
        return "# generated report", TokenUsage(prompt_tokens=3, completion_tokens=4, total_tokens=7)

    async def fake_suggestion(alert, cmdb, risk, rag_context=""):
        calls.append(("suggestion", cmdb.environment, rag_context))
        return "# generated suggestion", TokenUsage(prompt_tokens=5, completion_tokens=6, total_tokens=11)

    monkeypatch.setattr("app.tools.historical_alert_tool.run_historical_alert_search", fake_history)
    monkeypatch.setattr("app.tools.knowledge_base_tool._get_default_service", lambda: FakeKnowledgeService())
    monkeypatch.setattr("app.tools.splunk_log_tool.run_splunk_investigation", lambda *args, **kwargs: {"success": False, "error_code": "splunk_not_configured"})
    async def fake_agent_plan(self, alert, context):
        return "测试调查计划", TokenUsage()
    async def fake_agent_summary(self, alert, plan, evidence):
        return "证据研判", TokenUsage()
    monkeypatch.setattr("app.agents.AlertAnalysisAgent._plan", fake_agent_plan)
    monkeypatch.setattr("app.agents.AlertAnalysisAgent._summarize", fake_agent_summary)
    monkeypatch.setattr("app.services.report_service.generate_analysis_report", fake_report)
    monkeypatch.setattr("app.services.report_service.generate_suggestion", fake_suggestion)

    result = await alert_service.process_single_alert(_write_input(tmp_path, raw))

    assert result.from_sample is False
    assert [call[0] for call in calls] == ["history", "knowledge", "report", "suggestion"]
    assert "历史相似告警" in calls[2][2]
    assert "SOP/知识库：waf-sop.md" in calls[2][2]
    assert result.token_usage.total.total_tokens == 18
    assert AlertClassificationRepository().find(raw)["report"] == "# generated report"
    assert (get_settings().raw_alert_path / "alert.json").exists()
    assert len(list(get_settings().historical_enriched_alert_path.glob("*/*.json"))) == 1
    runs = list(get_settings().agent_runs_path.glob("*/*_agent_run.json"))
    assert len(runs) == 1
    assert [step["name"] for step in json.loads(runs[0].read_text(encoding="utf-8"))["steps"][1:4]] == [
        "historical_alert_search", "knowledge_base_search", "splunk_log_investigation",
    ]


@pytest.mark.asyncio
async def test_agent_always_calls_three_controlled_tools_before_evidence_analysis(monkeypatch):
    calls = []

    def history(query, top_k):
        calls.append("history")
        return {"success": True, "results": []}

    def knowledge(query, resource_id, hostname, top_k):
        calls.append("knowledge")
        return {"success": True, "evidence": {"assets": [], "documents": []}, "warnings": []}

    def splunk(alert_id):
        calls.append("splunk")
        return {"success": False, "error_code": "splunk_not_configured", "evidence": []}

    async def plan(self, alert, context):
        calls.append("plan")
        return "测试计划", TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2)

    async def summary(self, alert, plan, evidence):
        calls.append("analysis")
        return "基于三个 Tool 的研判", TokenUsage(prompt_tokens=2, completion_tokens=1, total_tokens=3)

    monkeypatch.setattr(AlertAnalysisAgent, "_historical", staticmethod(history))
    monkeypatch.setattr(AlertAnalysisAgent, "_knowledge", staticmethod(knowledge))
    monkeypatch.setattr(AlertAnalysisAgent, "_splunk", staticmethod(splunk))
    monkeypatch.setattr(AlertAnalysisAgent, "_plan", plan)
    monkeypatch.setattr(AlertAnalysisAgent, "_summarize", summary)

    result = await AlertAnalysisAgent().analyze(_raw_alert(), alert_id="2026-08-14/agent-test")

    assert calls == ["plan", "history", "knowledge", "splunk", "analysis"]
    assert result.analysis_result == "基于三个 Tool 的研判"
    assert result.token_usage.total_tokens == 5


def test_classification_library_upserts_same_key_and_enforces_capacity(tmp_path):
    raw = _raw_alert()
    path = tmp_path / "library.json"
    repo = AlertClassificationRepository(path=path, max_records=1)
    first = repo.upsert(raw, report="first", suggestion="first", risk_level="高", risk_details={})
    second = repo.upsert(raw, report="latest", suggestion="latest", risk_level="高", risk_details={})
    assert first["key"] == second["key"]
    assert repo.stats() == {"records": 1, "max_records": 1}
    assert repo._load()["records"][second["key"]]["report"] == "latest"

    another = RawAlert(alert_name="Other", results=[AlertResult(properties_requestUri="/random")])
    assert repo.upsert(another, report="no", suggestion="no", risk_level="低", risk_details={}) is None


def test_history_tool_and_knowledge_tool_are_local_contracts(monkeypatch):
    from app.tools.historical_alert_tool import run_historical_alert_search
    from app.tools.knowledge_base_tool import KnowledgeBaseSearchService

    class FakeIndex:
        def search(self, query, top_k):
            return [{"case_id": "2026-08-01/example", "similarity": 0.8}]

    history = run_historical_alert_search("waf scan", index=FakeIndex())
    assert history["success"] is True
    assert history["results"][0]["case_id"] == "2026-08-01/example"

    service = KnowledgeBaseSearchService(
        document_search=lambda query, top_k: [{"source": "sop.md", "chunk_index": 0, "score": 1, "text": "x" * 2000}],
        asset_search=lambda resource_id, hostname: CmdbLookupResult(found=True, environment="Production"),
    )
    result = service.search("waf", resource_id="AGW-1")
    assert result["success"] is True
    assert result["evidence"]["assets"][0]["environment"] == "Production"
    assert result["evidence"]["documents"][0]["text"].endswith("…")


def test_simulated_resource_is_always_non_production_when_cmdb_has_no_match():
    alert = RawAlert(results=[AlertResult(
        id="iWE-APP-SIM", properties_hostname="iwe.simulated.local",
    )])
    cmdb = alert_service._cmdb_from_agent_evidence({"knowledge": {"evidence": {"assets": []}}}, alert)
    assert cmdb.environment == "Non-Production"
    assert cmdb.match_type == "simulation"


def test_simulated_resource_overrides_unknown_placeholder_asset_from_tool():
    alert = RawAlert(results=[AlertResult(
        id="RareD NovoCare-APP-SIM", properties_hostname="rared-novocare.simulated.local",
    )])
    evidence = {"knowledge": {"evidence": {"assets": [
        {"found": False, "match_type": "none", "environment": "Unknown"},
    ]}}}
    cmdb = alert_service._cmdb_from_agent_evidence(evidence, alert)
    assert cmdb.environment == "Non-Production"
    assert cmdb.match_type == "simulation"


@pytest.mark.asyncio
async def test_router_unavailable_falls_back_to_agent_for_simulation(monkeypatch, tmp_path):
    raw = RawAlert(results=[AlertResult(
        id="iWE-APP-SIM", properties_hostname="iwe.simulated.local", count="1",
        properties_requestUri="/login", properties_action="应用异常",
    )])
    calls = []
    async def fake_agent(*args, **kwargs):
        calls.append("tools")
        return AgentAnalysisResult("test-agent", "", "", {"historical": {}, "knowledge": {"evidence": {"assets": []}}, "splunk": {}}, token_usage=TokenUsage())
    monkeypatch.setattr("app.agents.AlertAnalysisAgent.analyze", fake_agent)
    async def report(*args, **kwargs):
        return "# new", TokenUsage()
    async def suggestion(*args, **kwargs):
        return "# new suggestion", TokenUsage()
    monkeypatch.setattr("app.services.report_service.generate_analysis_report", report)
    monkeypatch.setattr("app.services.report_service.generate_suggestion", suggestion)
    result = await alert_service.process_single_alert(_write_input(tmp_path, raw, "simulation.json"))
    assert calls == ["tools"]
    assert result.risk_details.environment == "Non-Production"
