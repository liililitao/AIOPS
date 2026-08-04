#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure WAF Log Generator (Hardcoded Pool)
=========================================
用途: 基于生产环境真实数据字典池，随机组装生成完整的 Azure WAF 日志，
     用于 Splunk 告警规则测试。

设计思路 (方案B):
  - HOSTNAME_POOLS: 按 hostname 分组，绑定 resourceId/clientIp/requestUri 等专属字段
  - SHARED: 全局共享字段，所有 hostname 通用
  - 每次生成: 随机选 hostname → 从专属池取绑定字段 → 从 SHARED 取公共字段
  - 刷新 timeStamp 和 transactionId

数据来源: 生产环境 waf_blocked.csv，筛选两个会被告警命中的 hostname
  - purview.novonordiskchina.com.cn (60 条去重 URI, 14 个 IP)
  - api-obesity.novocare.com.cn (15 条去重 URI, 26 个 IP)

部署: 修改 OUTPUT_DIR 指向 Splunk 监控目录，运行 python waf_log_gen.py
"""

import csv
import os
import random
import uuid
import time
from datetime import datetime, timezone, timedelta

# ================= 配置区 =================
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_log")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "waf_log_gen.csv")
OUTPUT_COUNT = 60  # 每次运行生成的日志条数（可直接修改）

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

# ============================================================
# Hostname 专属数据池
# resourceId/clientIp/requestUri/instanceId/policyId 与 hostname
# 在生产中是强绑定的，此处一一对应，不交叉混用
# ============================================================

HOSTNAME_POOLS = {
    # ---- purview.novonordiskchina.com.cn ----
    "purview.novonordiskchina.com.cn": {
        "resourceId": [
            "/SUBSCRIPTIONS/88E39F7D-09DC-4B59-9491-B1CBF00279FB"
            "/RESOURCEGROUPS/RG-DAP-PRD-INFRA-N3-01"
            "/PROVIDERS/MICROSOFT.NETWORK/APPLICATIONGATEWAYS/AGW-DAP-PRD-N3-01",
        ],
        "clientIp": [
            "124.238.251.133", "124.238.251.134", "124.238.251.139",
            "27.155.113.16",
            "36.158.231.46", "36.158.231.47", "36.158.231.48",
            "36.158.231.49", "36.158.231.51", "36.158.231.52",
            "36.158.231.53", "36.158.231.55", "36.158.231.57",
            "36.158.231.58",
        ],
        "requestUri": [
            "/.aws/config", "/.aws/credentials",
            "/.env", "/.env.bak", "/.env.example", "/.env.local",
            "/.env.old", "/.env.prod", "/.env.production.local",
            "/.env.stage", "/.env_sample", "/.travis.yml",
            "/.vscode/.env",
            "/admin/.env", "/api/.env", "/api/config/config.yml",
            "/api/shared/.env", "/api/shared/config/.env",
            "/app/.env", "/app/config/parameters.yml",
            "/application/.env", "/apps/.env", "/awstats/.env",
            "/backend/.env", "/conf/.env", "/config/parameters.yml",
            "/core/.env", "/crm/.env", "/cron/.env",
            "/dev/.env", "/development/.env",
            "/docker/.env", "/docker/app/.env",
            "/env.backup", "/env/.env", "/js/.env", "/kyc/.env",
            "/laravel/.env", "/laravel/core/.env", "/local/.env",
            "/mail/.env", "/mailer/.env", "/main/.env",
            "/new/.env", "/new/.env.local", "/new/.env.production",
            "/new/.env.staging", "/nginx/.env",
            "/node/.env_example", "/node_modules/.env",
            "/portal/.env", "/prod/.env", "/public/.env",
            "/site/.env", "/storage/logs/laravel.log",
            "/web/.env", "/website/.env", "/wp-config.php.bak",
            "/www/.env", "/xampp/.env",
        ],
        "instanceId": ["appgw_0", "appgw_1"],
        "policyId": [
            "75#_subscriptions_88e39f7d-09dc-4b59-9491-b1cbf00279fb"
            "_resourceGroups_RG-DAP-PRD-Infra-N3-01"
            "_providers_Microsoft.Network"
            "_ApplicationGatewayWebApplicationFirewallPolicies_WAF-DAP-PRD-N3-01",
        ],
    },

    # ---- api-obesity.novocare.com.cn ----
    "api-obesity.novocare.com.cn": {
        "resourceId": [
            "/SUBSCRIPTIONS/57EB041C-8BF8-487B-A562-F9ACFFC16752"
            "/RESOURCEGROUPS/RG-NOVOCAREOBESITY-PRD-INFRA-01"
            "/PROVIDERS/MICROSOFT.NETWORK/APPLICATIONGATEWAYS"
            "/AGW-NOVOCAREOBESITY-PRD-01",
        ],
        "clientIp": [
            "111.62.149.18",
            "112.84.222.19", "112.84.222.101",
            "116.211.128.13", "116.211.128.16", "116.211.128.17",
            "116.211.128.19", "116.211.128.21", "116.211.128.99",
            "124.238.251.132", "124.238.251.133", "124.238.251.134",
            "124.238.251.136", "124.238.251.138", "124.238.251.139",
            "27.155.113.13", "27.155.113.14", "27.155.113.15",
            "27.155.113.16", "27.155.113.18", "27.155.113.32",
            "27.155.113.99",
            "36.158.231.48", "36.158.231.53", "36.158.231.62",
            "59.63.226.8",
        ],
        "requestUri": [
            "/.git/config",
            "/wp-config.php",
            "/membership/api/membership/v1/tasks",
            "/user/api/user/v1/user/login",
            "/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7"
            "?signature=07e1f5c6bd66263e5c906cdc1d0d7b0c4b446cc9"
            "&timestamp=1783046234&nonce=1347758690"
            "&openid=oVmQa7Qt3POItwdLM5ghA2vyfQxQ"
            "&encrypt_type=aes"
            "&msg_signature=c007ee2565f9e345b8f2b1b891dce02f09996f1a",
            "/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7"
            "?signature=0cb8c20282ace298ef6f18c02a910c7ca341eb17"
            "&timestamp=1783047207&nonce=1089772023"
            "&openid=oVmQa7Y0AxG5uEhx0Um_shz9r3-I"
            "&encrypt_type=aes"
            "&msg_signature=4bc268b7775d0a7f929910aca2cbef34f025f05d",
            "/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7"
            "?signature=1e1f869a0495151afca1e234bcde47d0ac65e537"
            "&timestamp=1783046216&nonce=1931590628"
            "&openid=oVmQa7VLdLOg6YVe-2YPf9nQqO_g"
            "&encrypt_type=aes"
            "&msg_signature=86fb522fd25338b79845ffc1958eb7e2f9e9c116",
            "/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7"
            "?signature=33957ff5bed32ed55e9d0cc45515aa5fcbf2c9ef"
            "&timestamp=1783047052&nonce=1419243734"
            "&openid=oVmQa7ZRhzOjWpWEBizUvYt14N-I"
            "&encrypt_type=aes"
            "&msg_signature=0e8b1a9eec441cdc43ae889efc5609838498c4f4",
            "/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7"
            "?signature=384d4d1c55a9db1f6f13028edc7ad04007c9657c"
            "&timestamp=1783047387&nonce=506767620"
            "&openid=oVmQa7RBIjEXyHQZ7gfnqNDghw5o"
            "&encrypt_type=aes"
            "&msg_signature=f1a90683bd0fb91cb27b93f810a8da00dbf62efa",
            "/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7"
            "?signature=5fcd25e911cd86c55893b851005577c51bdf5d26"
            "&timestamp=1783046191&nonce=603405742"
            "&openid=oVmQa7aN7S0hM2CAiBJZ1rFbfUyQ"
            "&encrypt_type=aes"
            "&msg_signature=c62f6b2ba3dfd8f748cdde5c5b4f71e68644287d",
            "/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7"
            "?signature=ab6a818d9d9061cf0838250adb1d7752de255ec1"
            "&timestamp=1783047206&nonce=257145291"
            "&openid=oVmQa7VEYyC6a1wWApszSh2xqSMU"
            "&encrypt_type=aes"
            "&msg_signature=f7f2de4c244359d1c7d2a28e1205fb169b41e2bf",
            "/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7"
            "?signature=b20ef512be37562044eebf92faa1d33810a8288d"
            "&timestamp=1783037859&nonce=1359840584"
            "&openid=oVmQa7eVNm09HKF5-tKB5ZvUZG4o"
            "&encrypt_type=aes"
            "&msg_signature=e0b22718b83bc16652c68065add637bc0e284ebd",
            "/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7"
            "?signature=b8363bdf8281efe0795d67d8c9cbf5e1138412f8"
            "&timestamp=1783046240&nonce=579415879"
            "&openid=oVmQa7UINaTq9bReHRfGS9LeLCO4"
            "&encrypt_type=aes"
            "&msg_signature=8928933a61d1c328ff3d2999b58e81a42acf149f",
            "/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7"
            "?signature=e6875cafc48b5f297329da1837b58f7746c93095"
            "&timestamp=1783043711&nonce=1422143956"
            "&openid=oVmQa7WCmEYGjIK5nPS8EEiKUwzc"
            "&encrypt_type=aes"
            "&msg_signature=5178f112475c563e604d4ccdb1a7976849ec4f5e",
        ],
        "instanceId": ["appgw_1", "appgw_3"],
        "policyId": [
            "82#_subscriptions_57eb041c-8bf8-487b-a562-f9acffc16752"
            "_resourceGroups_RG-NovocareObesity-PRD-Infra-01"
            "_providers_Microsoft.Network"
            "_ApplicationGatewayWebApplicationFirewallPolicies"
            "_WAF-NovocareObesity-PRD-01",
        ],
    },
}

# ============================================================
# 全局共享数据池 — 所有 hostname 共用，与 hostname 无绑定关系
# ============================================================

SHARED = {
    "operationName":      ["ApplicationGatewayFirewall"],
    "category":           ["ApplicationGatewayFirewallLog"],
    "properties.action":  ["Blocked"],
    "properties.ruleId":  ["949110"],
    "properties.ruleSetType":    ["Microsoft_DefaultRuleSet", "OWASP CRS"],
    "properties.ruleSetVersion": ["2.1", "3.2"],
    "properties.ruleGroup":      [
        "BLOCKING-EVALUATION",
        "REQUEST-949-BLOCKING-EVALUATION",
    ],
    "properties.message": [
        "Inbound Anomaly Score Exceeded (Total Score: 5)",
        "Inbound Anomaly Score Exceeded (Total Score: 7)",
        "Inbound Anomaly Score Exceeded (Total Score: 12)",
    ],
    "properties.policyScope":      ["Global"],
    "properties.policyScopeName":  ["Global"],
    "properties.engine":           ["Azwaf"],
    "properties.details.message":  [
        "Greater and Equal to Tx:inbound_anomaly_score_threshold"
        " at TX:anomaly_score.",
    ],
    "properties.details.data":     [""],
    "properties.details.file":     [
        "BLOCKING-EVALUATION.conf",
        "REQUEST-949-BLOCKING-EVALUATION.conf",
    ],
    "properties.details.line":     ["36", "79"],
}


def generate_one():
    """生成一条完整的 WAF 日志 (dict)，所有字段值均从真实数据池随机抽取"""
    # 1. 随机选 hostname
    hostname = random.choice(list(HOSTNAME_POOLS.keys()))
    hn_pool = HOSTNAME_POOLS[hostname]

    # 2. 从 hostname 专属池取绑定字段
    log = {
        "properties.hostname":      hostname,
        "resourceId":               random.choice(hn_pool["resourceId"]),
        "properties.clientIp":      random.choice(hn_pool["clientIp"]),
        "properties.requestUri":    random.choice(hn_pool["requestUri"]),
        "properties.instanceId":    random.choice(hn_pool["instanceId"]),
        "properties.policyId":      random.choice(hn_pool["policyId"]),
    }

    # 3. 从全局共享池取公共字段
    for field, pool in SHARED.items():
        log[field] = random.choice(pool)

    # 4. 刷新 timeStamp 和 transactionId（每次不同）
    now = datetime.now(timezone(timedelta(hours=8)))
    log["timeStamp"] = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"
    log["properties.transactionId"] = uuid.uuid4().hex

    return log


def main():
    print(f"[*] WAF 日志生成器启动 (硬编码数据池, 方案B)")
    purview = HOSTNAME_POOLS["purview.novonordiskchina.com.cn"]
    obesity = HOSTNAME_POOLS["api-obesity.novocare.com.cn"]
    print(f"    purview  专属池: {len(purview['requestUri'])} URIs, "
          f"{len(purview['clientIp'])} IPs, "
          f"{len(purview['resourceId'])} GW")
    print(f"    obesity  专属池: {len(obesity['requestUri'])} URIs, "
          f"{len(obesity['clientIp'])} IPs, "
          f"{len(obesity['resourceId'])} GW")
    print(f"    SHARED 池: {len(SHARED)} 字段")
    print(f"    计划生成: {OUTPUT_COUNT} 条")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_exists = os.path.isfile(OUTPUT_FILE)

    with open(OUTPUT_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        for _ in range(OUTPUT_COUNT):
            time.sleep(0.1)
            log = generate_one()
            writer.writerow(log)

        f.flush()

    print(f"[+] 已生成 {OUTPUT_COUNT} 条日志 → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
