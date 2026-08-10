# WAF 告警分析报告

---

## 告警概要

- **告警名称**：`test-waf`  
- **触发时间**：2026-07-10T16:20:10.969+08:00（本地时间） / 2026-07-10T08:20:10.969Z（UTC）  
- **风险等级**：**高**  
- **触发原因**：保存的搜索 `test-waf` 持续命中 2 次，触发告警（`always(2)`）  
- **原始 Splunk 查询链接**：[点击查看原始日志](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1783564199_1802.9%20%7C%20head%202%20%7C%20tail%201&earliest=0&latest=now)

---

## 告警数据详情

- **受影响资源 ID**：`AGW-DAP-PRD-N3-01`  
- **主机名**：`purview.novonordiskchina.com.cn`  
- **攻击路径**（被拦截请求 URI）：  
  ```
  /.env.bak /.env.example /.env.old /.env_sample /api/shared/.env /api/shared/config/.env 
  /app/config/parameters.yml /application/.env /conf/.env /core/.env /dev/.env /development/.env 
  /env.backup /laravel/core/.env /mailer/.env /new/.env.local /new/.env.staging /node/.env_example 
  /portal/.env /public/.env /site/.env /storage/logs/laravel.log
  ```
- **WAF 动作**：`Blocked`（共拦截 25 次请求）
- **告警条件**：符合“非测试环境域名 + 被拦截次数 ≥20”条件

---

## CMDB 资产信息

### 【证据溯源】

通过 CMDB 系统查询资源 ID `AGW-DAP-PRD-N3-01`，确认该资源为：

- **资源名称**：`AGW-DAP-PRD-N3-01`  
- **资源类型**：**Application Gateway**（应用网关）  
- **所属环境**：**Production（生产环境）**  
- **订阅名称**：`DAP-PRD`  
- **数据源**：Azure PaaS（第 283 行）  
- **匹配类型**：精确匹配（`exact`）  
- **查询状态**：成功（`found: true`）  

> 该资源为生产环境关键应用网关，承载真实业务流量，暴露攻击面后风险极高。

---

## 攻击分析

### 攻击类型分类

#### 【证据溯源】

根据攻击请求特征，系统识别攻击类型为：

1. **`env_scan`（环境文件扫描）** — 风险等级：**中**
   - 匹配路径：
     ```
     /.env.bak, /.env.example, /.env.old, /.env_sample, /api/shared/.env, /api/shared/config/.env,
     /application/.env, /conf/.env, /core/.env, /dev/.env, /development/.env, /env.backup,
     /laravel/core/.env, /mailer/.env, /new/.env.local, /new/.env.staging, /node/.env_example,
     /portal/.env, /public/.env, /site/.env
     ```
   - **攻击意图**：探测并访问 `.env` 等环境配置文件，此类文件常包含数据库密码、API 密钥、密钥对等敏感信息。攻击者可借此进一步渗透或横向移动。

2. **`config_scan`（配置文件扫描）** — 风险等级：**中**
   - 匹配路径：
     ```
     /app/config/parameters.yml, /storage/logs/laravel.log
     ```
   - **攻击意图**：尝试获取框架配置文件或应用日志，用于识别应用架构、调试信息或敏感操作记录，辅助后续攻击。

> **综合攻击风险评估**：攻击者已进入“探测敏感资产”阶段，虽尚未成功获取数据，但已定位关键目标，存在高威胁升级风险。

---

## 综合风险评估

| 风险维度        | 评估结果         | 说明 |
|----------------|------------------|------|
| **环境风险**     | 高               | 资源位于生产环境（Production），服务中断或数据泄露影响重大。 |
| **请求频次风险** | 低               | 25 次拦截，虽非海量攻击，但集中扫描敏感路径，攻击意图明确。 |
| **攻击类型风险** | 中               | 扫描环境文件与配置文件，属典型信息探查前置攻击。 |
| **总体风险**     | **高**           | 生产环境 + 信息探查攻击 → 高风险，需立即响应防止演变为数据泄露或未授权访问。 |

---

## 相关运维参考

1. **立即响应建议**
   - 检查 `purview.novonordiskchina.com.cn` 后端服务是否存在 `.env` 或配置文件被意外暴露。
   - 审查应用部署规范，确保敏感文件不在 Web 根目录或可访问路径下。
   - 在 WAF 中为该域名添加更严格的访问控制规则，封锁对 `/\.env.*`、`/storage/logs/` 等路径的访问。

2. **日志与溯源建议**
   - 结合 Azure Application Gateway 日志，分析源 IP 地址，进行 IP 封禁或速率限制。
   - 检查访问日志中是否有成功访问记录（非被拦截），确认是否已发生数据泄露。

3. **配置加固建议**
   - 后端 Web 服务器（如 Apache/Nginx）应配置 `Location` 指令拒绝访问 `.env`、`.yml`、`.log` 等敏感文件。
   - 使用 WAF 自定义规则或“路径阻断”策略，主动拦截常见敏感文件路径访问。

4. **后续监控建议**
   - 在 Splunk 中设置告警，监控对任何 `/\.env.*`、`/config/`、`/storage/logs/` 等路径的访问行为。
   - 对生产环境所有应用网关添加统一的 WAF 策略，防范同类扫描攻击。

---

> 报告生成时间：2026-07-29T14:37:38.146231  
> 报告人：网络安全运维团队  
> 注：本报告所引用 CMDB 数据与攻击类型分析均已标记【证据溯源】，确保可审计与可回溯。

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-07-29 14:38:37*