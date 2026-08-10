# 告警处理建议：`test-waf` —— 高风险环境/配置文件扫描攻击

---

## 🚨 立即行动（生产环境必须立即执行）

> **告警来源**：WAF 阻断了来自 `purview.novonordiskchina.com.cn` 的 25 次扫描请求，涉及 `.env`、`.yml`、`laravel.log` 等敏感文件路径，攻击类型为 **环境文件扫描 + 配置文件扫描**，风险等级 **高**，目标为 **生产环境**（`AGW-DAP-PRD-N3-01`）。

### ✅ 必须立即执行的操作清单：

1. **确认攻击源 IP 地址**  
   - 通过 Splunk 原始日志（[点击访问](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1783564199_1802.9%20%7C%20head%202%20%7C%20tail%201&earliest=0&latest=now)）提取攻击源 IP 地址（建议 `src_ip` 或 `client_ip`），并记录。
   - 使用 `| table client_ip, count` 补充统计攻击源分布。

2. **在 WAF 中临时封禁攻击源 IP**  
   - 登录 Azure Application Gateway WAF 管理台，进入“防火墙策略” → “自定义规则” → 创建新规则：
     - **匹配条件**：`Remote Address` = 攻击源 IP
     - **操作**：`Block`
     - **优先级**：最高（如 1）
   - **生效时间**：立即生效，并设置 72 小时临时封禁。

3. **检查后端应用服务器是否暴露敏感文件**  
   - 登录 `purview.novonordiskchina.com.cn` 对应的后端应用服务（如 Web 服务器或容器部署），执行：
     ```bash
     # 检查是否存在 .env、parameters.yml、laravel.log 等文件
     find /var/www/html -type f -name ".env*" -o -name "parameters.yml" -o -name "laravel.log" 2>/dev/null
     ```
   - 若存在且可被公网访问，**立即移除或限制访问权限**（如：HTTP 403 或移出 `wwwroot`）。

4. **通知应用负责人**  
   - 发送邮件/IM 消息给 `purview.novonordiskchina.com.cn` 应用负责人，附告警详情 + 攻击路径清单 + 需求：
     > “请立即检查后端是否存在敏感文件暴露，并确认应用是否允许访问 `.env`、`parameters.yml`、`laravel.log` 等路径。”

5. **记录事件并创建工单**  
   - 在 ITSM 系统创建安全事件工单（如 Jira/ServiceNow），标题：  
     `[高危] 2026-07-10 生产环境 WAF 拦截 25 次配置文件扫描攻击 - purview.novonordiskchina.com.cn`

---

## 🔍 调查步骤（用于判断为真实攻击或误报）

> 本告警 **高度疑似真实攻击**，但需进一步确认：

1. **回溯攻击源 IP 行为历史**  
   ```spl
   index=azure category=ApplicationGatewayFirewallLog client_ip=<攻击源IP>
   | bucket _time span=5m
   | stats count by _time, properties_requestUri, properties_action
   | table _time, properties_requestUri, properties_action, count
   ```

2. **检查是否为自动化工具扫描**  
   - 若攻击路径高度标准化（如 `/config/.env`、`/public/.env`），且 IP 来自非业务区域（如 AWS Lambda、Cloudflare 工具 IP、国外 IP），则可判定为**自动化扫描**。
   - 使用 [IPinfo.io](https://ipinfo.io/) 或 Azure Log Analytics 的 `geoip` 字段验证来源地理风险。

3. **检查是否为内部测试或 CI/CD 流水线误触发**  
   - 询问 DevOps 团队：是否有在该时间点对 `purview.novonordiskchina.com.cn` 执行自动化测试或安全扫描？
   - 若为内部扫描，需在 WAF 中设置白名单（仅限特定 CIDR 或 User-Agent）。

---

## 🛠 处置建议（根据风险差异）

### ▶ 高风险（当前情况）

- **必须封禁攻击源 + 检查后端文件暴露 + 通知应用负责人**
- 若发现后端确实存在敏感文件被访问，**立即执行数据泄露应急流程（如通知 DPO、审计日志、重置密钥）**
- 增加 WAF 规则：封锁对 `/\.env`、`/parameters\.yml`、`/laravel\.log` 的访问，无论是否被扫描。

### ▶ 中风险（类似攻击但发生于测试环境）

- 允许保留攻击日志用于分析，但需通知测试团队审查扫描脚本或测试用例。
- 若为持续性扫描，建议在 WAF 中设置限速或阻断规则，并通知安全团队评估是否需封禁。

### ▶ 低风险（如偶发、非敏感路径、非生产环境）

- 无需封禁，可记录并归档，用于后续攻击趋势分析。

---

## ⚙ 后续加固建议

### 1. WAF 规则优化

> 当前 WAF 已拦截，但需**主动防御**类似扫描行为：

```plaintext
# 新增自定义规则（Azure WAF）
规则名称：Block-Env-Config-Access
匹配条件：
  - 字段：Request URI
  - 操作：包含以下字符串
    /.env
    /parameters.yml
    /laravel.log
    /config/
    /storage/logs/
操作：Block
优先级：10
```

> 也可考虑启用 **OWASP CRS 3.0 的“敏感文件访问”规则组**

### 2. 系统安全加固

- **禁止静态文件暴露敏感配置**：
  - Nginx/Apache 配置禁止 `.env*`、`.yml`、`.log` 文件访问：
    ```nginx
    location ~* \.(env|yml|log)$ {
        deny all;
        return 403;
    }
    ```
  - Laravel 应用：确保 `.env` 文件不存放在 `public/` 目录，日志文件权限为 `640`，仅 Web 用户可读。

- **启用目录列表禁止**：
  ```nginx
  autoindex off;
  ```

- **日志监控升级**：
  - 为 `/storage/logs/laravel.log` 添加文件变更监控（如使用 auditd 或 Azure Monitor）。

### 3. 安全开发规范

- 要求开发团队：**禁止在代码仓库或发布包中包含 `.env` 文件**。
- 使用 Azure Key Vault 或 AWS Secrets Manager 管理敏感配置。
- CI/CD 流水线中加入“敏感文件扫描”步骤（如 `trufflehog` 或 `gitleaks`）。

---

## 📈 升级路径（什么情况下需升级处理）

> 满足以下任意条件，请立即升级至安全团队负责人或 SOC 二级响应：

1. **攻击源 IP 为高危地区或 Known Bad Actor**（如来自已知攻击组织 IP 段）。
2. **同一 IP 在 24 小时内触发 ≥3 次同类告警**（可能为持续性攻击）。
3. **后端确认存在敏感文件被成功访问或泄露**（需启动数据泄露应急响应流程）。
4. **攻击路径包含真实业务敏感接口（如 `/api/v1/users` + `.env` 扫描）**。
5. **攻击源使用伪造 User-Agent 或绕过 WAF 行为**（如 HTTP 参数编码混淆）。

---

## 📌 附录：攻击路径清单（供参考）

```plaintext
/.env.bak
/.env.example
/.env.old
/.env_sample
/api/shared/.env
/api/shared/config/.env
/app/config/parameters.yml
/application/.env
/conf/.env
/core/.env
/dev/.env
/development/.env
/env.backup
/laravel/core/.env
/mailer/.env
/new/.env.local
/new/.env.staging
/node/.env_example
/portal/.env
/public/.env
/site/.env
/storage/logs/laravel.log
```

---

> ✅ **处理完成标志**：  
> - 攻击源 IP 已被 WAF 封禁  
> - 后端敏感文件暴露风险已消除  
> - 所有加固规则已部署并验证  
> - 相关责任人已确认并

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-07-29 14:39:07*