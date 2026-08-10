# WAF 告警分析报告

---

## 告警概要

- **告警名称**：`test-waf`
- **触发时间（本地）**：2026-07-13T14:44:09.765+08:00
- **触发时间（UTC）**：2026-07-13T06:44:09.765Z
- **风险等级**：**高**
- **告警来源**：Splunk Saved Search，由周期性调度触发
- **原始数据链接**：[查看 Splunk 原始日志](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1783564199_1802.23%20%7C%20head%201%20%7C%20tail%201&earliest=0&latest=now)

---

## 告警数据详情

### 受影响资源

- **资源 ID**：`AGW-DAP-PRD-N3-01`
- **主机名**：`purview.novonordiskchina.com.cn`
- **攻击路径**：
  ```
  /.env.local
  /.env.production.local
  /admin/.env
  /app/.env
  /application/.env
  /conf/.env
  /crm/.env
  /cron/.env
  /development/.env
  /env.backup
  /laravel/core/.env
  /local/.env
  /node_modules/.env
  /prod/.env
  /public/.env
  /website/.env
  ```
- **WAF 动作**：`Blocked`
- **触发次数**：20 次（满足告警阈值：≥20）

---

## CMDB 资产信息

✅ **资产有效性确认**：

【证据溯源】  
通过 CMDB 查询确认资源 `AGW-DAP-PRD-N3-01` 为 Azure Application Gateway，归属生产环境（Production），所属订阅为 `DAP-PRD`，数据源为 “Azure PaaS” 表格第 283 行。

```json
{
  "found": true,
  "match_type": "exact",
  "resource_name": "AGW-DAP-PRD-N3-01",
  "resource_type": "Application gateway",
  "environment": "Production",
  "subscription": "DAP-PRD",
  "server_name": "",
  "source_sheet": "Azure PaaS",
  "source_row": 283
}
```

---

## 攻击分析

### 攻击类型分类

【证据溯源】  
本次攻击属于 `env_scan`（环境文件扫描），共匹配 16 个路径，均为常见 `.env` 文件路径模式，用于探测敏感配置文件泄露。

```json
{
  "type": "env_scan",
  "label": "环境文件扫描",
  "risk": "中",
  "matched": [
    "/.env.local", "/.env.production.local", "/admin/.env", "/app/.env",
    "/application/.env", "/conf/.env", "/crm/.env", "/cron/.env",
    "/development/.env", "/env.backup", "/laravel/core/.env", "/local/.env",
    "/node_modules/.env", "/prod/.env", "/public/.env", "/website/.env"
  ]
}
```

### 攻击特征

- 攻击者使用自动化工具（如 Burp Suite、Nmap、DirBuster 等）对 Web 应用进行目录探测。
- 重点探测目标为包含敏感环境变量的 `.env` 文件，常见于 Laravel、Django、Node.js 等框架项目中。
- 无业务合法访问特征，为典型的“目录遍历 + 敏感文件泄露探测”组合攻击。

### 风险评估

- 虽单次攻击行为风险中等（攻击类型风险“中”），但因作用于 **生产环境** 应用网关，整体风险升级为 **高**。
- 攻击者若成功访问 `.env` 文件，可能获取数据库凭证、API 密钥、OAuth Token 等敏感信息，导致数据泄露或横向渗透。

---

## 综合风险评估

| 维度             | 判定值         | 说明                                                                 |
|------------------|----------------|----------------------------------------------------------------------|
| 环境风险         | 高             | 作用于 Production 生产环境，影响业务连续性与数据安全                   |
| 攻击次数风险     | 低             | 20 次攻击在阈值边缘，未构成高频攻击                                 |
| 攻击类型风险     | 中             | env_scan 属于敏感信息探测行为，潜在危害中等                           |
| **综合风险**     | **高**         | 生产环境 + 敏感文件探测 → 触发高风险判定                              |

> 评估时间：2026-07-29T14:39:07.821235

---

## 相关运维参考

1. **WAF 规则加固建议**：
   - 在 Azure Application Gateway WAF 中启用 **OWASP 3.2 标准规则组**。
   - 针对 `/.env*`、`/config*`、`/backup*` 等敏感路径配置自定义规则阻断。
   - 建议添加 `SQL Injection` 与 `Path Traversal` 规则防护，防止后续绕过。

2. **资产端加固措施**：
   - 确保 Web 服务配置禁止目录列表（Directory Listing）。
   - 对 `.env` 文件设置严格文件权限（如 600），并确保其不位于 Web 根目录下。
   - 建议使用 `web.config`、`.htaccess` 或 Azure 的 `rewrite rules` 对敏感路径进行 403 拦截。

3. **监控告警优化建议**：
   - 当前告警规则基于 `count>=20`，建议对 `env_scan` 类型攻击可降级阈值至 5~10 次即触发告警。
   - 增加攻击来源 IP 地址维度聚合，便于封禁恶意源。

4. **CMDB 同步建议**：
   - 定期验证 Azure Application Gateway 资源与 CMDB 数据一致性（如通过 Azure REST API 自动比对）。
   - 若资源无关联服务器名（`server_name` 为空），应补充其后端池或应用名称以增强可追溯性。

---

> **报告生成时间**：2026-07-29T15:00:00+08:00  
> **报告责任人**：网络安全运维组  
> **审核人**：[待填写]  

--- 

✅ **备注**：本报告所引用 CMDB 数据及攻击分类结果已标注【证据溯源】，确保分析过程可回溯、可审计。

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-07-29 14:39:34*