# WAF 告警分析报告

---

## 告警概要

- **告警名称**：test-waf  
- **触发时间**：2026-07-14T17:23:41.189+08:00  
- **风险等级**：**高**  
- **触发原因**：Saved Search `[test-waf] always(1)`，命中规则为“单个资源在非白名单域名下触发 WAF Block 动作且请求次数 ≥20”  
- **原始 Splunk 查询链接**：[查看原始告警数据](https://your-splunk-instance.com/app/search/search?q=search%20index%3Dazure%20category%3DApplicationGatewayFirewallLog%20properties_action%3DBlocked%20properties_hostname!%3D%22novocareapp.novocare.com.cn%22%20AND%20properties_hostname!%3D%22test-novocareapp.novocare.com.cn%22%20%7C%20rex%20field%3DresourceId%20%22%5C%2F%3F%3Cid%3E%5B%5E%5C%2F%5D%2B%24%22%20%7C%20stats%20values(properties_action)%20as%20properties_action%20values(properties_requestUri)%20as%20properties_requestUri%20count%20by%20properties_hostname%2Cid%20%7C%20table%20id%2Cproperties_hostname%2Cproperties_requestUri%2Cproperties_action%2Ccount%20%7C%20search%20count%3E%3D20&earliest=2026-07-14T17:23:41.189%2B08:00&latest=2026-07-14T17:23:41.189%2B08:00)

---

## 告警数据详情

| 字段名           | 值                                     |
|------------------|----------------------------------------|
| 资源 ID          | `AGW-NOVOCAREOBESITY-PRD-01`           |
| 主机名           | `api-obesity.novocare.com.cn`          |
| 请求路径（部分） | - `/.git/config`<br>- `/external/open-api/...`<br>- `/membership/api/...`<br>- `/user/api/...` |
| WAF 动作         | `Blocked`                              |
| 请求次数         | 20                                     |

> 注：部分请求参数已被脱敏，原始数据保留于本地日志系统。

---

## CMDB 资产信息【证据溯源】

通过 CMDB 查询资源 `AGW-NOVOCAREOBESITY-PRD-01`，确认其资产信息如下：

- **资源名称**：`AGW-NOVOCAREOBESITY-PRD-01`
- **资源类型**：`APPLICATIONGATEWAYS`
- **环境**：`Production`
- **订阅 ID**：`57EB041C-8BF8-487B-A562-F9ACFFC16752`
- **数据来源**：`Azure PaaS`，第 3 行
- **匹配类型**：精确匹配

**结论**：该资源为生产环境的 Azure 应用网关实例，负责 `api-obesity.novocare.com.cn` 的流量防护，属于核心对外接口。  
✅ **【证据溯源】CMDB 查询确认该资源存在且为生产级资产，攻击目标明确，风险等级提升。**

---

## 攻击分析

### 攻击类型分类【证据溯源】

根据请求路径特征分析，本次告警包含两种攻击类型：

#### 1. `random_scan` - 随机扫描（风险：低）

- **匹配路径**（部分示例）：
  - `/.git/config` —— 企图访问版本控制系统敏感文件
  - 多条 `/external/open-api/external/v1/wechatMini/message/...` —— 疑似对微信小程序 API 的暴力探测或签名伪造尝试
- **特征**：重复访问不同参数组合的微信消息推送接口，带有时间戳、nonce、签名、openid 等参数，符合自动化扫描工具行为

#### 2. `api_exploit` - API漏洞探测（风险：中）

- **匹配路径**：
  - `/membership/api/membership/v1/tasks` —— 会员任务接口
  - `/user/api/user/v1/user/login` —— 用户登录接口
- **特征**：尝试访问高权限业务接口，可能是探测未授权访问、参数注入或爆破登录凭证

✅ **【证据溯源】攻击类型分析已基于请求路径进行归类，确认存在 API 探测与系统信息收集行为，风险等级判定合理。**

---

## 综合风险评估

根据三项维度综合评估：

| 维度              | 值              | 说明 |
|-------------------|-----------------|------|
| **环境风险**      | 高              | 生产环境，影响业务连续性 |
| **次数风险**      | 低              | 20次请求，非大规模 DDoS |
| **攻击类型风险**  | 中              | 包含 API 漏洞探测及信息收集，潜在危害中等 |
| **综合风险**      | **高**          | 由于发生在生产环境，且目标明确指向核心 API 和敏感路径，整体风险升级为“高” |

> 评估时间：2026-08-11T15:16:00.235977

---

## 相关运维参考

### 建议行动

1. **紧急响应**：
   - 检查 WAF 规则是否已针对 `/.git/config` 路径设置拦截（建议强化规则或阻断）
   - 对 `api-obesity.novocare.com.cn` 下 `/external/open-api/...` 路径启用更严格的参数校验或限流策略
   - 确认 `/user/api/user/v1/user/login` 是否启用多因素认证或登录失败锁定机制

2. **日志增强**：
   - 对比访问源 IP，查看是否来自已知恶意 IP 池或扫描工具指纹
   - 在 WAF 中增加 `ClientIP` 与 `User-Agent` 聚合分析，辅助溯源

3. **CMDB 与标签同步**：
   - 确保所有生产环境 API 网关资源在 CMDB 中明确标注“生产”、“对外暴露”、“需强化防护”标签，便于后续风险监控

4. **后续监控**：
   - 为该资源设置自定义告警，如：单日请求量 >100 或命中 `/\.git/` 路径即告警
   - 将 `api-obesity.novocare.com.cn` 主机加入 WAF 重点防护资产名单

---

**报告生成时间**：2026-08-11  
**分析师**：网络安全运维组  
**版本**：v1.0

## Splunk 溯源链接
- [在 Splunk 中查看](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1783564199_1802.382%20%7C%20head%201%20%7C%20tail%201&earliest=0&latest=now)

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-08-11 15:16:53*