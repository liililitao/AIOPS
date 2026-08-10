"""Server-side application authorization for alert lists and alert details."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class UserAccess:
    username: str
    role: str
    application_codes: frozenset[str]

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class AlertAuthorizationStore:
    """Read the existing user_application_permissions SQLite schema fail-closed."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    def user_access(self, username: str) -> UserAccess:
        normalized = _normalize_username(username)
        if not normalized:
            return UserAccess("", "user", frozenset())
        try:
            with self._connect() as connection:
                role_row = connection.execute(
                    "SELECT role FROM user_roles WHERE username = ? AND enabled = 1",
                    (normalized,),
                ).fetchone()
                if role_row is None:
                    return UserAccess(normalized, "user", frozenset())
                application_rows = connection.execute(
                    """
                    SELECT permission.application_code
                    FROM user_application_permissions AS permission
                    JOIN applications AS application
                      ON application.application_code = permission.application_code
                    WHERE permission.username = ? AND application.enabled = 1
                    """,
                    (normalized,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError("告警权限数据库不可用") from exc
        return UserAccess(
            username=normalized,
            role=str(role_row["role"]),
            application_codes=frozenset(str(row["application_code"]) for row in application_rows),
        )

    def can_access_alert(self, username: str, alert: Any) -> bool:
        access = self.user_access(username)
        if access.is_admin:
            return True
        application = self.resolve_alert_application(alert)
        return application is not None and application in access.application_codes

    def resolve_alert_application(self, alert: Any) -> str | None:
        """Resolve an alert to an application using explicit fields, then alert name."""
        payload = _as_dict(alert)
        candidates: list[str] = []
        for field in ("application_code", "application", "app_code", "service"):
            value = _text(payload.get(field))
            if value:
                candidates.append(value)

        results = payload.get("results")
        if isinstance(results, list):
            for item in results:
                if not isinstance(item, dict):
                    continue
                for field in ("application_code", "application", "app_code", "service"):
                    value = _text(item.get(field))
                    if value:
                        candidates.append(value)

        try:
            with self._connect() as connection:
                for candidate in candidates:
                    application = self._lookup_application(connection, candidate)
                    if application:
                        return application
                alert_name = _text(payload.get("alert_name"))
                if alert_name:
                    row = connection.execute(
                        "SELECT application_code FROM alert_rule_applications WHERE alert_name = ?",
                        (alert_name,),
                    ).fetchone()
                    if row:
                        return str(row["application_code"])
        except sqlite3.Error as exc:
            raise RuntimeError("告警权限数据库不可用") from exc
        return None

    def _connect(self) -> sqlite3.Connection:
        if not self.database_path.exists():
            raise RuntimeError(f"权限数据库不存在: {self.database_path}")
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _lookup_application(connection: sqlite3.Connection, value: str) -> str | None:
        normalized = value.strip().lower()
        row = connection.execute(
            "SELECT application_code FROM applications WHERE application_code = ? AND enabled = 1",
            (normalized,),
        ).fetchone()
        if row:
            return str(row["application_code"])
        row = connection.execute(
            """
            SELECT alias.application_code
            FROM application_aliases AS alias
            JOIN applications AS application
              ON application.application_code = alias.application_code
            WHERE alias.alias = ? AND application.enabled = 1
            """,
            (value,),
        ).fetchone()
        return str(row["application_code"]) if row else None


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return value if isinstance(value, dict) else {}


def _normalize_username(value: str) -> str:
    return str(value or "").strip().casefold()


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""
