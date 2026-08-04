"""
风险判定相关数据模型
"""

from pydantic import BaseModel


class RiskAssessment(BaseModel):
    """三维度风险判定结果"""
    environment_risk: str = "未知"                  # 高 / 中 / 低 / 未知
    environment: str = "Unknown"                    # CMDB 返回的 Environment
    count_risk: str = "低"
    count_value: int = 0
    attack_type_risk: str = "低"
    attack_types: list[str] = []
    overall_risk: str = "低"                        # 综合: max(环境, 数量, 攻击类型)
    assessed_at: str = ""
