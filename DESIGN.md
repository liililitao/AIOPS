# AIOps 智能告警分析系统 — 设计蓝图

> **版本**: v1.0  
> **创建日期**: 2026-07-21  
> **参考项目**: `mutil-rag-agent-main` (Multi-RAG-Agent AIOps Platform V3)  
> **项目路径**: `C:\Users\JHGZ\Desktop\aiops\codeProject\1-aiOpsPoc\aiops\`

---

## 目录

1. [项目概述](#1-项目概述)
2. [业务背景与问题](#2-业务背景与问题)
3. [当前人工处理流程](#3-当前人工处理流程)
4. [系统总体架构](#4-系统总体架构)
5. [数据层设计](#5-数据层设计)
6. [Agent 层设计](#6-agent-层设计)
7. [定时调度机制](#7-定时调度机制)
8. [前端 Web 页面设计](#8-前端-web-页面设计)
9. [Splunk Dashboard 集成](#9-splunk-dashboard-集成)
10. [技术栈](#10-技术栈)
11. [目录结构](#11-目录结构)
12. [配置文件设计](#12-配置文件设计)
13. [API 接口设计](#13-api-接口设计)
14. [实施路线图](#14-实施路线图)
15. [未来扩展](#15-未来扩展)

---

## 1. 项目概述

### 1.1 项目目标

构建一个 **AI Agent 驱动的智能告警分析系统**，替代运维人员从日常繁杂的 WAF 告警数据中解放出来，实现：

- **自动风险判定**：根据告警数据自动查询 CMDB，结合多维度信息判定告警风险等级
- **智能分析报告**：结合 RAG 检索运维手册，生成带证据溯源的分析报告
- **处理建议生成**：LLM 基于告警上下文自主生成可执行的处理建议
- **可视化展示**：通过 Splunk Dashboard 和自建 Web 页面展示处理结果

### 1.2 核心理念

> **模拟运维人员的操作流程，用 AI Agent + Tool + RAG 替代人工判断**

运维人员收到告警邮件后的操作：

1. 查看告警内容（域名、攻击路径、数量）
2. 去 CMDB 查域名属于测试机还是生产机
3. 根据经验判断风险等级
4. 根据运维手册执行处理流程

AI Agent 对应的操作：

1. 解析告警 JSON 数据
2. 调用 CMDB Tool 查询域名环境
3. 三维度模型判定风险等级
4. LLM 生成报告和建议

---

## 2. 业务背景与问题

### 2.1 当前痛点

- Splunk 平台持续监控 Azure 日志，WAF 告警规则触发后发邮件给运维人员
- 运维人员每天需要处理大量告警邮件，逐一判断风险等级
- 判断过程依赖个人经验（查 CMDB、看数量、看攻击类型）
- 重复性工作多，效率低，容易遗漏或误判

### 2.2 聚焦范围

**当前阶段专注处理 WAF（Web Application Firewall）告警**，后续可扩展到其他告警类型。

### 2.3 告警规则（SPL）

```
index=azure category=ApplicationGatewayFirewallLog properties_action=Blocked
properties_hostname!="novocareapp.novocare.com.cn" AND
properties_hostname!="test-novocareapp.novocare.com.cn"
| rex field=resourceId "\/(?<id>[^\/]+)$"
| stats values(properties_action) as properties_action values(properties_requestUri) as
properties_requestUri count by properties_hostname,id
| table id,properties_hostname,properties_requestUri,properties_action,count
| search count>=20
```

关键告警字段：`id`(Azure资源ID)、`properties_hostname`(域名)、`properties_requestUri`(攻击路径)、`properties_action`(动作)、`count`(触发次数)

---

## 3. 当前人工处理流程

> 来源：《收到WAF告警邮件之后的处理过程 1.docx》

### 3.1 判断严重程度（三维度）

| 维度          | 判断依据                        | 低风险                   | 中风险               | 高风险                       |
| ----------- | --------------------------- | --------------------- | ----------------- | ------------------------- |
| **A. 环境**   | 查 CMDB：hostname/id 对应生产还是测试 | 测试环境 (Non-Production) | —                 | 生产环境 (Production)         |
| **B. 数量**   | 告警中的 count 字段               | count < 100           | 100 ≤ count < 200 | count ≥ 200               |
| **C. 攻击类型** | requestUri 内容               | 杂乱目录扫描类（.env、backup等） | —                 | 针对 php/asp 动态页面或 admin 目录 |

> **综合判定**：三维度综合评估，取最高风险等级为最终等级。环境维度权重最高。

### 3.2 调查过程（严重程度高且频繁时触发）

1. **创建 ServiceNow Ticket** → 记录调查过程（标记为"未来实现"）
2. **Splunk 日志搜索** → 查对应域名日志，判断是短期突发还是长期持续
   - 短期突发 → 被攻击可能性大 → 联系应用同事 + CC 系统经理
   - 长期持续 + 非高危 URL → 攻击可能性不大
3. **根据应用回复** → 决定是否系统加固 / 修改 WAF 规则 → 关闭 Ticket

---

## 4. 系统总体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SPLUNK 平台                                   │
│                                                                      │
│  Azure日志 → WAF告警规则(SPL) → 触发告警                              │
│                                    ↓                                 │
│                  告警JSON写入 → 【告警数据/】目录                       │
└─────────────────────────────────────────────────────────────────────┘
                                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     AIOps Agent (定时 Cron 执行)                      │
│                                                                      │
│  ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌────────────────┐  │
│  │ 告警解析  │ → │ CMDB查询   │ → │ 风险判定  │ → │ 报告&建议生成  │  │
│  │ (Step 1) │   │ (Tool调用) │   │ (三维度)  │   │ (LLM)   │  │
│  └──────────┘   └───────────┘   └──────────┘   └────────────────┘  │
│                                     ↓                                │
│                    输出到【带风险等级的告警数据/】目录                    │
└─────────────────────────────────────────────────────────────────────┘
                                     ↓
          ┌──────────────────────────┼──────────────────────────┐
          ↓                          ↓                          ↓
┌─────────────────┐    ┌──────────────────────┐    ┌──────────────────┐
│ Splunk Dashboard │    │   自建 Web 页面 (2页)  │    │   数据存储层      │
│ (已有，只接收    │    │                      │    │                  │
│  带风险等级的    │    │ 页面1: 定时任务配置    │    │ - Milvus 向量库   │
│  告警 JSON)     │    │ 页面2: 结果展示+问答   │    │ - CMDB (xlsx/API) │
└─────────────────┘    └──────────────────────┘    └──────────────────┘
```

