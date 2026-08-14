# 告警处理建议：test-waf - 生产环境 WAF 高风险阻断事件

---

## 🚨 立即行动

1. **紧急隔离可疑 IP（如可获取）**  
   - 在 Azure Application Gateway WAF 规则集中**临时添加 IP 封禁规则**，匹配触发请求的 `clientIp`（需从原始日志提取）。
   - 若无法立即获取 IP，**启用 IP 频率限流规则**：对 `api-obesity.novocare.com.cn` 的 `/user/api/user/v1/user/login` 和 `/membership/api/membership/v1/tasks` 接口设置 `10 次/分钟` 限流。

2. **禁用或加固 `.git/config` 访问路径**  
   - 在 WAF 自定义规则中，**添加阻断规则**：  
     ```
     Match field: Request Uri
     Operator: Contains
     Value: /.git/config
     Action: Block
     ```
   - **检查 Web 服务器配置**（如 Nginx/Apache），确保 `.git` 目录被拒绝访问（`deny all` 或 403）。

3. **通知 API 团队**  
   - 立即通知负责 `membership` 和 `user` 服务的开发/运维团队，**确认该路径是否存在未授权访问漏洞**，并启动代码审计。

4. **记录事件并启动响应流程**  
   - 创建事件工单（如 Jira/ServiceNow），标记为 **P1（高危生产事件）**，通知安全部与架构组。

---

## 🔍 调查步骤（确认是否为真实攻击）

1. **回溯原始日志确认攻击来源**  
   - 查看 Azure Application Gateway 的原始防火墙日志，提取 `clientIp`、`userAgent`、`X-Forwarded-For`。
   - 检查是否来自已知威胁 IP 地址（如 AbuseIPDB、AlienVault OTX）。

2. **分析请求参数特征**  
   - 针对 `/external/open-api/external/v1/wechatMini/message/...` 的请求，验证签名参数是否合法：
     - 检查 `signature`、`timestamp`、`nonce` 是否被重放（时间戳是否合理、签名是否伪造）。
     - 验证 `openid` 是否为真实用户（通过微信接口校验）。
   - **若签名无效或 openid 非法 → 确认为 API 滥用/伪造攻击。**

3. **比对正常用户行为**  
   - 对比同一时间段内正常用户对该 API 的访问频率、参数组合、UA 字符串。
   - 若攻击 IP 使用 `curl`、`python-requests` 等自动化工具 UA，或请求频率呈“定时扫描”特征 → 高概率为自动化攻击。

4. **查看后端日志确认是否穿透**  
   - 检查 `api-obesity.novocare.com.cn` 后端服务（如 Kubernetes Pod 日志、API Gateway 日志）：
     - `Blocked` 请求是否被后端接收？→ 若未接收 → WAF 阻断有效。
     - 若部分请求穿透 → 检查 WAF 规则是否未覆盖或存在绕过。

---

## ⚠️ 处置建议（按风险等级差异化响应）

| 风险等级 | 建议处置 |
|----------|-----------|
| **高风险（生产环境 + API Exploit）** | ⛔ 紧急处置：<br>1. 暂时下线 `/user/api/user/v1/user/login` 和 `/membership/api/membership/v1/tasks` 接口，通过 WAF 返回 503；<br>2. 启动紧急代码审查，确认是否暴露敏感接口或存在未修复漏洞；<br>3. 所有相关团队加入事件响应会议。 |
| **中风险（API Exploit）** | 🔐 强化接口安全：<br>1. 对登录和任务接口启用**二次验证**（如短信/图形验证码）；<br>2. 对接口添加**访问令牌签名验证**；<br>3. 记录所有失败登录尝试并告警。 |
| **低风险（随机扫描）** | ✅ 快速确认即可：<br>1. 确认 `.git` 目录已屏蔽（若未屏蔽则立即加固）；<br>2. 确认微信 Mini 程序接口的签名验证机制健壮；<br>3. 记录并归档，无需紧急处理。 |

---

## 🛡️ 后续加固措施

### WAF 规则优化

1. **添加路径阻断规则**  
   ```plaintext
   Rule: Block .git directory access
   Condition: Uri contains "/.git"
   Action: Block

   Rule: Block API login flood
   Condition: Uri equals "/user/api/user/v1/user/login" AND Request Count > 5 in 1 minute
   Action: Block
   ```

2. **增强 API 防御规则**  
   - 对 `/external/open-api/external/v1/wechatMini/message/...` 路径：
     - 验证 `signature` 是否符合微信签名算法。
     - 验证 `timestamp` 是否在合理窗口（±5分钟）。
     - 阻断包含 `encrypt_type=aes` 但无对应加密字段的请求（可能伪造）。

3. **启用 CRS 3.3+ 规则集 + 自定义规则**  
   - 启用 OWASP CRS 规则集，重点启用：
     - `942200` (SQL Injection)
     - `933110` (HTTP Parameter Pollution)
     - `920350` (Remote File Inclusion)

### 系统安全加固

1. **后端服务加固**  
   - 所有 API 接口启用 **JWT Token + Scope 权限控制**。
   - 登录接口强制启用 **速率限制（Rate Limiting）** 和 **账户锁定策略**。
   - 启用**API 网关日志审计**，记录所有请求头、参数、响应码。

2. **代码层防御**  
   - 对 `/membership/api/membership/v1/tasks` 接口增加 **身份权限校验**（确保非登录用户无法访问）。
   - 对所有用户输入参数进行 **白名单校验 + 参数类型验证**。

3. **CI/CD 流水线安全检查**  
   - 在构建阶段加入 **SAST 扫描**（如 SonarQube），确保无硬编码密钥、无未授权接口。

---

## 📈 升级路径（何时需升级处理）

| 条件 | 升级动作 |
|------|----------|
| 同一 IP 在 1 小时内触发 > 50 次阻断 | 升级为 P0 事件，立即启动安全响应小组，提交至安全架构师。 |
| 发现有效凭证泄露或数据被提取行为 | 立即通知法务与合规部门，启动数据泄露响应预案。 |
| WAF 规则被绕过（请求穿透后端） | 升级至安全架构团队，重新评估 WAF 配置与规则有效性。 |
| 攻击源为已知 APT 组织 IP | 升级至 SOC 与威胁情报团队，启动威胁狩猎与横向移动排查。 |

---

## 📌 附注：生产 vs 测试环境策略差异

| 项目 | 生产环境 | 测试环境 |
|------|----------|----------|
| 响应级别 | P1 紧急事件 | P3 一般事件 |
| 处置方式 | 立即阻断 + 下线 + 审计 | 记录 + 模拟攻击复现 |
| WAF 规则 | 严格阻断 + 限流 | 仅记录 + 预警 |
| 接口访问 | 强制身份+权限验证 | 可临时开放调试 |
| 通知流程 | 安全部 + 架构组 + 产品经理 | 仅开发团队 |

---

✅ **处理建议总结**：本次事件为**高风险生产环境 API 漏洞探测 + 目录扫描行为**，建议立即加固 WAF、审查 API 接口安全，并启动安全响应流程。无需恐慌，但必须严肃对待，避免成为攻击突破口。

---  
📅 **建议完成时间**：2 小时内完成应急响应，24 小时内完成加固评审。

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-08-11 15:17:32*