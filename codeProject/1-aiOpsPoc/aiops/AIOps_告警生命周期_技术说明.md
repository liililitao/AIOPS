# AIOps 告警处理全生命周期技术说明

本文描述当前 AIOps 系统从 Splunk 页面点击跳转，到告警接入、LangGraph 编排分析、报告生成、归档与知识回灌的完整技术生命周期。

## 1. 总体链路

```text
Splunk Dashboard 点击跳转
  → Splunk 生成短时 HMAC 签名 URL
  → Flask Gateway 验签、角色校验、nonce 防重放
  → JWT Cookie + 302 清洗跳转
  → AIOps Web 前端 / FastAPI API
  → Splunk 告警同步或本地告警输入
  → 风险初判 + Router LLM 分类库比对
  → 命中：复用报告和建议
  → 未命中：LangGraph Tool-calling Agent
  → 历史案例 / 知识库+CMDB / 受控 Splunk 日志调查
  → 结构化证据研判、报告和处置建议
  → JSON/SQLite/Milvus 归档
  → 分类模板与历史案例向量回灌
  → 下一次告警快速复用或检索
```

## 2. 阶段一：Splunk 跳转与安全身份交接

### 2.1 用户操作起点

用户登录 Splunk Dashboard 后，点击“跳转 AIOps”按钮。Dashboard 不直接把用户名拼接进 URL，而是使用后台生成的短时签名链接。

### 2.2 Splunk 生成签名 URL

Splunk 自定义搜索命令 `aiopssignurl` 负责生成跳转 URL。它通过 Splunk REST API 的 `current-context` 接口获取当前真实用户和角色，然后生成如下字段：

- `v`：交接协议版本；
- `user`：当前 Splunk 用户；
- `roles`：当前 Splunk 角色集合；
- `exp`：过期时间；
- `nonce`：一次性随机数；
- `sig`：HMAC-SHA256 签名。

Dashboard 可周期性刷新该 URL；部署配置中通常将其有效期设置为约 90 秒。

涉及技术：Splunk Simple XML Dashboard、Splunk Custom Search Command、Python、Splunk REST API、HMAC-SHA256、随机 nonce。

### 2.3 Flask Gateway 校验与内部会话

用户访问签名 URL 后，Flask Gateway（默认端口 `5000`）执行以下安全校验：

1. 检查参数是否完整。
2. 检查 HMAC 签名是否与共享密钥一致。
3. 检查 URL 是否过期、TTL 是否超过网关允许范围。
4. 在 SQLite nonce 库中检查该随机数是否已被使用，阻止重放攻击。
5. 检查用户角色是否符合 `AIOPS_ALLOWED_ROLES` 白名单。
6. 校验通过后，使用独立 JWT 密钥生成 HS256 会话令牌。
7. 将 JWT 写入 `HttpOnly`、`SameSite=Lax` Cookie。
8. 返回 HTTP 302 到干净的 `/app/`，去除地址栏中的签名参数。

涉及技术：Flask、PyJWT、SQLite、HMAC-SHA256、HTTP Cookie、RBAC、HTTP 302。

## 3. 阶段二：前端、网关与后端服务

### 3.1 前端初始化

进入 `/app/` 后，浏览器加载 AIOps 前端。前端使用 HTML、CSS 与原生 JavaScript，通过 `fetch` 调用后端 API。初始化时会先读取当前会话信息，根据用户角色决定可访问的菜单和管理功能。

主要 API 包括：

- `GET /api/v1/session`：当前用户与角色；
- `GET /api/v1/alerts`：告警列表；
- `POST /api/v1/alerts/sync`：从 Splunk 同步告警；
- `POST /api/v1/alerts/{id}/analyze`：启动告警分析；
- `POST /api/v1/chat`：当前告警问答；
- `POST /api/v1/kb-chat`：知识库 RAG 问答；
- `POST /api/v1/scheduler/scan`：立即扫描待处理告警。

### 3.2 FastAPI 服务职责

FastAPI 服务（默认端口 `8001`）负责告警 API、Pydantic 参数校验、认证中间件、定时任务、文档管理、知识库问答及 AI 分析调度。

涉及技术：FastAPI、Uvicorn、Pydantic、CORS Middleware、APScheduler、Python asyncio。

