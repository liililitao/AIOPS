# 告警处理建议：`test-waf` - 高风险 WAF 阻断事件

> **告警时间**：2026-07-10T17:06:55.270+08:00  
> **环境判定**：非生产（Non-Production）  
> **风险等级**：高（因含“动态页面攻击”与“API漏洞探测”）  
> **来源设备**：`AGW-NOVOCAREOBESITY-PRD-01`（实际为测试环境）  
> **攻击目标域名**：`api-obesity.novocare.com.cn`  
> **阻断请求次数**：25次  
> **攻击类型**：随机扫描、API漏洞探测、动态页面攻击（含 `/wp-config.php`）

---

## 🚨 立即行动

**请在 15 分钟内完成下列操作：**

1. **临时封禁攻击源 IP**（若可从日志中提取）：
   - 登录 Azure Application Gateway WAF → “防火墙日志” → 筛选 `properties_hostname=api-obesity.novocare.com.cn` 且 `properties_action=Blocked`
   - 查找与该告警匹配的原始日志，提取 `clientIP` 与 `requestUri`，临时加入 WAF IP 黑名单（IP 限制规则）
   - **命令示例**（Azure CLI）：
     ```bash
     az network application-gateway waf-config set \
       --gateway-name AGW-NOVOCAREOBESITY-PRD-01 \
       --resource-group <your-rg> \
       --enabled true \
       --firewall-mode Prevention \
       --rule-set-type OWASP \
       --rule-set-version 3.2 \
       --disabled-rule-groups "CRS_920"
     ```

2. **确认当前环境归属**：
   - 确认 `api-obesity.novocare.com.cn` 是否属于“测试环境”或“开发环境”（CMDB 显示为 Non-Production）
   - **如为测试环境，立即通知研发/测试负责人暂停所有非必要外网访问**

3. **检查是否有真实攻击意图**：
   - 特别关注 `/wp-config.php` 请求（属于 WordPress 配置文件，常被攻击者用于信息窃取）
   - 检查服务器端是否部署了 WordPress 或类似 CMS
   - 如无，则为攻击者探测路径，需记录并加固

---

## 🔍 调查步骤

以下操作应在 1 小时内完成：

1. **日志深度分析**：
   - 在 Splunk 中打开原始日志链接，筛选 `index=azure category=ApplicationGatewayFirewallLog properties_hostname=api-obesity.novocare.com.cn`
   - 查看 `clientIP`、`userAgent`、`clientIP` 分布情况，确认是否来自同一来源
   - 使用以下 SPL 进一步分析：
     ```spl
     index=azure category=ApplicationGatewayFirewallLog properties_hostname="api-obesity.novocare.com.cn" properties_action=Blocked
     | stats count by clientIP, userAgent, properties_requestUri
     | sort -count
     | head 10
     ```

2. **确认是否误报或内部测试**：
   - 联系“诺和关怀肥胖症”项目组（CMDB 显示归属为 NovocareObesity-TST/DEV）
   - 询问近期是否有自动化测试、API 压力测试、安全扫描等行为
   - 如为内部测试，需在 WAF 中配置白名单规则或测试域名隔离

3. **攻击意图研判**：
   - `/wp-config.php` → 高风险动态页面探测，可能尝试获取数据库凭据
   - `/membership/api/membership/v1/tasks`、`/user/api/user/v1/user/login` → 尝试探测 API 接口暴露/未授权访问
   - **结论**：攻击者在进行**漏洞探测 + 业务接口扫描 + CMS 路径探测**，属于**组合式攻击前奏**

---

## 🛡️ 处置建议

### ✅ 生产环境（如误配或未来迁移）：
- **紧急隔离**：立即启用 WAF 的“预览模式” → 设置规则组 `CRS_900` 级别为“阻止”，防止进一步攻击
- **启用自定义规则**：
  - 阻止 `/wp-config.php`、`/wp-admin/`、`/wp-login.php` 等 WordPress 路径
  - 阻止 `/api/user/login` 未携带有效 Token 的请求（可结合 API 网关做二次校验）