### 4.1 数据流总览

```
输入数据源:
  ├── 告警数据/              ← Splunk 定时写入的 WAF 告警 JSON
  ├── CMDB数据库/            ← 设备/域名清单 (xlsx，未来 API)
  └── 运维手册 (向量库)       ← SOP 文档经 Embedding 存入 Milvus

Agent 处理:
  ├── 1. 扫描新告警 → 对比 processed_alerts.json 去重
  ├── 2. 解析 JSON → 提取 id, hostname, requestUri, count
  ├── 3. 调用 cmdb_lookup Tool → 查 Environment
  ├── 4. 三维度风险判定 → 综合等级: 低/中/高
  ├── 5. RAG 检索运维手册 → 获取相关 SOP
  └── 6. LLM 生成:
        ├── 分析报告 (含证据溯源)
        └── 处理建议

输出:
  ├── 带风险等级的告警数据/   ← 原始告警 + risk_level 字段
  ├── 分析报告/               ← Markdown 分析报告
  ├── 处理建议/               ← Markdown 处理建议
  └── processed_alerts.json  ← 已处理告警索引
```

---

## 5. 数据层设计

### 5.1 输入：告警数据（来自 Splunk）

**路径**: `../告警数据/`（与 aiops 项目同级，由 Splunk 定时写入）

**格式**: JSON 文件，命名规则 `alert_{alert_name}_{timestamp}.json`

**示例文件**: `alert_test-waf_20260713_144409.json`

**数据结构**:

```json
{
  "alert_name": "test-waf",
  "trigger_time": "2026-07-13T14:44:09.765+08:00",
  "trigger_time_utc": "2026-07-13T06:44:09.765Z",
  "event_count": 1,
  "trigger_reason": "Saved Search [test-waf] always(1)",
  "splunk_url": "http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?...",
  "search_terms": "SPL 搜索语句(简化版)",
  "full_spl": "SPL 搜索语句(完整版)",
  "results": [
    {
      "id": "AGW-DAP-PRD-N3-01",
      "properties_hostname": "purview.novonordiskchina.com.cn",
      "properties_requestUri": "/.env.local /.env.production.local /admin/.env ...",
      "properties_action": "Blocked",
      "count": "20",
      "__mv_properties_requestUri": "$/.env.local$;$/.env.production.local$;..."
    }
  ],
  "operator_notes": ""
}
```

**Agent 需要提取的关键字段**:

| 字段                                | 用途                     | 示例值                               |
| --------------------------------- | ---------------------- | --------------------------------- |
| `results[].id`                    | CMDB 查询主键（Azure 资源 ID） | `AGW-DAP-PRD-N3-01`               |
| `results[].properties_hostname`   | CMDB 查询辅助键（域名）         | `purview.novonordiskchina.com.cn` |
| `results[].properties_requestUri` | 攻击类型判定                 | `/.env.local /admin/.env ...`     |
| `results[].count`                 | 数量判定                   | `20`                              |
| `results[].properties_action`     | 动作类型                   | `Blocked`                         |

### 5.2 CMDB 数据库

**路径**: `../CMDB数据库/NNSH CIOA_Service_Azure__monthly_summary -V2.70-20260601.xlsx`

**当前格式**: Excel (.xlsx)，未来切换为 API 接口

**Sheet 结构**:

