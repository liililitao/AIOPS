"""
CMDB 查询数据模型
"""

from typing import Optional

from pydantic import BaseModel


class CmdbLookupResult(BaseModel):
    """CMDB 查询结果"""
    found: bool = False
    match_type: str = "none"                        # exact / fuzzy / none
    resource_name: str = ""
    resource_type: str = ""
    environment: str = "Unknown"                    # Production / Non-Production / Unknown
    subscription: str = ""
    server_name: str = ""
    source_sheet: str = ""                          # Azure PaaS / Azure IaaS / Computer System List
    source_row: int = 0
    error: str = ""
