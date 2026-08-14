# 每日从 Splunk 导入 CMDB CSV

## 配置

在 `aiops/.env` 中设置：

```dotenv
CMDB_TYPE=splunk_csv
CMDB_CSV_PATH=data/cmdb_latest.csv
CMDB_SPLUNK_QUERY=search index=cmdb | fields "Resource Name" "Resource Type" Environment SUBSCRIPTION | head 50000
CMDB_SPLUNK_SYNC_ENABLED=true
CMDB_SPLUNK_SYNC_HOUR=1
CMDB_SPLUNK_SYNC_MINUTE=0
```

将示例查询替换为实际的 CMDB 数据查询。查询结果必须包含至少一个可识别的 CMDB 字段，例如 `Resource Name`、`Server Name`、`Environment` 或 `域名和证书`。

## 运行方式

- AIOps 启动时注册每日任务，默认每天 01:00 执行。
- 任务调用 Splunk `/services/search/jobs/export`，请求 `output_mode=csv`。
- CSV 先校验表头和数据行，再使用临时文件原子替换 `data/cmdb_latest.csv`。
- 下载或校验失败时保留上一份成功文件，不会覆盖有效数据。
- 成功替换后自动清除 CMDB 内存缓存，后续告警查询使用新数据。
- 配置页的“立即从 Splunk 同步 CMDB”可用于联调，不必等到凌晨。

修改 `.env` 后必须重启后端。若页面显示旧配置，请确认浏览器访问的是当前 5000 端口服务。
