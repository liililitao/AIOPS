#!/usr/bin/env python3
"""步骤 1: 启动 PostgreSQL 并初始化 CMDB 数据.

前置条件:
  docker compose -f cmdb_pipeline/docker-compose.cmdb.yml up -d

本脚本做的事:
  1. 验证 PostgreSQL 连接
  2. 检查 cmdb_devices 表是否存在
  3. 打印当前 CMDB 数据供确认
"""

import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("请先安装 psycopg2: pip install psycopg2-binary")
    sys.exit(1)

# ---- 数据库连接配置 (与 docker-compose.cmdb.yml 对齐) ----
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "cmdb",
    "user": "cmdb_admin",
    "password": "cmdb_pass_2024",
}


def connect():
    return psycopg2.connect(**DB_CONFIG)


def check_tables(conn):
    """检查表是否存在."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [r[0] for r in cur.fetchall()]
        print(f"  已存在的表: {tables}")
        return tables


def show_devices(conn):
    """展示所有 CMDB 设备."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ip, hostname, app_name, owner, env, business_level
            FROM cmdb_devices
            ORDER BY id
        """)
        rows = cur.fetchall()
        print(f"\n  CMDB 设备列表 ({len(rows)} 条):")
        print(f"  {'IP':<16} {'主机名':<18} {'应用':<14} {'负责人':<6} {'环境':<6} {'业务等级'}")
        print(f"  {'-'*16} {'-'*18} {'-'*14} {'-'*6} {'-'*6} {'-'*8}")
        for r in rows:
            print(f"  {r[0]:<16} {r[1]:<18} {r[2]:<14} {r[3]:<6} {r[4]:<6} {r[5]}")
        return rows


def show_change_log(conn):
    """展示最近的变更日志."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, device_id, operation, changed_at
            FROM cmdb_change_log
            ORDER BY id DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            print(f"\n  最近变更日志 ({len(rows)} 条):")
            for r in rows:
                print(f"    #{r[0]} device={r[1]} op={r[2]} at={r[3]}")
        else:
            print("\n  变更日志: (空)")


def main():
    print("=" * 60)
    print("步骤 1: CMDB 数据库初始化验证")
    print("=" * 60)

    # 1. 连接
    print("\n[1] 连接 PostgreSQL (localhost:5433)...")
    try:
        conn = connect()
        print("  [OK] 连接成功")
    except Exception as e:
        print(f"  [FAIL] 连接失败: {e}")
        print("\n  请确认 Docker 已启动:")
        print("    docker compose -f cmdb_pipeline/docker-compose.cmdb.yml up -d")
        sys.exit(1)

    # 2. 检查表
    print("\n[2] 检查数据表...")
    tables = check_tables(conn)
    required = ["cmdb_devices", "cmdb_change_log"]
    missing = [t for t in required if t not in tables]
    if missing:
        print(f"  [FAIL] 缺少表: {missing}")
        print("  请检查 sql/init_cmdb.sql 是否正确挂载")
    else:
        print("  [OK] 所有表已就绪")

    # 3. 展示数据
    print("\n[3] 查询 CMDB 数据...")
    devices = show_devices(conn)

    show_change_log(conn)

    conn.close()
    print("\n" + "=" * 60)
    print("初始化验证完成! 运行下一步: python cmdb_pipeline/02_crud_operations.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