```
Sheet 1: Computer System List (33行 × 17列)
  ├── 关键列: 系统名称, Status, 域名和证书, 订阅名称

Sheet 2: Subscription (99行 × 11列)
  ├── 关键列: Subscription Name, GxP, Status, CIOA or not

Sheet 3: Azure IaaS (54行 × 29列) ⭐ 核心
  ├── 关键列: Resource Name, Environment, Server Name, Subscription Name
  └── Environment 值: "Production" / "Non-Production"

Sheet 4: Azure PaaS (1734行 × 22列) ⭐ 核心
  ├── 关键列: Resource Name, Resource Type, Environment, SUBSCRIPTION
  └── Environment 值: "Production" / "Non-Production"

Sheet 5: ChangeLog (173行)
  └── 版本变更记录
```

**CMDB 查询策略（两级匹配）**:

```
第一优先级: 精确匹配
  告警中的 id 字段 → Azure PaaS/IaaS 的 Resource Name 列 → 获取 Environment

第二优先级: 模糊匹配（兜底）
  告警中的 properties_hostname → Computer System List 的 域名和证书 列
    → 通过订阅名称关联到 Azure IaaS/PaaS → 获取 Environment
```

**Environment → 风险映射**:

| CMDB Environment | 风险等级  |
| ---------------- | ----- |
| `Production`     | **高** |
| `Non-Production` | **低** |

### 5.3 运维手册（向量数据库）

**存储**: Milvus 向量数据库

**内容**: WAF 告警处理 SOP、系统运维手册、安全事件响应流程等 Markdown 文档

**RAG 流程**（由现有 `mutil-rag-agent-main` 项目的能力提供）:

```
用户查询/告警上下文
    → Embedding (text-embedding-v4 或 bge-m3)
    → Milvus 向量检索 (HNSW + COSINE)
    → 混合检索 (BM25 + RRF 融合)
    → Reranker 重排序
    → 返回 Top-K 相关文档片段
```

> **注意**: 本项目不重新实现 RAG 基础设施，通过调用 Milvus 接口获取检索结果。向量数据的入库、分块、Embedding 等操作由外部流程处理。

### 5.4 已处理告警索引

**路径**: `aiops/data/processed_alerts.json`

**用途**: 记录已处理过的告警文件名，避免重复处理

**格式**:

```json
{
  "processed_files": {
    "alert_test-waf_20260713_144409.json": {
      "processed_at": "2026-07-13T14:45:30.123+08:00",
      "risk_level": "低",
      "output_dir": "2026-07-13/"
    }
  },
  "last_scan_time": "2026-07-13T14:50:00.000+08:00"
}
```

### 5.5 输出数据

#### 5.5.1 带风险等级的告警数据

**路径**: `../带风险等级的告警数据/{YYYY-MM-DD}/alert_{name}_{timestamp}.json`

**格式**: 原始告警 JSON + `risk_level` 字段

```json
{
  ...原始告警全部字段...,
  "risk_level": "高",
  "risk_details": {
    "environment_risk": "高",
    "environment": "Production",
    "count_risk": "低",
    "count_value": 20,
    "attack_type_risk": "中",
    "attack_types": ["env_scan", "admin_target"],
    "overall_risk": "高",
    "assessed_at": "2026-07-13T14:45:30.123+08:00"
  }
}
```

#### 5.5.2 分析报告

**路径**: `aiops/output/reports/{YYYY-MM-DD}/{alert_name}_{timestamp}_analysis.md`

**内容要求**:

```markdown
# WAF 告警分析报告

## 1. 告警概要
- 告警名称、触发时间、事件数量
- Splunk 搜索链接（可溯源）

## 2. 告警数据详情
- 受影响资源 ID、域名
- 被攻击路径列表
- WAF 动作（Blocked/Detected）

## 3. CMDB 资产信息（证据溯源）
- 查询方式：通过 Resource ID "AGW-DAP-PRD-N3-01" 在 CMDB Azure PaaS 表中匹配
- 查询结果：Environment = Production
- 订阅名称：xxx
- 资源类型：Application Gateway
- [附 CMDB 查询截图/记录]

## 4. 攻击分析
- 攻击类型分类
- 攻击频率
- 攻击来源特征

## 5. 风险评估
- 环境维度：高（生产环境）
- 数量维度：低（20次）
- 攻击类型维度：中（含 admin 目录扫描）
- 综合风险等级：高

## 6. 相关运维手册（证据溯源）
- [引用 RAG 检索到的 SOP 片段]
- 来源文档：xxx.md，章节：xxx
```

#### 5.5.3 处理建议

**路径**: `aiops/output/suggestions/{YYYY-MM-DD}/{alert_name}_{timestamp}_suggestion.md`

**内容要求**: LLM 根据告警上下文 + CMDB 信息 + 运维手册自主生成，包括：

```markdown
# WAF 告警处理建议

## 1. 立即行动
- [ ] 确认是否为真实攻击
- [ ] ...

## 2. 调查步骤
- 在 Splunk 中搜索 xxx 域名相关日志
- ...

## 3. 处置建议
- 如为真实攻击：xxx
- 如为误报：xxx

## 4. 后续加固
- WAF 规则优化建议
- 系统安全加固建议

## 5. 参考文档
- [运维手册 xxx]
```

