from app.tools.historical_alert_tool import search_historical_alerts
from app.tools.knowledge_base_tool import search_knowledge_base
from app.tools.splunk_log_tool import investigate_splunk_logs

HISTORICAL_ALERT_TOOLS = [search_historical_alerts]
KNOWLEDGE_BASE_TOOLS = [search_knowledge_base]
SPLUNK_LOG_TOOLS = [investigate_splunk_logs]
ALERT_ANALYSIS_TOOLS = [
    search_historical_alerts,
    search_knowledge_base,
    investigate_splunk_logs,
]

__all__ = [
    "search_historical_alerts",
    "search_knowledge_base",
    "investigate_splunk_logs",
    "HISTORICAL_ALERT_TOOLS",
    "KNOWLEDGE_BASE_TOOLS",
    "SPLUNK_LOG_TOOLS",
    "ALERT_ANALYSIS_TOOLS",
]
