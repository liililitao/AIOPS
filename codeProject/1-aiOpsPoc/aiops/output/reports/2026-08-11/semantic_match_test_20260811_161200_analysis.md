# WAF 告警分析报告

---

## 1. 告警概要

- **告警名称**：`test-waf`
- **触发时间（本地）**：2026-07-30T16:44:02.098+08:00
- **触发时间（UTC）**：2026-07-30T08:44:02.098Z
- **风险等级**：**高**
- **事件数量**：1
- **触发原因**：Saved Search `test-waf` 持续触发（always(1)）
- **原始 Splunk 查询链接**：[点击查看原始日志](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1785399180_15.0%20%7C%20head%201%20%7C%20tail%201&earliest=0&latest=now)

---

## 2. 告警数据详情

- **受影响资源 ID**：`AGW-DAP-PRD-N3-01`
- **目标主机名**：`purview.novonordiskchina.com.cn`
- **攻击路径**：
  ```
  /.aws/credentials
  /.env.example
  /.env.production.local
  /.travis.yml
  /api/config/config.yml
  /backend/.env
  /cron/.env
  /docker/.env
  /local/.env
  /mail/.env
  /mailer/.env
  /main/.env
  /new/.env
  /new/.env.staging
  /node/.env_example
  /node_modules/.env
  /prod/.env
  /site/.env
  /website/.env
  ```
- **WAF 动作**：`Blocked`
- **累计触发次数**：21 次

---

## 3. CMDB 资产信息

【证据溯源】  
根据 CMDB 查询结果，资源 `AGW-DAP-PRD-N3-01` 为 Azure Application Gateway，部署于 **生产环境（Production）**，所属订阅为 `88E39F7D-09DC-4B59-9491-B1CBF00279FB`，来源为“Azure PaaS”清单第2行。

> **CMDB 查询方式**：按 `resource_name = "AGW-DAP-PRD-N3-01"` 精确匹配，返回类型为 `APPLICATIONGATEWAYS`，环境标识为 `Production`，符合高风险评估前提。

---

## 4. 攻击分析

### 攻击类型分类

【证据溯源】  
根据攻击特征匹配分析，本次攻击涉及以下三类扫描行为：

- **随机扫描（random_scan）** — 风险：**低**
  - 匹配路径：
    - `/.aws/credentials`
    - `/.travis.yml`
  - 特征：攻击者尝试探测是否存在云凭证或CI配置文件，属常规信息收集行为。

- **环境文件扫描（env_scan）** — 风险：**中**
  - 匹配路径（共 16 项）：
    ```
    /.env.example
    /.env.production.local
    /backend/.env
    /cron/.env
    /docker/.env
    /local/.env
    /mail/.env
    /mailer/.env
    /main/.env
    /new/.env
    /new/.env.staging
    /node/.env_example
    /node_modules/.env
    /prod/.env
    /site/.env
    /website/.env
    ```
  - 特征：广泛探测各类 `.env` 文件，意图窃取数据库连接、API密钥、服务账户凭证等敏感配置，此类文件若泄露可能导致系统被横向渗透。

- **配置文件扫描（config_scan）** — 风险：**中**
  - 匹配路径：
    - `/api/config/config.yml`
  - 特征：尝试访问 API 配置文件，可能用于获取系统结构、路由规则、依赖服务地址等信息。

> **攻击趋势判断**：攻击者采用“广撒网”式扫描，覆盖主流开发与部署环境文件路径，表明其目标为自动化漏洞挖掘，而非特定系统攻击。

---

## 5. 综合风险评估

根据三维度判定模型：

| 维度             | 评估值             | 说明                                     |
|------------------|--------------------|------------------------------------------|
| **环境风险**     | ⚠️ 高              | 资产部署于 **生产环境**，影响业务连续性 |
| **事件计数风险** | ✅ 低              | 仅 21 次触发，非高频暴力攻击           |
| **攻击类型风险** | ⚠️ 中              | 含多个中风险扫描类型（env_scan, config_scan） |

> **综合风险等级**：**高**  
> **评估时间**：2026-08-11T14:39:03.205319

---

## 6. 相关运维参考

### 建议行动项：

1. **确认目标系统敏感性**  
   - 核查 `purview.novonordiskchina.com.cn` 是否为对外暴露系统，是否含敏感数据或业务接口。
   - 如为内部系统，建议调整 WAF 规则或防火墙策略，限制外部访问源。

2. **加强环境文件保护**  
   - 确保所有 `.env`、`.yml`、`.json` 配置文件**不在 Web 根目录或可访问路径中存放**。
   - 配置 Web 服务器禁止直接访问 `/.env*`、`/config/*` 等敏感路径。
   - 建议使用 Docker/K8s Secret 或 Azure Key Vault 管理敏感配置，而非明文文件。

3. **WAF 规则优化建议**  
   - 针对 `/api/config/config.yml` 等路径，可设置**更严格的访问控制规则**，如仅允许特定IP或API网关调用。
   - 对 `/.aws/credentials`、`/.travis.yml` 等路径，建议添加**自定义规则组**，直接封禁访问并告警。

4. **日志与监控增强**  
   - 建议在 Splunk 中创建**攻击模式聚合看板**，对 `env_scan` + `config_scan` 同时命中事件进行高优告警。
   - 针对 `AGW-DAP-PRD-N3-01` 启用更详细的 WAF 日志记录，便于溯源攻击源 IP。

5. **渗透测试建议**  
   - 对该域名及关联子系统执行**配置文件泄露渗透测试**，模拟攻击者行为验证防御有效性。

---

> **注**：本报告依据原始告警数据、CMDB资产信息及攻击分类算法生成，所有分析结果均标注【证据溯源】，确保可审计、可追溯。建议运维团队在72小时内完成初步响应与策略调整。

---  
✅ 报告生成时间：2026-08-11T14:45:00+08:00  
🧑‍💻 报告人：网络安全运维中心（SOC）

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-08-11 14:39:50*