---

## 6. Agent 层设计

### 6.1 架构模式

**沿用 `mutil-rag-agent-main` 的 Plan-Execute-Replan 模式（LangGraph）**：

```
用户输入/定时触发
    │
    ▼
┌─────────────┐
│ Skill Router │  识别任务类型 → 选择 WAF Alert Skill
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Planner   │  生成执行计划 (4-6 步骤)
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────────────┐
│  Executor   │ ──→ │ Tool: cmdb_lookup    │
│  (循环)     │ ──→ │ Tool: search_sop     │
│             │ ──→ │ LLM: 分析/生成       │
└──────┬──────┘     └─────────────────────┘
       │
       ▼
┌─────────────┐
│  Replanner  │  评估进度 → 继续/完成/重规划
└──────┬──────┘
       │ (完成)
       ▼
┌─────────────┐
│   Report    │  LLM 生成最终报告 + 建议
└─────────────┘
```

### 6.2 WAF Alert Skill 定义

**Skill 名称**: `waf_alert_handler`

**描述**: 处理 Splunk WAF 告警，自动判定风险等级并生成分析报告

**执行计划模板（Playbook）**:

```
Step 1: 扫描并解析告警数据
  - 检查【告警数据/】目录中的新 JSON 文件
  - 对比 processed_alerts.json 去重
  - 解析 JSON 提取关键字段

Step 2: CMDB 资产查询
  - 调用 cmdb_lookup Tool，传入 id 和 hostname
  - 获取 Environment 和关联的订阅/资源信息

Step 3: 三维度风险判定
  - 环境维度：Production → 高 / Non-Production → 低
  - 数量维度：count<100 → 低 / 100≤count<200 → 中 / count≥200 → 高
  - 攻击类型维度：扫描类 → 低 / 动态页面/admin类 → 高
  - 综合等级：取最高值

Step 4: RAG 检索运维手册
  - 调用 search_sop Tool，查询相关 WAF 处理流程
  - 检索相关安全加固文档

Step 5: 生成分析报告
  - LLM 综合告警数据 + CMDB 结果 + RAG 检索结果
  - 生成 Markdown 分析报告（含证据溯源）

Step 6: 生成处理建议
  - LLM 根据上下文自主生成可执行的处理建议

Step 7: 输出结果
  - 写带风险等级的告警 JSON
  - 写分析报告 Markdown
  - 写处理建议 Markdown
  - 更新 processed_alerts.json
```

### 6.3 CMDB Lookup Tool 设计

**这是 Agent 调用 CMDB 的核心 Tool，后期可人工修改查询逻辑**

**Tool 名称**: `cmdb_lookup`

**Tool 描述**: "查询 CMDB 数据库，根据 Azure 资源 ID 或域名获取设备所属环境（Production/Non-Production）及相关资产信息"

**输入参数**:

```python
{
    "resource_id": "AGW-DAP-PRD-N3-01",          # 告警中的 id 字段
    "hostname": "purview.novonordiskchina.com.cn"  # 告警中的 hostname 字段
}
```

**输出**:

```python
{
    "found": true,
    "match_type": "exact",           # "exact" | "fuzzy" | "none"
    "resource_name": "AGW-CDCShare-spl-n3-01",
    "resource_type": "Application gateway",
    "environment": "Production",     # 核心字段
    "subscription": "CDC Shared Services",
    "server_name": "vm-cdcshared-prd-spl9forwarder",
    "source_sheet": "Azure PaaS",
    "source_row": 2
}
```

**实现方式**:

- **当前**：Python 函数用 `openpyxl` 读取 xlsx，先精确匹配 `Resource Name`，再模糊匹配 `域名和证书`
- **未来**：替换为 HTTP 请求调用 CMDB API，SQL 查询语句可配置在 `.env` 或独立 SQL 文件中
- **查询逻辑与 SQL 分离**：将查询语句放在配置文件或独立 `.sql` 文件中，方便运维人员后期修改

**配置示例**:

```ini
# .env 中 CMDB 相关配置
CMDB_TYPE=xlsx                    # xlsx | api
CMDB_XLSX_PATH=../CMDB数据库/NNSH CIOA_Service_Azure__monthly_summary -V2.70-20260601.xlsx
CMDB_API_URL=                     # 未来 API 地址
CMDB_API_TOKEN=                   # 未来 API Token
```

### 6.4 风险判定模型

**三维度综合判定**，代码实现为独立函数 `assess_risk()`：

