"""Agent 运行租约：把业务完成状态与 LangGraph checkpoint 关联起来。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.agents.alert_analysis_agent import resolve_agent_run_id
from app.schemas.alert import RawAlert


class AgentRunRegistry:
    """按 alert_id 保存当前未完成 run，避免重试误建新 thread。"""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    async def acquire(
        self,
        alert: RawAlert,
        *,
        alert_id: str,
        formal_output_exists: bool,
    ) -> str:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        fingerprint = resolve_agent_run_id(
            alert,
            alert_id=alert_id,
            formal_output_exists=False,
        )
        async with aiosqlite.connect(self.database_path) as database:
            await self._setup(database)
            await database.execute("BEGIN IMMEDIATE")
            cursor = await database.execute(
                """
                SELECT run_id, input_fingerprint, status
                FROM agent_run_registry
                WHERE alert_id = ?
                """,
                (alert_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()
            if row and row[2] == "running" and row[1] == fingerprint:
                await database.commit()
                return str(row[0])

            run_id = resolve_agent_run_id(
                alert,
                alert_id=alert_id,
                formal_output_exists=formal_output_exists,
            )
            now = datetime.now(timezone.utc).isoformat()
            await database.execute(
                """
                INSERT INTO agent_run_registry (
                    alert_id, run_id, input_fingerprint, status, updated_at
                ) VALUES (?, ?, ?, 'running', ?)
                ON CONFLICT(alert_id) DO UPDATE SET
                    run_id = excluded.run_id,
                    input_fingerprint = excluded.input_fingerprint,
                    status = 'running',
                    updated_at = excluded.updated_at
                """,
                (alert_id, run_id, fingerprint, now),
            )
            await database.commit()
            return run_id

    async def mark_completed(self, alert_id: str, run_id: str) -> None:
        if not self.database_path.exists():
            return
        async with aiosqlite.connect(self.database_path) as database:
            await self._setup(database)
            await database.execute(
                """
                UPDATE agent_run_registry
                SET status = 'completed', updated_at = ?
                WHERE alert_id = ? AND run_id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), alert_id, run_id),
            )
            await database.commit()

    @staticmethod
    async def _setup(database: aiosqlite.Connection) -> None:
        await database.execute("PRAGMA busy_timeout = 5000")
        await database.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_run_registry (
                alert_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                input_fingerprint TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await database.commit()
