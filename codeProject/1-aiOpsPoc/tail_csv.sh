#!/bin/bash
# 用法: tail_csv.sh <csv文件路径>
# Splunk scripted input — 只输出新增的行
FILE="$1"
STATE_FILE="/data/splunk/var/test_log_app/.offset_$(basename $FILE)"

# 读取上次位置
OFFSET=0
[ -f "$STATE_FILE" ] && OFFSET=$(cat "$STATE_FILE")

# 获取当前文件大小
SIZE=$(stat -c%s "$FILE" 2>/dev/null || echo 0)

# 有新增内容
if [ "$SIZE" -gt "$OFFSET" ]; then
    tail -c +$((OFFSET+1)) "$FILE"
fi

echo "$SIZE" > "$STATE_FILE"