## 4. 阶段三：告警接入与标准化

告警可以来自三类入口：

1. Splunk 实时或手动同步；
2. 上传 JSON 告警；
3. 应用模拟器生成的模拟告警。

### 4.1 Splunk 告警同步

同步服务使用 `httpx.AsyncClient` 调用 Splunk 导出搜索接口：

```text
/services/search/jobs/export
```

返回内容以 JSON Line 形式流式读取。系统会合并普通字段和 `_raw` 中的 JSON 字段，统一提取告警名称、应用编码、时间、主机、请求 URI、动作、告警次数、风险等级和查询信息。

系统使用 `_cd`、`_time`、告警名称、主机及原始内容构造 SHA-256 指纹，生成稳定的 `alert_id`。标准化后的对象以 `RawAlert` Pydantic 模型进入后续流程，并写入本地 JSON 缓存。

涉及技术：httpx、asyncio、JSON Lines、SHA-256、Pydantic、JSON 文件归档。

## 5. 阶段四：本地预处理与风险初判

每条告警首先进入确定性的本地预处理，不依赖模型。

### 5.1 风险计算

`risk_assessor.py` 根据以下维度评估初步风险：

- 资产环境：生产、非生产或未知；
- 告警次数及频率；
- 请求 URI 对应攻击类型和最高风险等级。

`attack_classifier.py` 识别 URI 中反映的攻击或异常类型，例如注入、路径探测、扫描等。

### 5.2 告警分类签名

系统生成可审计的分类签名，主要字段为：

- `alert_name`；
- `trigger_reason`；
- `search_terms`；
- `operator_notes`；
- `hostname`；
- `request_uri`；
- `action`。

这些字段用于后续分类库语义比对。

## 6. 阶段五：LangGraph 顶层分类编排

顶层 `AlertProcessingGraph` 将告警处理分为两条固定分支：

```text
START → classify
  ├─ classification hit  → reuse  → END
  └─ miss / unavailable → analyze → END
```

### 6.1 分类候选的硬性边界

进入模型比对前，系统只保留同时满足以下条件的模板候选：

- 相同应用编码；
- 相同告警名称；
- 相同风险等级；
- 具备完整分类签名、分析报告和处理建议。

因此，模型不会跨应用或跨风险等级复用处置结论。

### 6.2 Router LLM 语义比对

Router 模型对新告警签名与候选模板进行语义比对。模型只能返回：

```text
sample_id:模板ID,score:分数
```

或：

```text
no_match
```

当前模型通过 OpenAI-compatible API 调用：

- 包：`langchain-openai`；
- 类：`ChatOpenAI`；
- 配置：`ROUTER_MODEL`；
- 当前默认模型：`openai_gpt5`；
- 默认阈值：`SEMANTIC_MATCH_THRESHOLD=85`。

调用使用指数退避重试、超时控制，并记录输入/输出 Token。

### 6.3 分类命中分支

当得分达到阈值时：

1. 直接复用分类库中的历史报告和处理建议；
2. 重新计算当前告警的风险，不复用旧风险；
3. 不调用 Agent、历史检索、知识库检索和 Splunk 调查；
4. 更新分类模板命中次数和最近命中时间；
5. 归档本次增强告警。

分类库保存在 `data/alert_classifications.json`，通过临时文件替换实现尽量安全的原子写入。

## 7. 阶段六：LangGraph Tool-calling Agent

当分类未命中、模型超时或输出不合规时，顶层图进入 `AlertAnalysisAgent`。

### 7.1 Agent 图结构

```text
START → agent_model
          ├─ 模型要求 Tool → ToolNode → collect_evidence → agent_model
          ├─ 无 Tool 调用    → finalize_analysis
          └─ 超过最大步数    → degraded_analysis

finalize_analysis → validate_agent_output
  ├─ 校验通过           → END
  ├─ 首次校验失败       → finalize_analysis（一次修复）
  └─ 仍失败             → degraded_analysis → END
```

### 7.2 模型与调用约束

Agent 使用 `EXECUTOR_MODEL`，当前默认是 `openai_gpt5`。模型通过 LangGraph `ToolNode` 按需调用已注册 Tool，而非旧实现中“每条告警固定顺序调用三个 Tool”。

