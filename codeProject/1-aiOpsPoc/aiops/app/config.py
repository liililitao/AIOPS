"""
应用配置管理 - 基于 pydantic-settings，从 .env 文件加载
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，所有值从 .env 或环境变量加载"""

    # ==========================================
    # 应用基础
    # ==========================================
    APP_NAME: str = "AIOps-Alert-Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8001
    HOST: str = "0.0.0.0"

    # ==========================================
    # LLM API 配置 (OpenAI‑compatible)
    # ==========================================
    LLM_BASE_URL: str = "https://api.marketplace.novo-genai.com/v1"
    LLM_API_KEY: str = ""
    LLM_USER_EMAIL: str = ""

    # 模型配置
    ROUTER_MODEL: str = "openai_gpt5"
    PLANNER_MODEL: str = "openai_gpt5"
    EXECUTOR_MODEL: str = "openai_gpt5"
    REPORT_MODEL: str = "openai_gpt5"
    RAG_CHAT_MODEL: str = "openai_gpt5"

    # LLM 参数
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT: int = 120

    # ==========================================
    # 定时扫描配置
    # ==========================================
    SCAN_ENABLED: bool = True
    SCAN_INTERVAL_MINUTES: int = 5
    ALERT_INPUT_DIR: str = "../mutil-rag-agent-main-v1/告警数据"
    ALERT_OUTPUT_DIR: str = "../mutil-rag-agent-main-v1/带风险等级的告警数据"
    PROCESSED_INDEX_PATH: str = "data/processed_alerts.json"
    # 原始告警和增强告警的规范归档位置。前端输出目录可以继续保持现有配置，
    # 但历史告警库始终以这两处本地文件为权威来源。
    RAW_ALERT_DIR: str = "data/alerts"
    HISTORICAL_ENRICHED_ALERT_DIR: str = "output/enriched_alerts"
    # 模拟应用告警分为待分析原始数据与 AI 增强结果，二者绝不互相覆盖。
    APPLICATION_ALERT_DIR: str = "data/application_alerts"
    APPLICATION_ENRICHED_ALERT_DIR: str = "output/application_alerts"

    # Splunk 真实告警数据源
    SPLUNK_ENABLED: bool = False
    SPLUNK_BASE_URL: str = ""
    SPLUNK_TOKEN: str = ""
    SPLUNK_VERIFY_TLS: bool = True
    SPLUNK_ALERT_INDEX: str = "waflogalert"
    SPLUNK_ALERT_QUERY: str = ""
    SPLUNK_ALERT_EARLIEST_TIME: str = "-24h@h"
    SPLUNK_ALERT_LATEST_TIME: str = "now"
    SPLUNK_ALERT_MAX_RESULTS: int = 500
    SPLUNK_TIMEOUT_SECONDS: int = 20
    # Agent 的 Splunk 日志调查配置。查询模板和索引均由服务端控制，不能由
    # 模型或前端输入任意 SPL，避免 Agent 获得写入或越权检索能力。
    SPLUNK_LOG_INDEX: str = "azure"
    SPLUNK_INVESTIGATION_MAX_RESULTS: int = 200
    SPLUNK_INVESTIGATION_MAX_ITEMS: int = 10
    SPLUNK_INVESTIGATION_MAX_TEXT_CHARS: int = 160
    SPLUNK_INVESTIGATION_ITEM_BUDGET_CHARS: int = 4000
    SPLUNK_INVESTIGATION_TOTAL_BUDGET_CHARS: int = 12000

    # Splunk 跳转认证与应用告警权限
    AIOPS_AUTH_ENABLED: bool = False
    AIOPS_HANDOFF_SECRET: str = ""
    AIOPS_SESSION_SECRET: str = ""
    AIOPS_HANDOFF_MAX_TTL_SECONDS: int = 120
    AIOPS_HANDOFF_CLOCK_SKEW_SECONDS: int = 5
    AIOPS_HANDOFF_NONCE_DB: str = "data/handoff_nonces.sqlite3"
    AIOPS_SESSION_HOURS: int = 8
    AIOPS_COOKIE_SECURE: bool = False
    AIOPS_AUTHZ_DB: str = ""

    # ==========================================
    # CMDB 数据源
    # ==========================================
    CMDB_TYPE: Literal["xlsx", "csv", "splunk_csv", "api"] = "xlsx"
    CMDB_XLSX_PATH: str = ""
    CMDB_CSV_PATH: str = "data/cmdb_latest.csv"
    CMDB_SPLUNK_QUERY: str = ""
    CMDB_SPLUNK_SYNC_ENABLED: bool = False
    CMDB_SPLUNK_SYNC_HOUR: int = 1
    CMDB_SPLUNK_SYNC_MINUTE: int = 0
    CMDB_API_URL: str = ""
    CMDB_API_TOKEN: str = ""

    # ==========================================
    # 风险判定参数
    # ==========================================
    RISK_COUNT_HIGH_THRESHOLD: int = 200
    RISK_COUNT_MEDIUM_THRESHOLD: int = 100

    # ==========================================
    # Milvus 向量数据库
    # ==========================================
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "sop_knowledge"
    HISTORICAL_ALERT_COLLECTION: str = "historical_alerts"
    MILVUS_ENABLED: bool = False
    HISTORICAL_ALERT_INDEX_ENABLED: bool = True

    # Embedding
    EMBEDDING_PROVIDER: Literal["openai", "dashscope", "ollama"] = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_API_KEY: str = ""

    # ==========================================
    # 输出配置
    # ==========================================
    OUTPUT_REPORTS_DIR: str = "output/reports"
    OUTPUT_SUGGESTIONS_DIR: str = "output/suggestions"
    OUTPUT_AGENT_RUNS_DIR: str = "output/agent_runs"

    # ==========================================
    # Web 服务
    # ==========================================
    FRONTEND_DIR: str = "frontend"
    CORS_ORIGINS: str = "*"

    # ==========================================
    # 知识库配置
    # ==========================================
    KB_ADMIN_TOKEN: str = "aiops123"

    # ==========================================
    # 日志
    # ==========================================
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    # ==========================================
    # Agent 配置
    # ==========================================
    MAX_AGENT_STEPS: int = 7
    AGENT_TIMEOUT_SECONDS: int = 300

    # ==========================================
    # 告警分类库：结果仍按“告警类别 × 告警风险等级”有限存储。
    # 复用前由 ROUTER_MODEL 比对新告警与分类库/收藏样本的业务语义；
    # 只有模型给出的分数达到阈值才命中。
    # ==========================================
    ALERT_CLASSIFICATION_ENABLED: bool = True
    ALERT_CLASSIFICATION_STORE: str = "data/alert_classifications.json"
    ALERT_CLASSIFICATION_MAX_RECORDS: int = 280
    SEMANTIC_MATCH_THRESHOLD: int = 85
    ALERT_CLASSIFICATION_AUTO_ENROLL: bool = True
    ALERT_CLASSIFICATION_MAX_CANDIDATES: int = 12
    ALERT_CLASSIFICATION_MAX_FIELD_CHARS: int = 800

    # 分类库未命中后由 Agent 调用三个 Tool 的参数。
    HISTORICAL_ALERT_TOP_K: int = 3
    KNOWLEDGE_BASE_TOP_K: int = 5
    AGENT_EVIDENCE_MAX_CONTEXT_CHARS: int = 7000

    # pydantic‑settings 配置，必须放在类内部，与字段对齐
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}

    @property
    def project_root(self) -> Path:
        """aiops 项目根目录"""
        return Path(__file__).parent.parent.resolve()

    @property
    def alert_input_path(self) -> Path:
        """告警输入目录绝对路径"""
        path = Path(self.ALERT_INPUT_DIR)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def agent_runs_path(self) -> Path:
        path = Path(self.OUTPUT_AGENT_RUNS_DIR)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def alert_output_path(self) -> Path:
        """告警输出目录绝对路径"""
        path = Path(self.ALERT_OUTPUT_DIR)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def raw_alert_path(self) -> Path:
        """历史告警库使用的原始告警归档目录。"""
        path = Path(self.RAW_ALERT_DIR)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def historical_enriched_alert_path(self) -> Path:
        """历史告警库使用的增强告警规范归档目录。"""
        path = Path(self.HISTORICAL_ENRICHED_ALERT_DIR)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def application_alert_path(self) -> Path:
        """模拟应用告警的原始、待分析数据目录。"""
        path = Path(self.APPLICATION_ALERT_DIR)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def application_enriched_alert_path(self) -> Path:
        """模拟应用告警经 AI 分析后的独立增强数据目录。"""
        path = Path(self.APPLICATION_ENRICHED_ALERT_DIR)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def alert_classification_store_path(self) -> Path:
        path = Path(self.ALERT_CLASSIFICATION_STORE)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def embedding_dimension(self) -> int:
        """当前 Embedding 模型的维度，用于独立的历史告警索引。"""
        model = self.EMBEDDING_MODEL.lower()
        if self.EMBEDDING_PROVIDER == "ollama":
            return 1024
        if "3-large" in model:
            return 3072
        if "3-small" in model or "ada" in model:
            return 1536
        return 1024

    @property
    def cmdb_xlsx_path(self) -> Optional[Path]:
        """CMDB xlsx 文件绝对路径"""
        if not self.CMDB_XLSX_PATH:
            return None
        path = Path(self.CMDB_XLSX_PATH)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve() if path.exists() else None

    @property
    def cmdb_csv_path(self) -> Optional[Path]:
        """CMDB CSV 文件绝对路径。"""
        if not self.CMDB_CSV_PATH:
            return None
        path = Path(self.CMDB_CSV_PATH)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve() if path.exists() else None

    @property
    def processed_index_path(self) -> Path:
        """已处理告警索引文件路径"""
        path = Path(self.PROCESSED_INDEX_PATH)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def handoff_nonce_db_path(self) -> Path:
        path = Path(self.AIOPS_HANDOFF_NONCE_DB)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def authorization_db_path(self) -> Path:
        if self.AIOPS_AUTHZ_DB:
            path = Path(self.AIOPS_AUTHZ_DB)
            if not path.is_absolute():
                path = self.project_root / path
            return path.resolve()
        return (self.project_root.parent / "gateway" / "data" / "aiops_authorization.sqlite3").resolve()

    @property
    def reports_path(self) -> Path:
        """分析报告输出目录"""
        path = Path(self.OUTPUT_REPORTS_DIR)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def suggestions_path(self) -> Path:
        """处理建议输出目录"""
        path = Path(self.OUTPUT_SUGGESTIONS_DIR)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    def validate_runtime(self) -> list[str]:
        """启动时验证关键配置，返回警告列表"""
        warnings = []
        if not self.LLM_API_KEY:
            warnings.append("LLM_API_KEY 未配置，LLM 调用将不可用")
        if self.CMDB_TYPE == "xlsx" and not self.cmdb_xlsx_path:
            warnings.append(
                f"CMDB xlsx 文件不存在: {self.CMDB_XLSX_PATH}，CMDB 查询将返回 Unknown"
            )
        if self.CMDB_TYPE in {"csv", "splunk_csv"} and not self.cmdb_csv_path:
            warnings.append(
                f"CMDB CSV 文件不存在: {self.CMDB_CSV_PATH}，CMDB 查询将返回 Unknown"
            )
        if self.CMDB_SPLUNK_SYNC_ENABLED and not self.CMDB_SPLUNK_QUERY:
            warnings.append("CMDB_SPLUNK_SYNC_ENABLED=true，但 CMDB_SPLUNK_QUERY 未配置")
        if not self.alert_input_path.exists():
            warnings.append(
                f"告警输入目录不存在: {self.alert_input_path}，将自动创建"
            )
        if self.SPLUNK_ENABLED:
            if not self.SPLUNK_BASE_URL:
                warnings.append("SPLUNK_ENABLED=true，但 SPLUNK_BASE_URL 未配置")
            if not self.SPLUNK_TOKEN:
                warnings.append("SPLUNK_ENABLED=true，但 SPLUNK_TOKEN 未配置")
        if self.AIOPS_AUTH_ENABLED:
            if len(self.AIOPS_HANDOFF_SECRET.encode("utf-8")) < 32:
                warnings.append("AIOPS_AUTH_ENABLED=true，但 AIOPS_HANDOFF_SECRET 无效")
            if len(self.AIOPS_SESSION_SECRET.encode("utf-8")) < 32:
                warnings.append("AIOPS_AUTH_ENABLED=true，但 AIOPS_SESSION_SECRET 无效")
            if not self.authorization_db_path.exists():
                warnings.append(f"告警权限数据库不存在: {self.authorization_db_path}")
        return warnings


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
