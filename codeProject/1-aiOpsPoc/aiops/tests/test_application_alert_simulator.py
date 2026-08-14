from pathlib import Path
import pytest

from app.config import get_settings
from app.schemas.alert import EnrichedAlert, RiskDetails
from app.schemas.cmdb import CmdbLookupResult
from app.schemas.risk import RiskAssessment
from app.services import application_alert_simulator as simulator
from app.services import alert_service
from app.services import report_service
from app.api.v1 import alerts as alert_api


def test_application_simulator_generates_log_and_listable_alert(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(type(settings), "application_alert_path", property(lambda _: tmp_path / "data" / "application_alerts"))
    monkeypatch.setattr(type(settings), "application_enriched_alert_path", property(lambda _: tmp_path / "output" / "application_alerts"))
    monkeypatch.setattr(type(settings), "reports_path", property(lambda _: tmp_path / "output" / "reports"))
    monkeypatch.setattr(type(settings), "suggestions_path", property(lambda _: tmp_path / "output" / "suggestions"))
    monkeypatch.setattr(type(settings), "processed_index_path", property(lambda _: tmp_path / "processed.json"))

    generator = simulator._load_log_generator()
    monkeypatch.setattr(generator, "OUTPUT_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(simulator, "_load_log_generator", lambda: generator)

    result = simulator.generate_application_alert(rule_id=1, count=3)

    assert result["alert_id"].startswith("appsim_")
    assert result["generated_logs"] == 3
    assert Path(result["log_path"]).exists()
    assert Path(result["log_path"]).name == "app_alert_iwe_Login_Failed.csv"
    assert len(Path(result["log_path"]).read_text(encoding="utf-8").splitlines()) == 4
    assert result["alert"]["application_code"] == "iWE"
    assert result["alert"]["results"][0]["properties_action"] == "应用异常"
    assert result["alert"]["risk_level"] == "待分析"
    assert result["alert"]["risk_details"] is None
    assert len(list((tmp_path / "data" / "application_alerts").glob("*/*.json"))) == 1
    assert not list((tmp_path / "output" / "application_alerts").glob("*/*.json"))
    listed = alert_service.get_alert_list()
    assert listed == []


@pytest.mark.asyncio
async def test_ai_analysis_writes_separate_enriched_alert_report_and_suggestion(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(type(settings), "application_alert_path", property(lambda _: tmp_path / "data" / "application_alerts"))
    monkeypatch.setattr(type(settings), "application_enriched_alert_path", property(lambda _: tmp_path / "output" / "application_alerts"))
    monkeypatch.setattr(type(settings), "reports_path", property(lambda _: tmp_path / "output" / "reports"))
    monkeypatch.setattr(type(settings), "suggestions_path", property(lambda _: tmp_path / "output" / "suggestions"))
    monkeypatch.setattr(type(settings), "processed_index_path", property(lambda _: tmp_path / "processed.json"))
    generator = simulator._load_log_generator()
    monkeypatch.setattr(generator, "OUTPUT_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(simulator, "_load_log_generator", lambda: generator)

    created = simulator.generate_application_alert(rule_id=1, count=3)
    async def fake_standard_pipeline(raw_path, classification_alert_id=None):
        assert raw_path.name == f"{created['alert_id']}.json"
        assert classification_alert_id == created["alert_id"]
        raw = __import__("json").loads(raw_path.read_text(encoding="utf-8"))
        assert "risk_level" not in raw
        assert "risk_details" not in raw
        date = raw_path.parent.name
        (settings.reports_path / date).mkdir(parents=True, exist_ok=True)
        (settings.suggestions_path / date).mkdir(parents=True, exist_ok=True)
        (settings.reports_path / date / f"{created['alert_id']}_analysis.md").write_text("```markdown\n# AI 报告\n```", encoding="utf-8")
        (settings.suggestions_path / date / f"{created['alert_id']}_suggestion.md").write_text("```md\n# AI 建议\n```", encoding="utf-8")
        raw.update(risk_level="中", risk_details=RiskDetails(overall_risk="中"), from_sample=False)
        return EnrichedAlert(**raw)

    monkeypatch.setattr(alert_service, "process_single_alert", fake_standard_pipeline)
    analyzed = await simulator.analyze_application_alert(created["alert_id"])

    raw_file = next((tmp_path / "data" / "application_alerts").glob("*/*.json"))
    raw = raw_file.read_text(encoding="utf-8")
    assert '"risk_level"' not in raw
    enriched_file = next((tmp_path / "output" / "application_alerts").glob("*/*.json"))
    assert '"risk_level": "中"' in enriched_file.read_text(encoding="utf-8")
    assert analyzed["risk_level"] == "中"
    assert len(list((tmp_path / "output" / "reports").glob("*/*_analysis.md"))) == 1
    assert len(list((tmp_path / "output" / "suggestions").glob("*/*_suggestion.md"))) == 1
    assert (next((tmp_path / "output" / "reports").glob("*/*.md")).read_text(encoding="utf-8") == "# AI 报告")


def test_completed_alert_list_reads_enriched_risk_level(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(type(settings), "application_alert_path", property(lambda _: tmp_path / "data" / "application_alerts"))
    monkeypatch.setattr(type(settings), "application_enriched_alert_path", property(lambda _: tmp_path / "output" / "application_alerts"))
    monkeypatch.setattr(type(settings), "processed_index_path", property(lambda _: tmp_path / "processed.json"))
    alert_id, filename, date = "appsim_done", "appsim_done.json", "2026-08-13"
    raw = {"alert_name": "demo", "risk_level": "待分析", "results": [{"properties_hostname": "demo.local"}]}
    enriched = {**raw, "risk_level": "高", "risk_details": {"overall_risk": "高"}}
    raw_path = tmp_path / "data" / "application_alerts" / date / filename
    enhanced_path = tmp_path / "output" / "application_alerts" / date / filename
    raw_path.parent.mkdir(parents=True)
    enhanced_path.parent.mkdir(parents=True)
    raw_path.write_text(__import__("json").dumps(raw), encoding="utf-8")
    enhanced_path.write_text(__import__("json").dumps(enriched), encoding="utf-8")
    alert_service._save_index(settings.processed_index_path, {"processed_files": {filename: {
        "source": "application_simulator", "processed_at": "2026-08-13T00:00:00", "raw_dir": date,
        "enriched_dir": date, "analysis_status": "completed", "risk_level": "高",
    }}})
    listed = alert_service.get_alert_list()
    assert listed[0].id == alert_id
    assert listed[0].risk_level == "高"


def test_application_alert_detail_exposes_classification_reuse_metadata(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(type(settings), "application_alert_path", property(lambda _: tmp_path / "data" / "application_alerts"))
    monkeypatch.setattr(type(settings), "application_enriched_alert_path", property(lambda _: tmp_path / "output" / "application_alerts"))
    monkeypatch.setattr(type(settings), "reports_path", property(lambda _: tmp_path / "output" / "reports"))
    monkeypatch.setattr(type(settings), "suggestions_path", property(lambda _: tmp_path / "output" / "suggestions"))
    monkeypatch.setattr(type(settings), "processed_index_path", property(lambda _: tmp_path / "processed.json"))
    filename, date = "appsim_reused.json", "2026-08-13"
    enriched_path = tmp_path / "output" / "application_alerts" / date / filename
    enriched_path.parent.mkdir(parents=True)
    enriched_path.write_text(__import__("json").dumps({
        "alert_name": "demo", "risk_level": "中", "results": [], "from_sample": True,
        "match_sample_id": "api_exploit:medium", "match_score": 100,
    }), encoding="utf-8")
    alert_service._save_index(settings.processed_index_path, {"processed_files": {filename: {
        "source": "application_simulator", "raw_dir": date, "enriched_dir": date,
        "analysis_status": "completed",
    }}})
    detail = alert_service.get_alert_detail("appsim_reused")
    assert detail.from_sample is True
    assert detail.match_sample_id == "api_exploit:medium"
    assert detail.match_score == 100


def test_standard_output_normalization_removes_markdown_fence(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(type(settings), "reports_path", property(lambda _: tmp_path / "reports"))
    monkeypatch.setattr(type(settings), "suggestions_path", property(lambda _: tmp_path / "suggestions"))
    (tmp_path / "reports" / "2026-08-13").mkdir(parents=True)
    (tmp_path / "suggestions" / "2026-08-13").mkdir(parents=True)
    (tmp_path / "reports" / "2026-08-13" / "appsim_demo_analysis.md").write_text("```markdown\n# 报告\n```", encoding="utf-8")
    (tmp_path / "suggestions" / "2026-08-13" / "appsim_demo_suggestion.md").write_text("```md\n# 建议\n```", encoding="utf-8")
    simulator._normalize_required_outputs("2026-08-13", "appsim_demo")
    assert (tmp_path / "reports" / "2026-08-13" / "appsim_demo_analysis.md").read_text(encoding="utf-8") == "# 报告"
    assert (tmp_path / "suggestions" / "2026-08-13" / "appsim_demo_suggestion.md").read_text(encoding="utf-8") == "# 建议"


def test_delete_application_alert_removes_alert_outputs_but_keeps_csv(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(type(settings), "application_alert_path", property(lambda _: tmp_path / "data" / "application_alerts"))
    monkeypatch.setattr(type(settings), "application_enriched_alert_path", property(lambda _: tmp_path / "output" / "application_alerts"))
    monkeypatch.setattr(type(settings), "reports_path", property(lambda _: tmp_path / "output" / "reports"))
    monkeypatch.setattr(type(settings), "suggestions_path", property(lambda _: tmp_path / "output" / "suggestions"))
    monkeypatch.setattr(type(settings), "processed_index_path", property(lambda _: tmp_path / "processed.json"))
    generator = simulator._load_log_generator()
    monkeypatch.setattr(generator, "OUTPUT_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(simulator, "_load_log_generator", lambda: generator)

    created = simulator.generate_application_alert(rule_id=1, count=3)
    csv_path = Path(created["log_path"])
    assert simulator.delete_application_alert(created["alert_id"]) is True
    assert csv_path.exists()
    assert not list((tmp_path / "data" / "application_alerts").glob("*/*.json"))
    assert alert_service.get_alert_list() == []


@pytest.mark.asyncio
async def test_create_endpoint_automatically_runs_ai_analysis(monkeypatch):
    calls = []

    def fake_generate(rule_id, count):
        calls.append(("generate", rule_id, count))
        return {"alert_id": "appsim_auto", "alert": {}, "log_path": "logs.csv", "generated_logs": count}

    async def fake_analyze(alert_id):
        calls.append(("analyze", alert_id))
        return {"risk_level": "中"}

    monkeypatch.setattr(alert_api, "generate_application_alert", fake_generate)
    monkeypatch.setattr(alert_api, "analyze_application_alert", fake_analyze)
    result = await alert_api.create_application_alert_simulation({"rule_id": 1, "count": 4})

    assert calls == [("generate", 1, 4), ("analyze", "appsim_auto")]
    assert result["status"] == "ok"
    assert result["risk_level"] == "中"


def test_application_alert_fallback_uses_application_titles_not_waf():
    alert = EnrichedAlert(
        alert_name="app_alert_iwe_Login_Failed", application_code="iWE",
        results=[], risk_level="低", risk_details=RiskDetails(overall_risk="低"),
    )
    risk = RiskAssessment(
        environment="Non-Production", environment_risk="低", count_risk="低",
        count_value=1, attack_type_risk="低", attack_types=[], overall_risk="低",
    )
    cmdb = CmdbLookupResult(found=False, match_type="simulation", environment="Non-Production")
    report = report_service._generate_fallback_report(alert, cmdb, risk, {})
    suggestion = report_service._generate_fallback_suggestion(alert, cmdb, risk, {})
    assert report.startswith("# 应用告警分析报告")
    assert suggestion.startswith("# 应用告警处理建议")
    assert "WAF" not in report
    assert "WAF" not in suggestion