- **日志告警联动**：配置 Azure Monitor + Action Group，将此类事件自动推送至安全团队 Slack/邮件

### 🧪 非生产环境（当前环境）：
- **允许观察，但限制范围**：
  - 保持 WAF“预防模式”，但仅允许来自内部 IP 段（如 10.0.0.0/8, 172.16.0.0/12）访问
  - 禁止公网直接访问 `/external/open-api/`、`/user/api/` 等敏感路径（通过 API 网关控制）
- **添加白名单规则**：
  - 针对内部测试脚本 IP 地址或 User-Agent（如 `Jenkins/`、`PostmanRuntime/`）添加例外规则
- **通知开发团队**：
  - 要求对 `/external/open-api/` 接口进行参数签名验证、频率限制、IP 限流
  - 检查 `/user/api/user/v1/user/login` 是否存在未授权访问漏洞

---

## 🔧 后续加固

### WAF 规则优化建议：

| 规则类型 | 建议操作 |
|----------|----------|
| **自定义规则** | 添加：`MatchVariable: RequestUri` + `Operator: Contains` + `MatchValue: /wp-config.php` → Block |
| **速率限制** | 为 `/external/open-api/`、`/user/api/` 路径配置速率限制（如 100 次/分钟/IP） |
| **地理限制** | 如仅限中国访问，可屏蔽非大陆 IP |
| **User-Agent 检测** | 拦截空 UA 或常见扫描器 UA（如 `sqlmap`, `nmap`, `wget`） |

### 系统安全加固建议：

| 模块 | 建议措施 |
|------|----------|
| **API 接口** | 强制所有 API 请求携带有效 JWT Token，增加签名验证、时间戳、nonce |
| **服务器配置** | 禁止目录浏览，隐藏服务器版本信息（如 NGINX → `server_tokens off`） |
| **日志审计** | 启用 WAF 日志 + Application Insights + 审计日志联动，确保可追溯攻击链 |
| **测试环境隔离** | 为测试环境使用独立域名（如 `test-api-obesity.novocare.com.cn`），不绑定公网 IP，仅允许 VPN 访问 |

---

## 📈 升级路径

以下情况需**立即升级至安全应急响应流程（SOP-SEC-001）**：

- 🔴 **出现以下任意一条，视为严重事件**：
  - 攻击源 IP 来自已知恶意网络（如 C2 服务器、僵尸网络）
  - 有实际数据返回（如 WAF 日志显示 `properties_responseBody` 含敏感信息）
  - 同一资产在 24 小时内出现 3 次以上高风险告警
  - 攻击涉及生产环境（本例为测试环境，但如后续迁移需升级）

- 📲 **升级联系人**：
  - 安全工程师：@SecurityTeam（企业微信/钉钉）
  - 运维值班：@OpsOnCall（24小时手机）
  - 项目负责人：@NovocareObesity-DevLead

---

## 📝 附录：快速确认表

| 项目 | 是否完成 | 备注 |
|------|----------|------|
| [ ] 检查攻击源 IP |  | 从 WAF 日志提取 |
| [ ] 确认环境为测试 | ✅ | CMDB 显示 Non-Production |
| [ ] 检查是否有 WordPress |  | 如无，保留 WAF 规则 |
| [ ] 通知研发团队 |  | 询问是否为内部测试 |
| [ ] 添加 `/wp-config.php` 阻断规则 |  | 优先级最高 |

---

> **安全提示**：即使为测试环境，也应视同生产对待。 attackers 会利用测试环境作为跳板攻击生产系统。务必执行加固措施，避免“测试环境沦陷 → 生产环境被控”的风险链。

--- 
✅ **本建议执行人**：安全运维工程师  
⏱️ **建议完成时限**：2 小时内完成初步处置，24 小时内完成加固闭环  
📌 **下次

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-07-30 09:52:55*