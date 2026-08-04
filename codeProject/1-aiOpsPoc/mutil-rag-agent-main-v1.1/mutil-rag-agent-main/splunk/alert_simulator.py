#!/usr/bin/env python3
"""Splunk 告警模拟器 — 定时随机生成告警推送到 AIOps Agent.

用法:
  python splunk/alert_simulator.py                  # 默认每 15-30 秒随机推一条
  python splunk/alert_simulator.py --interval 10    # 固定每 10 秒
  python splunk/alert_simulator.py --count 50       # 只推 50 条后停止
  python splunk/alert_simulator.py --burst 5        # 一次推 5 条(模拟告警风暴)

告警类型:
  cpu_high        — CPU 使用率 > 90%
  memory_high     — 内存使用率 > 85% / OOM
  disk_full       — 磁盘使用率 > 90% / inode 满
  service_500     — 服务返回 5xx 错误
  network_timeout — 网络超时 / 连接失败
  container_down  — Docker 容器异常
"""

import argparse
import json
import random
import time
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

# ---- 告警类型模板 ----
ALERT_TEMPLATES = [
    {
        "alert_type": "cpu_high",
        "title": "CPU 使用率过高",
        "severity": "critical",
        "templates": [
            "{host} CPU 使用率持续 {pct}%，超过阈值 90%，已持续 {duration} 分钟",
            "{host} 服务器 CPU 负载飙升到 {pct}%，业务响应明显变慢",
            "{host} 所有核心 CPU 使用率均超过 {pct}%，风扇全速运转",
        ],
    },
    {
        "alert_type": "memory_high",
        "title": "内存使用率过高",
        "severity": "high",
        "templates": [
            "{host} 内存使用率达到 {pct}%，可用内存不足 500MB",
            "{host} 发生 OOM Kill，进程 {process} 被终止",
            "{host} 内存持续上涨，疑似内存泄漏，当前使用率 {pct}%",
        ],
    },
    {
        "alert_type": "disk_full",
        "title": "磁盘空间不足",
        "severity": "high",
        "templates": [
            "{host} 磁盘分区 {mount} 使用率已达 {pct}%，剩余空间不足 5GB",
            "{host} inode 使用率 {pct}%，可能出现 No space left on device",
            "{host} 日志文件快速增长，{mount} 分区预计 {duration} 分钟后写满",
        ],
    },
    {
        "alert_type": "service_500",
        "title": "服务 5xx 错误",
        "severity": "high",
        "templates": [
            "{host} 服务 {service} 返回大量 500 错误，5xx 比率 {pct}%",
            "{host} API {endpoint} 响应 503 Service Unavailable",
            "{host} 网关超时，{service} 上游服务 504 Gateway Timeout",
        ],
    },
    {
        "alert_type": "network_timeout",
        "title": "网络连接超时",
        "severity": "medium",
        "templates": [
            "{host} 到 {target} 的网络延迟超过 5000ms，丢包率 {pct}%",
            "{host} 无法连接到 {target}:{port}，Connection Refused",
            "{host} DNS 解析 {domain} 超时，可能 DNS 服务异常",
        ],
    },
    {
        "alert_type": "container_down",
        "title": "容器异常",
        "severity": "critical",
        "templates": [
            "Docker 容器 {container} 意外退出，exit code={exit_code}",
            "容器 {container} 频繁重启，最近 1 小时重启了 {restart_count} 次",
            "容器 {container} 健康检查失败，端口 {port} 不可达",
        ],
    },
]

# ---- 模拟资源池 ----
HOST_POOL = [
    "10.0.1.101", "10.0.1.102", "10.0.1.103",
    "10.0.2.11",  "10.0.2.12",
    "192.168.1.50", "192.168.1.51",
    "172.16.0.10", "172.16.0.11",
]

SERVICE_POOL = ["payment-gateway", "user-service", "order-service", "inventory-api", "notification-svc"]
CONTAINER_POOL = ["redis-cache", "mysql-db", "nginx-proxy", "kafka-broker", "elasticsearch-node1"]
TARGET_POOL = ["api.example.com", "db-master.internal", "redis-cluster.internal", "192.168.2.1"]
DOMAIN_POOL = ["api.example.com", "db.internal", "cdn.example.com", "auth.internal"]
MOUNT_POOL = ["/dev/sda1", "/dev/sdb1", "/data", "/var/log"]
PROCESS_POOL = ["java", "python3", "redis-server", "mysqld", "node"]