```python
def assess_risk(environment: str, count: int, request_uris: str) -> dict:
    """
    三维度综合风险判定

    Args:
        environment: CMDB 查询结果 "Production" / "Non-Production" / "Unknown"
        count: 告警 count 字段值
        request_uris: 攻击路径字符串

    Returns:
        {
            "environment_risk": "高" | "低" | "未知",
            "count_risk": "高" | "中" | "低",
            "attack_type_risk": "高" | "中" | "低",
            "overall_risk": "高" | "中" | "低",
            "attack_types": ["env_scan", "admin_target", ...]
        }
    """

    # 维度A：环境风险
    if environment == "Production":
        env_risk = "高"
    elif environment == "Non-Production":
        env_risk = "低"
    else:
        env_risk = "未知"

    # 维度B：数量风险 (阈值可配置)
    if count >= 200:
        count_risk = "高"
    elif count >= 100:
        count_risk = "中"
    else:
        count_risk = "低"

    # 维度C：攻击类型风险
    attack_types = classify_attack_types(request_uris)
    if any(t in ["php_attack", "asp_attack", "admin_target"] for t in attack_types):
        attack_risk = "高"
    elif any(t in ["env_scan", "backup_scan"] for t in attack_types):
        attack_risk = "中"
    else:
        attack_risk = "低"

    # 综合判定：取最高
    risk_order = {"低": 0, "中": 1, "高": 2, "未知": 1}
    overall = max([env_risk, count_risk, attack_risk], key=lambda x: risk_order[x])

    return {
        "environment_risk": env_risk,
        "count_risk": count_risk,
        "attack_type_risk": attack_risk,
        "overall_risk": overall,
        "attack_types": attack_types
    }
```

**攻击类型分类规则**（`classify_attack_types` 函数）：

| 攻击特征                                  | 分类标签              | 风险倾向 |
| ------------------------------------- | ----------------- | ---- |
| `/.env`, `/env.backup`, `/.env.local` | `env_scan`        | 中    |
| `/admin/`, `/administrator/`          | `admin_target`    | 高    |
| `*.php`, `*.asp`, `*.aspx`, `*.jsp`   | `dynamic_page`    | 高    |
| `/conf/`, `/backup/`, `/cron/`        | `config_scan`     | 中    |
| `/node_modules/`, `/vendor/`          | `dependency_scan` | 低    |
| 其他杂乱路径                                | `random_scan`     | 低    |

### 6.5 RAG 检索 Tool

**Tool 名称**: `search_sop`

**Tool 描述**: "搜索运维手册向量数据库，获取与当前告警相关的 SOP 文档和处理流程"

**输入**: 查询字符串（由告警上下文拼接而成）

**输出**: Top-K 相关文档片段（含来源、章节、相关度分数）

### 6.6 LLM 调用策略

沿用 `mutil-rag-agent-main` 的分层模型策略：

| 角色       | 模型              | 用途              |
| -------- | --------------- | --------------- |
| Router   | 快速/便宜模型         | 识别任务类型（WAF告警处理） |
| Planner  | 中等模型            | 生成执行计划          |
| Executor | Tool-calling 模型 | 执行工具调用          |
| Report   | Pro 模型          | 生成分析报告和处理建议     |

支持的 LLM 后端: DashScope（阿里云）、DeepSeek、Ollama（本地）

---

## 7. 定时调度机制

### 7.1 调度方式

**Cron-like 定时轮询**，默认每 5 分钟扫描一次【告警数据/】目录。

### 7.2 实现方案

在 FastAPI 应用中集成 **APScheduler**：

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=5, id='scan_alerts')
async def scan_and_process_alerts():
    """扫描告警目录，处理新告警"""
    ...
```

### 7.3 可配置参数

```ini
# .env 配置
SCAN_INTERVAL_MINUTES=5           # 扫描间隔（分钟），默认5分钟
SCAN_ENABLED=true                 # 是否启用定时扫描
ALERT_INPUT_DIR=../告警数据        # 告警输入目录（相对于 aiops 项目）
```

### 7.4 动态调整

- **代码级**：修改 `.env` 中的 `SCAN_INTERVAL_MINUTES`，重启生效
- **Web 页面级**（理想目标）：在 Web 页面 1 的配置面板中调整间隔，调用 API 动态更新调度器
  - 如果 Web 端动态调整实现复杂，退而求其次：仅支持在 `.env` 中修改

---

## 8. 前端 Web 页面设计

### 8.1 技术方案

沿用 `mutil-rag-agent-main` 的前端模式：

- **纯静态 SPA**（单页面应用）
- `index.html` + `app.js` + `styles.css`
- FastAPI 直接 serve 静态文件
- SSE（Server-Sent Events）用于实时数据推送

### 8.2 页面1：定时任务配置页 (`/config`)

**功能**:

```
┌──────────────────────────────────────────────────────────┐
│  AIOps 告警处理 - 配置面板                                │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 定时扫描配置                                        │  │
│  │                                                    │  │
│  │ 扫描间隔: [  5  ] 分钟      [应用]                  │  │
│  │                                                    │  │
│  │ 当前状态: ● 运行中                                  │  │
│  │ 上次扫描: 2026-07-21 14:30:00                       │  │
│  │ 下次扫描: 2026-07-21 14:35:00                       │  │
│  │                                                    │  │
│  │ [立即扫描]  [暂停]  [恢复]                           │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 风险判定参数                                        │  │
│  │                                                    │  │
│  │ 数量阈值-高: [200]    中: [100]                      │  │
│  │ CMDB 类型: [xlsx ▼]  路径: [................]       │  │
│  │                                                    │  │
│  │ [保存配置]                                          │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 手动触发                                            │  │
│  │                                                    │  │
│  │ 上传告警文件: [选择文件] [处理]                       │  │
│  │ 或输入告警JSON: [文本框................] [处理]       │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 8.3 页面2：结果展示页 (`/results`)

