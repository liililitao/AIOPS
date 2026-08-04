#!/bin/bash
# wrapper_alert.sh
# Splunk 告警动作入口 — 串行调用两个 Python 告警脚本
# 部署: cp wrapper_alert.sh /data/splunk/bin/scripts/
#       chown splunk:splunk /data/splunk/bin/scripts/wrapper_alert.sh
#       chmod 755 /data/splunk/bin/scripts/wrapper_alert.sh

SCRIPT_DIR="/data/splunk/bin/scripts"

echo "[wrapper] 开始执行告警动作..."
echo "[wrapper] -> alert_to_file.py (无风险等级 → waf_alerts)"
python3 "$SCRIPT_DIR/alert_to_file.py"
rc1=$?

echo "[wrapper] -> alert_to_file_risk.py (有风险等级 → waflogalert)"
python3 "$SCRIPT_DIR/alert_to_file_risk.py"
rc2=$?

echo "[wrapper] 完成. exit: alert_to_file.py=$rc1  alert_to_file_risk.py=$rc2"
exit 0
