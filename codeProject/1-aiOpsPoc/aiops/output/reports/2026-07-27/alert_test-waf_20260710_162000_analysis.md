# WAF 告警分析报告

## 1. 告警概要
- **告警名称**: test-waf
- **触发时间**: 2026-07-10T16:20:00.988+08:00
- **事件数量**: 2
- **综合风险等级**: **高**

## 2. 告警数据详情
- **资源 ID**: AGW-DAP-PRD-N3-01
- **域名**: purview.novonordiskchina.com.cn
- **攻击路径**: /.aws/config /.env.example /.env.prod /.env_sample /api/shared/config/.env /awstats/.env /backend/.env /crm/.env /cron/.env /docker/.env /laravel/core/.env /new/.env.local /new/.env.staging /node_modules/.env /site/.env /wp-config.php.bak /xampp/.env
- **WAF 动作**: Blocked
- **触发次数**: 23

## 3. CMDB 资产信息【证据溯源】
- **查询方式**: 精确匹配 Resource Name: AGW-DAP-PRD-N3-01
- **匹配来源**: Azure PaaS (第283行)
- **Environment**: Production
- **订阅名称**: DAP-PRD
- **资源类型**: Application gateway

## 4. 攻击分析
- **攻击类型**: random_scan, env_scan, dynamic_page
- **最高攻击风险**: 高

- **随机扫描** (低): /.aws/config
- **环境文件扫描** (中): /.env.example, /.env.prod, /.env_sample, /api/shared/config/.env, /awstats/.env
- **动态页面攻击** (高): /wp-config.php.bak

## 5. 综合风险评估
| 维度 | 判定 | 详情 |
|------|------|------|
| 环境风险 | 高 | Production |
| 数量风险 | 低 | count=23 |
| 攻击类型风险 | 高 | random_scan, env_scan, dynamic_page |
| **综合** | **高** | - |

## 6. 溯源链接
- [在 Splunk 中查看](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1783564199_1802.8%20%7C%20head%202%20%7C%20tail%201&earliest=0&latest=now)

---
*📋 模板自动填充 (LLM 不可用) · 2026-07-27 11:10:15*
