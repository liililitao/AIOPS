# 告警处理建议：`test-waf` - 环境文件扫描攻击（高风险）

---

## 🔴 立即行动（生产环境需立即执行）

✅ **1. 确认 WAF 拦截有效性**  
- 登录 Azure Application Gateway 控制台 → 查看 `AGW-DAP-PRD-N3-01` 的防火墙日志  
- 核实告警中 `20 次拦截` 是否均成功阻止，确认无绕过行为  
- 检查 `properties_requestUri` 列中的路径是否均为非法尝试（`.env` 文件访问）

✅ **2. 查看源 IP & 用户行为**  
- 在 Splunk 中执行原始搜索，追加 `| stats count by properties_clientIp, properties_userAgent`  
- 识别攻击源 IP（如为公网 IP，立即加入 WAF 全局黑名单）  
- 检查是否来自已知恶意 IP 库（如 AbuseIPDB、AlienVault OTX）

✅ **3. 告警升级 + 通知责任人**  
- 立即通知 **安全响应组 + 应用负责人（purview.novonordiskchina.com.cn）**  
- 启动 **生产环境高风险事件响应流程**（参考组织 SOP）  
- 记录事件编号（如: `SEC-20260729-AGW-DAP-PRD-N3-01-001`）

✅ **4. 短期缓解（如无法立即加固）**  
- 在 Azure WAF 中为该网关添加**自定义规则**，阻断所有对 `/.env*` 路径的访问  
  ➤ 规则示例：`Request URI contains ".env"` → 动作：`Block`  
- 启用 WAF 的“**核心规则集（CRS）3.2+**”并确保启用了“**敏感文件访问防护**”规则

---

## 🔍 调查步骤（确认是否真实攻击）

📌 **1. 检查是否为合法工具/脚本误扫**  
- 查询 CMDB 或应用发布记录：是否有 CI/CD 工具、健康检查脚本访问 `/admin/.env` 或类似路径？  
- 与 `purview.novonordiskchina.com.cn` 团队确认：是否有自动化测试或部署脚本在此时间段活动？

📌 **2. 查看关联日志（是否存在后续攻击）**  
- 在 Splunk 中扩展时间范围（如 -24h），搜索：  
  ```
  index=azure category=ApplicationGatewayFirewallLog 
  properties_hostname="purview.novonordiskchina.com.cn" 
  | stats count by properties_requestUri, properties_clientIp
  ```
- 若发现扫描后出现 SQL注入、目录遍历、或登录尝试 → 判定为**攻击链延伸**，需紧急处置

📌 **3. 溯源攻击者行为图谱**  
- 使用 Azure Sentinel 或第三方 SIEM 工具关联：  
  - 该 IP 是否访问过其他域名？  
  - 是否伴随异常 User-Agent 或高频 404 请求？  
  - 是否尝试下载 `.env` 文件（响应状态码 200 / 206）？

---

## 🛡️ 处置建议（按风险级别差异化处理）

### ✅ 高风险场景（当前状态）  
> 🔹 生产环境 + 环境文件扫描 + 已发生 20 次拦截  
> 🔹 存在泄露敏感配置（数据库密码、API密钥）风险

**立即措施**：  
- ✅ **临时封禁源 IP**（如可识别）  
- ✅ **强化 WAF 规则**（见上文）  
- ✅ **应用层加固**（见“后续加固”）  
- ✅ **通知开发团队验证 `.env` 文件是否存在**  
  ➤ 若存在，必须移至非 Web 可访问路径 + 设置文件权限 600  
  ➤ 若不存在，建议部署“404 响应伪装”或重定向至监控页面

### ⚠️ 中低风险场景（如为测试环境或少量请求）  
> 🔹 测试环境 + 请求量 < 5  
> 🔹 可能为误报或内部扫描

**快速确认后关闭**：  
- 与测试负责人确认扫描行为  
- 如为合法测试，更新 WAF 白名单或在测试域名排除规则  
- 不关闭告警，但标记为“已确认为合法行为”

