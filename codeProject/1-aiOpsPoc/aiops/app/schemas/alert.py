"""
告警数据模型 - Splunk WAF 告警 JSON 结构
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AlertResult(BaseModel):
    """告警结果中的单条记录"""
    id: str = ""                                    # Azure 资源 ID, 如 AGW‑DAP‑PRD‑N3‑01
    properties_hostname: str = ""                   # 域名
    properties_requestUri: str = ""                 # 攻击路径
    properties_action: str = ""                     # 动作: Blocked / Detected
    count: str = "0"                                # 触发次数（JSON 中为字符串）
    __mv_properties_requestUri: Optional[str] = None

    @property
    def count_int(self) -> int:
        """count 字段转为整数"""
        try:
            return int(self.count)
        except (ValueError, TypeError):
            return 0

    @property
    def request_uri_list(self) -> list[str]:
        """将攻击路径解析为列表"""
        raw = self.properties_requestUri or ""
        return [u.strip() for u in raw.split() if u.strip()]


class RawAlert(BaseModel):
    """原始的 Splunk 告警数据"""
    alert_name: str = ""
    application_code: str = ""                    # iWE / WeCall 等受管应用编码
    trigger_time: str = ""                          # ISO 8601 本地时间
    trigger_time_utc: str = ""                      # ISO 8601 UTC
    event_count: int = 0
    trigger_reason: str = ""
    splunk_url: str = ""
    search_terms: str = ""                          # SPL 简化版
    full_spl: str = ""                              # SPL 完整版
    results: list[AlertResult] = []
    operator_notes: str = ""


class RiskDetails(BaseModel):
    """风险判定详情"""
    environment_risk: str = "未知"                  # 高 / 中 / 低 / 未知
    environment: str = "Unknown"                    # Production / Non‑Production
    count_risk: str = "低"
    count_value: int = 0
    attack_type_risk: str = "低"
    attack_types: list[str] = []
    overall_risk: str = "低"                        # 综合风险等级
    assessed_at: str = ""


class TokenUsage(BaseModel):
    """单次 LLM 调用的 Token 消耗"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ProcessTokenUsage(BaseModel):
    """一次告警处理的完整 Token 统计"""
    agent_planning: Optional[TokenUsage] = None    # Agent 调查规划消耗
    agent_analysis: Optional[TokenUsage] = None    # Agent 汇总三个 Tool 证据的消耗
    analysis_report: Optional[TokenUsage] = None    # 分析报告 LLM 消耗
    suggestion: Optional[TokenUsage] = None         # 处理建议 LLM 消耗
    total: TokenUsage = TokenUsage()                # 合计


class EnrichedAlert(RawAlert):
    """带风险等级的告警数据
    新增语义样本复用标记字段：from_sample / match_sample_id / match_score
    全部为可选，未命中样本时为 None，兼容历史旧告警json
    """
    risk_level: str = "低"
    risk_details: Optional[RiskDetails] = None
    token_usage: Optional[ProcessTokenUsage] = None

    # ========== 新增：语义样本匹配元数据 ==========
    from_sample: Optional[bool] = None          # True=复用样本报告；False=本次大模型实时生成；None=老数据无此字段
    match_sample_id: Optional[str] = None       # 命中的样本ID
    match_score: Optional[int] = None           # 匹配分数 0‑100
    agent_run_id: Optional[str] = None           # 分类未命中时对应的 Agent 运行记录
    agent_analysis: Optional[str] = None         # Agent 基于 Tool 证据得出的结论摘要


class AlertListItem(BaseModel):
    """告警列表项（用于前端展示）"""
    id: str
    alert_name: str
    hostname: str
    trigger_time: str
    risk_level: str
    processed_at: str
    application_code: str = ""


class AlertDetail(BaseModel):
    """告警详情（含报告和建议）
    补充透出样本复用信息，前端页面可以直接读取展示
    """
    alert: Optional[EnrichedAlert] = None
    risk_details: Optional[RiskDetails] = None
    analysis_report: Optional[str] = None
    suggestion: Optional[str] = None
    token_usage: Optional[ProcessTokenUsage] = None
    # 分类库复用信息，供前端详情页展示。
    from_sample: Optional[bool] = None
    match_sample_id: Optional[str] = None
    match_score: Optional[int] = None
