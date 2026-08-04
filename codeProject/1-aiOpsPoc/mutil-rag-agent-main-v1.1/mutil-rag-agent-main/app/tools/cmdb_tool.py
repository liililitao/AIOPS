"""CMDB 查询工具 (Mock) — 模拟公司 CMDB 数据库查询.

Agent 调用此工具获取设备/IP 对应的业务信息:
  - 设备名、所属应用、负责人、环境、业务等级
  - 用于告警关联和风险等级评估

生产环境替换为真实 CMDB API 调用即可 (接口不变).
"""

from langchain_core.tools import tool
from loguru import logger

# 模拟 CMDB 数据 (生产环境替换为 HTTP API 调用)
_MOCK_CMDB = {
    "10.0.1.101": {"hostname": "pay-gw-01", "app_name": "支付网关服务", "owner": "张三", "env": "PROD", "business_level": "核心"},
    "10.0.1.102": {"hostname": "pay-gw-02", "app_name": "支付网关服务", "owner": "张三", "env": "PROD", "business_level": "核心"},
    "10.0.1.103": {"hostname": "user-svc-01", "app_name": "用户中心", "owner": "李四", "env": "PROD", "business_level": "重要"},
    "10.0.2.11":  {"hostname": "order-svc-01", "app_name": "订单服务", "owner": "王五", "env": "PROD", "business_level": "核心"},
    "10.0.2.12":  {"hostname": "order-svc-02", "app_name": "订单服务", "owner": "王五", "env": "PROD", "business_level": "核心"},
    "192.168.1.50": {"hostname": "inventory-db", "app_name": "库存数据库", "owner": "赵六", "env": "PROD", "business_level": "重要"},
    "192.168.1.51": {"hostname": "cache-node-01", "app_name": "缓存集群", "owner": "钱七", "env": "PROD", "business_level": "一般"},
    "172.16.0.10": {"hostname": "kafka-broker-01", "app_name": "消息队列", "owner": "孙八", "env": "PROD", "business_level": "重要"},
    "172.16.0.11": {"hostname": "es-node-01", "app_name": "搜索引擎", "owner": "周九", "env": "PROD", "business_level": "一般"},
    "99.99.99.99": {"hostname": "pay-gw-prod", "app_name": "支付网关服务", "owner": "张三", "env": "PROD", "business_level": "核心"},
}

_UNKNOWN_TEMPLATE = {
    "hostname": "未知设备",
    "app_name": "未知应用",
    "owner": "未知",
    "env": "未知",
    "business_level": "未知",
}


@tool
def query_cmdb(ip: str = "", hostname: str = "") -> str:
    """查询 CMDB 获取设备/IP 的业务信息。用于告警关联和风险评估。

    在以下场景调用本工具:
    - 收到告警后需要了解受影响设备的业务归属
    - 评估告警影响范围时需要知道业务等级
    - 需要联系设备负责人时

    Args:
        ip: 设备 IP 地址, 例如 "10.0.1.101"
        hostname: 主机名, 例如 "pay-gw-01" (与 ip 二选一)

    Returns:
        设备详细信息, 含应用名、负责人、环境、业务等级
    """
    # 按 IP 查
    if ip and ip in _MOCK_CMDB:
        info = _MOCK_CMDB[ip]
    # 按主机名查
    elif hostname:
        match = None
        for v in _MOCK_CMDB.values():
            if v["hostname"] == hostname:
                match = v
                break
        info = match or _UNKNOWN_TEMPLATE
    else:
        return "请提供 IP 或 hostname 参数"

    logger.info(f"[cmdb_tool] 查询 {ip or hostname} -> {info['app_name']} ({info['business_level']})")

    return (
        f"## CMDB 设备信息\n\n"
        f"| 字段 | 值 |\n"
        f"|---|---|\n"
        f"| 主机名 | {info['hostname']} |\n"
        f"| 应用名称 | {info['app_name']} |\n"
        f"| 负责人 | {info['owner']} |\n"
        f"| 环境 | {info['env']} |\n"
        f"| 业务等级 | {info['business_level']} |\n"
        f"| 查询 IP | {ip or '(未提供)'} |"
    )
