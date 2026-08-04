#!/usr/bin/env python3
"""步骤 5: Kafka Consumer — 消费变更事件, 写入本地缓存 (模拟 Flink → OpenSearch).

生产环境:
  Flink 从 Kafka 消费 → 加工清洗 → 写入 OpenSearch
  Agent 的 query_cmdb() 读 OpenSearch (毫秒级)

本脚本 (学习用途):
  从 Kafka 消费 → 写入本地 Python 字典缓存 (模拟 OpenSearch)
  让你直观理解 "Kafka 消息 → 下游缓存更新" 的过程

启动方式:
  # 终端 1: 启动 Consumer (这个脚本)
  python cmdb_pipeline/05_kafka_consumer.py

  # 终端 2: 启动 Producer
  python cmdb_pipeline/04_kafka_producer.py

  # 终端 3: 做 CRUD
  python cmdb_pipeline/02_crud_operations.py

  → Consumer 会实时打印从 Kafka 收到的变更并更新本地缓存
"""

import sys
import json
import time
import threading
from datetime import datetime

try:
    from kafka import KafkaConsumer
    from kafka.errors import NoBrokersAvailable
except ImportError:
    print("请先安装: pip install kafka-python")
    sys.exit(1)

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "cmdb.devices.change"

# ---- 本地缓存 (模拟 OpenSearch 中的 CMDB 快照) ----
# 生产环境中这是 OpenSearch 索引, 查询延迟 < 10ms
cmdb_cache: dict[str, dict] = {}
cache_lock = threading.Lock()


def apply_change(payload: dict) -> dict | None:
    """把一条 CDC 事件应用到本地缓存.

    Returns:
        变更摘要, 用于打印
    """
    op = payload.get("op", "")
    before = payload.get("before") or {}
    after = payload.get("after") or {}

    device_id = str(payload.get("device_id", ""))
    source_info = payload.get("source", {})

    with cache_lock:
        if op in ("c", "INSERT", "create"):
            # INSERT: 新记录加入缓存
            cmdb_cache[device_id] = after
            return {
                "action": "INSERT",
                "device_id": device_id,
                "hostname": after.get("hostname", "?"),
                "app_name": after.get("app_name", "?"),
                "cache_size": len(cmdb_cache),
            }

        elif op in ("u", "UPDATE", "update"):
            # UPDATE: 覆盖旧记录
            old_host = cmdb_cache.get(device_id, {}).get("hostname", "?")
            cmdb_cache[device_id] = after if after else before
            return {
                "action": "UPDATE",
                "device_id": device_id,
                "hostname": after.get("hostname", old_host),
                "cache_size": len(cmdb_cache),
            }

        elif op in ("d", "DELETE", "delete"):
            # DELETE: 从缓存中移除
            removed = cmdb_cache.pop(device_id, None)
            return {
                "action": "DELETE",
                "device_id": device_id,
                "hostname": (removed or before).get("hostname", "?"),
                "cache_size": len(cmdb_cache),
            }

    return None


def init_cache_from_pg():
    """从 PostgreSQL 加载全量 CMDB 数据到本地缓存.

    生产环境中, OpenSearch 首次启动时会从 PostgreSQL 做全量同步 (snapshot),
    之后再通过 Kafka 增量更新.
    """
    try:
        import psycopg2
    except ImportError:
        print("[Consumer] psycopg2 未安装, 跳过初始加载")
        return

    DB_CONFIG = {
        "host": "localhost", "port": 5433,
        "dbname": "cmdb", "user": "cmdb_admin", "password": "cmdb_pass_2024",
    }
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM cmdb_devices")
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                record = dict(zip(cols, row))
                # 把 datetime 转成字符串以支持 JSON 序列化
                for k, v in record.items():
                    if isinstance(v, datetime):
                        record[k] = str(v)
                with cache_lock:
                    cmdb_cache[str(record["id"])] = record
        conn.close()
        print(f"[Consumer] 从 PostgreSQL 加载了 {len(cmdb_cache)} 条设备记录")
    except Exception as e:
        print(f"[Consumer] PostgreSQL 连接失败 ({e}), 缓存从空开始")


def create_consumer():
    """创建 Kafka Consumer."""
    print(f"[Consumer] 连接 Kafka {KAFKA_BOOTSTRAP}, Topic={KAFKA_TOPIC}...")
    for attempt in range(10):
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id="cmdb-cache-sync",        # 消费组
                auto_offset_reset="latest",         # 从最新消息开始
                enable_auto_commit=True,            # 自动提交 offset
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                consumer_timeout_ms=1000,           # 每 1 秒超时以便检查退出
            )
            print(f"  [OK] 连接成功, 消费组=cmdb-cache-sync")
            return consumer
        except NoBrokersAvailable:
            if attempt < 9:
                print(f"  等待 Kafka 启动... ({attempt+1}/10)")
                time.sleep(3)
            else:
                raise
    return None


def search_cache(ip: str = "", hostname: str = "") -> dict | None:
    """从本地缓存中查询设备 (模拟 OpenSearch 查询)."""
    with cache_lock:
        for record in cmdb_cache.values():
            if ip and record.get("ip") == ip:
                return record
            if hostname and record.get("hostname") == hostname:
                return record
    return None


def main():
    print("=" * 60)
    print("步骤 5: Kafka Consumer — 变更事件 → 本地缓存")
    print("=" * 60)
    print()
    print("生产环境对应:")
    print("  本脚本           →  Flink 流处理作业")
    print("  cmdb_cache       →  OpenSearch 索引")
    print("  search_cache()   →  Agent 的 query_cmdb() 查询")
    print()

    # 1. 从 PostgreSQL 全量加载初始数据
    init_cache_from_pg()

    # 2. 创建 Kafka Consumer
    consumer = create_consumer()
    if consumer is None:
        print("[FAIL] Kafka 不可用, 请先启动: docker compose -f cmdb_pipeline/docker-compose.cmdb.yml up -d")
        sys.exit(1)

    print(f"\n[Consumer] 开始消费 Topic={KAFKA_TOPIC}...")
    print(f"[Consumer] 当前缓存大小: {len(cmdb_cache)}")
    print(f"[Consumer] 等待 Producer 推送变更...")
    print(f"[Consumer] 按 Ctrl+C 停止\n")

    consumed = 0
    try:
        for message in consumer:
            consumed += 1
            value = message.value
            payload = value.get("payload", value)  # 兼容两种格式

            result = apply_change(payload)

            if result:
                action_icons = {"INSERT": "[+]", "UPDATE": "[*]", "DELETE": "[-]"}
                icon = action_icons.get(result["action"], "[?]")
                print(f"  {icon} [{result['action']:<6}] "
                      f"Kafka offset={message.offset} "
                      f"device={result['device_id']} "
                      f"({result['hostname']}) "
                      f"缓存={result['cache_size']} 条")

            # 每收到一条就演示一次缓存查询
            if consumed <= 3:
                demo_ip = (payload.get("after") or {}).get("ip", "")
                if demo_ip:
                    record = search_cache(ip=demo_ip)
                    if record:
                        print(f"         [验证查询] query_cmdb(ip={demo_ip}) → "
                              f"{record.get('hostname')} / {record.get('app_name')}")
                print()

    except KeyboardInterrupt:
        print(f"\n[Consumer] 已停止, 共消费 {consumed} 条消息")
        print(f"[Consumer] 最终缓存: {len(cmdb_cache)} 条设备记录")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
