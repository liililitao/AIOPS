#!/usr/bin/env python3
"""一键导入 Splunk Dashboard XML 配置."""
import requests, urllib3, sys
from pathlib import Path

urllib3.disable_warnings()

SPLUNK_API = "https://localhost:8089/servicesNS/admin/search/data/ui/views"
XML_FILE = Path(__file__).parent / "splunk_dashboard.xml"

if not XML_FILE.exists():
    print(f"文件不存在: {XML_FILE}")
    sys.exit(1)

xml_content = XML_FILE.read_text(encoding="utf-8")

r = requests.post(
    SPLUNK_API,
    auth=("admin", "12345678"),
    data={"name": "aiops_overview", "eai:data": xml_content},
    verify=False,
    timeout=15,
)

if r.status_code in (200, 201):
    print("Dashboard 导入成功!")
    print("访问: http://localhost:8001/en-US/app/search/aiops_overview")
elif r.status_code == 409:
    print("Dashboard 已存在, 尝试更新...")
    # 先获取现有视图再更新
    r2 = requests.get(
        f"{SPLUNK_API}/aiops_overview",
        auth=("admin", "12345678"),
        params={"output_mode": "json"},
        verify=False,
        timeout=10,
    )
    if r2.status_code == 200:
        # 更新
        r3 = requests.post(
            f"{SPLUNK_API}/aiops_overview",
            auth=("admin", "12345678"),
            data={"eai:data": xml_content},
            verify=False,
            timeout=15,
        )
        if r3.status_code in (200, 201):
            print("Dashboard 更新成功!")
            print("访问: http://localhost:8001/en-US/app/search/aiops_overview")
        else:
            print(f"更新失败: HTTP {r3.status_code}")
            print(r3.text[:300])
    else:
        print(f"查询失败: HTTP {r2.status_code}")
else:
    print(f"导入失败: HTTP {r.status_code}")
    print(r.text[:500])
