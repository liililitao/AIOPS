# 按用户显示应用告警

当前 AIOps 服务已经支持：

1. 使用 Splunk `aiopssignurl` 的 HMAC 签名验证 URL 中的用户名；
2. 将用户名写入服务端会话，不再信任浏览器自行修改的 `user` 参数；
3. 从 `user_application_permissions` 查询用户可访问的应用；
4. 在告警列表和单条告警详情两个接口都执行过滤。

## 启用认证

在 `aiops/.env` 中补充：

```dotenv
AIOPS_AUTH_ENABLED=true
AIOPS_HANDOFF_SECRET=与Splunk端hmac_secret完全相同的内容
AIOPS_SESSION_SECRET=一串新的、不同的至少32字符随机密钥
AIOPS_AUTHZ_DB=C:/Users/BOLL/Desktop/aiops/codeProject/1-aiOpsPoc/gateway/data/aiops_authorization.sqlite3
AIOPS_COOKIE_SECURE=false
```

`AIOPS_HANDOFF_SECRET` 不能重新生成，必须和 Splunk `aiops_handoff/local/hmac_secret` 一致；`AIOPS_SESSION_SECRET` 则只给 AIOps 服务使用。HTTP 本地测试保持 `AIOPS_COOKIE_SECURE=false`，切换 HTTPS 后改为 `true`。

生成会话密钥但不写入文件：

```powershell
& C:/Users/BOLL/Desktop/aiops/codeProject/1-aiOpsPoc/aiops/.venv/Scripts/python.exe -c "import secrets; print(secrets.token_hex(32))"
```

## 配置用户权限

在 `gateway` 目录运行：

```powershell
python authorization.py grant zhangsan iwe
python authorization.py grant lisi wecall
python authorization.py grant wangwu pmt
python authorization.py set-role adminboll admin
python authorization.py show-user zhangsan
```

当前权限库已经包含截图中的三条授权。普通用户只看得到被授权的应用；管理员可以看到全部应用。

## 告警如何归属应用

告警必须满足以下任一条件：

- `alert_name` 在 `alert_rule_applications` 表中，例如 `app_alert_iwe_Login_Failed → iwe`；
- 告警顶层或 `results` 中带 `application_code`、`application`、`app_code` 或 `service`，例如 `application_code=iwe`。

无法解析应用的告警默认对普通用户隐藏。管理员仍可看到，例如当前的 `adminboll`。

修改 `.env` 后重启 AIOps 服务，并从 Splunk Dashboard 重新点击入口获取新的签名链接。旧链接只允许使用一次，重复使用会被拒绝。
