#!/usr/bin/env python3
"""步骤 6: CMDB 查询工具 — Agent 实际调用的 query_cmdb() 函数.

本脚本展示了 Agent 是如何查 CMDB 的:

查询优先级 (和现实生产环境一致):
  1. 本地缓存 (OpenSearch / Python dict)  — 毫秒级, 不打 PostgreSQL
  2. PostgreSQL 直查                       — 缓存 miss 时的回源

和当前项目 app/tools/cmdb_tool.py 的关系:
  当前: _MOCK_CMDB = {"10.0.1.101": {...}}  (硬编码字典)
  升级后: 先查缓存(缓存由Kafka实时同步) → 缓存miss → 查 PostgreSQL

这就是 "Flink+Kafka 对 Agent 透明" 的具体体现:
  Agent 不知道缓存是 Kafka 同步的, 它只知道缓存里有数据.
"""

import sys
from datetime import datetime

# ---- 模拟的本地缓存 (05_kafka_consumer.py 维护) ----
# 生产环境: OpenSearch 索引, 由 Flink 实时同步
_cache = {}


def init_cache(records: list[dict]):
    """初始化缓存 (Consumer 调用)."""
    global _cache
    _cache = {r.get("ip", ""): r for r in records if r.get("ip")}


def update_cache(ip: str, record: dict | None):
    """更新缓存 (Consumer 在收到 Kafka 消息后调用).

    record=None 表示删除.
    """
    if record is None:
        _cache.pop(ip, None)
    else:
        _cache[ip] = record


# ============================================================
# Agent 实际调用的函数 — 接口和 app/tools/cmdb_tool.py 完全相同
# ============================================================
def query_cmdb(ip: str = "", hostname: str = "") -> str:
    """查询 CMDB 获取设备信息。Agent 会调用这个函数.

    查询路径:
      1. 先查本地缓存 (由 Kafka → Consumer 实时同步)
      2. 缓存 miss → 查 PostgreSQL (回源)
      3. PostgreSQL 也 miss → 返回 "未知设备"

    Args:
        ip: 设备 IP
        hostname: 主机名 (与 ip 二选一)

    Returns:
        Markdown 格式的设备信息
    """
    record = None
    source = ""

    # ---- 路径 1: 查本地缓存 ----
    if ip and ip in _cache:
        record = _cache[ip]
        source = "缓存 (Kafka 同步)"
    elif hostname:
        for r in _cache.values():
            if r.get("hostname") == hostname:
                record = r
                source = "缓存 (Kafka 同步)"
                break

    # ---- 路径 2: 缓存 miss, 回源 PostgreSQL ----
    if record is None:
        record = _query_postgres(ip, hostname)
        if record:
            source = "PostgreSQL (回源)"
            # 回源后写入缓存, 下次命中的就是缓存
            if record.get("ip"):
                _cache[record["ip"]] = record

    # ---- 路径 3: 完全没有 ----
    if record is None:
        return (f"## CMDB 查询结果\n\n"
                f"未找到设备信息。查询条件: ip={ip or '(无)'}, hostname={hostname or '(无)'}\n\n"
                f"请确认设备是否已在 CMDB 中注册。")

    return _format_result(record, source)


def _query_postgres(ip: str = "", hostname: str = "") -> dict | None:
    """回源 PostgreSQL 查询.

    生产环境: 这个函数应该在 95%+ 的情况下不被触发 (缓存命中率 > 95%).
    """
    try:
        import psycopg2
    except ImportError:
        return None

    DB_CONFIG = {
        "host": "localhost", "port": 5433,
        "dbname": "cmdb", "user": "cmdb_admin", "password": "cmdb_pass_2024",
    }

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            if ip:
                cur.execute("SELECT * FROM cmdb_devices WHERE ip = %s", (ip,))
            elif hostname:
                cur.execute("SELECT * FROM cmdb_devices WHERE hostname = %s", (hostname,))
            else:
                return None
            row = cur.fetchone()
            if row:
                cols = [d[0] for d in cur.description]
                record = dict(zip(cols, row))
                for k, v in record.items():
                    if isinstance(v, datetime):
                        record[k] = str(v)
                return record
        conn.close()
    except Exception:
        pass
    return None


def _format_result(record: dict, source: str) -> str:
    """格式化为 Markdown (和 app/tools/cmdb_tool.py 输出一致)."""
    return (
        f"## CMDB 设备信息\n\n"
        f"| 字段 | 值 |\n"
        f"|---|---|\n"
        f"| 主机名 | {record.get('hostname', '?')} |\n"
        f"| IP | {record.get('ip', '?')} |\n"
        f"| 应用名称 | {record.get('app_name', '?')} |\n"
        f"| 负责人 | {record.get('owner', '?')} |\n"
        f"| 环境 | {record.get('env', '?')} |\n"
        f"| 业务等级 | {record.get('business_level', '?')} |\n"
        f"| 机房 | {record.get('room', '?')} |\n"
        f"| 操作系统 | {record.get('os', '?')} |\n"
        f"| 数据来源 | {source} |\n"
    )


# ============================================================
# 独立测试
# ============================================================
def main():
    print("=" * 60)
    print("步骤 6: CMDB 查询工具 — query_cmdb() 函数测试")
    print("=" * 60)
    print()

    # 模拟 Consumer 初始化缓存
    init_cache([
        {"ip": "10.0.1.101", "hostname": "pay-gw-01", "app_name": "支付网关服务",
         "owner": "张三", "env": "PROD", "business_level": "核心", "room": "A栋-3F-01", "os": "CentOS 7.9"},
        {"ip": "10.0.1.102", "hostname": "pay-gw-02", "app_name": "支付网关服务",
         "owner": "张三", "env": "PROD", "business_level": "核心", "room": "A栋-3F-02", "os": "CentOS 7.9"},
    ])
    print(f"缓存初始化: {len(_cache)} 条记录")

    # 测试 1: 缓存命中
    print("\n--- 测试 1: 缓存命中 ---")
    result = query_cmdb(ip="10.0.1.101")
    print(result)

    # 测试 2: 缓存 miss → 回源 PostgreSQL
    print("\n--- 测试 2: 缓存 miss → PostgreSQL 回源 ---")
    result = query_cmdb(ip="192.168.1.50")
    print(result)

    # 测试 3: 完全 miss
    print("\n--- 测试 3: 设备不存在 ---")
    result = query_cmdb(ip="1.2.3.4")
    print(result)

    # 展示缓存命中统计
    print("\n" + "=" * 60)
    print("提示: 如果上面测试 2 显示'PostgreSQL (回源)', 说明缓存 miss → PostgreSQL 兜底")
    print("     下次再查同一个 IP 就会命中缓存 (因为回源后自动写入了缓存)")
    print("=" * 60)


if __name__ == "__main__":
    main()
