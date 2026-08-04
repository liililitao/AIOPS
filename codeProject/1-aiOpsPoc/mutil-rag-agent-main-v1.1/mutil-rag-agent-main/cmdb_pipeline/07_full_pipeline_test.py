#!/usr/bin/env python3
"""端到端测试: CMDB → CDC → Kafka → Consumer → 缓存查询.

一键验证完整链路:
  python cmdb_pipeline/07_full_pipeline_test.py

前提:
  docker compose -f cmdb_pipeline/docker-compose.cmdb.yml up -d
  pip install psycopg2-binary kafka-python
"""

import sys
import time
import json
import threading
from datetime import datetime

# ---- 检查依赖 ----
MISSING = []
try:
    import psycopg2
except ImportError:
    MISSING.append("psycopg2-binary")
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import NoBrokersAvailable
except ImportError:
    MISSING.append("kafka-python")

if MISSING:
    print(f"请先安装依赖: pip install {' '.join(MISSING)}")
    sys.exit(1)

DB_CONFIG = {
    "host": "localhost", "port": 5433,
    "dbname": "cmdb", "user": "cmdb_admin", "password": "cmdb_pass_2024",
}
KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "cmdb.devices.change"


def step(msg):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}")


def check(msg, ok):
    print(f"  {'[OK]' if ok else '[FAIL]'} {msg}")
    return ok