def generate_alert() -> dict:
    """随机生成一条告警."""
    tmpl = random.choice(ALERT_TEMPLATES)
    host = random.choice(HOST_POOL)
    now = datetime.now(timezone(timedelta(hours=8)))

    # 构造描述
    desc_tmpl = random.choice(tmpl["templates"])
    description = desc_tmpl.format(
        host=host,
        pct=random.randint(85, 99),
        duration=random.randint(5, 120),
        mount=random.choice(MOUNT_POOL),
        service=random.choice(SERVICE_POOL),
        endpoint=f"/api/{random.choice(['pay','order','user','query'])}",
        target=random.choice(TARGET_POOL),
        port=random.choice([3306, 6379, 9092, 8080, 443]),
        domain=random.choice(DOMAIN_POOL),
        container=random.choice(CONTAINER_POOL),
        process=random.choice(PROCESS_POOL),
        exit_code=random.choice([1, 137, 143]),
        restart_count=random.randint(5, 30),
    )

    return {
        "alert_type": tmpl["alert_type"],
        "title": tmpl["title"],
        "severity": tmpl["severity"],
        "host_ip": host,
        "description": description,
        "timestamp": now.isoformat(),
        "source": "alert_simulator",
        "raw_metric": {
            "cpu_pct": random.randint(85, 99),
            "memory_pct": random.randint(80, 98),
            "disk_pct": random.randint(88, 99),
        },
    }


async def push_alert(alert: dict, endpoint: str) -> bool:
    """推送告警到 FastAPI."""
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(endpoint, json=alert)
            ok = resp.status_code == 200
            data = resp.json()
            status = data.get("data", {}).get("risk_level", "?")
            print(f"  → HTTP {resp.status_code} | 风险等级: {status} | {alert['title']}")
            return ok
    except Exception as e:
        print(f"  ✗ 推送失败: {type(e).__name__}: {e}")
        return False


async def run_simulator(
    endpoint: str,
    interval: float = 20,
    count: int = 0,
    burst: int = 1,
):
    """运行模拟器主循环."""
    print(f"告警模拟器已启动")
    print(f"  目标: {endpoint}")
    print(f"  间隔: {interval:.0f}s (随机 ±50%)")
    print(f"  每轮: {burst} 条")
    print(f"  总数: {'无限' if count == 0 else count}")
    print("-" * 50)

    sent = 0
    try:
        while count == 0 or sent < count:
            remaining = count - sent if count > 0 else float("inf")
            batch = min(burst, remaining) if count > 0 else burst

            for _ in range(batch):
                alert = generate_alert()
                await push_alert(alert, endpoint)
                sent += 1
                if count > 0 and sent >= count:
                    break
                await asyncio.sleep(random.uniform(0.3, 1.0))

            if count > 0 and sent >= count:
                break

            # 随机间隔 (避免太规律)
            wait = interval * random.uniform(0.5, 1.5)
            print(f"\n已发送 {sent} 条, 等待 {wait:.0f}s...")
            await asyncio.sleep(wait)

    except KeyboardInterrupt:
        print(f"\n模拟器已停止, 共发送 {sent} 条告警")

    print(f"完成! 累计 {sent} 条告警已推送到 {endpoint}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Splunk 告警模拟器")
    parser.add_argument("--endpoint", default="http://localhost:9900/api/v1/splunk/alert",
                        help="告警接收端点")
    parser.add_argument("--interval", type=float, default=60,
                        help="发送间隔(秒), 默认 20s")
    parser.add_argument("--count", type=int, default=1,
                        help="总条数限制, 0=无限")
    parser.add_argument("--burst", type=int, default=1,
                        help="每轮发送条数, 默认 1")
    args = parser.parse_args()

    import asyncio
    asyncio.run(run_simulator(args.endpoint, args.interval, args.count, args.burst))