系统配置：

- `MAX_AGENT_STEPS=7`：模型与 Tool 循环最大步数；
- `AGENT_OUTPUT_REPAIR_LIMIT=1`：结构化输出最多修复一次；
- `AGENT_CHECKPOINT_ENABLED=true`：默认启用断点恢复；
- `AGENT_CHECKPOINT_DB=data/agent_checkpoints.sqlite3`：checkpoint SQLite 数据库；
- `AGENT_TIMEOUT_SECONDS=300`：Agent 超时配置。

### 7.3 受控 Tool 集合

模型只可使用以下三个 Tool：

1. `search_historical_alerts`
   - 查询历史相似告警；
   - 对当前告警摘要生成 Embedding；
   - 在 Milvus 的 `historical_alerts` 集合中执行余弦相似度 Top-K 检索；
   - 返回历史案例、历史分析和历史建议。

2. `search_knowledge_base`
   - 检索 SOP、运维文档和知识库片段；
   - 查询 CMDB 资产事实，包括环境、应用、主机、负责人等；
   - CMDB 支持 Excel、CSV、Splunk CSV 和未来 API 扩展。

3. `investigate_splunk_logs`
   - 查询当前告警的受控 Splunk 日志证据；
   - Tool 入参不允许携带任意 SPL、索引名或告警 ID；
   - 当前告警 ID 从服务器 `AlertToolContext` 注入，模型不能伪造身份；
   - SPL 使用固定只读模板、命令白名单、时间窗和返回量预算。

### 7.4 Tool 运行时安全上下文

每次 Agent 运行创建不可变的 `AlertToolContext`：

- `alert_id`；
- `run_id`；
- `actor_id`；
- 可选 Splunk 服务实例。

该上下文只由服务端注入，不暴露给模型的 Tool 参数 Schema。这样可以阻止模型通过修改 Tool 参数访问其他告警或执行非预期查询。

涉及技术：LangGraph、LangChain Tool、ToolNode、ToolRuntime、Python dataclass、Pydantic。

## 8. 阶段七：结构化证据研判与输出校验

Agent 最终不直接把自由文本当作可信结论，而是要求模型按 `AgentAnalysis` Pydantic Schema 输出结构化结果。

结构包括：

- `conclusion`：研判结论；
- `hypotheses`：根因假设与置信度；
- `impact`：影响评估；
- `actions`：按优先级排列的建议；
- `validation_steps`：验证步骤；
- `evidence_refs`：证据引用；
- `evidence_gaps`：证据缺口；
- `confidence`：总体置信度。

校验逻辑包括：

1. Pydantic 类型、字段完整性和额外字段校验；
2. `evidence_refs` 必须能在 Tool 返回结果中定位；
3. Tool 调用失败时，结果必须在 `evidence_gaps` 明确说明对应缺口；
4. 首次不通过时，让模型只修复校验错误；
5. 修复仍失败时生成低置信度降级结论，避免输出无法验证的内容。

通过校验后，结构化结果被确定性渲染为兼容前端的 Markdown 分析内容。

## 9. 阶段八：报告、建议与最终风险

Agent 取得的证据与结构化研判会进入报告生成流程。

1. 根据 CMDB 环境、告警次数、攻击类型重新计算最终风险。
2. `REPORT_MODEL` 生成分析报告。
3. `REPORT_MODEL` 生成处置建议。
4. 记录 Router、Agent、报告、建议等阶段的 Token 用量。
5. 将最终风险、报告、建议和 Agent 运行信息写入增强告警。

当前默认模型配置：

```text
ROUTER_MODEL=openai_gpt5
PLANNER_MODEL=openai_gpt5
EXECUTOR_MODEL=openai_gpt5
REPORT_MODEL=openai_gpt5
RAG_CHAT_MODEL=openai_gpt5
```

## 10. 阶段九：断点恢复与运行注册

LangGraph checkpoint 使用 SQLite 保存图状态。系统还使用 `AgentRunRegistry` 建立告警与运行 ID 的映射。

处理规则：

1. 对同一条尚未完成的告警，重试时复用稳定 `run_id` 和 LangGraph `thread_id`；
2. 已有正式输出后用户主动再次分析，创建新的 `run_id`；
3. 通过 checkpoint 恢复图状态，避免重复创建独立的分析线程；
4. 若 checkpoint 或模型不可用，Agent 降级为可审计的低置信度结论。

