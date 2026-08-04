#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure WAF Log Replay Generator - 基于生产数据回放
=================================================
用途: 从生产日志 waf_blocked.csv 中提取真实数据，筛选目标 hostname，
     回放生成字段完整的模拟 WAF 日志，用于 Splunk 告警测试。

与 waf_log_once.py 的区别:
  - waf_log_once.py: 硬编码少量字段，随机拼接，只覆盖 1 个 hostname
  - waf_log_replay.py: 从生产数据提取全部 23 个字段，顺序回放真实行，
    只刷新时间戳和 transactionId，覆盖 2 个会被告警命中的 hostname

部署: 放在测试机上，修改 OUTPUT_DIR 指向 Splunk 监控目录
      python waf_log_replay.py
"""

import csv
import os
import uuid
from datetime import datetime, timezone, timedelta

# ================= 配置区 =================
# 生产日志源文件（位于本脚本同目录）
SOURCE_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testlog", "waf_blocked.csv")

# 输出目录 — 必须是 Splunk 监控的目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testlog")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "waf_log_replay.csv")

# 每次运行生成的日志条数（可配置）
OUTPUT_COUNT = 50

# 目标 hostname — 只回放会被告警命中的 hostname
TARGET_HOSTNAMES = {
    "purview.novonordiskchina.com.cn",
    "api-obesity.novocare.com.cn",
}

# 输出字段列表 — Azure WAF 完整字段（扁平化，和 Splunk 导出列名一致）
OUTPUT_FIELDNAMES = [
    "timeStamp",
    "resourceId",
    "operationName",
    "category",
    "properties.instanceId",
    "properties.clientIp",
    "properties.requestUri",
    "properties.ruleSetType",
    "properties.ruleSetVersion",
    "properties.ruleId",
    "properties.ruleGroup",
    "properties.message",
    "properties.action",
    "properties.hostname",
    "properties.transactionId",
    "properties.policyId",
    "properties.policyScope",
    "properties.policyScopeName",
    "properties.engine",
    "properties.details.message",
    "properties.details.data",
    "properties.details.file",
    "properties.details.line",
]
# ==========================================


def load_pool(source_path):
    """
    从生产 Splunk 导出 CSV 中提取目标 hostname 的行，
    返回一个 list[dict]，每行只保留 OUTPUT_FIELDNAMES 中定义的字段。
    """
    pool = []
    seen = set()

    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hostname = row.get("properties.hostname", "").strip()
            if hostname not in TARGET_HOSTNAMES:
                continue

            # 从生产 CSV 的列映射到输出字段
            item = {}
            for field in OUTPUT_FIELDNAMES:
                val = row.get(field, "")
                if val:
                    item[field] = val.strip()
                else:
                    item[field] = ""

            # 去重：相同 (hostname, resourceId, requestUri) 只保留一条
            # 否则同一个 requestUri 生成太多会失真
            dedup_key = (
                item.get("properties.hostname", ""),
                item.get("resourceId", ""),
                item.get("properties.requestUri", ""),
            )
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            pool.append(item)

    return pool


def interleave_pool(pool):
    """
    将数据池按 hostname 分组后交错排列，确保输出中每种 hostname 都出现。
    不改变任何字段值，只改变 pool 中元素的排列顺序。

    例如 pool=[A1,A2,A3, B1,B2] → [A1,B1, A2,B2, A3]
    """
    from collections import defaultdict
    groups = defaultdict(list)
    for item in pool:
        hostname = item.get("properties.hostname", "")
        groups[hostname].append(item)

    # 按组大小降序排列各组（大的组先取，避免小的组耗尽早结束）
    sorted_groups = sorted(groups.values(), key=len, reverse=True)

    result = []
    max_len = max(len(g) for g in sorted_groups)
    for i in range(max_len):
        for g in sorted_groups:
            if i < len(g):
                result.append(g[i])
    return result


def refresh_log(item, index):
    """刷新一条日志：更新 timeStamp 和 transactionId，其余字段保持原值"""
    now = datetime.now(timezone(timedelta(hours=8)))
    ts = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"

    new_item = dict(item)  # 浅拷贝足够（所有值都是 str）
    new_item["timeStamp"] = ts
    new_item["properties.transactionId"] = uuid.uuid4().hex
    return new_item


def main():
    print(f"[*] WAF 日志回放器启动")
    print(f"    数据源: {SOURCE_CSV}")
    print(f"    目标 hostname: {TARGET_HOSTNAMES}")
    print(f"    计划生成: {OUTPUT_COUNT} 条")

    # 1. 加载数据池
    pool = load_pool(SOURCE_CSV)
    print(f"    数据池大小: {len(pool)} 条（已去重）")

    if not pool:
        print("[!] 数据池为空，请检查 SOURCE_CSV 路径和 TARGET_HOSTNAMES 配置")
        return

    # 2. 交错排列（确保不同 hostname 交替出现）
    pool = interleave_pool(pool)

    # 3. 显示数据池构成
    from collections import Counter
    hostname_cnt = Counter(p["properties.hostname"] for p in pool)
    for hn, cnt in hostname_cnt.items():
        gw_set = set(
            p["resourceId"].split("/")[-1]
            for p in pool
            if p["properties.hostname"] == hn
        )
        print(f"      {hn}: {cnt} 条, 网关={gw_set}")

    # 4. 轮询生成日志
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_exists = os.path.isfile(OUTPUT_FILE)

    with open(OUTPUT_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        for i in range(OUTPUT_COUNT):
            # 顺序回放：轮完一轮再从头循环
            item = pool[i % len(pool)]
            log = refresh_log(item, i)
            writer.writerow(log)

        f.flush()

    print(f"[+] 已生成 {OUTPUT_COUNT} 条日志 → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
