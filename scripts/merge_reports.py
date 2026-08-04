#!/usr/bin/env python
"""
合并分析报告和处理建议为单个文档
用法: python scripts/merge_reports.py <alert_name>
"""

import sys
from pathlib import Path
from datetime import datetime


def merge(alert_name: str, date_str: str = None):
    """将分析报告和处理建议合并为一个 Markdown 文件"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    base = Path(__file__).parent.parent
    report_dir = base / "output" / "reports" / date_str
    sug_dir = base / "output" / "suggestions" / date_str

    reports = sorted(report_dir.glob(f"{alert_name}*.md")) if report_dir.exists() else []
    suggestions = sorted(sug_dir.glob(f"{alert_name}*.md")) if sug_dir.exists() else []

    if not reports and not suggestions:
        print(f"未找到 {alert_name} 的报告或建议")
        return

    merged = []
    merged.append(f"# {alert_name} — 综合分析报告\n")
    merged.append(f"> 合并时间: {datetime.now().isoformat()}\n")
    merged.append("---\n")

    if reports:
        merged.append("\n# 第一部分：分析报告\n")
        merged.append(reports[-1].read_text(encoding="utf-8"))
        merged.append("\n---\n")

    if suggestions:
        merged.append("\n# 第二部分：处理建议\n")
        merged.append(suggestions[-1].read_text(encoding="utf-8"))

    output_path = base / "output" / f"{alert_name}_merged_{date_str}.md"
    output_path.write_text("".join(merged), encoding="utf-8")
    print(f"合并完成: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python merge_reports.py <alert_name> [date]")
        sys.exit(1)
    merge(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