**功能**:

```
┌──────────────────────────────────────────────────────────┐
│  AIOps 告警处理 - 结果展示                                │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 筛选: 风险等级 [全部 ▼]  日期范围 [....]             │  │
│  │ 搜索: [关键词................]                       │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─────────┬──────────┬────────┬────────┬────────────┐  │
│  │ 告警名称  │ 域名      │ 风险等级 │ 时间    │ 操作       │  │
│  ├─────────┼──────────┼────────┼────────┼────────────┤  │
│  │ test-waf │ purview..│ 🔴 高   │ 07-13  │ [查看详情] │  │
│  │ test-waf │ test-xxx │ 🟢 低  │ 07-13  │ [查看详情] │  │
│  └─────────┴──────────┴────────┴────────┴────────────┘  │
│                                                          │
│  ┌─ 告警详情 ─────────────────────────────────────────┐  │
│  │                                                    │  │
│  │ [告警数据] [分析报告] [处理建议] [AI 问答]           │  │
│  │                                                    │  │
│  │ ┌─ 分析报告 Tab ─────────────────────────────────┐ │  │
│  │ │                                                │ │  │
│  │ │ # WAF 告警分析报告                              │ │  │
│  │ │                                                │ │  │
│  │ │ ## 告警概要                                     │ │  │
│  │ │ ... (Markdown 渲染)                             │ │  │
│  │ │                                                │ │  │
│  │ │ ## CMDB 资产信息（证据溯源）                      │ │  │
│  │ │ > 查询方式: Resource ID 精确匹配 CMDB Azure PaaS │ │  │
│  │ │ > 查询结果: Environment = Production            │ │  │
│  │ │                                                │ │  │
│  │ └────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ AI 问答 ──────────────────────────────────────────┐  │
│  │ [用户提问输入框........................] [发送]      │  │
│  │                                                    │  │
│  │ 🤖: 根据当前告警数据，我建议...                       │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**Tab 说明**:

| Tab   | 内容                     | 数据来源              |
| ----- | ---------------------- | ----------------- |
| 告警数据  | 原始告警 JSON + 风险等级标注     | 带风险等级的告警数据目录      |
| 分析报告  | Markdown 报告渲染（含证据溯源链接） | 分析报告目录            |
| 处理建议  | Markdown 建议渲染          | 处理建议目录            |
| AI 问答 | 基于当前告警上下文的 RAG 对话      | LLM + Milvus 实时检索 |

---

## 9. Splunk Dashboard 集成

### 9.1 说明

Splunk Dashboard **已完成**，本项目只需确保输出的带风险等级告警数据格式符合其要求。

### 9.2 输出格式

Dashboard 只接收 **带风险等级的告警 JSON**，核心新增字段：`risk_level`（`"高"` / `"中"` / `"低"`）。

### 9.3 数据流向

```
【带风险等级的告警数据/】目录 → Splunk 定时拉取/推送 → Dashboard 展示
```

---

## 10. 技术栈

| 层次              | 技术                             | 说明                      |
| --------------- | ------------------------------ | ----------------------- |
| **后端框架**        | Python FastAPI                 | 沿用 mutil-rag-agent-main |
| **Agent 编排**    | LangGraph                      | Plan-Execute-Replan 模式  |
| **LLM**         | 诺和AI API接口                     | 多后端支持，分层模型策略            |
| **向量数据库**       | Milvus                         | 运维手册 RAG 检索             |
| **Embedding**   | text-embedding-v4 / bge-m3     | 向量化                     |
| **任务调度**        | APScheduler                    | 定时扫描告警目录                |
| **CMDB 读取**     | openpyxl (当前) / httpx (未来 API) | 封装为 Agent Tool          |
| **前端**          | 纯静态 HTML + JS + CSS            | SPA，SSE 实时通信            |
| **Markdown 渲染** | marked.js                      | 前端渲染报告                  |
| **配置管理**        | pydantic-settings + .env       | 所有参数可配置                 |

---

## 11. 目录结构

```
aiops/                                  # 项目根目录
├── DESIGN.md                           # 本设计文档
├── requirements.txt                    # Python 依赖
├── .env.example                        # 配置模板
├── .env                                # 实际配置（不提交）
├── run.py                              # 启动入口
│
├── app/                                # 核心应用
│   ├── main.py                         # FastAPI 入口 + 生命周期
│   ├── config.py                       # 配置管理 (pydantic-settings)
│   │
│   ├── agents/                         # LangGraph Agent
│   │   ├── state.py                    # Agent 状态定义
│   │   ├── graph.py                    # 主图编排
│   │   ├── skill_router.py             # 技能路由（识别WAF告警任务）
│   │   ├── planner.py                  # 规划器（生成执行计划）
│   │   ├── executor.py                 # 执行器（调用Tool）
│   │   ├── replanner.py                # 重规划器
│   │   └── report.py                   # 报告生成器
│   │
│   ├── skills/                         # Skill 定义
│   │   └── definitions/
│   │       └── waf_alert_handler.md    # WAF告警处理 Playbook
│   │
│   ├── tools/                          # Tool 实现
│   │   ├── cmdb_tool.py                # CMDB 查询工具 ⭐
│   │   ├── sop_search_tool.py          # 运维手册 RAG 检索工具
│   │   └── file_tool.py                # 文件读写工具
│   │
│   ├── core/                           # 核心组件
│   │   ├── llm.py                      # LLM 工厂
│   │   ├── risk_assessor.py            # 三维度风险判定 ⭐
│   │   ├── attack_classifier.py        # 攻击类型分类 ⭐
│   │   └── scheduler.py                # 定时任务管理
│   │
│   ├── api/                            # API 路由
│   │   └── v1/
│   │       ├── alerts.py               # 告警相关接口
│   │       ├── config.py               # 配置相关接口
│   │       └── chat.py                 # RAG 问答接口
│   │
│   ├── schemas/                        # Pydantic 模型
│   │   ├── alert.py                    # 告警数据模型
│   │   ├── cmdb.py                     # CMDB 数据模型
│   │   └── risk.py                     # 风险判定模型
│   │
│   └── services/                       # 业务逻辑
│       ├── alert_service.py            # 告警处理服务
│       └── report_service.py           # 报告生成服务
│
├── frontend/                           # Web 前端（静态文件）
│   ├── index.html                      # SPA 入口
│   ├── app.js                          # 前端逻辑
│   ├── styles.css                      # 样式
│   └── lib/                            # 第三方 JS 库（marked.js 等）
│
├── data/                               # 本地数据
│   ├── processed_alerts.json           # 已处理告警索引
│   └── attack_patterns.json            # 攻击类型识别规则（可人工更新）
│
├── output/                             # 输出目录
│   ├── reports/                        # 分析报告 (Markdown)
│   │   └── {YYYY-MM-DD}/
│   └── suggestions/                    # 处理建议 (Markdown)
│       └── {YYYY-MM-DD}/
│
├── scripts/                            # 辅助脚本
│   ├── merge_reports.py                # 合并分析报告和处理建议为单个文档
│   └── init_db.py                      # 初始化/检查 Milvus 连接
│
└── tests/                              # 测试
    ├── test_risk_assessor.py
    ├── test_cmdb_tool.py
    └── test_agent_flow.py
