#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Splunk Alert Action Script - 告警信息本地持久化 (含风险等级)
============================================================
用途: 替代邮件告警，将 Splunk 告警上下文和搜索结果写入本地 JSON 文件，
     同时自动附加随机风险等级 (高/中/低)，省去二次处理步骤。

部署: 复制到 /data/splunk/bin/scripts/alert_to_file_risk.py
      chown splunk:splunk /data/splunk/bin/scripts/alert_to_file_risk.py
      chmod 755 /data/splunk/bin/scripts/alert_to_file_risk.py

Splunk 告警动作配置中填写脚本名: alert_to_file_risk.py
"""

import csv
import gzip
import json
import os
import random
import sys
from datetime import datetime

# ================= 配置区 =================
# 告警输出目录（Splunk 用户必须有写权限）
OUTPUT_DIR = "/data/splunk/var/log/splunk/waflogalert"
INDEX_FILE = os.path.join(OUTPUT_DIR, "alert_index.txt")
# ==========================================


def read_env():
    """读取 Splunk 通过环境变量传入的告警上下文"""
    env = {}
    for i in range(9):
        key = f"SPLUNK_ARG_{i}"
        val = os.environ.get(key, "")
        env[key] = val
    return env


def read_results(gz_path):
    """
    读取 SPLUNK_ARG_8 指向的搜索结果文件（gzip 压缩 CSV）
    返回: list[dict] — CSV 每一行的字典
    """
    if not gz_path or not os.path.isfile(gz_path):
        return []

    rows = []
    try:
        with gzip.open(gz_path, mode="rt", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"[!] 读取搜索结果失败: {e}", file=sys.stderr)
    return rows


def build_content(env, results):
    """
    根据环境变量和搜索结果组装一个结构化的告警输出文档
    """
    alert_name = env.get("SPLUNK_ARG_4", "unknown")
    event_count = env.get("SPLUNK_ARG_1", "0")
    trigger_reason = env.get("SPLUNK_ARG_5", "")
    splunk_url = env.get("SPLUNK_ARG_6", "")
    search_terms = env.get("SPLUNK_ARG_2", "")
    full_spl = env.get("SPLUNK_ARG_3", "")

    # 提取 rows 中的有效字段（仅保留非空列，去除冗余）
    slim_results = []
    for row in results:
        clean_row = {k: v for k, v in row.items() if v and v.strip()}
        if clean_row:
            slim_results.append(clean_row)

    return {
        "alert_name": alert_name,
        "trigger_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        + "+08:00",
        "trigger_time_utc": datetime.utcnow().strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z",
        "event_count": int(event_count) if event_count.isdigit() else 0,
        "trigger_reason": trigger_reason,
        "splunk_url": splunk_url,
        "search_terms": search_terms,
        "full_spl": full_spl,
        "risk_level": random.choice(["高", "中", "低"]),
        "results": slim_results,
        "operator_notes": "",
    }


def write_json(output_path, content):
    """将告警摘要写入 JSON 文件"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    print(f"[+] JSON 告警记录已写入: {output_path}")


def append_index(content, json_filename):
    """
    追加一行汇总到索引文件，格式:
    [2026-07-09 09:59:00] test-waf | 命中25条 | 高风险 | id=xxx hostname=xxx | 详见 xxx.json
    """
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alert_name = content.get("alert_name", "unknown")
    count = content.get("event_count", 0)
    risk = content.get("risk_level", "")

    results = content.get("results", [])
    summary = ""
    if results:
        first = results[0]
        rid = first.get("id", "-")
        host = first.get("properties_hostname", "-")
        uris = first.get("properties_requestUri", "-")
        if len(uris) > 80:
            uris = uris[:77] + "..."
        summary = f"id={rid} hostname={host} uri={uris}"

    line = f"[{now}] {alert_name} | 命中{count}条 | {risk}风险 | {summary} | 详见 {json_filename}\n"

    with open(INDEX_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"[+] 索引行已追加: {INDEX_FILE}")


def main():
    print(f"[*] alert_to_file_risk.py 启动, PID={os.getpid()}")

    # 1. 读取环境变量
    env = read_env()
    gz_path = env.get("SPLUNK_ARG_8", "")
    alert_name = env.get("SPLUNK_ARG_4", "unknown")

    print(f"    告警名称: {alert_name}")
    print(f"    事件数量: {env.get('SPLUNK_ARG_1', '0')}")
    print(f"    结果文件: {gz_path}")

    # 2. 读取搜索结果
    results = read_results(gz_path)
    print(f"    读取到 {len(results)} 条结果行")

    # 3. 组装内容 (含随机风险等级)
    content = build_content(env, results)
    print(f"    风险等级: {content['risk_level']}")

    # 4. 生成文件名: alert_<告警名>_<时间戳>.json
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = alert_name.replace("/", "_").replace(" ", "_")
    json_file = f"alert_{safe_name}_{ts}.json"
    json_path = os.path.join(OUTPUT_DIR, json_file)

    # 5. 写入 JSON 文件
    write_json(json_path, content)

    # 6. 追加索引行
    append_index(content, json_file)

    print(f"[+] 告警持久化完成: {json_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
