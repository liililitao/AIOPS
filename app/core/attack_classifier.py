"""
攻击类型分类器 - 根据 requestUri 判定攻击类型
规则可配置，存储在 data/attack_patterns.json 中
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aiops.attack_classifier")

# 默认攻击模式规则
DEFAULT_PATTERNS = {
    "env_scan": {
        "label": "环境文件扫描",
        "risk": "中",
        "patterns": [".env", "env.backup", ".env.local", ".env.production", "env.old", ".env.bak"],
    },
    "admin_target": {
        "label": "管理后台攻击",
        "risk": "高",
        "patterns": ["/admin", "/administrator", "/wp-admin", "/manager", "/console", "/backstage"],
    },
    "dynamic_page": {
        "label": "动态页面攻击",
        "risk": "高",
        "patterns": [".php", ".asp", ".aspx", ".jsp", ".do", ".action", ".cgi"],
    },
    "config_scan": {
        "label": "配置文件扫描",
        "risk": "中",
        "patterns": ["/conf/", "/config/", "/backup/", "/cron/", "/logs/", "/database/"],
    },
    "dependency_scan": {
        "label": "依赖文件扫描",
        "risk": "低",
        "patterns": ["/node_modules/", "/vendor/", "/WEB-INF/", "/META-INF/"],
    },
    "upload_exploit": {
        "label": "上传漏洞探测",
        "risk": "高",
        "patterns": ["/upload", "/uploads", "/fileupload", ".war", ".jar", "webshell"],
    },
    "api_exploit": {
        "label": "API漏洞探测",
        "risk": "中",
        "patterns": ["/api/", "/graphql", "/swagger", "/actuator", "/jmx", "/debug"],
    },
    "random_scan": {
        "label": "随机扫描",
        "risk": "低",
        "patterns": [],  # 兜底
    },
}


def _load_patterns() -> dict:
    """加载攻击模式规则（从 JSON 文件或使用默认值）"""
    patterns_file = Path(__file__).parent.parent.parent / "data" / "attack_patterns.json"
    if patterns_file.exists():
        try:
            return json.loads(patterns_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[ATTACK] Pattern file load failed, using defaults: {e}")
    return DEFAULT_PATTERNS


def classify_attack_types(request_uri: str) -> list[dict]:
    """
    对攻击路径进行分类

    Args:
        request_uri: 告警中的 properties_requestUri 字符串
                      格式: "/path1 /path2 /path3" (空格分隔)

    Returns:
        [{"type": "env_scan", "label": "环境文件扫描", "risk": "中", "matched": ["/.env", ...]}, ...]
    """
    if not request_uri:
        return [{"type": "unknown", "label": "未知", "risk": "低", "matched": []}]

    patterns = _load_patterns()
    uris = [u.strip() for u in request_uri.split() if u.strip()]
    results = []

    for uri in uris:
        matched = False
        for rule_key, rule in patterns.items():
            if rule_key == "random_scan":
                continue
            for pat in rule.get("patterns", []):
                if pat.lower() in uri.lower():
                    # 找到已有分类或创建新分类
                    found = None
                    for r in results:
                        if r["type"] == rule_key:
                            found = r
                            break
                    if found:
                        found["matched"].append(uri)
                    else:
                        results.append({
                            "type": rule_key,
                            "label": rule.get("label", rule_key),
                            "risk": rule.get("risk", "低"),
                            "matched": [uri],
                        })
                    matched = True
                    break
            if matched:
                break

        if not matched:
            # 归入 random_scan
            found = None
            for r in results:
                if r["type"] == "random_scan":
                    found = r
                    break
            if found:
                found["matched"].append(uri)
            else:
                results.append({
                    "type": "random_scan",
                    "label": "随机扫描",
                    "risk": "低",
                    "matched": [uri],
                })

    return results if results else [{"type": "unknown", "label": "未知", "risk": "低", "matched": []}]


def get_attack_type_summary(request_uri: str) -> dict:
    """
    获取攻击类型摘要

    Returns:
        {
            "types": ["env_scan", "admin_target", ...],
            "highest_risk": "高",
            "details": [...]
        }
    """
    results = classify_attack_types(request_uri)
    types = [r["type"] for r in results]
    risk_order = {"低": 0, "中": 1, "高": 2}
    highest_risk = max(results, key=lambda r: risk_order.get(r["risk"], 0))
    return {
        "types": types,
        "highest_risk": highest_risk["risk"],
        "details": results,
    }
