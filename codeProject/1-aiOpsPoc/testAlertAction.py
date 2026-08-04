#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Splunk Alert Action Test Script
用途: 验证告警触发后脚本是否能正常执行
注意: 此脚本由 splunkd 进程调用，运行用户通常为 splunk/nobody
"""

import os
import sys
import json
from datetime import datetime

def main():
    # 【关键】使用绝对路径！Splunk alert script 的工作目录是不确定的
    # 建议输出到 $SPLUNK_HOME/var/log/splunk/ 或你有写权限的目录
    OUTPUT_DIR = "/data/splunk/bin/scripts"
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "helloworld.py")

    try:
        # 创建空文件
        with open(OUTPUT_FILE, "w") as f:
            pass  # 生成空文件即可

        # 【强烈建议】同时写一个带时间戳的日志，方便确认每次触发都生效
        log_file = os.path.join(OUTPUT_DIR, "alert_action_test.log")
        with open(log_file, "a") as lf:
            timestamp = datetime.now().isoformat()
            # Splunk 会通过 stdin 传入告警结果的 JSON，读取前几个字段用于调试
            stdin_data = ""
            if not sys.stdin.isatty():
                stdin_data = sys.stdin.read()[:500]  # 只读前500字符防止阻塞
            lf.write(f"[{timestamp}] helloworld.py created | stdin_preview={stdin_data}\n")

        # 退出码 0 = 成功，非0 = Splunk 会标记该 alert action 失败
        sys.exit(0)

    except Exception as e:
        # 将异常写入 splunkd 可捕获的 stderr
        sys.stderr.write(f"Alert action failed: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()