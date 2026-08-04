# Splunk AIOps PoC — 新增功能完全拆解

> 本文档逐一讲解在 `mutil-rag-agent-main` 基础上为 Splunk PoC 新增/修改的每个文件，
> 包括：加了什么、为什么加、设计依据、模仿了项目中哪个已有模式。

---

## 目录

1. [总览：新增了什么](#1-总览新增了什么)
2. [新增文件逐个拆解](#2-新增文件逐个拆解)
   - [2.1 告警模拟器](#21-alert_simulatorpy)
   - [2.2 CMDB 查询工具](#22-cmbd_toolpy)
   - [2.3 Splunk Forwarder](#23-splunk_forwarderpy)
   - [2.4 告警接收 API](#24-splunkpy)
   - [2.5 Splunk 告警分类 Skill](#25-skillmd)
   - [2.6 Splunk Dashboard XML](#26-splunk_dashboardxml)
   - [2.7 Dashboard 导入脚本](#27-import_dashboardpy)
3. [修改文件逐个拆解](#3-修改文件逐个拆解)
   - [3.1 main.py — 注册新路由](#31-mainpy)
   - [3.2 mcp_loader.py — 注册新工具](#32-mcp_loaderpy)
   - [3.3 meta.py — 注册工具元数据](#33-metapy)
4. [架构全景图](#4-架构全景图)
5. [关键设计决策 Q&A](#5-关键设计决策-qa)

---

## 1. 总览：新增了什么

在原有 Agent 项目的基础上，新增了 **Splunk 告警输入管道** 和 **Splunk Dashboard 输出管道**，形成了完整的闭环：

```
原有项目 (已有):                    本次 PoC 新增:
┌──────────────────────┐          ┌──────────────────────────────┐
│ 用户输入 → Agent     │          │ Splunk 告警 → Agent → Splunk │
│ AIOps 诊断 → 前端    │    →     │ Dashboard 输出               │
│ (RAG + MCP 工具)     │          │ (CMDB + HEC + Dashboard)     │
└──────────────────────┘          └──────────────────────────────┘
```

### 新增文件（7个）

| 文件 | 作用 | 模仿的已有模式 |
|------|------|---------------|
| `splunk/alert_simulator.py` | 随机告警生成器 | `splunk/test_webhook.py` |
| `app/tools/cmdb_tool.py` | CMDB 查询工具 | `app/tools/knowledge_tool.py` |
| `app/services/splunk_forwarder.py` | 结果写入 Splunk HEC | `app/services/aiops_service.py` 的异步模式 |
| `app/api/v1/splunk.py` | 告警接收端点 | `app/api/v1/aiops.py` |
| `app/skills/definitions/splunk_alert_classify/SKILL.md` | 告警诊断 Skill | `app/skills/definitions/host_resource_diagnosis/SKILL.md` |
| `splunk/splunk_dashboard.xml` | Dashboard 配置 | 无（Splunk 原生格式） |
| `splunk/import_dashboard.py` | Dashboard 导入脚本 | `scripts/ingest_kb_corpus.py` 的独立脚本模式 |

### 修改文件（3个）

| 文件 | 改动 | 依据 |
|------|------|------|
| `app/main.py` | 注册 splunk 路由 | 照搬 `webhook.router` 的注册方式 |
| `app/tools/mcp_loader.py` | 注册 `query_cmdb` 工具 | 照搬 `search_knowledge_base` 的注册方式 |
| `app/tools/meta.py` | 注册 `query_cmdb` 元数据 | 照搬 `search_knowledge_base` 的元数据声明 |

---

## 2. 新增文件逐个拆解

### 2.1 alert_simulator.py

**文件位置：** `splunk/alert_simulator.py`

**加了什么：** 一个独立的 Python 脚本，定时随机生成 6 种运维告警，通过 HTTP POST 推送到 FastAPI 端点。

**为什么加：**
- Splunk 真正的告警需要配置 Saved Search + Alert Action，很复杂
- PoC 阶段需要快速产生告警数据来验证链路
- 模拟器可以产生**可控的、可重复的**测试数据

**模拟的 6 种告警类型：**

| 告警类型 | 严重程度 | 模拟场景 |
|----------|----------|----------|
| `cpu_high` | critical | CPU 使用率 > 90% |
| `memory_high` | high | 内存 > 85% / OOM |
| `disk_full` | high | 磁盘 > 90% / inode 满 |
| `service_500` | high | HTTP 5xx 错误 |
| `network_timeout` | medium | 网络超时 / DNS 异常 |
| `container_down` | critical | Docker 容器退出 |

**每条告警的数据结构（和真实 Splunk Webhook 对齐）：**
```python
{
    "alert_type": "cpu_high",       # 告警分类
    "title": "CPU 使用率过高",       # 人类可读标题
    "severity": "critical",         # 严重程度
    "host_ip": "10.0.1.101",        # 故障 IP
    "description": "CPU 99%...",    # 详细描述
    "timestamp": "2026-...(ISO)",   # ISO8601 时间戳
    "source": "alert_simulator",    # 来源标识
}
```

**模仿对象：**
- `splunk/test_webhook.py` — 都是向 FastAPI 发 HTTP POST 请求
- `splunk/用 Python 打通 Splunk API.py` — 资源池设计（HOST_POOL、SERVICE_POOL 等）借鉴了其中对 Splunk 数据字段的理解

**关键设计决策：**
- 用 `httpx.AsyncClient` 而不是 `requests` — 因为要定时循环推，异步不阻塞
- `timeout=120` — Agent 需要 60-90 秒诊断，10 秒超时不够
- `--interval` 默认 20 秒带 ±50% 随机抖动 — 避免太规律，模拟真实告警的随机性
- `--burst` 参数支持一次推多条 — 模拟"告警风暴"

**代码行数：** ~180 行

---

### 2.2 cmdb_tool.py

**文件位置：** `app/tools/cmdb_tool.py`

**加了什么：** 一个 LangChain `@tool` 装饰的工具函数，提供 CMDB 查询能力。

**为什么加：**
- 公司实际场景中，收到告警后第一件事是查 CMDB：这个 IP 是谁的？什么业务？谁负责？
- 这个信息直接影响**风险等级评估**（核心业务的告警优先级当然高于测试环境）
- 原有项目只有 `search_knowledge_base`（查运维手册），没有"根据 IP 查设备信息"的能力

**工具签名：**
```python
@tool
def query_cmdb(ip: str = "", hostname: str = "") -> str:
    """查询 CMDB 获取设备/IP 的业务信息。用于告警关联和风险评估。"""
```

**模仿对象：**
- `app/tools/knowledge_tool.py` — 结构完全一致：
  - 都用 `@tool` 装饰器
  - 都返回 Markdown 格式的字符串（方便 LLM 阅读）
  - 都有详细的 description 告诉 LLM 什么时候该调这个工具
  - 内部失败都返回友好提示而不是抛异常

**对比：**
```
search_knowledge_base(query) → RAG 检索运维手册 → Markdown 文档片段
query_cmdb(ip)               → 查 Mock CMDB     → Markdown 表格
两个工具对 LLM 来说是一样的调用体验
```

**Mock 数据的设计依据：**
- `10.0.1.101` → 支付网关服务（核心业务）— 对应 `alert_simulator.py` 的 HOST_POOL
- `10.0.1.102` → 支付网关服务（核心业务）
- `10.0.1.103` → 用户中心（重要业务）
- `192.168.1.50` → 库存数据库（重要业务）
- 等等

IP 池和 `alert_simulator.py` 的 HOST_POOL 是**一致的**，保证模拟告警能命中 CMDB。

**替换为真实 CMDB 的方式：**
只需把 `_MOCK_CMDB` 字典替换为 HTTP API 调用，工具签名和对 LLM 的接口完全不变。

**代码行数：** ~90 行

---

### 2.3 splunk_forwarder.py

**文件位置：** `app/services/splunk_forwarder.py`

**加了什么：** 把 Agent 诊断结果异步写入 Splunk HEC（HTTP Event Collector）的服务。

**为什么加：**
- Agent 诊断完了要有地方输出，Dashboard 需要从 Splunk 读数据
- HEC 是 Splunk 官方的数据写入接口，只需一行 JSON POST
- 写入失败不能阻塞诊断响应（fire-and-forget 模式）

**数据转换逻辑（核心）：**

```python
def _format_for_splunk(raw_alert, diagnosis):
    输入:
      raw_alert  = {alert_type, severity, host_ip, description}      # 来自模拟器
      diagnosis  = {risk_level, priority, report, app_name, ...}     # 来自 Agent
    输出:
      Splunk event = {
        alert_type, severity, host_ip,          # 原始告警字段
        risk_level, priority,                   # Agent 评估
        app_name, owner, business_level,        # CMDB 关联
        diagnosis_summary, full_report,         # 诊断结果
        timestamp                                # Splunk 索引时间
      }
```

**风险等级到优先级的映射：**
```python
risk_level 5 → "紧急"
risk_level 4 → "高"
risk_level 3 → "中"
risk_level 1-2 → "低"
```

**模仿对象：**
- `app/services/aiops_service.py:143-147` — `asyncio.create_task()` 异步写入的诊断报告缓存模式
  原代码在诊断完成后 `await chat_memory.append_diagnosis_report()`，我们是 `asyncio.create_task(_safe_forward(...))`
- 同样是 fire-and-forget，不阻塞主响应

**为什么用 HEC 而不是 Splunk REST API：**
- HEC 是专门为数据写入设计的，延迟最低
- 只需一个 token 认证，不需要每次 basic auth
- 自动处理索引、时间戳解析

**代码行数：** ~140 行

---

### 2.4 splunk.py

**文件位置：** `app/api/v1/splunk.py`

**加了什么：** FastAPI 路由，提供 `POST /api/v1/splunk/alert` 端点。

**为什么加：**
- 这是告警进入 Agent 系统的**唯一入口**
- 协调整个流程：接收告警 → 跑 Agent → 提取结果 → 写入 Splunk

**完整流程（一个函数完成所有编排）：**

```python
@router.post("/alert")
async def receive_splunk_alert(request: Request):
    # 1. 解析 JSON body
    payload = await request.json()

    # 2. 跑 Agent 诊断（复用 LangGraph 完整链路）
    diagnosis = await _run_diagnosis(payload)

    # _run_diagnosis 内部做的事:
    #   a. 把告警拼成 query: "收到一条告警, 请诊断: ..."
    #   b. 调 graph.ainvoke({"input": query})
    #   c. 从 response 中提取 risk_level 和 priority
    #   d. 合并 CMDB 数据

    # 3. 异步写入 Splunk（fire-and-forget）
    asyncio.create_task(_safe_forward(payload, diagnosis))

    # 4. 立即返回诊断摘要给调用方
    return ApiResponse.success(data={
        "risk_level": 3,
        "priority": "中",
        "diagnosis_summary": "..."
    })
```

**模仿对象：**
- `app/api/v1/aiops.py` — 结构完全照搬：
  ```python
  # 原版 aiops.py
  router = APIRouter(prefix="/aiops", tags=["aiops"])
  @router.post("/diagnose")
  async def aiops_diagnose(req: DiagnosisRequest) -> EventSourceResponse:
      # ...调 aiops_service.stream_diagnose()

  # 新版 splunk.py
  router = APIRouter(prefix="/splunk", tags=["splunk"])
  @router.post("/alert")
  async def receive_splunk_alert(request: Request) -> ApiResponse:
      # ...调 _run_diagnosis()
  ```
- `app/services/aiops_service.py:88-101` — `graph.ainvoke()` 的调用方式完全一致
- `app/services/aiops_service.py:143-147` — `asyncio.create_task()` 异步写入模式

**为什么用 `Request` 而不是 Pydantic Model：**
- 告警 JSON 格式灵活（Splunk、Prometheus、自定义系统格式不同）
- PoC 阶段不需要严格校验，够用即可
- 生产环境可以替换为 Pydantic Model 做参数校验

**代码行数：** ~140 行

---

### 2.5 SKILL.md

**文件位置：** `app/skills/definitions/splunk_alert_classify/SKILL.md`

**加了什么：** 一个专用于"通用告警分类诊断"的 Skill 定义文件。

**为什么加：**
- 原有 4 个 Skill 是针对具体故障域的（主机/网络/容器），没有一个"通用告警处理"的 Skill
- Splunk 来的告警类型多样（CPU/内存/磁盘/5xx/网络/容器），需要一个能覆盖所有这些的 Skill
- Skill 的 `allowed_tools` 白名单需要包含 `query_cmdb`（新增工具）

**SKILL.md 的结构：**

```
┌──────────────────────────────────────────┐
│ YAML Frontmatter                         │
│ ─────────────                            │
│ name: splunk_alert_classify             │  ← 被 Router 匹配用
│ display_name: Splunk 告警分类诊断         │
│ description: ...                         │  ← Router 判断选哪个 Skill
│ triggers: [告警, alert, cpu_high, ...]   │  ← 触发关键字
│ allowed_tools:                           │  ← ★ 关键是加了 query_cmdb
│   - search_knowledge_base                │
│   - query_cmdb            ← 新增!        │
│   - get_current_time                     │
│   - get_local_system_overview            │
│   - ...                                  │
│ risk_level: low                          │
├──────────────────────────────────────────┤
│ Markdown Body (Playbook)                  │
│ ─────────────                            │
│ Phase 1: 解析告警信息                     │
│ Phase 2: 查 CMDB 确定业务归属 (必须)       │  ← 强制 Agent 先查 CMDB
│ Phase 3: 查知识库匹配 SOP                 │
│ Phase 4: 风险评估 (1-5级)                 │  ← 明确定义评估矩阵
│ Phase 5: 输出报告格式                     │
└──────────────────────────────────────────┘
```

**模仿对象：**
- `app/skills/definitions/host_resource_diagnosis/SKILL.md` — 结构完全一致：
  - 同样的 YAML frontmatter 字段（name / display_name / description / triggers / allowed_tools / risk_level）
  - 同样的 Markdown body 结构（适用场景 → Phase 1/2/3 → 输出格式 → 注意事项）
  - 同样的工具白名单设计（只列本 Skill 需要的工具）

**风险评估矩阵（给 LLM 的指引）：**
```
风险等级 = 告警严重程度 + 业务等级 + 故障域 + SOP建议

严重程度:  critical=5, high=4, medium=3, low=2
业务等级:  核心=+1, 重要=+0, 一般=-1
最终:
  5级(紧急): 核心业务 + critical 告警
  4级(高):   核心业务 + high 告警
  3级(中):   一般业务 + high / 重要业务 + medium
  2级(低):   一般业务 + medium
  1级(忽略): 测试环境 / 已知问题
```

**为什么不用 Pydantic 硬编码而是在 Markdown 里写指引：**
- 这是这个项目 Skill 系统的核心设计理念 — **给 LLM 看的知识，放在 Markdown 里比放在代码里更灵活**
- 改风险评估规则 = 改 SKILL.md 文件 = 重启生效，不需要改 Python 代码

**代码行数：** ~130 行

---

### 2.6 splunk_dashboard.xml

**文件位置：** `splunk/splunk_dashboard.xml`

**加了什么：** Splunk Dashboard 的 XML 配置，定义 8 个可视化面板。

**为什么加：**
- Splunk 的 Dashboard 是通过 XML 配置的（Splunk Simple XML 格式）
- 直接在 UI 里拖拽创建也可以，但 XML 导入更快、可版本管理、可复用

**8 个面板的设计逻辑：**

```
第一行 (概览统计):  数字卡片 ×4
  ① 告警总数                        → | stats count
  ② 紧急告警 (risk_level>=4)        → | search risk_level>=4 | stats count
  ③ 受影响应用数                     → | stats dc(app_name)
  ④ 平均风险等级                     → | stats avg(risk_level)

第二行 (分布饼图):  饼图 ×2
  ⑤ 告警类型分布                    → | stats count by alert_type → pie
  ⑥ 优先级分布                      → | stats count by priority → pie

第三行 (趋势折线):  折线图 ×1
  ⑦ 告警趋势 (每5分钟)             → | timechart span=5m count by alert_type → line

第四行 (分析图):  折线图 + 柱状图 ×2
  ⑧ 风险等级趋势                    → | timechart span=5m avg(risk_level) → line
  ⑨ 受影响应用 Top 10              → | stats count by app_name | head 10 → column

第五行 (数据表):  表格 ×2
  ⑩ 优先级处理队列 (按risk_level排序) → | table ... | sort risk_level desc
  ⑪ 诊断报告详情 (最近20条)          → | table ... | sort timestamp desc
```

**每个面板的 SPL 查询为何这样写：**
- 所有查询都从 `index=aiops_results sourcetype=_json` 取数据
- 字段名和 `splunk_forwarder.py` 中 `_format_for_splunk()` 输出的字段**严格一致**
- 例如 Dashboard 引用 `risk_level`、`priority`、`app_name`、`alert_type`，这些字段正是 forwarder 写入的字段名

**代码行数：** ~150 行

---

### 2.7 import_dashboard.py

**文件位置：** `splunk/import_dashboard.py`

**加了什么：** 用 Splunk REST API 一键导入 Dashboard XML 的脚本。

**为什么加：**
- Splunk Dashboard 导入需要手动操作 UI（设置→视图→新建→粘贴XML→保存），步骤多
- 自动化导入方便 CI/CD、方便重置环境

**模仿对象：**
- `scripts/ingest_kb_corpus.py` — 都是独立脚本模式：
  - 都有 `if __name__ == "__main__"` 入口
  - 都连接外部服务（Milvus / Splunk API）
  - 失败都有明确的错误提示

**代码行数：** ~50 行

---

## 3. 修改文件逐个拆解

### 3.1 main.py

**修改位置：** `app/main.py:29` 和 `app/main.py:149`

**改了什么：**
```python
# 第 29 行: 导入
- from app.api.v1 import aiops, chat, documents, health, skills, webhook
+ from app.api.v1 import aiops, chat, documents, health, skills, splunk, webhook

# 第 149 行: 注册路由
+ app.include_router(splunk.router, prefix=API_PREFIX)
```

**为什么这样改：**
- 完全模仿 `webhook.router` 的注册方式
- `webhook.router` 也是后加的，它注册的是 `POST /api/v1/webhook/alertmanager`
- 我们的 `splunk.router` 注册的是 `POST /api/v1/splunk/alert`
- 两者结构完全一致：`APIRouter(prefix="/xxx")` → `app.include_router(xxx.router, prefix="/api/v1")`

**不需要改其他地方：**
- 不需要改 docker-compose
- 不需要改 requirements.txt
- 不需要改 .env（Splunk 配置硬编码在 forwarder 中，PoC 阶段够了）

---

### 3.2 mcp_loader.py

**修改位置：** `app/tools/mcp_loader.py:25` 和 `app/tools/mcp_loader.py:36-43`

**改了什么：**
```python
# 新增导入
+ from app.tools.cmdb_tool import query_cmdb

# get_local_tools() 返回值新增一个工具
  return [
      search_knowledge_base,
      get_current_time,
      ...
      list_top_processes,
+     query_cmdb,                          # ← 新增
  ]
```

**为什么这样改（关键！）：**
- `get_all_tools()` 是 Agent 获取所有可用工具的唯一入口
- 你加一个工具，只需要在 `get_local_tools()` 的列表里加一行
- Agent、Skill 白名单过滤、并行编排全部自动生效，不需要额外配置
- 这意味着 **新增工具的成本 = 1 个文件（工具本体）+ 1 行注册代码 + 1 条元数据注册**

**模仿对象：**
- `search_knowledge_base` 的注册方式 — 同样在 import 中添加，在 return 列表中添加
- `time_tool.get_current_time` 也是同样的模式

**工具发现到调用的完整链路（新增 query_cmdb 自动走通）：**
```
get_all_tools() → 去重 → filter_tools_for_skill() → bind_tools() → LLM 看到 → LLM 调用 → tool.ainvoke()
```

---

### 3.3 meta.py

**修改位置：** `app/tools/meta.py:115-121`

**改了什么：**
```python
TOOL_META = {
    "search_knowledge_base": ToolMeta(...),
+   "query_cmdb": ToolMeta(               # ← 新增
+       read_only=True,                    # 只读查询
+       concurrency_safe=True,             # 可并发
+       max_result_chars=2000,             # CMDB 返回短，截断阈值低
+       risk_level="low",                  # 无副作用，低风险
+       search_hint="cmdb device ip ...",  # 工具发现关键词
+   ),
    "get_current_time": ToolMeta(...),
}
```

**为什么必须加（如果不加会怎样）：**
- `ToolMeta` 有 "fail-closed" 设计：未登记的工具默认 `read_only=False, concurrency_safe=False`
- 如果不登记：
  - `read_only=False` → READ_ONLY 模式下会被拒绝
  - `concurrency_safe=False` → 只能串行执行，不能和其他工具并行 gather
  - ASK_DESTRUCTIVE 模式下会被要求人工审批
- **登记后正确标记为只读+可并发 → 可以和其他只读工具（如 search_knowledge_base）并行执行**

**模仿对象：**
- `search_knowledge_base` 的 ToolMeta 声明 — 同样都是只读、可并发、低风险
- 元数据字段含义: 参考 `app/tools/meta.py:32-98` 中 ToolMeta 类的注释

**`search_hint` 字段的作用：**
- 给未来 ToolSearch 功能用的（类似 cc-haha 的二级工具发现）
- PoC 阶段不影响，但按规范填了

---

## 4. 架构全景图

```
                        ┌──────────────────────────────┐
                        │      SPLUNK (Docker)          │
                        │  Web :8001   API :8089        │
                        │  HEC :8088                    │
                        │                              │
                        │  ┌────────────────────────┐  │
                        │  │ Dashboard (XML import)  │  │
                        │  │ aiops_overview          │  │
                        │  │ - 优先级列表             │  │
                        │  │ - 告警饼图 + 趋势折线    │  │
                        │  │ - 受影响应用柱状图        │  │
                        │  │ - 诊断详情表              │  │
                        │  └──────────┬─────────────┘  │
                        │             │ read index     │
                        │  ┌──────────▼─────────────┐  │
                        │  │ index=aiops_results     │  │
                        │  │ (HEC 写入)              │  │
                        │  └─────────────────────────┘  │
                        └──────────┬───────────────────┘
                                   │ HEC POST (fire & forget)
                                   │
┌──────────────────────────────────┼──────────────────────────────────┐
│                      FastAPI (:9900)                                 │
│                                                                     │
│  ┌──────────────────────────┐    ┌───────────────────────────────┐ │
│  │ alert_simulator.py       │    │ splunk_forwarder.py            │ │
│  │ (独立脚本)                │    │ (异步写入 Splunk)              │ │
│  │ 随机生成6种告警           │    │                               │ │
│  │ ──POST──►                │    │ ◄── diagnosis result ──       │ │
│  └──────────────────────────┘    └───────────────────────────────┘ │
│              │                                  ▲                   │
│              ▼                                  │                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  POST /api/v1/splunk/alert  (app/api/v1/splunk.py)            │ │
│  │                                                                │ │
│  │  await request.json() → payload                                │ │
│  │       │                                                        │ │
│  │       ▼                                                        │ │
│  │  _run_diagnosis(payload)                                       │ │
│  │       │                                                        │ │
│  │       ├──► graph.ainvoke({"input": query})  ← 复用 LangGraph   │ │
│  │       │       │                                                │ │
│  │       │       ├── skill_router → splunk_alert_classify Skill  │ │
│  │       │       ├── planner → 基于 Playbook 制定诊断步骤          │ │
│  │       │       ├── executor → 调 query_cmdb + search_knowledge  │ │
│  │       │       └── replanner → 输出 risk_level + report         │ │
│  │       │                                                        │ │
│  │       ▼                                                        │ │
│  │  _parse_diagnosis_report(report) → {risk_level, priority}      │ │
│  │  asyncio.create_task(forward_to_splunk(...))  ← 异步写Splunk   │ │
│  │  return ApiResponse.success({risk_level, priority, ...})       │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  工具层                                                         │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │ │
│  │  │search_knowledge│  │  query_cmdb    │  │ get_local_*    │  │ │
│  │  │_base (已有)    │  │  (新增 ★)       │  │ (已有)         │  │ │
│  │  │ RAG 查运维手册  │  │  查CMDB设备信息 │  │  psutil 采集   │  │ │
│  │  └────────────────┘  └────────────────┘  └────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. 关键设计决策 Q&A

### Q1: 为什么 Splunk 配置值（token、URL）直接硬编码而不是放 .env？

**答：** PoC 阶段为了快速跑通。生产环境应该放到 .env：
```env
SPLUNK_HEC_URL=https://localhost:8088/services/collector
SPLUNK_HEC_TOKEN=09b8d03c-af42-4b25-9af6-174fa10f3ded
SPLUNK_INDEX=aiops_results
```
然后 `splunk_forwarder.py` 从 `settings` 读取。这个参考项目已有模式：`app/config.py:157-168` 就是 MCP server URL 的配置方式。

### Q2: 为什么 CMDB 用 Mock 数据而不是接真实 API？

**答：** 分层替换策略：
- `_MOCK_CMDB` 是一个 Python 字典，函数接口是 `query_cmdb(ip) → str`
- 替换时只需把函数体改为 `httpx.get("http://cmdb.internal/api/device", params={"ip": ip})`
- Agent 和 Skill 完全不需要改动 — 它们只知道"有个工具叫 query_cmdb"

### Q3: 为什么 Skill 定义了 5 个 Phase 而不是简单的几句话？

**答：** 这就是这个项目 Skill-first 设计的精髓。LLM 需要**具体的操作指引**才能稳定产出高质量诊断。对比：

```
弱指引: "收到告警后查CMDB和知识库给出诊断"  → LLM 可能跳过 CMDB、风险等级乱打
强指引: Phase 1→2→3→4→5 分步明确           → LLM 按步骤走，输出格式稳定
```

### Q4: 为什么 `_run_diagnosis()` 不用 SSE 流式而是 `graph.ainvoke()`？

**答：** PoC 阶段简化。SSE 流式需要前端消费（如原项目的 `handleAiopsEvent()`），而 Splunk 告警是机器调用的，不需要打字机效果。`graph.ainvoke()` 一次返回完整结果，代码更简单。生产环境如果要看到实时诊断过程，改用 `graph.astream()` 即可。

### Q5: 同样加一个工具，为什么改了 3 个文件（cmdb_tool.py + mcp_loader.py + meta.py）？

**答：** 这 3 个文件对应 3 层：

| 文件 | 注册了什么 | 不注册会怎样 |
|------|-----------|-------------|
| `cmdb_tool.py` | 工具函数本体 | 没有工具可用 |
| `mcp_loader.py` | 工具加入 Agent 可用列表 | Agent 看不到这个工具 |
| `meta.py` | 工具的**安全元数据** | 默认 read_only=False → 不能并行、被权限拦截 |

这是这个项目的规范：**新增一个工具 = 函数 + 注册 + 元数据，三步缺一不可**。参考 `search_knowledge_base` 的注册方式完全一致。

### Q6: 告警诊断结果为什么同时返回 HTTP 响应 + 写入 Splunk？

**答：** 双通道：
- **HTTP 响应** → 给调用方（模拟器）立即确认
- **Splunk HEC** → 给 Dashboard 持久化存储

这模仿了原项目中 `aiops_service.py` 的设计——返回 SSE 流的同时，异步把报告写入 Redis 缓存（用于后续 RAG Chat 查询）。

---

## 总结：学完这个 PoC 你应该掌握的设计模式

| 模式 | 在哪个文件体现 | 怎么复用 |
|------|---------------|---------|
| **@tool 装饰器** | cmdb_tool.py | 新增任何 LLM 可调用的工具 |
| **SKILL.md 双层结构** | splunk_alert_classify/SKILL.md | 新增任何故障处理剧本 |
| **APIRouter 路由注册** | splunk.py + main.py | 新增任何 API 端点 |
| **ToolMeta 安全注册** | meta.py | 确保工具的安全语义正确 |
| **Fire-and-forget 异步写入** | splunk_forwarder.py | 任何"不阻塞响应"的后台写入 |
| **独立脚本 + 自动导入** | alert_simulator.py / import_dashboard.py | CI/CD 自动化 |
| **Mock → 真实 API 分层替换** | cmdb_tool.py 的 _MOCK_CMDB | 渐进式开发 |

---

> 文档生成时间: 2026-06-03
> 项目: mutil-rag-agent-main + Splunk PoC
