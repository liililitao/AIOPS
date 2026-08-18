"""可信的 Agent Tool 运行时上下文。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AlertToolContext:
    """由服务端注入、不会暴露给模型的本次分析身份与依赖。"""

    alert_id: str
    run_id: str
    actor_id: str = "system"
    splunk_service: Any | None = None
