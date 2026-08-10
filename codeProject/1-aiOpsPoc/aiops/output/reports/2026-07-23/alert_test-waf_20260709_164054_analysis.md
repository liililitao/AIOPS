# WAF 告警分析报告

## 1. 告警概要
- **告警名称**: test-waf
- **触发时间**: 2026-07-09T16:40:54.130+08:00
- **事件数量**: 1
- **综合风险等级**: **高**

## 2. 告警数据详情
- **资源 ID**: AGW-NCMA-PRD-01
- **域名**: purview.novonordiskchina.com.cn
- **攻击路径**: /.env~ /api/app/shop/hysOrderResultUrlParse /laravel/core/.env /main/.env /new/.env.staging /www/.env /xampp/.env
- **WAF 动作**: Blocked
- **触发次数**: 25

## 3. CMDB 资产信息【证据溯源】
- **查询方式**: 精确匹配 Resource Name: AGW-NCMA-PRD-01
- **匹配来源**: Azure PaaS (第1130行)
- **Environment**: Production
- **订阅名称**: NovoCare-MobileApp-PRD
- **资源类型**: Application gateway

## 4. 攻击分析
- **攻击类型**: env_scan, api_exploit
- **最高攻击风险**: 中

- **环境文件扫描** (中): /.env~, /laravel/core/.env, /main/.env, /new/.env.staging, /www/.env
- **API漏洞探测** (中): /api/app/shop/hysOrderResultUrlParse

## 5. 综合风险评估
| 维度 | 判定 | 详情 |
|------|------|------|
| 环境风险 | 高 | Production |
| 数量风险 | 低 | count=25 |
| 攻击类型风险 | 中 | env_scan, api_exploit |
| **综合** | **高** | - |

## 6. 溯源链接
- [在 Splunk 中查看](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1783564199_1802.4%20%7C%20head%201%20%7C%20tail%201&earliest=0&latest=now)

---
*本报告由 AIOps Agent 自动生成 · 2026-07-23T15:38:40.439343*
