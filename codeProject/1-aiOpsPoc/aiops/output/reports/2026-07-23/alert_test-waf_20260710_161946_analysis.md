# WAF 告警分析报告

## 1. 告警概要
- **告警名称**: test-waf
- **触发时间**: 2026-07-10T16:19:46.462+08:00
- **事件数量**: 2
- **综合风险等级**: **高**

## 2. 告警数据详情
- **资源 ID**: AGW-DAP-PRD-N3-01
- **域名**: purview.novonordiskchina.com.cn
- **攻击路径**: /.env /.env.local /.env.old /.env.prod /.travis.yml /api/.env /api/config/config.yml /api/shared/config/.env /app/.env /app/config/parameters.yml /application/.env /backend/.env /conf/.env /core/.env /dev/.env /docker/.env /docker/app/.env /env.backup /laravel/.env /main/.env /prod/.env /website/.env /wp-config.php.bak
- **WAF 动作**: Blocked
- **触发次数**: 30

## 3. CMDB 资产信息【证据溯源】
- **查询方式**: 精确匹配 Resource Name: AGW-DAP-PRD-N3-01
- **匹配来源**: Azure PaaS (第283行)
- **Environment**: Production
- **订阅名称**: DAP-PRD
- **资源类型**: Application gateway

## 4. 攻击分析
- **攻击类型**: env_scan, random_scan, config_scan, dynamic_page
- **最高攻击风险**: 高

- **环境文件扫描** (中): /.env, /.env.local, /.env.old, /.env.prod, /api/.env
- **随机扫描** (低): /.travis.yml
- **配置文件扫描** (中): /api/config/config.yml, /app/config/parameters.yml
- **动态页面攻击** (高): /wp-config.php.bak

## 5. 综合风险评估
| 维度 | 判定 | 详情 |
|------|------|------|
| 环境风险 | 高 | Production |
| 数量风险 | 低 | count=30 |
| 攻击类型风险 | 高 | env_scan, random_scan, config_scan, dynamic_page |
| **综合** | **高** | - |

## 6. 溯源链接
- [在 Splunk 中查看](http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1783564199_1802.7%20%7C%20head%202%20%7C%20tail%201&earliest=0&latest=now)

---
*本报告由 AIOps Agent 自动生成 · 2026-07-23T16:56:19.158720*
