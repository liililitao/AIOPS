import json
from types import SimpleNamespace

from app.schemas.alert import AlertListItem
from app.services import alert_service, splunk_alert_service


def test_remote_alerts_are_archived_per_alert_and_as_current_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(
        splunk_alert_service,
        "get_settings",
        lambda: SimpleNamespace(alert_input_path=tmp_path),
    )

    alerts = [
        {"id": "splunk_one", "alert_name": "First"},
        {"id": "splunk_two", "alert_name": "Second"},
    ]
    splunk_alert_service.persist_remote_alerts_for_frontend(
        alerts, synced_at="2026-08-12T00:00:00+00:00"
    )

    archive_dir = tmp_path / "前端同步告警"
    assert json.loads((archive_dir / "splunk_one.json").read_text(encoding="utf-8"))["alert"] == alerts[0]
    current = json.loads((archive_dir / "当前同步列表.json").read_text(encoding="utf-8"))
    assert current["total"] == 2
    assert current["alerts"] == alerts


def test_full_frontend_list_is_saved_as_a_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(
        alert_service,
        "get_settings",
        lambda: SimpleNamespace(alert_input_path=tmp_path),
    )
    items = [
        AlertListItem(
            id="local_alert",
            alert_name="Local alert",
            hostname="host.example.com",
            trigger_time="2026-08-12T00:00:00+00:00",
            risk_level="高",
            processed_at="2026-08-12T00:00:00+00:00",
        )
    ]

    alert_service._save_frontend_alert_list_snapshot(items)

    snapshot = json.loads(
        (tmp_path / "前端同步告警" / "前端告警列表快照.json").read_text(
            encoding="utf-8"
        )
    )
    assert snapshot["total"] == 1
    assert snapshot["alerts"][0]["id"] == "local_alert"