```

### 11.1 与现有数据目录的关系

```
mutil-rag-agent-main-v1/
├── mutil-rag-agent-main/               # 原有参考项目
├── aiops/                              # ← 本项目（新建）
├── 告警数据/                            # Splunk 输入（已有）
├── CMDB数据库/                          # CMDB 数据（已有）
├── 带风险等级的告警数据/                  # Agent 输出（已有目录结构）
└── 收到WAF告警邮件之后的处理过程 1.docx   # 运维流程参考文档
```

---

## 12. 配置文件设计

### 12.1 `.env` 完整配置项

```ini
# ==========================================
# 应用基础配置
# ==========================================
APP_NAME=AIOps-Alert-Agent
APP_VERSION=1.0.0
DEBUG=false
PORT=8001
HOST=0.0.0.0

# ==========================================
# 定时扫描配置
# ==========================================
SCAN_ENABLED=true
SCAN_INTERVAL_MINUTES=5
ALERT_INPUT_DIR=../告警数据
ALERT_OUTPUT_DIR=../带风险等级的告警数据
PROCESSED_INDEX_PATH=data/processed_alerts.json

# ==========================================
# CMDB 数据源配置
# ==========================================
CMDB_TYPE=xlsx
CMDB_XLSX_PATH=../CMDB数据库/NNSH CIOA_Service_Azure__monthly_summary -V2.70-20260601.xlsx
# CMDB_API_URL=                    # 未来 API 模式时启用
# CMDB_API_TOKEN=                  # 未来 API 模式时启用

# ==========================================
# 风险判定参数（可后期调整）
# ==========================================
RISK_COUNT_HIGH_THRESHOLD=200
RISK_COUNT_MEDIUM_THRESHOLD=100

# ==========================================
# LLM 配置
# ==========================================
# 主 LLM 后端: dashscope | deepseek | ollama
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here

# 模型分层
ROUTER_MODEL=qwen-flash
PLANNER_MODEL=qwen-plus
EXECUTOR_MODEL=qwen-flash
REPORT_MODEL=qwen-pro

# ==========================================
# Milvus 向量数据库（运维手册 RAG）
# ==========================================
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=sop_knowledge
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=text-embedding-v4

