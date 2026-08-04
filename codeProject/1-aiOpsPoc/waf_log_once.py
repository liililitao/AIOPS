#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure WAF Log Generator for Splunk Alert Testing
用途: 单次生成1条模拟的 WAF Blocked 日志，用于触发 Splunk 告警
"""

import csv
import os
import random
import uuid
import time
from datetime import datetime

# ================= 配置区 =================
# 【关键】输出目录必须是 splunk 用户有写权限的目录！
# 建议放在 $SPLUNK_HOME/var/log/splunk/waf_simulator/ 下
OUTPUT_DIR = "C:/Users/JHGZ/Desktop/aiops/codeProject/1-aiOpsPoc/testlog"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "waf_log_sim.csv")
# ==========================================

# 模拟数据池 (基于你的 CSV 提取)
CLIENT_IPS = ["124.238.251.133", "36.158.231.55", "111.62.149.24", "114.238.251.132"]
HOSTNAMES = ["purview.novonordiskchina.com.cn"]
REQUEST_URIS = [
    "/api/app/shop/hysOrderResultUrlParse",
    "/new/.env.staging",
    "/.env~",
    "/laravel/core/.env",
    "/xampp/.env",
    "/www/.env",
    "/main/.env"
]
MESSAGES = [
    "Access denied with code 403. Pattern match url, at QueryString.",
    "Inbound Anomaly Score Exceeded (Total Score: 7)",
    "Inbound Anomaly Score Exceeded (Total Score: 10)"
]
RULE_IDS = ["949110", "942100", "931100"]

def generate_waf_log():
    """生成单条 WAF 日志字典"""
    # 使用当前时间，格式与 Azure 日志一致 (ISO8601)
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"

    return {
        "timeStamp": timestamp,
        "resourceId": "/SUBSCRIPTIONS/A2A54B14-D1D1-4DC1-9CE5-1E2BC7D6C6E7/RESOURCEGROUPS/RG-NCMA-PRD-INFRA-01/PROVIDERS/MICROSOFT.NETWORK/APPLICATIONGATEWAYS/AGW-NCMA-PRD-01",
        "operationName": "ApplicationGatewayFirewall",
        "category": "ApplicationGatewayFirewallLog",
        "properties.clientIp": random.choice(CLIENT_IPS),
        "properties.requestUri": random.choice(REQUEST_URIS),
        "properties.action": "Blocked",
        "properties.hostname": random.choice(HOSTNAMES),
        "properties.message": random.choice(MESSAGES),
        "properties.ruleId": random.choice(RULE_IDS),
        "properties.ruleGroup": "BLOCKING-EVALUATION",
        "properties.transactionId": uuid.uuid4().hex
    }

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fieldnames = [
        "timeStamp", "resourceId", "operationName", "category",
        "properties.clientIp", "properties.requestUri", "properties.action",
        "properties.hostname", "properties.message", "properties.ruleId",
        "properties.ruleGroup", "properties.transactionId"
    ]
    file_exists = os.path.isfile(OUTPUT_FILE)

    print(f"[*] WAF日志生成器启动，输出文件：{OUTPUT_FILE}")

    try:
        with open(OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            
            # 一次性循环生成25条
            for i in range(25):
                log_data = generate_waf_log()
                writer.writerow(log_data)
                time.sleep(0.2)  # 每条日志间隔
            f.flush()

            print(f"[+] 成功生成25条日志")
    except Exception as e:
        print(f"[!] 执行失败：{e}")

if __name__ == "__main__":
    main()