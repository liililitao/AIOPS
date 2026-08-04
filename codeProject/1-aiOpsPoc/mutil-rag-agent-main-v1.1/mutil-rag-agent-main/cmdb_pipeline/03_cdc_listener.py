#!/usr/bin/env python3
"""步骤 3: CDC 变更监听 — 模拟 Flink CDC 读取 PostgreSQL 变更.

真实生产环境:
  Flink CDC 连接器直接读 PostgreSQL 的 WAL (Write-Ahead Log),
  不需要触发器、不需要额外表。实时性毫秒级。

本脚本 (学习用途):
  用 psycopg2 的 NOTIFY/LISTEN + 轮询 cmdb_change_log 来模拟 CDC 效果。
  让你直观理解 "数据库变更 → 被外部程序捕获 → 转成事件" 的过程。

启动方式:
  # 终端 1: 启动 CDC 监听
  python cmdb_pipeline/03_cdc_listener.py

  # 终端 2: 做 CRUD 操作
  python cmdb_pipeline/02_crud_operations.py

  → 终端 1 会实时打印捕获到的变更事件
"""

import sys
import time
import json
import threading
import psycopg2
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "cmdb",
    "user": "cmdb_admin",
    "password": "cmdb_pass_2024",
}

# 最后读取的变更日志 ID (模拟 Flink CDC 的 offset)
_last_log_id = 0


def get_last_log_id(conn):
    """获取当前最大的变更日志 ID."""
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id), 0) FROM cmdb_change_log")
        return cur.fetchone()[0]


def poll_changes(conn, last_id):
    """轮询 cmdb_change_log, 返回 last_id 之后的新增记录."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, device_id, operation, old_data, new_data, changed_at
            FROM cmdb_change_log
            WHERE id > %s
            ORDER BY id
        """, (last_id,))
        return cur.fetchall()


def format_event(row):
    """把数据库行转成类 Kafka 事件格式."""
    eid, device_id, operation, old_data, new_data, changed_at = row
    return {
        "event_id": eid,
        "device_id": device_id,
        "operation": operation,
        "old_data": old_data,
        "new_data": new_data,
        "changed_at": str(changed_at),
        "source": "cmdb_change_log",
        "captured_at": datetime.now().isoformat(),
    }


def listen_notify(conn, stop_event):
    """用 PostgreSQL NOTIFY/LISTEN 机制实时感知变更.

    触发器在每次变更后发送 NOTIFY, 这里收到通知后立即轮询.
    """
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("LISTEN cmdb_change_channel;")

    while not stop_event.is_set():
        # poll() 会阻塞最多 1 秒等通知
        conn.poll()
        while conn.notifies:
            notify = conn.notifies.pop(0)
            yield notify


def main():
    global _last_log_id

    print("=" * 60)
    print("步骤 3: CDC 变更监听器 (模拟 Flink CDC)")
    print("=" * 60)
    print()
    print("工作原理:")
    print("  1. 连接 PostgreSQL, 记录当前变更日志位置")
    print("  2. 每 1 秒轮询 cmdb_change_log, 获取新变更")
    print("  3. 把变更转成 JSON 事件格式 (和生产环境 Flink CDC 输出一致)")
    print()
    print("现在请另开一个终端, 运行:")
    print("  python cmdb_pipeline/02_crud_operations.py")
    print()
    print("按 Ctrl+C 停止监听")
    print("=" * 60)
    print()

    conn = connect()
    _last_log_id = get_last_log_id(conn)
    print(f"[CDC] 已连接 PostgreSQL, 起始 offset = {_last_log_id}")
    print(f"[CDC] 等待变更...\n")

    try:
        while True:
            time.sleep(1)  # 每秒轮询一次 (生产环境用 WAL 不需要轮询)

            changes = poll_changes(conn, _last_log_id)
            for row in changes:
                event = format_event(row)
                _last_log_id = row[0]

                # 格式化打印
                op = event["operation"]
                icon = {"INSERT": "[+]", "UPDATE": "[*]", "DELETE": "[-]"}.get(op, "[?]")
                ts = event["changed_at"][:19] if event["changed_at"] else "?"

                print(f"  {icon} [{op:<6}] {ts}  device_id={event['device_id']}")

                if op == "INSERT":
                    new = event.get("new_data", {}) or {}
                    print(f"         新增: {new.get('hostname', '?')} / {new.get('app_name', '?')}")
                elif op == "UPDATE":
                    old = event.get("old_data", {}) or {}
                    new = event.get("new_data", {}) or {}
                    if old.get("owner") != new.get("owner"):
                        print(f"         负责人变更: {old.get('owner','?')} → {new.get('owner','?')}")
                    if old.get("business_level") != new.get("business_level"):
                        print(f"         业务等级调整: {old.get('business_level','?')} → {new.get('business_level','?')}")
                elif op == "DELETE":
                    old = event.get("old_data", {}) or {}
                    print(f"         删除: {old.get('hostname', '?')} / {old.get('ip', '?')}")

                # 打印完整 JSON (和生产环境的 Kafka 消息格式一致)
                print(f"         [事件JSON] {json.dumps(event, ensure_ascii=False)}")
                print()

    except KeyboardInterrupt:
        print(f"\n[CDC] 已停止, 最后 offset = {_last_log_id}")
    finally:
        conn.close()


def connect():
    return psycopg2.connect(**DB_CONFIG)


if __name__ == "__main__":
    main()
