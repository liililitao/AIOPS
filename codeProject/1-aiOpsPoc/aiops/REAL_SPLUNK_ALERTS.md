# 接入真实 Splunk 告警

页面有两类数据：原有的本地已处理告警，以及从 Splunk 同步的告警。启用后，首次打开“告警结果”、点击“刷新”或“立即扫描”都会调用 Splunk 管理 API，将最新结果缓存并显示在列表中。

## 1. 创建最小权限的只读账号和 REST 凭据

1. 在 Splunk Web 打开 `Settings → Access controls → Users`，创建专用账号，例如 `aiops_reader`；不要使用 `admin`。
2. 给该账号分配只允许搜索 `waflogalert` 索引的角色（至少需要 `search` 能力和该索引的读取权限）。
3. 在 Splunk 服务器终端为该账号生成 REST `sessionKey`：

   ```bash
   export SPLUNK_USERNAME=aiops_reader
   read -s -p "Splunk password: " SPLUNK_PASSWORD; export SPLUNK_PASSWORD
   python3 /路径/到/get_token.py
   unset SPLUNK_PASSWORD
   ```

   输出中 `<sessionKey>...</sessionKey>` 标签内的内容就是要填入 `SPLUNK_TOKEN` 的值。

不要使用 `Settings → Data inputs → HTTP Event Collector` 创建的 HEC Token：它只能写入事件，不能查询告警。也不要把密码或 Token 提交到 Git、Dashboard XML 或聊天消息中。

`sessionKey` 通常会过期，适合先完成联调。生产环境应请 Splunk 管理员签发可轮换、长期有效且兼容 `Authorization: Splunk` 的服务凭据，并保存在密钥管理服务中。

## 2. 配置运行 AIOps 后端的 `.env`

在 `aiops/.env` 中添加实际值：

```dotenv
PORT=5000
SPLUNK_ENABLED=true
SPLUNK_BASE_URL=https://spl9-tst-hfwr01.chinanorth3.cloudapp.chinacloudapi.cn:8089
SPLUNK_TOKEN=粘贴-aiops_reader-的-sessionKey
SPLUNK_VERIFY_TLS=true
SPLUNK_ALERT_INDEX=waflogalert
SPLUNK_ALERT_EARLIEST_TIME=-24h@h
SPLUNK_ALERT_LATEST_TIME=now
SPLUNK_ALERT_MAX_RESULTS=500
```

如果测试环境使用自签名证书，确认服务器身份后才可临时设置 `SPLUNK_VERIFY_TLS=false`。生产环境应保留 `true`。

当 `waflogalert` 不是目标数据源时，可以用 `SPLUNK_ALERT_QUERY` 配置完整 SPL，例如：

```dotenv
SPLUNK_ALERT_QUERY=search index=waflogalert | sort 0 - _time | head 500
```

## 3. 重启 AIOps 后端

在 `aiops` 目录运行：

```powershell
.\.venv\Scripts\python.exe .\run.py
```

## 4. 验证

打开页面后，点击“刷新”。正常时会请求 `POST /api/v1/alerts/sync`，随后列表显示最新的 Splunk 告警。点击“立即扫描”会先同步 Splunk，再执行原有本地告警目录扫描，完成后刷新列表。

可以直接访问以下地址排查：

```text
http://127.0.0.1:5000/api/v1/alerts
```

若同步失败，页面会提示 Splunk 连接或认证错误；常见原因是 8089 端口未开放、Token 缺少 `search` 权限、证书不受信任，或 `waflogalert` 索引不存在。
