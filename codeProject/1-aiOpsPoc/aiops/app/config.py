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
    # LLM API 配置 (OpenAI-compatible)
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
    ALERT_INPUT_DIR: str = "../告警数据"
    ALERT_OUTPUT_DIR: str = "../带风险等级的告警数据"
    PROCESSED_INDEX_PATH: str = "data/processed_alerts.json"

    # ==========================================
    # CMDB 数据源
    # ==========================================
    CMDB_TYPE: Literal["xlsx", "api"] = "xlsx"
    CMDB_XLSX_PATH: str = ""
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
    MILVUS_ENABLED: bool = False

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
    def alert_output_path(self) -> Path:
        """告警输出目录绝对路径"""
        path = Path(self.ALERT_OUTPUT_DIR)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

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
    def processed_index_path(self) -> Path:
        """已处理告警索引文件路径"""
        path = Path(self.PROCESSED_INDEX_PATH)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

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
        if not self.alert_input_path.exists():
            warnings.append(
                f"告警输入目录不存在: {self.alert_input_path}，将自动创建"
            )
        return warnings


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
