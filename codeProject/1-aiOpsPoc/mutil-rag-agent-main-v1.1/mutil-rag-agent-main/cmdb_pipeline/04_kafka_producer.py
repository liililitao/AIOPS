#!/usr/bin/env python3
"""步骤 4: Kafka Producer — 把 CMDB 变更事件发送到 Kafka.

生产环境:
  Flink CDC 直接写 Kafka → Kafka 作为消息中间件解耦上下游

本脚本 (学习用途):
  从 cmdb_change_log 读取变更 → 发送到 Kafka Topic "cmdb.devices.change"
  让你直观理解 "数据库变更 → Kafka 消息" 的过程

前置: Kafka 必须已启动
  docker compose -f cmdb_pipeline/docker-compose.cmdb.yml up -d

如果 kafka-python 未安装:
  pip install kafka-python
"""

import sys
import time
import json
from datetime import datetime

try:
    import psycopg2
except ImportError:
    print("请先安装: pip install psycopg2-binary")
    sys.exit(1)

try:
    from kafka import KafkaProducer
    from kafka.errors import NoBrokersAvailable
except ImportError:
    print("请先安装: pip install kafka-python")
    sys.exit(1)

# ---- 配置 ----
DB_CONFIG = {
    "host": "localhost", "port": 5433,
    "dbname": "cmdb", "user": "cmdb_admin", "password": "cmdb_pass_2024",
}
KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "cmdb.devices.change"


def connect_pg():
    return psycopg2.connect(**DB_CONFIG)


def create_kafka_producer():
    """创建 Kafka Producer, 带重试."""
    print(f"[Kafka] 连接 {KAFKA_BOOTSTRAP}...")
    for attempt in range(5):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                key_serializer=lambda k: str(k).encode("utf-8") if k else None,
                acks="all",                          # 等待所有副本确认
                retries=3,                           # 发送失败重试
                max_in_flight_requests_per_connection=1,  # 保证顺序
            )
            print(f"  [OK] 连接成功")
            return producer
        except NoBrokersAvailable:
            if attempt < 4:
                print(f"  等待 Kafka 启动... ({attempt+1}/5)")
                time.sleep(5)
            else:
                raise
    return None


def format_kafka_message(row):
    """把数据库行转成 Kafka 消息格式.

    这个格式和生产环境中 Flink CDC → Kafka 的输出一致.
    """
    eid, device_id, operation, old_data, new_data, changed_at = row

    # Key: device_id (保证同一设备的事件有序)
    key = str(device_id)

    # Value: 完整事件
    value = {
        "schema": "cmdb_devices",
        "payload": {
            "before": old_data,                     # UPDATE/DELETE 的旧值
            "after": new_data,                      # INSERT/UPDATE 的新值
            "op": operation.lower()[:1],           # c=create, u=update, d=delete
            "ts_ms": int(time.time() * 1000),
            "source": {
                "db": "cmdb",
                "table": "cmdb_devices",
                "connector": "flink-cdc-postgres",  # 生产环境会标明来源
            },
        },
    }
    return key, value


def get_unsent_changes(conn, last_id):
    """获取未发送的变更."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, device_id, operation, old_data, new_data, changed_at
            FROM cmdb_change_log
            WHERE id > %s
            ORDER BY id
        """, (last_id,))
        return cur.fetchall()


def main():
    print("=" * 60)
    print("步骤 4: Kafka Producer — CMDB 变更 → Kafka")
    print("=" * 60)
    print()

    # 连接
    pg = connect_pg()
    producer = create_kafka_producer()

    # 获取起始 offset
    with pg.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id), 0) FROM cmdb_change_log")
        last_id = cur.fetchone()[0]
    print(f"[Producer] 起始 offset = {last_id}, Topic = {KAFKA_TOPIC}")
    print(f"[Producer] 等待新变更... (在另一个终端运行 02_crud_operations.py)")
    print(f"[Producer] 按 Ctrl+C 停止\n")

    sent_count = 0
    try:
        while True:
            time.sleep(1)

            changes = get_unsent_changes(pg, last_id)
            for row in changes:
                last_id = row[0]
                key, value = format_kafka_message(row)

                # 发送到 Kafka
                future = producer.send(KAFKA_TOPIC, key=key, value=value)
                # 等待确认 (生产环境可以用异步)
                record_metadata = future.get(timeout=10)

                sent_count += 1
                op_map = {"INSERT": "[+]", "UPDATE": "[*]", "DELETE": "[-]"}
                icon = op_map.get(value["payload"]["op"].upper(), "[?]")
                if row[2] == "INSERT":
                    icon = "[+]"
                elif row[2] == "UPDATE":
                    icon = "[*]"
                elif row[2] == "DELETE":
                    icon = "[-]"
                else:
                    icon = "[?]"

                print(f"  {icon} 已发送 #{sent_count}: device_id={key} "
                      f"operation={row[2]} "
                      f"→ Kafka partition={record_metadata.partition} "
                      f"offset={record_metadata.offset}")

    except KeyboardInterrupt:
        print(f"\n[Producer] 已停止, 共发送 {sent_count} 条消息")
    finally:
        producer.flush()
        producer.close()
        pg.close()


if __name__ == "__main__":
    main()
