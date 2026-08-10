"""Application-level alert authorization for the AIOps gateway.

The source of identity remains Splunk.  This module only stores the AIOps
role and the applications that each authenticated Splunk user may access.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any


APPLICATIONS = (
    ("iwe", "iWE"),
    ("wecall", "WeCall"),
    ("pmt", "PMT for S&D"),
    ("dspot", "D.Spot"),
    ("rared", "RareD NovoCare"),
    ("novocare_diabetes", "NovoCare Diabetes"),
    ("budget_tool", "Budget Tool"),
)

APPLICATION_ALIASES = (
    ("iwe", "iwe"),
    ("iWE", "iwe"),
    ("wecall", "wecall"),
    ("WeCall", "wecall"),
    ("pmt", "pmt"),
    ("PMT for S&D", "pmt"),
    ("dspot", "dspot"),
    ("D.Spot", "dspot"),
    ("rared", "rared"),
    ("RareD NovoCare", "rared"),
    ("novocare_diabetes", "novocare_diabetes"),
    ("NovoCare Diabetes", "novocare_diabetes"),
    ("budget_tool", "budget_tool"),
    ("Budget Tool", "budget_tool"),
)

ALERT_RULE_APPLICATIONS = (
    ("app_alert_iwe_Login_Failed", "iwe"),
    ("app_alert_iwe_Data_Docking_Failure", "iwe"),
    ("app_alert_wecall_Password_Verification_Failed", "wecall"),
    ("app_alert_pmt_Dif_Light", "pmt"),
    ("app_alert_pmt_Login_Failed", "pmt"),
    ("app_alert_pmt_Token_Invalid", "pmt"),
    ("app_alert_dspot_Login_Failed", "dspot"),
    ("app_alert_dspot_Export_Failed", "dspot"),
    ("app_alert_rared_Add_Role", "rared"),
    ("app_alert_rared_Edit_Points", "rared"),
    ("app_alert_rared_PII_export", "rared"),
    ("app_alert_novocare_diabetes_Change_of_Role_Privileges", "novocare_diabetes"),
    ("app_alert_novocare_diabetes_Modify_User", "novocare_diabetes"),
    ("app_alert_novocare_diabetes_User_Data_Export", "novocare_diabetes"),
    ("app_alert_budget_tool_Login_Failed", "budget_tool"),
    ("app_alert_budget_tool_System_Error", "budget_tool"),
)


@dataclass(frozen=True)
class UserAccess:
    username: str
    role: str
    application_codes: frozenset[str]

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def default_database_path() -> str:
    configured = os.environ.get("AIOPS_AUTHZ_DB", "").strip()
    if configured:
        return configured
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "aiops_authorization.sqlite3"
    )


def normalize_username(username: str) -> str:
    return str(username or "").strip().casefold()


class AuthorizationStore:
    """SQLite-backed user-to-application authorization store."""

    def __init__(self, database_path: str):
        self.database_path = os.path.abspath(database_path)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        directory = os.path.dirname(self.database_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS applications (
                    application_code TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS application_aliases (
                    alias TEXT PRIMARY KEY COLLATE NOCASE,
                    application_code TEXT NOT NULL REFERENCES applications(application_code),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS alert_rule_applications (
                    alert_name TEXT PRIMARY KEY COLLATE NOCASE,
                    application_code TEXT NOT NULL REFERENCES applications(application_code),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_roles (
                    username TEXT PRIMARY KEY COLLATE NOCASE,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
                    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_application_permissions (
                    username TEXT NOT NULL COLLATE NOCASE REFERENCES user_roles(username) ON DELETE CASCADE,
                    application_code TEXT NOT NULL REFERENCES applications(application_code),
                    granted_by TEXT NOT NULL DEFAULT 'admin',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (username, application_code)
                );

                CREATE INDEX IF NOT EXISTS idx_user_application_permissions_app
                    ON user_application_permissions(application_code);
                """
            )
            connection.executemany(
                """
                INSERT INTO applications(application_code, display_name)
                VALUES (?, ?)
                ON CONFLICT(application_code) DO UPDATE SET
                    display_name = excluded.display_name
                """,
                APPLICATIONS,
            )
            connection.executemany(
                """
                INSERT INTO application_aliases(alias, application_code)
                VALUES (?, ?)
                ON CONFLICT(alias) DO UPDATE SET
                    application_code = excluded.application_code
                """,
                APPLICATION_ALIASES,
            )
            connection.executemany(
                """
                INSERT INTO alert_rule_applications(alert_name, application_code)
                VALUES (?, ?)
                ON CONFLICT(alert_name) DO UPDATE SET
                    application_code = excluded.application_code
                """,
                ALERT_RULE_APPLICATIONS,
            )
            connection.execute(
                """
                INSERT INTO user_roles(username, role)
                VALUES ('admin', 'admin')
                ON CONFLICT(username) DO NOTHING
                """
            )

    def user_access(self, username: str) -> UserAccess:
        normalized = normalize_username(username)
        if not normalized:
            return UserAccess(username="", role="user", application_codes=frozenset())

        with self._connection() as connection:
            role_row = connection.execute(
                """
                SELECT role
                FROM user_roles
                WHERE username = ? AND enabled = 1
                """,
                (normalized,),
            ).fetchone()
            if role_row is None:
                return UserAccess(
                    username=normalized, role="user", application_codes=frozenset()
                )
            application_rows = connection.execute(
                """
                SELECT permission.application_code
                FROM user_application_permissions AS permission
                JOIN applications AS application
                    ON application.application_code = permission.application_code
                WHERE permission.username = ? AND application.enabled = 1
                ORDER BY permission.application_code
                """,
                (normalized,),
            ).fetchall()

        return UserAccess(
            username=normalized,
            role=str(role_row["role"]),
            application_codes=frozenset(row["application_code"] for row in application_rows),
        )

    def grant(self, username: str, application_code: str, granted_by: str = "admin") -> None:
        normalized = normalize_username(username)
        if not normalized:
            raise ValueError("username must not be empty")
        application = self._require_application(application_code)

        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO user_roles(username, role)
                VALUES (?, 'user')
                ON CONFLICT(username) DO NOTHING
                """,
                (normalized,),
            )
            connection.execute(
                """
                INSERT INTO user_application_permissions(username, application_code, granted_by)
                VALUES (?, ?, ?)
                ON CONFLICT(username, application_code) DO UPDATE SET
                    granted_by = excluded.granted_by
                """,
                (normalized, application, normalize_username(granted_by) or "admin"),
            )

    def revoke(self, username: str, application_code: str) -> bool:
        normalized = normalize_username(username)
        application = self._require_application(application_code)
        with self._connection() as connection:
            result = connection.execute(
                """
                DELETE FROM user_application_permissions
                WHERE username = ? AND application_code = ?
                """,
                (normalized, application),
            )
        return result.rowcount > 0

    def set_role(self, username: str, role: str) -> None:
        normalized = normalize_username(username)
        normalized_role = str(role or "").strip().lower()
        if not normalized:
            raise ValueError("username must not be empty")
        if normalized_role not in {"admin", "user"}:
            raise ValueError("role must be 'admin' or 'user'")

        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO user_roles(username, role, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(username) DO UPDATE SET
                    role = excluded.role,
                    enabled = 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (normalized, normalized_role),
            )

    def resolve_task_application(self, task: dict[str, Any]) -> str | None:
        payload = task.get("payload") if isinstance(task, dict) else None
        payload = payload if isinstance(payload, dict) else {}

        alert_name = self._first_value(
            payload.get("alertname"),
            task.get("alertname") if isinstance(task, dict) else None,
        )
        if alert_name:
            application = self._lookup(
                "SELECT application_code FROM alert_rule_applications WHERE alert_name = ?",
                alert_name,
            )
            if application:
                return application

        for candidate in (
            payload.get("application_code"),
            payload.get("application"),
            payload.get("app_code"),
            payload.get("service"),
            task.get("service") if isinstance(task, dict) else None,
        ):
            value = self._first_value(candidate)
            if not value:
                continue
            application = self._lookup(
                "SELECT application_code FROM application_aliases WHERE alias = ?",
                value,
            )
            if application:
                return application
        return None

    def can_access_task(self, username: str, task: dict[str, Any]) -> bool:
        access = self.user_access(username)
        if access.is_admin:
            return True
        application = self.resolve_task_application(task)
        return application is not None and application in access.application_codes

    def list_applications(self) -> list[tuple[str, str]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT application_code, display_name
                FROM applications
                WHERE enabled = 1
                ORDER BY application_code
                """
            ).fetchall()
        return [(row["application_code"], row["display_name"]) for row in rows]

    def _require_application(self, application_code: str) -> str:
        normalized = str(application_code or "").strip().lower()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT application_code
                FROM applications
                WHERE application_code = ? AND enabled = 1
                """,
                (normalized,),
            ).fetchone()
        if row is None:
            valid = ", ".join(code for code, _ in self.list_applications())
            raise ValueError(f"unknown application '{application_code}', valid values: {valid}")
        return str(row["application_code"])

    def _lookup(self, query: str, value: str) -> str | None:
        with self._connection() as connection:
            row = connection.execute(query, (value,)).fetchone()
        return str(row["application_code"]) if row else None

    @staticmethod
    def _first_value(*values: Any) -> str:
        for value in values:
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""


def _main() -> int:
    parser = argparse.ArgumentParser(description="Manage AIOps alert application permissions")
    parser.add_argument("--db", default=default_database_path(), help="SQLite database path")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create tables and seed applications/rules/admin")

    grant = commands.add_parser("grant", help="Grant a user access to an application")
    grant.add_argument("username")
    grant.add_argument("application_code")
    grant.add_argument("--granted-by", default="admin")

    revoke = commands.add_parser("revoke", help="Remove a user's access to an application")
    revoke.add_argument("username")
    revoke.add_argument("application_code")

    role = commands.add_parser("set-role", help="Set a user's AIOps role")
    role.add_argument("username")
    role.add_argument("role", choices=("admin", "user"))

    show_user = commands.add_parser("show-user", help="Show a user's effective access")
    show_user.add_argument("username")
    commands.add_parser("list-applications", help="List valid application codes")

    args = parser.parse_args()
    store = AuthorizationStore(args.db)

    if args.command == "init":
        print(f"initialized: {store.database_path}")
    elif args.command == "grant":
        store.grant(args.username, args.application_code, args.granted_by)
        print(f"granted {args.username} -> {args.application_code}")
    elif args.command == "revoke":
        removed = store.revoke(args.username, args.application_code)
        print("revoked" if removed else "permission did not exist")
    elif args.command == "set-role":
        store.set_role(args.username, args.role)
        print(f"role updated: {args.username} -> {args.role}")
    elif args.command == "show-user":
        access = store.user_access(args.username)
        applications = ", ".join(sorted(access.application_codes)) or "(none)"
        print(f"username={access.username}\nrole={access.role}\napplications={applications}")
    elif args.command == "list-applications":
        for code, name in store.list_applications():
            print(f"{code}\t{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