# ==========================================
# 输出配置
# ==========================================
OUTPUT_REPORTS_DIR=output/reports
OUTPUT_SUGGESTIONS_DIR=output/suggestions

# ==========================================
# Web 服务配置
# ==========================================
FRONTEND_DIR=frontend
CORS_ORIGINS=*
```

---

## 13. API 接口设计

### 13.1 告警相关

| 方法     | 路径                       | 说明               |
| ------ | ------------------------ | ---------------- |
| `GET`  | `/api/v1/alerts`         | 获取已处理告警列表（分页、筛选） |
| `GET`  | `/api/v1/alerts/{id}`    | 获取单个告警详情（含报告和建议） |
| `POST` | `/api/v1/alerts/process` | 手动提交告警 JSON 进行处理 |
| `POST` | `/api/v1/alerts/upload`  | 上传告警文件进行处理       |

### 13.2 配置相关

| 方法    | 路径                                | 说明             |
| ----- | --------------------------------- | -------------- |
| `GET` | `/api/v1/config`                  | 获取当前配置（间隔、阈值等） |
| `PUT` | `/api/v1/config`                  | 更新配置（动态调整）     |
| `GET` | `/api/v1/config/scheduler/status` | 获取调度器运行状态      |

### 13.3 调度器控制

| 方法     | 路径                         | 说明         |
| ------ | -------------------------- | ---------- |
| `POST` | `/api/v1/scheduler/scan`   | 手动触发一次立即扫描 |
| `POST` | `/api/v1/scheduler/pause`  | 暂停定时扫描     |
| `POST` | `/api/v1/scheduler/resume` | 恢复定时扫描     |

### 13.4 RAG 问答

| 方法     | 路径                    | 说明              |
| ------ | --------------------- | --------------- |
| `POST` | `/api/v1/chat`        | 基于告警上下文的 RAG 问答 |
| `GET`  | `/api/v1/chat/stream` | SSE 流式问答        |

### 13.5 报告相关

| 方法    | 路径                                      | 说明              |
| ----- | --------------------------------------- | --------------- |
| `GET` | `/api/v1/reports/{alert_id}/analysis`   | 获取分析报告 Markdown |
| `GET` | `/api/v1/reports/{alert_id}/suggestion` | 获取处理建议 Markdown |

---

## 14. 实施路线图

### Phase 1: 项目骨架搭建

- [ ] 创建项目目录结构
- [ ] 编写 `.env.example` 和 `config.py`
- [ ] FastAPI 入口 + 静态文件服务
- [ ] 前端基础框架（index.html + 路由）

### Phase 2: CMDB Tool + 风险判定

- [ ] 实现 `cmdb_tool.py`（xlsx 读取查询）
- [ ] 实现 `attack_classifier.py`（攻击类型识别）
- [ ] 实现 `risk_assessor.py`（三维度判定）
- [ ] 单元测试

### Phase 3: Agent 编排

- [ ] 定义 WAF Alert Skill Playbook
- [ ] 实现 LangGraph 主图（Plan-Execute-Replan）
- [ ] 实现告警扫描 + 去重逻辑
- [ ] 实现输出写入（JSON + Markdown）
- [ ] 实现 `processed_alerts.json` 索引机制

### Phase 4: 定时调度

- [ ] APScheduler 集成
- [ ] 调度器控制 API
- [ ] 手动触发 API

### Phase 5: 前端 Web 页面

- [ ] 页面1：定时任务配置面板
- [ ] 页面2：结果展示（告警列表 + 详情 Tab + Markdown 渲染）
- [ ] AI 问答面板

### Phase 6: RAG 集成

- [ ] Milvus 连接验证
- [ ] `sop_search_tool.py` 实现
- [ ] RAG 问答 API

### Phase 7: 联调与优化

- [ ] 端到端流程测试（用现有告警数据）
- [ ] 阈值调优
- [ ] 前端交互优化
- [ ] 文档完善

---

## 15. 未来扩展

### 15.1 短期（Phase 2-3 完成后）

- **CMDB API 模式**：从 xlsx 切换到 HTTP API 调用
- **ServiceNow 集成**：自动创建 Ticket（参考运维手册 3.2-A）
- **Splunk 日志查询**：Agent 自动在 Splunk 中搜索域名相关日志（参考运维手册 3.2-B）

### 15.2 中期

- **告警类型扩展**：从 WAF 扩展到 MySQL、Redis、K8s 等（可复用 mutil-rag-agent-main 的 Skill 体系）
- **告警关联分析**：同一 Incident Group 内的多条告警关联分析
- **多租户支持**：不同团队的告警隔离

### 15.3 长期

- **自动化处置**：Agent 自动执行低风险告警的处置操作（如临时封禁 IP、调整 WAF 规则）
- **告警预测**：基于历史数据预测告警趋势
- **知识图谱**：构建 CMDB + 告警 + SOP 知识图谱

---

> **文档维护者**: AIOps Team  
> **最后更新**: 2026-07-21  
> **下一步**: 按 Phase 1 开始实施
