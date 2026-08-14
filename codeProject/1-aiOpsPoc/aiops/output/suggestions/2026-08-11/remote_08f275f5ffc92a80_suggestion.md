# 🛡️ WAF 告警处理建议：高风险生产环境扫描攻击

---

## ✅ 立即行动

> **⚠️ 该告警涉及生产环境（`Production`），攻击目标为敏感配置文件（`.env`, `.yml`, `.credentials`），存在泄露风险。需在 **30分钟内** 启动应急响应。**

1. **确认攻击源 IP（从 Splunk 日志中提取）**
   - 访问 [Splunk 查询链接](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1785399180_15.0%20%7C%20head%201%20%7C%20tail%201&earliest=0&latest=now)
   - 执行原始 SPL 查询，添加 `| table properties_clientIp, properties_hostname, properties_requestUri, count`，定位源 IP。
   - 立即在 Azure Application Gateway WAF 中添加 **IP 封禁规则**（优先级最高）。

2. **封禁攻击源 IP（Azure WAF 层面）**
   - 登录 Azure Portal → Application Gateway → `AGW-DAP-PRD-N3-01` → WAF → 自定义规则
   - 新增规则：
     ```
     名称：Block-EnvScan-IP
     优先级：100（最高）
     匹配条件：Client IP Address = <攻击源IP>（多个IP用OR连接）
     动作：Block
     ```
   - 保存并部署。

3. **通知应用负责人**
   - 通知 `purview.novonordiskchina.com.cn` 应用Owner，确认是否有合法访问 `.env` 或 `/api/config/config.yml` 的需求。
   - 确认是否允许 `/api/config/config.yml` 在公网访问 —— **如无业务需求，应立即移除或设为内部访问**。

---

## 🔍 调查步骤

> 在封禁攻击源后，进行深度调查以判断是否为真实攻击或误报。

1. **检查 `.env` 文件是否真实存在**
   - 登录后端应用服务器或容器（如使用 Kubernetes，检查 Pod 中 `/app/.env` 等路径）
   - 确认：
     - 是否存在 `.env` 文件？
     - 文件是否包含敏感配置（数据库密码、API Key、密钥等）？
     - 是否可通过公网路径访问（如 `curl https://purview.novonordiskchina.com.cn/.env`）？

2. **分析访问日志（IIS/Nginx/APache）**
   - 检查应用层日志，确认是否有来自该 IP 的成功请求（如 200/302 响应）
   - 若发现“访问被 WAF 拦截但应用层仍有日志”，说明 WAF 规则未完全生效，需检查 WAF 代理模式。

3. **确认是否为自动化扫描器**
   - 使用 [Censys](https://censys.io/) 或 [Shodan](https://shodan.io/) 检查该 IP 是否为已知扫描器（如 `nmap`, `dirsearch`, `acunetix`）。
   - 若为公开扫描器 IP，可在 Azure 防火墙或 NSG 中增加区域封禁（如封禁美国/俄罗斯高频扫描源 IP 段）。

4. **验证 WAF 规则是否覆盖完整攻击路径**
   - 该攻击路径为 `/api/config/config.yml`、`/backend/.env` 等，确认 WAF 是否启用了 OWASP 3.2+ 规则组中的 `942430`, `942440`（敏感文件访问检测）。

---

## 🚨 处置建议（按风险分级）

### 🔴 高风险处置（当前情况适用）
- **立即封禁攻击源 IP**
- **移除或保护公网可访问的配置文件路径**：
  - 如无业务需求，**禁止 `/api/config/config.yml` 公网访问**
  - 如需访问，改为内部 API 路由或添加 JWT / API Key 验证
  - `.env` 文件**绝不应通过 Web 服务暴露**

- **升级 WAF 策略**：
  - 添加自定义规则：匹配 URI 包含 `.env`、`.yml`、`.credentials` 的请求 → Block
  - 示例规则：
    ```
    字段：Request Uri
    操作符：Contains
    值：.env
    动作：Block
    ```

### 🟡 中风险（历史扫描 / 低频攻击）
- 无需立即封禁 IP，但需：
  - 记录攻击源 IP 到“黑名单库”
  - 设置告警阈值：相同 IP 1 小时内 >10 次扫描 → 自动封禁

### 🟢 低风险（误报或内部测试）
- 如确认为内部扫描工具（如 Jenkins 自动化测试），需：
  - 在 WAF 中添加白名单 IP
  - 或在日志系统中添加“忽略规则”

---

## 🛠 后续加固建议

### 1. WAF 规则优化
- 启用 Azure WAF OWASP 3.2+ 规则组（必须）
- 新增自定义规则（阻断敏感文件访问）：
  ```text
  优先级：100
  条件：Request Uri 包含 ".env" OR ".yml" OR ".credentials"
  动作：Block
  ```
- 建议启用 **“异常检测”功能**：自动封禁高频访问敏感路径的 IP

### 2. 系统安全加固
- **禁止静态文件服务暴露敏感文件**
  - 在应用服务器（如 Nginx）中配置：
    ```nginx
    location ~* \.(env|yml|yaml|credentials|travis\.yml)$ {
        deny all;
        return 403;
    }
    ```
- **配置安全头（CSP, HSTS）**
  - 防止 XSS 与中间人攻击
  - 示例：
    ```nginx
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline';";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    ```

### 3. 环境配置管理
- **禁止 `.env` 文件存在于 Web 项目根目录**
  - 应部署在 `/etc/secrets/` 或通过 Azure Key Vault 注入
- **使用 Docker 多阶段构建**：避免将 `.env` 打包进最终镜像

---

## 📈 升级路径（何时需要升级处理）

| 条件 | 升级动作 |
|------|----------|
| 攻击源 IP 为云服务商（如 AWS EC2、Azure VM）且持续攻击 | 提交云厂商 Abuse Report，申请封禁 |
| 检测到敏感文件存在且可下载（如 `.env` 返回 200） | 立即启动数据泄露响应流程，通知安全部与合规部门 |
| 攻击类型升级为“RCE尝试”或“SQL注入” | 升级为 P0 级事件，启动应急演练 |
| 同一主机 24 小时内出现 >5 次类似告警 | 考虑将该主机加入“隔离区”，暂停公网访问直至排查完毕 |
| 该域名被用于外部服务（如 API Gateway） | 考虑增加 API Gateway 层面鉴权（如 JWT） |

---

## 🧩 生产 vs 测试环境差异处理

| 环境 | 处理策略 |
|------|----------|
| **生产环境**（当前） | ⚡ 立即封禁 + 深度加固，通知业务 owner，2 小时内闭环 |
| **测试环境**（如 `test-novocareapp.novocare.com.cn`） | 🛑 不封禁攻击源，但记录日志；添加白名单 IP；禁止测试环境暴露敏感路径 |

---

✅ **处理闭环建议**
- 完成上述操作后，在工单系统中更新状态为 `Fixed`，并附上：
  - 封禁 IP 列表
  - 修改的 WAF 规则截图
  - 应用配置加固说明
- 48 小时后复查 Splunk 日志，确认无新攻击。

---

> 🔐 **安全不是功能，而是责任。**  
> 本次攻击虽被 WAF 拦截，但暴露了应用层配置风险。请同步推进“配置文件脱敏 & 权限隔离”专项治理。

---  
**撰写人：安全运维工程师**  
**时间：2026-08-11**

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-08-11 14:40:40*