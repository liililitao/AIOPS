---
name: waf_alert_handler
description: >
  处理 Splunk WAF（Web Application Firewall）告警。
  自动解析告警数据、查询 CMDB 判定环境、三维度风险评估、生成分析报告和处理建议。
tags: [waf, alert, splunk, security]
version: "1.0"
---

# WAF 告警处理 Skill

## 概述

此 Skill 用于自动处理来自 Splunk 平台的 WAF 告警。替代运维人员从收到告警邮件到判定风险等级、生成报告的全流程。

## 适用场景

- Splunk WAF 告警 (index=azure, category=ApplicationGatewayFirewallLog)
- Azure Application Gateway 防火墙日志触发的 Blocked 事件
- 需要判定告警风险等级并生成处理建议

## 执行计划 (Playbook)

### Step 1: 扫描并解析告警数据
- 检查告警输入目录中的新 JSON 文件
- 对比 `processed_alerts.json` 索引去重
- 解析 JSON 提取关键字段: `id`, `properties_hostname`, `properties_requestUri`, `count`

### Step 2: CMDB 资产查询
- 调用 `cmdb_lookup` Tool
  - 第一优先级: 用 `id` (Azure 资源 ID) 精确匹配 CMDB 的 Resource Name
  - 第二优先级: 用 `properties_hostname` (域名) 模糊匹配 CMDB 的域名和证书列
- 获取 `Environment`: Production / Non-Production / Unknown

### Step 3: 三维度风险判定
- **维度 A (环境)**: Production → 高, Non-Production → 低
- **维度 B (数量)**: count ≥ 200 → 高, ≥ 100 → 中, < 100 → 低
- **维度 C (攻击类型)**: 动态页面/admin → 高, 配置扫描 → 中, 随机扫描 → 低
- **综合**: 取三维度最高值

### Step 4: 攻击类型分析
- 解析 `properties_requestUri`
- 按攻击模式分类: env_scan, admin_target, dynamic_page, config_scan 等

### Step 5: 生成分析报告
- LLM 综合告警数据 + CMDB 结果 + 攻击分析
- 生成 Markdown 报告（含证据溯源）
- 输出到 `output/reports/{YYYY-MM-DD}/`

### Step 6: 生成处理建议
- LLM 根据告警上下文 + 环境 + 风险等级
- 生成差异化、可执行的处理建议
- 输出到 `output/suggestions/{YYYY-MM-DD}/`

### Step 7: 输出结果
- 写带风险等级的告警 JSON → 告警输出目录
- 更新 `processed_alerts.json` 索引

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| RISK_COUNT_HIGH_THRESHOLD | 200 | 数量高风险阈值 |
| RISK_COUNT_MEDIUM_THRESHOLD | 100 | 数量中风险阈值 |
| SCAN_INTERVAL_MINUTES | 5 | 扫描间隔（分钟） |

## 输出

1. `../带风险等级的告警数据/{date}/alert_*.json` — 原始告警 + risk_level
2. `output/reports/{date}/` — 分析报告 (Markdown)
3. `output/suggestions/{date}/` — 处理建议 (Markdown)
