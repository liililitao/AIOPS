import asyncio
from pathlib import Path
from types import SimpleNamespace

from app import main


def test_frontend_hides_admin_pages_until_permission_is_loaded():
    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
    html = (frontend_dir / "index.html").read_text(encoding="utf-8")
    script = (frontend_dir / "app.js").read_text(encoding="utf-8")

    assert 'data-tab="results">📊 告警结果</button>' in html
    for tab in ("kbchat", "knowledge", "config"):
        assert f'data-tab="{tab}" hidden' in html
        assert f'id="tab-{tab}" hidden' in html
    assert "await applyNavigationPermissions();" in script
    assert "document.querySelectorAll('.admin-only')" in script
    assert "resultsTab.textContent = '📊 告警分析'" in script


def test_session_endpoint_keeps_full_navigation_in_unauthenticated_dev_mode(monkeypatch):
    monkeypatch.setattr(main, "settings", SimpleNamespace(AIOPS_AUTH_ENABLED=False))

    result = asyncio.run(main.current_session(SimpleNamespace(state=SimpleNamespace())))

    assert result == {"authenticated": False, "is_admin": True}


def test_session_endpoint_marks_regular_user_as_non_admin(monkeypatch):
    class FakeAuthorizationStore:
        def __init__(self, _database_path):
            pass

        def user_access(self, username):
            assert username == "zhangsan"
            return SimpleNamespace(username="zhangsan", is_admin=False)

    monkeypatch.setattr(
        main,
        "settings",
        SimpleNamespace(AIOPS_AUTH_ENABLED=True, authorization_db_path=Path("authorization.sqlite3")),
    )
    monkeypatch.setattr(main, "AlertAuthorizationStore", FakeAuthorizationStore)

    result = asyncio.run(
        main.current_session(SimpleNamespace(state=SimpleNamespace(authenticated_user="zhangsan")))
    )

    assert result == {"authenticated": True, "username": "zhangsan", "is_admin": False}