涉及技术：`langgraph-checkpoint-sqlite`、`aiosqlite`、SQLite。

## 11. 阶段十：持久化、审计与归档

处理过程中会保存以下数据：

- 原始告警：`data/alerts`；
- Splunk 同步缓存：`data/splunk_alerts.json`；
- 增强告警：`output/alerts`；
- 分析报告：`output/reports`；
- 处理建议：`output/suggestions`；
- Agent 运行记录：`output/agent_runs`；
- 历史案例：`historical_alerts`；
- 分类模板库：`data/alert_classifications.json`；
- 已处理索引：`data/processed_alerts.json`；
- Agent checkpoint：`data/agent_checkpoints.sqlite3`；
- HMAC nonce：`data/handoff_nonces.sqlite3`。

Agent 运行记录可包含 run ID、thread ID、调用步骤、Tool 结果、错误码、结构化分析状态、降级原因和 Token 用量，便于审计与复盘。

## 12. 阶段十一：Milvus、Embedding 与知识回灌

### 12.1 向量化

文本通过 Embedding 服务转换为向量，默认配置：

```text
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

也可以切换到 Ollama 本地 Embedding，例如 `bge-m3`。

### 12.2 向量存储与检索

系统使用 Milvus 或 Milvus Lite：

- SOP/知识库集合：`sop_knowledge`；
- 历史案例集合：`historical_alerts`；
- 检索度量：COSINE；
- 索引：IVF_FLAT；
- 本地开发环境可回退到 Milvus Lite。

### 12.3 闭环回灌

每次完整分析后：

1. 新报告和建议进入分类库，供 Router 模型后续复用；
2. 历史案例写入向量索引，供后续 Agent 检索；
3. 专家可在前端补充备注和处置经验；
4. 文档管理模块可上传新的 SOP，重新分块并建立向量索引；
5. 后续告警因此具备更多模板和历史证据。

## 13. 阶段十二：前端展示与问答

前端为用户提供：

- 告警列表与风险过滤；
- 告警详情；
- AI 分析报告；
- 处理建议；
- 当前告警 AI 问答；
- 知识库 RAG 问答；
- 调度和配置管理。

知识库问答流程为：问题 Embedding → Milvus Top-K 检索 → 检索结果作为上下文 → `RAG_CHAT_MODEL` 流式回答 → 前端展示参考来源。

## 14. 关键技术与依赖清单

| 能力 | 技术/组件 |
| --- | --- |
| Splunk 跳转 | Splunk Dashboard、Custom Search Command、REST API |
| 身份交接 | HMAC-SHA256、nonce、TTL、角色白名单 |
| 内部会话 | Flask、PyJWT、HS256、HttpOnly Cookie、SQLite |
| API 服务 | FastAPI、Uvicorn、Pydantic、CORS |
| 调度 | APScheduler |
| LLM 调用 | OpenAI-compatible API、LangChain、langchain-openai、ChatOpenAI |
| 流程编排 | LangGraph、StateGraph、ToolNode、ToolRuntime |
| 结构化输出 | Pydantic、Schema 校验、证据引用校验、一次修复、降级输出 |
| 断点恢复 | langgraph-checkpoint-sqlite、aiosqlite、SQLite |
| 外部 HTTP | httpx、requests |
| 告警/文档存储 | JSON、SQLite、文件系统 |
| CMDB | Excel/openpyxl、CSV、Splunk CSV、API 扩展 |
| 向量检索 | pymilvus、Milvus、Milvus Lite、COSINE、IVF_FLAT |
| Embedding | text-embedding-3-small；可选 Ollama/bge-m3 |
| 安全与审计 | HMAC、JWT、SHA-256、RBAC、只读 SPL 白名单、运行记录、Token 统计 |

## 15. 最终闭环

```text
安全跳转
  → 告警同步
  → 风险初判
  → 分类库语义复用
  → LangGraph 按需调查
  → 结构化校验
  → 报告与建议
  → 专家确认
  → 分类模板、历史案例、知识库回灌
  → 下一次告警更快、更可审计地处置
```
