#!/usr/bin/env python3
"""步骤 2: 对 CMDB 执行增删改操作, 观察变更日志.

本脚本模拟运维人员的日常 CMDB 操作:
  1. INSERT — 新增一台设备
  2. UPDATE — 修改设备信息 (负责人变更 / 升级为核心业务)
  3. DELETE — 下架一台设备

每次操作后, 自动查询 cmdb_change_log 展示触发器记录的变更.
"""

import sys
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "cmdb",
    "user": "cmdb_admin",
    "password": "cmdb_pass_2024",
}


def connect():
    return psycopg2.connect(**DB_CONFIG)


def show_table(conn, title, query):
    """执行查询并打印结果."""
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        print(f"\n  {title} ({len(rows)} 条):")
        if not rows:
            print("    (空)")
            return
        col_names = [d[0] for d in cur.description]
        print(f"    {' | '.join(col_names)}")
        print(f"    {'-' * 50}")
        for row in rows:
            print(f"    {' | '.join(str(v)[:30] for v in row)}")


def main():
    print("=" * 60)
    print("步骤 2: CMDB CRUD 操作 — 增删改 + 变更日志验证")
    print("=" * 60)

    conn = connect()
    conn.autocommit = True  # 每条语句立即提交, 便于观察

    # ---- 操作前快照 ----
    print("\n--- 操作前 ---")
    show_table(conn, "当前设备列表",
        "SELECT id, ip, hostname, app_name, owner, business_level FROM cmdb_devices ORDER BY id")

    # ============================================================
    # 操作 1: INSERT — 新加一台设备
    # ============================================================
    print("\n" + "=" * 60)
    print("操作 1: INSERT — 新增设备")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO cmdb_devices (ip, hostname, app_name, owner, env, business_level, room, os)
            VALUES ('10.0.3.50', 'aiops-test-01', 'AIOps平台', '吴十', 'TEST', '一般', 'D栋-1F-01', 'Ubuntu 24.04')
            ON CONFLICT (ip) DO UPDATE SET updated_at = NOW()
            RETURNING id, ip, hostname
        """)
        new_id, new_ip, new_host = cur.fetchone()
        print(f"  [OK] 已插入: id={new_id}  ip={new_ip}  hostname={new_host}")

    show_table(conn, "变更日志 (应该有 1 条 INSERT 记录)",
        "SELECT id, device_id, operation, changed_at FROM cmdb_change_log ORDER BY id DESC LIMIT 5")

    # ============================================================
    # 操作 2: UPDATE — 修改设备信息
    # ============================================================
    print("\n" + "=" * 60)
    print("操作 2: UPDATE — 升级业务等级 + 换负责人")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE cmdb_devices
            SET business_level = '核心',
                owner = '吴十(接管)',
                updated_at = NOW()
            WHERE ip = '192.168.1.51'
            RETURNING id, ip, business_level, owner
        """)
        row = cur.fetchone()
        if row:
            print(f"  [OK] 已更新: id={row[0]}  ip={row[1]}  →  {row[2]} / {row[3]}")
        else:
            print("  (未找到匹配记录)")

    show_table(conn, "变更日志 (应该有 INSERT + UPDATE 记录)",
        "SELECT id, device_id, operation, changed_at FROM cmdb_change_log ORDER BY id DESC LIMIT 5")

    # ============================================================
    # 操作 3: DELETE — 下架设备
    # ============================================================
    print("\n" + "=" * 60)
    print("操作 3: DELETE — 下架测试设备")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM cmdb_devices
            WHERE ip = '10.0.3.50'
            RETURNING id, ip, hostname
        """)
        row = cur.fetchone()
        if row:
            print(f"  [OK] 已删除: id={row[0]}  ip={row[1]}  hostname={row[2]}")
        else:
            print("  (未找到匹配记录)")

    show_table(conn, "变更日志 (应该有 INSERT + UPDATE + DELETE 各一条)",
        "SELECT id, device_id, operation, changed_at FROM cmdb_change_log ORDER BY id DESC LIMIT 5")

    # ---- 操作后快照 ----
    print("\n--- 操作后 ---")
    show_table(conn, "当前设备列表",
        "SELECT id, ip, hostname, app_name, owner, business_level FROM cmdb_devices ORDER BY id")

    conn.close()
    print("\n" + "=" * 60)
    print("CRUD 操作完成! 运行下一步: python cmdb_pipeline/03_cdc_listener.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
