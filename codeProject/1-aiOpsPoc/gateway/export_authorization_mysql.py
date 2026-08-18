"""Export the AIOps SQLite authorization database as MySQL 8 SQL.

The generated file creates only the AIOps authorization schema and its data.
MySQL users, passwords, and network permissions are intentionally handled by
the separate server bootstrap step.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


TABLES = (
    "applications",
    "application_aliases",
    "alert_rule_applications",
    "user_roles",
    "user_application_permissions",
)

SCHEMA = """
CREATE DATABASE IF NOT EXISTS `aiops`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `aiops`;

CREATE TABLE IF NOT EXISTS `applications` (
  `application_code` VARCHAR(100) NOT NULL,
  `display_name` VARCHAR(255) NOT NULL,
  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`application_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `application_aliases` (
  `alias` VARCHAR(255) NOT NULL,
  `application_code` VARCHAR(100) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`alias`),
  CONSTRAINT `fk_alias_application`
    FOREIGN KEY (`application_code`) REFERENCES `applications` (`application_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `alert_rule_applications` (
  `alert_name` VARCHAR(255) NOT NULL,
  `application_code` VARCHAR(100) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`alert_name`),
  CONSTRAINT `fk_rule_application`
    FOREIGN KEY (`application_code`) REFERENCES `applications` (`application_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `user_roles` (
  `username` VARCHAR(255) NOT NULL,
  `role` ENUM('admin', 'user') NOT NULL,
  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `user_application_permissions` (
  `username` VARCHAR(255) NOT NULL,
  `application_code` VARCHAR(100) NOT NULL,
  `granted_by` VARCHAR(255) NOT NULL DEFAULT 'admin',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`username`, `application_code`),
  KEY `idx_user_application_permissions_app` (`application_code`),
  CONSTRAINT `fk_permission_user`
    FOREIGN KEY (`username`) REFERENCES `user_roles` (`username`) ON DELETE CASCADE,
  CONSTRAINT `fk_permission_application`
    FOREIGN KEY (`application_code`) REFERENCES `applications` (`application_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
""".strip()


def mysql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


def insert_statement(table: str, row: sqlite3.Row) -> str:
    columns = list(row.keys())
    fields = ", ".join(f"`{column}`" for column in columns)
    values = ", ".join(mysql_literal(row[column]) for column in columns)
    updates = ", ".join(f"`{column}` = VALUES(`{column}`)" for column in columns if column not in {"created_at"})
    return f"INSERT INTO `{table}` ({fields}) VALUES ({values}) ON DUPLICATE KEY UPDATE {updates};"


def export_database(source: Path) -> str:
    connection = sqlite3.connect(source)
    connection.row_factory = sqlite3.Row
    try:
        lines = ["-- Generated from the AIOps SQLite authorization database.", "SET NAMES utf8mb4;", SCHEMA, ""]
        for table in TABLES:
            rows = connection.execute(f"SELECT * FROM {table}").fetchall()
            lines.append(f"-- {table}: {len(rows)} row(s)")
            lines.extend(insert_statement(table, row) for row in rows)
            lines.append("")
        return "\n".join(lines)
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export AIOps authorization SQLite data for MySQL 8")
    parser.add_argument("--source", type=Path, default=Path("data/aiops_authorization.sqlite3"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"SQLite database not found: {args.source}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(export_database(args.source), encoding="utf-8", newline="\n")
    print(f"exported: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
