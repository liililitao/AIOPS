"""
三维度风险判定模型

维度 A: 环境风险 (来自 CMDB Environment)
维度 B: 数量风险 (来自告警 count 字段)
维度 C: 攻击类型风险 (来自 requestUri 分析)

综合规则: 取三维度中的最高风险等级
"""

import logging
from datetime import datetime

from app.config import get_settings
from app.core.attack_classifier import get_attack_type_summary
from app.schemas.risk import RiskAssessment

logger = logging.getLogger("aiops.risk")


def assess_risk(
    environment: str,
    count: int,
    request_uri: str,
) -> RiskAssessment:
    """
    三维度综合风险判定

    Args:
        environment: CMDB 查询结果 "Production" / "Non-Production" / "Unknown"
        count: 告警 count 字段数值
        request_uri: 攻击路径字符串

    Returns:
        RiskAssessment 包含各维度判定和综合等级
    """
    settings = get_settings()

    # -----------------------------------------
    # 维度 A: 环境风险
    # -----------------------------------------
    env = environment.strip() if environment else "Unknown"
    if env == "Production":
        env_risk = "高"
    elif env == "Non-Production":
        env_risk = "低"
    else:
        env_risk = "未知"

    # -----------------------------------------
    # 维度 B: 数量风险 (阈值可配置)
    # -----------------------------------------
    if count >= settings.RISK_COUNT_HIGH_THRESHOLD:
        count_risk = "高"
    elif count >= settings.RISK_COUNT_MEDIUM_THRESHOLD:
        count_risk = "中"
    else:
        count_risk = "低"

    # -----------------------------------------
    # 维度 C: 攻击类型风险
    # -----------------------------------------
    attack_summary = get_attack_type_summary(request_uri)
    attack_risk = attack_summary["highest_risk"]

    # -----------------------------------------
    # 综合判定: 取最高
    # -----------------------------------------
    risk_order = {"低": 0, "中": 1, "高": 2, "未知": 1}
    risks = [
        (env_risk, "环境"),
        (count_risk, "数量"),
        (attack_risk, "攻击类型"),
    ]
    highest = max(risks, key=lambda r: risk_order.get(r[0], 0))
    overall = highest[0]

    logger.info(
        f"风险判定: 环境={env_risk}({env}), 数量={count_risk}({count}), "
        f"攻击={attack_risk}({attack_summary['types']}), → 综合={overall}"
    )

    return RiskAssessment(
        environment_risk=env_risk,
        environment=env,
        count_risk=count_risk,
        count_value=count,
        attack_type_risk=attack_risk,
        attack_types=attack_summary["types"],
        overall_risk=overall,
        assessed_at=datetime.now().isoformat(),
    )
