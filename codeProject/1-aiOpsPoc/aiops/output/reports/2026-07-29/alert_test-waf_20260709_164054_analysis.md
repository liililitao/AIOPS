# WAF 告警分析报告

---

## 告警概要

- **告警名称**: `test-waf`
- **触发时间（本地）**: `2026-07-09T16:40:54.130+08:00`
- **触发时间（UTC）**: `2026-07-09T08:40:54.130Z`
- **风险等级**: ⚠️ **高**
- **告警来源**: Splunk 日志分析平台，基于预设搜索策略触发
- **原始告警链接**: [Splunk 原始查询链接](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1783564199_1802.4%20%7C%20head%201%20%7C%20tail%201&earliest=0&latest=now)

---

## 告警数据详情

### 受影响资源

- **资源标识（ID）**: `AGW-NCMA-PRD-01`
- **主机域名**: `purview.novonordiskchina.com.cn`
- **请求路径（被拦截）**:  
  ```
  /.env~ /api/app/shop/hysOrderResultUrlParse /laravel/core/.env /main/.env /new/.env.staging /www/.env /xampp/.env
  ```
- **WAF 动作**: `Blocked`（共 25 次拦截）
- **触发规则**: 针对非白名单域名（排除 `novocareapp.novocare.com.cn` 与 `test-novocareapp.novocare.com.cn`）中，请求次数 ≥20 的被拦截事件进行聚合告警

---

## CMDB 资产信息

### 证据溯源

> 【证据溯源】通过 CMDB 查询确认资源 `AGW-NCMA-PRD-01` 为生产环境的 Azure 应用网关（Application Gateway），属于 `NovoCare-MobileApp-PRD` 订阅，记录在“Azure PaaS”工作表第 1130 行。

- **资源名称**: `AGW-NCMA-PRD-01`
- **资源类型**: Application Gateway
- **环境**: Production
- **订阅**: `NovoCare-MobileApp-PRD`
- **数据来源**: Azure PaaS
- **匹配状态**: 精确匹配（exact）

---

## 攻击分析

### 攻击类型分类

> 【证据溯源】根据攻击特征匹配分析，攻击类型被归类为：
> - `env_scan`（环境文件扫描）
> - `api_exploit`（API漏洞探测）
> 最高风险等级：**中**

#### 1. 环境文件扫描（env_scan）
- **风险等级**: 中
- **攻击特征**:
  - 攻击者尝试访问多种常见的 `.env` 文件路径，如：
    ```
    /.env~
    /laravel/core/.env
    /main/.env
    /new/.env.staging
    /www/.env
    /xampp/.env
    ```
  - 此类文件通常包含数据库凭据、密钥、API令牌等敏感配置信息，目标是窃取环境配置用于后续攻击。
- **潜在影响**: 若未被拦截，可能导致配置泄露、权限提升或横向移动。

#### 2. API 漏洞探测（api_exploit）
- **风险等级**: 中
- **攻击特征**:
  - 访问路径 `/api/app/shop/hysOrderResultUrlParse` 为非标准或未公开 API 路径，可能用于探测业务逻辑缺陷或参数注入。
  - 攻击者可能试图利用 Order Result URL 解析功能，寻找 SSRF、命令注入或敏感数据泄露等漏洞。
- **潜在影响**: 可能导致业务数据泄露、服务异常或被利用构建更复杂的攻击链。

---

## 综合风险评估

基于三维度综合评估：

| 维度          | 评分       | 说明 |
|---------------|------------|------|
| **环境风险**    | ⚠️ 高     | 资产位于生产环境（Production），任何攻击成功均可直接影响业务可用性与数据安全 |
| **攻击次数风险** | ✅ 低     | 触发次数为 25 次，虽未形成高频攻击，但属于集中式试探，不可忽视 |
| **攻击类型风险** | ⚠️ 中     | 包含环境文件扫描与 API 漏洞探测，属于典型的“侦察+利用”组合，具备渗透意图 |
| **整体风险**    | ⚠️ **高** | 生产环境 + 侦察型攻击组合 = 高风险，建议立即响应并加固防护策略 |

> 评估时间: `2026-07-29T14:36:15.990201`

---

## 相关运维参考建议

1. **WAF 规则优化**：
   - 针对 `/api/app/shop/hysOrderResultUrlParse` 路径，建议启用更严格的参数检查或添加 IP 限速策略。
   - 对 `.env` 类敏感文件访问路径，可配置“路径模式拒绝”规则（如正则：`.*\.env(.*)?`），在 WAF 层面直接拦截。

2. **资产暴露面检查**：
   - 检查 `purview.novonordiskchina.com.cn` 是否应对外暴露上述路径，确认是否为误配或历史残留接口。
   - 建议在 Web 服务器或应用层添加访问控制（如 Nginx `deny all;` / 防盗链配置），防止直接访问配置文件。

3. **日志告警增强**：
   - 当前规则仅在 count>=20 时触发，建议对关键路径（如 `.env`、`/api/app/shop/`）设置“单次拦截即告警”，提高响应敏感度。

4. **安全加固建议**：
   - 确保所有生产环境应用无 `.env` 文件存在于 Web 根目录下，应迁移至非 Web 可访问路径。
   - 对 API 接口进行最小权限和输入验证，防止未授权调用或路径注入。

5. **后续监控**：
   - 持续监控该主机（`AGW-NCMA-PRD-01`）是否再次出现类似扫描行为。
   - 增加对源 IP 的封禁机制，若来自固定攻击源，可考虑在 Azure NSG 层面做源头拦截。

---

> **报告生成者**: 网络安全运维团队  
> **生成时间**: 2026-07-29T15:00:00+08:00  
> **参考工具**: Splunk、CMDB、Azure Application Gateway Logs

--- 

✅ **建议行动状态**: **待执行加固 & 监控闭环**

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-07-29 14:36:45*