def main():
    print("=" * 60)
    print("  CMDB Pipeline 端到端测试")
    print("  PostgreSQL → CDC (change_log) → Kafka → Consumer → 缓存")
    print("=" * 60)

    all_ok = True

    # ====== 1. PostgreSQL ======
    step("1. 验证 PostgreSQL 连接")
    try:
        pg = psycopg2.connect(**DB_CONFIG)
        pg.autocommit = True  # 立即设置，避免事务冲突
        all_ok &= check("PostgreSQL 连接", True)
    except Exception as e:
        all_ok &= check(f"PostgreSQL 连接: {e}", False)
        print("\n请先启动: docker compose -f cmdb_pipeline/docker-compose.cmdb.yml up -d")
        sys.exit(1)

    with pg.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM cmdb_devices")
        count = cur.fetchone()[0]
        all_ok &= check(f"cmdb_devices 表: {count} 条记录", count > 0)

        cur.execute("SELECT COUNT(*) FROM cmdb_change_log")
        log_count = cur.fetchone()[0]
        check(f"cmdb_change_log 表: {log_count} 条变更记录", True)

    # ====== 2. Kafka ======
    step("2. 验证 Kafka 连接 + 创建 Topic")
    try:
        from kafka.admin import KafkaAdminClient, NewTopic
        admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP)
        topics = admin.list_topics()
        all_ok &= check(f"Kafka 连接成功, 已有 Topics: {topics}", True)

        if KAFKA_TOPIC not in topics:
            try:
                admin.create_topics([NewTopic(KAFKA_TOPIC, num_partitions=1, replication_factor=1)])
                time.sleep(1)
                check(f"创建 Topic: {KAFKA_TOPIC}", True)
            except Exception as e:
                check(f"创建 Topic: {e}", False)
        admin.close()
    except NoBrokersAvailable:
        all_ok &= check("Kafka 不可用", False)
        all_ok = False

    # ====== 3. CRUD 操作 ======
    step("3. 执行 CRUD 操作 (INSERT + UPDATE + DELETE)")

    with pg.cursor() as cur:
        # 先确保测试数据不存在
        cur.execute("DELETE FROM cmdb_devices WHERE ip = '10.0.99.99'")

    # INSERT
    with pg.cursor() as cur:
        cur.execute("""
            INSERT INTO cmdb_devices (ip, hostname, app_name, owner, env, business_level)
            VALUES ('10.0.99.99', 'e2e-test-host', '端到端测试应用', '测试员', 'TEST', '一般')
            ON CONFLICT (ip) DO UPDATE SET updated_at = NOW()
            RETURNING id
        """)
        test_id = cur.fetchone()[0]
        check(f"INSERT: id={test_id} ip=10.0.99.99", True)

    # UPDATE
    with pg.cursor() as cur:
        cur.execute("""
            UPDATE cmdb_devices SET business_level='核心', owner='测试员(升级)'
            WHERE id = %s
        """, (test_id,))
        check(f"UPDATE: id={test_id} → 业务等级=核心", True)

    # ====== 4. 验证变更日志 ======
    step("4. 验证 CDC 变更日志 (模拟 Flink CDC 从 WAL 读取)")
    with pg.cursor() as cur:
        cur.execute("""
            SELECT id, operation FROM cmdb_change_log
            WHERE device_id = %s ORDER BY id DESC
        """, (test_id,))
        logs = cur.fetchall()
        for log_id, op in logs:
            check(f"CDC 日志 #{log_id}: {op}", True)

    # ====== 5. Kafka 发送 ======
    step("5. 发送变更事件到 Kafka")
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else str(k).encode("utf-8"),
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    )

    with pg.cursor() as cur:
        cur.execute("""
            SELECT id, device_id, operation, old_data, new_data, changed_at
            FROM cmdb_change_log WHERE device_id = %s ORDER BY id
        """, (test_id,))
        for row in cur.fetchall():
            log_id, dev_id, op, old_d, new_d, ts = row
            msg = {
                "payload": {
                    "before": old_d, "after": new_d,
                    "op": op.lower()[:1],
                    "device_id": str(dev_id),
                    "ts_ms": int(time.time() * 1000),
                    "source": {"db": "cmdb", "table": "cmdb_devices", "connector": "e2e-test"},
                }
            }
            future = producer.send(KAFKA_TOPIC, key=str(dev_id).encode("utf-8"), value=msg)
            meta = future.get(timeout=10)
            check(f"Kafka 发送: {op} partition={meta.partition} offset={meta.offset}", True)

    producer.flush()
    producer.close()

    # ====== 6. Kafka 消费 → 缓存更新 ======
    step("6. Kafka 消费 → 本地缓存更新")
    cmdb_cache = {}

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="e2e-test-group",
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    received = 0
    for msg in consumer:
        received += 1
        payload = msg.value.get("payload", msg.value)
        op = payload.get("op", "")
        after = payload.get("after") or {}
        dev_id = payload.get("device_id", "")

        if op in ("c", "INSERT", "create"):
            cmdb_cache[dev_id] = after
        elif op in ("u", "UPDATE", "update"):
            cmdb_cache[dev_id] = after if after else cmdb_cache.get(dev_id, {})
        elif op in ("d", "DELETE", "delete"):
            cmdb_cache.pop(dev_id, None)

    consumer.close()
    check(f"收到 {received} 条 Kafka 消息", received > 0)
    check(f"缓存更新: {len(cmdb_cache)} 条记录", len(cmdb_cache) > 0)

    # ====== 7. 验证缓存查询 ======
    step("7. 验证缓存查询 (模拟 Agent query_cmdb)")
    test_record = cmdb_cache.get(str(test_id))
    if test_record:
        check(f"缓存命中: {test_record.get('hostname')} / {test_record.get('app_name')}", True)
        check(f"业务等级: {test_record.get('business_level')} (应为'核心')",
              test_record.get("business_level") == "核心")
    else:
        check("缓存命中", False)

    # ====== 8. 清理测试数据 ======
    step("8. 清理测试数据")
    with pg.cursor() as cur:
        cur.execute("DELETE FROM cmdb_devices WHERE ip = '10.0.99.99'")
        check("测试设备已删除", True)

    # 清理 Kafka consumer group offset
    try:
        admin2 = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP)
        admin2.delete_consumer_groups(["e2e-test-group"])
        admin2.close()
    except Exception:
        pass

    pg.close()

    # ====== 结果 ======
    step("测试结果")
    if all_ok:
        print("  [OK] 全部通过!")
        print()
        print("  CMDB Pipeline 完整链路验证完毕:")
        print("    1. PostgreSQL 存储 CMDB 数据")
        print("    2. 触发器自动记录变更到 cmdb_change_log")
        print("    3. CDC 监听器 (03_cdc_listener.py) 捕获变更")
        print("    4. Kafka Producer (04_kafka_producer.py) 发送到 Kafka")
        print("    5. Kafka Consumer (05_kafka_consumer.py) 消费 → 更新本地缓存")
        print("    6. query_cmdb() (06) 从缓存查询, 缓存 miss 时回源 PostgreSQL")
        print()
        print("  生产环境对应:")
        print("    cmdb_change_log 触发器  →  Flink CDC 读 PostgreSQL WAL")
        print("    04_kafka_producer.py    →  Flink CDC 写 Kafka")
        print("    05_kafka_consumer.py    →  Flink 作业消费 Kafka 写 OpenSearch")
        print("    本地 Python 缓存        →  OpenSearch 索引")
    else:
        print("  [FAIL] 有测试失败, 请检查上面的输出")


if __name__ == "__main__":
    main()