---

## 🔧 后续加固（防止重复发生）

### 📌 1. WAF 规则优化

- ✅ **新增自定义规则**：阻断所有以 `/.env`, `/.env.*`, `/env.*`, `/.env.*.local` 结尾的请求  
- ✅ **启用 CRS 规则 930100、930110、930120**（路径遍历与敏感文件防护）  
- ✅ **配置“异常请求速率限制”**：同一 IP 1 分钟内超过 10 次尝试访问敏感路径 → 自动封禁 1 小时

### 📌 2. 应用系统加固

- ✅ **删除或重命名所有 .env 文件** → 移至 `/config/` 目录或使用环境变量  
- ✅ **设置 Web 服务器权限**：  
  - Nginx/Apache：禁止访问 `.env*` 文件  
    ```
    location ~* \.(env|env\.local|env\.production\.local)$ { deny all; }
    ```
  - 静态资源服务器：禁止目录列表 + 设置 `robots.txt` 阻止爬虫访问敏感路径
- ✅ **部署“敏感文件监控告警”**：  
  使用文件完整性监控（FIM）工具（如 OSSEC、Wazuh）监控 `.env` 文件变更或访问

### 📌 3. 日志与监控增强

- ✅ **在 Splunk 中新增告警**：  
  `count > 5` 且 `properties_requestUri` 包含 `.env` → 立即告警 + 邮件通知  
- ✅ **部署“攻击行为画像”**：  
  对频繁访问 `/admin/`, `/api/`, `/config/` + `.env` 组合路径的请求打标并告警

---

## 📈 升级路径

| 条件 | 升级动作 |
|------|----------|
| ❗ 源 IP 为已知恶意 IP 或攻击者后续发起 SQL 注入/命令执行 | ➤ 立即升级至**安全事件响应组 + CISO 团队**，启动取证与隔离 |
| ❗ 发现 `.env` 文件实际可访问或返回 200 | ➤ **立即下线该应用节点** + 通知业务负责人 + 启动安全审计 |
| ❗ 攻击源为内网 IP 或员工设备 | ➤ 通知内网安全团队 + 下发终端安全策略 + 禁用相关服务 |
| ❗ 同一应用在多个网关均出现类似告警 | ➤ 升级至**架构安全团队**，评估是否为全局配置缺陷 |

---

## 📝 附：快速操作命令示例（供运维复制执行）

```bash
# 1. 在 Azure CLI 中查看 WAF 日志（需替换 resource group）
az network application-gateway waf-log show --resource-group <RG> --name AGW-DAP-PRD-N3-01

# 2. Splunk 中快速聚合攻击源 IP
index=azure category=ApplicationGatewayFirewallLog properties_hostname="purview.novonordiskchina.com.cn" 
| stats count by properties_clientIp, properties_userAgent

# 3. 临时添加 WAF 自定义规则（示例）
az network application-gateway waf-policy custom-rule create \
  --policy-name MyWAFPolicy \
  --resource-group <RG> \
  --name BlockEnvFiles \
  --priority 100 \
  --action Block \
  --rule-type MatchRule \
  --match-conditions variable-name=RequestUri pattern-match=".env" ignore-case=true
```

---

✅ **处理建议完成确认**  
- [ ] 已确认攻击源与行为  
- [ ] 已加固 WAF + 应用配置  
- [ ] 已通知相关团队并记录事件  
- [ ] 已添加监控与未来告警策略  

> ⚠️ **重要提示**：环境变量文件 `.env` 是现代应用的核心机密载体，一旦泄露将导致数据库、API、密钥全面暴露 —— **请务必彻底移除其 Web 可访问性。**

---  
**建议执行人**：安全运维工程师 / 应用负责人  
**建议完成时间**：**2 小时内完成紧急处置，24 小时内完成全面加固**

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-07-29 14:40:08*