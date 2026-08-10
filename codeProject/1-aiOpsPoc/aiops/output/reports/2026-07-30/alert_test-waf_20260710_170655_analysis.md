# WAF 告警分析报告

---

## 告警概要

- **告警名称**：`test-waf`  
- **触发时间**：2026-07-10T17:06:55.270+08:00（北京时间）  
- **风险等级**：`高`  
- **触发原因**：Saved Search `test-waf` 持续匹配到满足条件的 WAF 阻断日志（`count>=20`）  
- **原始数据链接**：[Splunk 原始日志查看](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1783564199_1802.22%20%7C%20head%201%20%7C%20tail%201&earliest=0&latest=now)

---

## 告警数据详情

| 字段 | 值 |
|------|----|
| 受影响资源 ID | `AGW-NOVOCAREOBESITY-PRD-01` |
| 主机名 | `api-obesity.novocare.com.cn` |
| WAF 动作 | `Blocked` |
| 请求 URI（部分） | `/external/open-api/external/v1/wechatMini/message/...`, `/membership/api/membership/v1/tasks`, `/user/api/user/v1/user/login`, `/wp-config.php` |
| 阻断次数 | **25** 次 |
| 涉及攻击类型 | `random_scan`, `api_exploit`, `dynamic_page` |

> ✅ **说明**：攻击者在短时间内针对多个接口发起请求，WAF 成功阻断全部 25 次请求，未造成实际入侵。

---

## CMDB 资产信息

【证据溯源】  
根据 CMDB 查询结果，主机 `api-obesity.novocare.com.cn` 关联资源如下：

- **资源名称**：诺和关怀肥胖症-NNRC Novocare Obesity  
- **环境**：`Non-Production`（测试/预发布环境）  
- **订阅（Subscription）**：`NovocareObesity-DEV`, `NovocareObesity-TST`  
- **匹配类型**：模糊匹配（fuzzy）  
- **数据来源**：`Computer System List` 表格，第 19 行  
- **备注**：资产归属明确，非生产环境，但存在暴露风险。

> 📌 **建议**：非生产环境仍需严格访问控制与安全监控，防止被用作跳板或信息收集目标。

---

## 攻击分析

### 攻击类型分类

【证据溯源】  
根据攻击特征匹配与风险评估，攻击类型分类结果如下：

| 类型 | 标签 | 风险等级 | 匹配路径示例 |
|------|------|----------|--------------|
| `random_scan` | 随机扫描 | 低 | `/external/open-api/external/v1/wechatMini/message/wx98f3f60b481fdab7?...`（多个不同 openid 与签名） |
| `api_exploit` | API 漏洞探测 | 中 | `/membership/api/membership/v1/tasks`, `/user/api/user/v1/user/login` |
| `dynamic_page` | 动态页面攻击 | 高 | `/wp-config.php`（WordPress 配置文件，常用于探测 CMS 漏洞） |

---

### 攻击特征

1. **随机扫描行为**：
   - 针对微信小程序消息接口发起大量带随机参数的请求，疑似用于探测接口敏感性或绕过签名验证策略。
   - 请求参数包含 `openid`, `signature`, `timestamp`, `nonce`, `msg_signature` —— 符合微信官方消息校验机制，但请求者无授权来源。

2. **API 漏洞探测**：
   - 探测 `/membership/api/membership/v1/tasks` 和 `/user/api/user/v1/user/login` 接口，可能意图：
     - 暴力破解登录接口；
     - 获取未授权的会员任务数据；
     - 探测是否存在未鉴权或越权访问漏洞。

3. **动态页面攻击（高危）**：
   - 请求 `/wp-config.php` —— 该文件为 WordPress 核心配置文件，包含数据库凭据等敏感信息。
   - 若服务器未正确配置权限或未阻止访问，可能导致**数据库泄露**或**Webshell 植入**。

---

## 综合风险评估

| 评估维度 | 风险等级 | 说明 |
|----------|----------|------|
| **环境风险** | 低 | 目标为非生产环境（Non-Production），无直接影响生产数据与服务 |
| **请求频次风险** | 低 | 25 次请求在短时间内被阻断，未造成服务负载冲击或大量日志淹没 |
| **攻击类型风险** | 高 | 包含高危动态页面攻击（`/wp-config.php`）和 API 探测行为，意图明确，具备渗透能力 |
| **综合风险等级** | **高** | 虽然环境非生产，但攻击者具备明确探测意图与技术手段，若未及时加固，存在横向移动或数据泄露风险 |

---

## 相关运维参考

### ✅ 立即处置建议

1. **检查 Web 服务路径权限**：
   - 确保 `/wp-config.php` 等敏感文件在 Web 服务中**禁止外部访问**。
   - 修改 `.htaccess` 或 Nginx/Apache 配置，禁止对 `wp-*`、`*.php`、配置文件的直接访问。

2. **加固 API 接口安全**：
   - 对 `/membership/api/membership/v1/tasks`、`/user/api/user/v1/user/login` 等敏感接口：
     - 启用 IP 白名单或限流策略；
     - 强制要求 JWT/OAuth2 鉴权；
     - 记录并告警异常登录尝试。

3. **监控微信消息接口异常访问**：
   - 建议在 WAF 或 API 网关层增加“签名验证失败”告警规则；
   - 检查微信公众号/小程序后台，确认是否存在未授权的 `appid` 或 `openid` 调用。

### 🛡️ 长期加固建议

- **环境隔离**：非生产环境也应配置 WAF、访问控制、审计日志，禁止无授权公网访问。
- **自动化扫描防护**：部署主动式爬虫阻断（如 Bot Manager），识别并封禁扫描型请求。
- **资产定期审计**：通过 CMDB 与 WAF 日志联动，自动识别“非预期访问路径”并标记高风险。

---

## 附录：原始告警搜索语句（Splunk）

```spl
index=azure category=ApplicationGatewayFirewallLog properties_action=Blocked
properties_hostname!="novocareapp.novocare.com.cn" AND
properties_hostname!="test-novocareapp.novocare.com.cn"
| rex field=resourceId "/(?<id>[^/]+)$"
| stats values(properties_action) as properties_action values(properties_requestUri) as properties_requestUri count by properties_hostname,id
| table id,properties_hostname,properties_requestUri,properties_action,count
| search count>=20
```

---

> 📬 报告生成时间：2026-07-30T09:52:00.001550  
> 🧑‍💻 分析人：网络安全运维团队  
> 🛡️ 后续跟踪：建议 72 小时内完成安全加固并重新评估风险。

---
*🤖 AI 生成 (qwen_qwen3_vl_235b_a22b) · 2026-07-30 09:52:24*