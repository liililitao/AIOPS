# 🚨 高风险 WAF 告警处理建议：`test-waf` —— `AGW-NCMA-PRD-01` 生产环境攻击探测

---

## 🚫 立即行动

> ⚠️ 本告警触发于**生产环境**，攻击类型含**环境文件扫描 + API漏洞探测**，整体风险等级**高**，需立即处理。

### ✅ 紧急操作清单（15分钟内完成）：

1. **临时封禁攻击源 IP**
   - 通过 Azure Application Gateway WAF 防火墙或 NSG 快速封禁发起请求的客户端IP（需从原始日志中提取，如尚未提取，请从 Splunk 原始日志中查询 `properties_clientIp` 字段）
   - 操作路径：Azure 门户 → Application Gateway → WAF 策略 → 自定义规则 → 添加 IP 封禁规则（如 IP 1.2.3.4）

2. **确认是否为误报或内部扫描**
   - 检查 `purview.novonordiskchina.com.cn` 是否属于公司内部业务域名
   - 联系业务团队确认是否在进行安全扫描或自动化测试（如 ZAP、BurpSuite、Nessus 等）
   - 如为误报，记录并关闭告警；如为真实攻击，进入“调查步骤”

3. **启动攻击溯源流程**
   - 从 Splunk 原始日志中提取完整请求链，包括：
     - `properties_clientIp`
     - `properties_requestUri` 的完整路径
     - `properties_httpMethod`
     - `properties_userAgent`
   - 检查是否来自已知恶意IP（如 AlienVault OTX、 AbuseIPDB）

---

## 🔍 调查步骤

> 目标：确认是否为真实攻击、攻击意图、是否已成功渗透

### 1. 关联日志检查（30分钟内完成）

```spl
index=azure category=ApplicationGatewayFirewallLog properties_hostname="purview.novonordiskchina.com.cn"
| search properties_requestUri="/.env~" OR properties_requestUri="/laravel/core/.env" OR properties_requestUri="/api/app/shop/hysOrderResultUrlParse"
| table _time, properties_clientIp, properties_requestUri, properties_httpMethod, properties_userAgent, properties_action, properties_status
| sort -_time
```

> 关注点：
- 是否有 `Allowed` 的请求？说明 WAF 未完全拦截
- `properties_userAgent` 是否为常见爬虫/扫描器（如 `python-requests`, `sqlmap`, `nmap`）
- 是否有其他端点被扫描（如 `/admin`, `/backup`, `/wp-config.php`）

### 2. 资产确认与服务暴露面评估

- 从 CMDB 确认 `AGW-NCMA-PRD-01` 所代理的后端服务
- 确认 `/api/app/shop/hysOrderResultUrlParse` 是否为合法公开API
  - 若为内部API，应禁止公网访问，仅允许内网或API网关转发
  - 若为外部API，检查其是否存在未授权访问漏洞（如未校验Token、未做IP白名单）

### 3. 环境文件风险核查

- 确认 `purview.novonordiskchina.com.cn` 后端服务是否使用 Laravel / XAMPP 等框架
- 检查服务器上是否存在 `.env` 文件被误暴露（即使 WAF 拦截，也需确认代码库或部署过程未遗留敏感文件）
- 建议：立即对后端服务器执行 `find /var/www -name ".env*" -type f` 扫描，删除或重命名非必要 `.env` 文件

---

## 🛡️ 处置建议（按风险等级差异化处理）

### 🔴 高风险生产环境处置（当前情况）

- **强制封禁攻击源 IP（24小时临时封禁）**
- **WAF 自定义规则加固（立即生效）**
  - 添加规则：阻断包含 `/\.env`、`/api/app/shop/hysOrderResultUrlParse` 的任何请求（除非为白名单IP）
  - 示例规则（Azure WAF）：
    ```
    Rule Name: Block .env access
    Condition: RequestURI contains .env
    Action: Block
    ```
- **通知后端开发团队**
  - 要求立即检查 `/api/app/shop/hysOrderResultUrlParse` 接口是否存在逻辑漏洞或未授权访问
  - 若非公开API，应立即下线或接入API网关鉴权

### 🟡 中风险（测试环境同理但可放宽）

- 若为测试环境，可暂不封禁IP，但需记录攻击源、通知测试团队
- 启用日志告警（如每天>5次扫描告警），用于评估测试工具是否过度扫描

### 🟢 低风险（仅限开发/本地环境）

- 忽略或仅记录日志，无需处置

---

## 🔧 后续加固建议

### 1. WAF 规则优化

- 增加正则规则拦截常见敏感路径：
  ```regex
  \.env|\.env\.backup|\.env\.staging|laravel/core/\.env|xampp/\.env|wp-config\.php|config\.php|web.config
  ```
- 针对 `/api/app/shop/` 路径启用 **API 限流 + 身份认证强制校验**（如 JWT Token）

### 2. 后端服务加固

- **敏感文件保护**：
  - 所有 `.env` 文件应设置 `chmod 600`，并禁止通过 Web 服务器直接访问
  - 使用 `.htaccess` 或 Nginx 配置禁止访问 `.env` 目录
- **API 安全防护**：
  - 对 `/api/app/shop/hysOrderResultUrlParse` 接口增加 Token 校验和速率限制（如 100次/分钟）
  - 增加请求来源白名单（如只允许特定 CDN 或网关 IP 访问）

### 3. 监控增强

- 增加 Splunk 告警规则：
  ```spl
  index=azure category=ApplicationGatewayFirewallLog properties_action=Blocked
  | search properties_hostname="purview.novonordiskchina.com.cn" AND (properties_requestUri="/.env*" OR properties_requestUri="/api/app/shop/hysOrderResultUrlParse")
  | stats count by properties_clientIp
  | where count >= 5
  | sendalert email to="security-team@novonordisk.com" subject="Suspicious .env/API Scan Detected"
  ```

---

## 📈 升级路径

> 以下情况需立即升级至安全响应团队（SOC）或高级安全工程师

| 条件 | 升级动作 |
|------|----------|
| 攻击源 IP 为已知恶意IP（如 AlienVault OTX 评分 >80） | 通知SOC，提交事件单，启动应急响应 |
| 后端服务确认被成功访问或返回敏感数据（如返回 200+ .env 内容） | 立即下线该API，启动数据泄露调查流程 |
| 同一 IP 或网段在24小时内多次触发类似告警（>5次） | 启动攻击者画像分析，封禁整个C段或AS号 |
| WAF 规则误报率高（>30%） | 通知安全架构师优化规则，避免业务中断 |

---

## ✅ 总结

| 项目 | 内容 |
|------|------|
| 告警名称 | `test-waf` |
| 受影响资源 | `AGW-NCMA-PRD-01`（生产环境） |
| 风险等级 | ⚠️ 高风险 |
| 攻击类型 | 环境文件扫描 + API漏洞探测 |
| 建议处理时效 | ⏱️ 1小时（含调查+处置+加固） |
| 优先级 | 🔴 紧急 |

---

> 📌 **最终建议**：立即封禁IP + 检查后端API安全性 + 加固WAF规则 + 通知业务团队评估影响。务必在24小时内完成完整处置并提交事件报告。

--- 

✅ 完成以上操作后，请在工单系统中标记为“已处理”，并附上Splunk日志链接与封禁IP列表。

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-07-29 14:37:38*