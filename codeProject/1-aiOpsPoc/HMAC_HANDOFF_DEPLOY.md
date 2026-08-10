# Splunk → AIOps HMAC 安全跳转部署说明

## 已实现的安全流程

1. Splunk Dashboard 每 30 秒执行一次服务端命令 `aiopssignurl`。
2. 命令使用当前 Splunk 会话调用 `current-context`，取得真实用户名和角色。
3. 命令生成 90 秒有效的 `user + roles + exp + nonce + sig` URL。
4. AIOps 网关检查有效期、HMAC 签名和 nonce 是否已使用。
5. 验证通过后，网关签发内部 JWT Cookie，并 302 到不含签名参数的 `/app/`。
6. 同一个 nonce 再次使用会被拒绝；修改用户名、角色或过期时间也会导致验签失败。

> HMAC Secret 与 JWT Secret 必须是两个不同的随机密钥，且都不能提交到代码库。

## 一、部署 Splunk 签名命令

将整个目录：

```text
splunk_app/aiops_handoff
```

复制到 Splunk 服务器：

```text
/data/splunk/etc/apps/aiops_handoff
```

确认主要文件位置：

```text
/data/splunk/etc/apps/aiops_handoff/default/commands.conf
/data/splunk/etc/apps/aiops_handoff/bin/aiops_sign_url.py
/data/splunk/etc/apps/aiops_handoff/bin/aiops_handoff_protocol.py
```

为脚本增加执行权限：

```bash
sudo chown -R splunk:splunk /data/splunk/etc/apps/aiops_handoff
sudo chmod 750 /data/splunk/etc/apps/aiops_handoff/bin/*.py
```

## 二、生成并配置共享 HMAC Secret

在 Splunk 服务器生成一个 32 字节随机密钥：

```bash
sudo mkdir -p /data/splunk/etc/apps/aiops_handoff/local
openssl rand -hex 32 | sudo tee /data/splunk/etc/apps/aiops_handoff/local/hmac_secret >/dev/null
sudo chown splunk:splunk /data/splunk/etc/apps/aiops_handoff/local/hmac_secret
sudo chmod 600 /data/splunk/etc/apps/aiops_handoff/local/hmac_secret
```

配置 AIOps 跳转地址：

```bash
printf '%s\n' 'http://spl9-tst-hfwr01.chinanorth3.cloudapp.chinacloudapi.cn:5000/app/' \
  | sudo tee /data/splunk/etc/apps/aiops_handoff/local/handoff_url >/dev/null
sudo chown splunk:splunk /data/splunk/etc/apps/aiops_handoff/local/handoff_url
sudo chmod 600 /data/splunk/etc/apps/aiops_handoff/local/handoff_url
```

默认签名有效期是 90 秒。如需调整，可创建 `local/ttl_seconds`；网关允许的最大 TTL 也要同步调整。

## 三、重启并验证 Splunk 命令

```bash
sudo -u splunk /data/splunk/bin/splunk restart
```

登录 Splunk，在 Search & Reporting 中执行：

```spl
| makeresults
| aiopssignurl
| table handoff_user handoff_exp handoff_url
```

成功标准：返回当前登录用户名以及包含以下参数的 URL：

```text
v=1&user=...&exp=...&nonce=...&roles=...&sig=...
```

如果出现 `sessionKey/splunkdUri` 缺失，应确认 `commands.conf` 中保留：

```ini
enableheader = true
passauth = true
```

## 四、部署 AIOps 网关

将以下两个文件部署到同一目录：

```text
gateway/gateway.py
gateway/handoff_auth.py
```

将 Splunk 的 HMAC Secret 安全复制一份到网关服务器，例如：

```text
/opt/aiops-gateway/secrets/handoff_secret
```

再单独生成 JWT Secret：

```bash
sudo mkdir -p /opt/aiops-gateway/secrets /var/lib/aiops-gateway
openssl rand -hex 32 | sudo tee /opt/aiops-gateway/secrets/jwt_secret >/dev/null
sudo chmod 600 /opt/aiops-gateway/secrets/handoff_secret
sudo chmod 600 /opt/aiops-gateway/secrets/jwt_secret
```

启动网关前配置环境变量：

项目中的 `gateway/.env.hmac.example` 列出了完整配置项。也可以在当前 shell 中设置：

```bash
export AIOPS_HANDOFF_SECRET_FILE=/opt/aiops-gateway/secrets/handoff_secret
export JWT_SECRET_FILE=/opt/aiops-gateway/secrets/jwt_secret
export AIOPS_HANDOFF_MAX_TTL_SECONDS=120
export AIOPS_HANDOFF_CLOCK_SKEW_SECONDS=5
export AIOPS_HANDOFF_NONCE_DB=/var/lib/aiops-gateway/handoff_nonces.sqlite3
export ALLOW_LEGACY_SPLUNK_USER=false
export ALLOW_SPLUNK_TOKEN_QUERY=false
export AUTH_COOKIE_SECURE=false
python3 gateway.py
```

当前地址是 HTTP，所以示例暂时使用 `AUTH_COOKIE_SECURE=false`。切换到 HTTPS 后必须改为：

```bash
export AUTH_COOKIE_SECURE=true
```

检查配置状态：

```text
http://spl9-tst-hfwr01.chinanorth3.cloudapp.chinacloudapi.cn:5000/health
```

应包含：

```json
{
  "hmac_handoff": "configured",
  "jwt_signing": "configured"
}
```

## 五、可选：根据 Splunk 角色限制访问

不设置 `AIOPS_ALLOWED_ROLES` 时，所有通过 HMAC 验证的 Splunk 用户都可以进入。

例如只允许 `admin` 或 `power`：

```bash
export AIOPS_ALLOWED_ROLES=admin,power
```

角色来自 Splunk `current-context`，包含在 HMAC 签名中，用户无法通过修改 URL 增加角色。

## 六、更新 Dashboard

在 Splunk 中打开 WAF Dashboard：

```text
编辑 → 源代码
```

使用项目中的完整 `waf_dashboard.xml` 替换原 XML 后保存。新版 Dashboard 不再直接使用：

```text
?splunk_user=$env:user$
```

而是使用隐藏搜索产生的 `$aiops_handoff_url$`。

## 七、验收检查

1. Dashboard 按钮能够正常显示并打开 AIOps。
2. 首次请求包含 `user/exp/nonce/roles/sig`，随后 302 到干净的 `/app/`。
3. 网关日志包含 `Splunk HMAC authentication succeeded`。
4. 将 URL 中的 `user` 改成 `admin` 后访问，应返回 `401 signature`。
5. 完整复制同一个签名 URL再次访问，应返回 `401 replay`。
6. 等待链接过期后访问，应返回 `401 expired`。

生产环境还应启用 HTTPS；HMAC 只能防止参数篡改，不能加密网络流量。
