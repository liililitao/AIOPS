"""LangGraph Tool-calling Agent 的本地契约测试。"""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.alert_analysis_graph import create_alert_analysis_graph
from app.agents.alert_analysis_agent import AlertAnalysisAgent, resolve_agent_run_id
from app.core.alert_tool_runtime import AlertToolContext
from app.schemas.alert import AlertResult, RawAlert
from app.schemas.agent_analysis import (
    AgentAnalysis,
    EvidenceReference,
    RecommendedAction,
    RootCauseHypothesis,
)
from app.services.agent_run_registry import AgentRunRegistry
from app.tools import ALERT_ANALYSIS_TOOLS
from app.tools.splunk_log_tool import investigate_splunk_logs


class QueuedToolModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.bound_tool_names = []
        self.calls = 0

    def bind_tools(self, tools):
        self.bound_tool_names = [item.name for item in tools]
        return self

    async def ainvoke(self, messages):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class StructuredQueuedToolModel(QueuedToolModel):
    def __init__(self, responses, structured_responses):
        super().__init__(responses)
        self.structured_responses = list(structured_responses)
        self.structured_calls = 0

    def with_structured_output(self, schema):
        owner = self

        class StructuredInvoker:
            async def ainvoke(self, messages):
                owner.structured_calls += 1
                response = owner.structured_responses.pop(0)
                if isinstance(response, Exception):
                    raise response
                return response

        return StructuredInvoker()


def _valid_analysis(**overrides):
    values = {
        "conclusion": "当前请求已被 WAF 阻断，仍需确认是否存在绕过尝试。",
        "hypotheses": [RootCauseHypothesis(
            hypothesis="自动化扫描",
            rationale="请求路径具有探测特征。",
            confidence="中",
        )],
        "impact": "暂未发现已成功利用的证据。",
        "actions": [RecommendedAction(
            priority="中",
            action="核对同源后续请求。",
            rationale="用于确认扫描是否持续。",
            requires_approval=False,
        )],
        "validation_steps": ["复核相关 WAF 日志"],
        "evidence_refs": [],
        "evidence_gaps": ["尚未查询当前 Splunk 日志"],
        "confidence": "中",
    }
    values.update(overrides)
    return AgentAnalysis(**values)


@tool
def sample_history(query: str) -> str:
    """Return historical evidence for a query."""
    return json.dumps(
        {"success": True, "results": [{"case_id": "h-1", "query": query}]},
        ensure_ascii=False,
    )


@tool
def forbidden_knowledge(query: str) -> str:
    """Fail if the model did not request this tool explicitly."""
    raise AssertionError(f"unrequested tool executed: {query}")


@tool
def failing_history(query: str) -> str:
    """Raise a controlled error for ToolNode failure handling tests."""
    raise RuntimeError(f"history unavailable: {query}")


@tool
def search_historical_alerts(query: str, top_k: int = 3) -> str:
    """Return historical alert evidence."""
    return json.dumps(
        {"success": True, "results": [{"case_id": "history-1"}]},
        ensure_ascii=False,
    )


def test_alert_analysis_registry_contains_exactly_three_tools():
    assert [item.name for item in ALERT_ANALYSIS_TOOLS] == [
        "search_historical_alerts",
        "search_knowledge_base",
        "investigate_splunk_logs",
    ]
    assert "cmdb_lookup" not in {item.name for item in ALERT_ANALYSIS_TOOLS}


def test_splunk_tool_hides_trusted_alert_identity_from_model_schema():
    properties = investigate_splunk_logs.tool_call_schema.model_json_schema()[
        "properties"
    ]

    assert set(properties) == {"investigations", "window_minutes"}
    assert "alert_id" not in properties


@pytest.mark.asyncio
async def test_splunk_tool_receives_alert_identity_from_runtime_context():
    class RecordingSplunkService:
        def __init__(self):
            self.requests = []

        async def investigate(self, request):
            self.requests.append(request)
            return {
                "success": True,
                "alert_id": request.alert_id,
                "evidence_type": "splunk_log",
                "evidence": [],
                "warnings": [],
                "error_code": None,
                "truncated": False,
            }

    service = RecordingSplunkService()
    model = QueuedToolModel([
        AIMessage(
            content="",
            tool_calls=[{
                "name": "investigate_splunk_logs",
                "args": {
                    "investigations": ["temporal_pattern"],
                    "window_minutes": 15,
                },
                "id": "splunk-call",
                "type": "tool_call",
            }],
        ),
        AIMessage(content="Splunk 调查完成"),
    ])
    graph = create_alert_analysis_graph(
        model=model,
        tools=[investigate_splunk_logs],
        max_steps=4,
    )

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="分析告警")],
            "iteration": 0,
            "exhausted": False,
        },
        context=AlertToolContext(
            alert_id="trusted-alert-id",
            run_id="run-1",
            splunk_service=service,
        ),
    )

    tool_message = next(
        message for message in result["messages"]
        if isinstance(message, ToolMessage)
    )
    assert service.requests[0].alert_id == "trusted-alert-id"
    assert json.loads(tool_message.content)["alert_id"] == "trusted-alert-id"


@pytest.mark.asyncio
async def test_agent_graph_accepts_valid_structured_analysis():
    model = StructuredQueuedToolModel(
        [AIMessage(content="调查完成")],
        [_valid_analysis()],
    )
    graph = create_alert_analysis_graph(
        model=model,
        tools=[],
        max_steps=4,
        output_schema=AgentAnalysis,
        output_repair_limit=1,
    )

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="分析告警")],
        "iteration": 0,
        "exhausted": False,
        "evidence": {"historical": {}, "knowledge": {}, "splunk": {}},
    })

    assert AgentAnalysis.model_validate(result["analysis"]).confidence == "中"
    assert result["status"] == "completed"
    assert result["validation_repair_count"] == 0


@pytest.mark.asyncio
async def test_agent_graph_repairs_nonexistent_evidence_reference_once():
    invalid = _valid_analysis(evidence_refs=[EvidenceReference(
        source="splunk",
        reference="splunk:event-1",
        claim="存在持续攻击",
    )])
    model = StructuredQueuedToolModel(
        [AIMessage(content="调查完成")],
        [invalid, _valid_analysis()],
    )
    graph = create_alert_analysis_graph(
        model=model,
        tools=[],
        max_steps=4,
        output_schema=AgentAnalysis,
        output_repair_limit=1,
    )

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="分析告警")],
        "iteration": 0,
        "exhausted": False,
        "evidence": {"historical": {}, "knowledge": {}, "splunk": {}},
    })

    assert result["status"] == "completed"
    assert result["validation_repair_count"] == 1
    assert model.structured_calls == 2
    assert result["analysis"]["evidence_refs"] == []


@pytest.mark.asyncio
async def test_agent_graph_requires_failed_tool_to_be_an_evidence_gap():
    missing_gap = _valid_analysis(evidence_gaps=[])
    repaired = _valid_analysis(evidence_gaps=["Splunk 日志查询暂不可用"])
    model = StructuredQueuedToolModel(
        [AIMessage(content="调查完成")],
        [missing_gap, repaired],
    )
    graph = create_alert_analysis_graph(
        model=model,
        tools=[],
        max_steps=4,
        output_schema=AgentAnalysis,
        output_repair_limit=1,
    )

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="分析告警")],
        "iteration": 0,
        "exhausted": False,
        "evidence": {
            "historical": {},
            "knowledge": {},
            "splunk": {
                "success": False,
                "error_code": "splunk_search_unavailable",
            },
        },
    })

    assert result["status"] == "completed"
    assert result["validation_repair_count"] == 1
    assert model.structured_calls == 2


@pytest.mark.asyncio
async def test_agent_graph_degrades_after_single_failed_repair():
    invalid = _valid_analysis(evidence_refs=[EvidenceReference(
        source="knowledge",
        reference="knowledge:missing",
        claim="资产属于生产环境",
    )])
    model = StructuredQueuedToolModel(
        [AIMessage(content="调查完成")],
        [invalid, invalid],
    )
    graph = create_alert_analysis_graph(
        model=model,
        tools=[],
        max_steps=4,
        output_schema=AgentAnalysis,
        output_repair_limit=1,
    )

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="分析告警")],
        "iteration": 0,
        "exhausted": False,
        "evidence": {"historical": {}, "knowledge": {}, "splunk": {}},
    })

    degraded = AgentAnalysis.model_validate(result["analysis"])
    assert result["status"] == "degraded"
    assert result["validation_repair_count"] == 1
    assert model.structured_calls == 2
    assert degraded.confidence == "低"
    assert degraded.evidence_refs == []
    assert result["degraded_reasons"]


@pytest.mark.asyncio
async def test_agent_graph_resumes_same_thread_without_repeating_tool():
    tool_calls = []

    @tool
    def counted_history(query: str) -> str:
        """Record one historical lookup."""
        tool_calls.append(query)
        return json.dumps({"success": True, "results": []})

    model = StructuredQueuedToolModel(
        [
            AIMessage(
                content="",
                tool_calls=[{
                    "name": "counted_history",
                    "args": {"query": "scan"},
                    "id": "history-1",
                    "type": "tool_call",
                }],
            ),
            RuntimeError("simulated process interruption"),
            AIMessage(content="恢复后完成调查"),
        ],
        [_valid_analysis()],
    )
    graph = create_alert_analysis_graph(
        model=model,
        tools=[counted_history],
        max_steps=4,
        output_schema=AgentAnalysis,
        output_repair_limit=1,
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "alert-1:run-1"}}

    with pytest.raises(RuntimeError, match="simulated process interruption"):
        await graph.ainvoke(
            {
                "messages": [HumanMessage(content="分析告警")],
                "iteration": 0,
                "exhausted": False,
                "evidence": {
                    "historical": {}, "knowledge": {}, "splunk": {},
                },
            },
            config=config,
        )

    result = await graph.ainvoke(None, config=config)

    assert result["status"] == "completed"
    assert tool_calls == ["scan"]


@pytest.mark.asyncio
async def test_sqlite_checkpoint_resumes_across_graph_instances(tmp_path):
    database = tmp_path / "agent-checkpoints.sqlite3"
    config = {"configurable": {"thread_id": "alert-2:run-1"}}
    tool_calls = []

    @tool
    def counted_history(query: str) -> str:
        """Record one historical lookup."""
        tool_calls.append(query)
        return json.dumps({"success": True, "results": []})

    first_model = StructuredQueuedToolModel(
        [
            AIMessage(
                content="",
                tool_calls=[{
                    "name": "counted_history",
                    "args": {"query": "persistent scan"},
                    "id": "history-2",
                    "type": "tool_call",
                }],
            ),
            RuntimeError("stop first graph"),
        ],
        [],
    )
    async with AsyncSqliteSaver.from_conn_string(str(database)) as saver:
        first_graph = create_alert_analysis_graph(
            model=first_model,
            tools=[counted_history],
            max_steps=4,
            output_schema=AgentAnalysis,
            checkpointer=saver,
        )
        with pytest.raises(RuntimeError, match="stop first graph"):
            await first_graph.ainvoke(
                {
                    "messages": [HumanMessage(content="分析告警")],
                    "iteration": 0,
                    "exhausted": False,
                    "evidence": {
                        "historical": {}, "knowledge": {}, "splunk": {},
                    },
                },
                config=config,
            )

    second_model = StructuredQueuedToolModel(
        [AIMessage(content="第二个 Graph 恢复完成")],
        [_valid_analysis()],
    )
    async with AsyncSqliteSaver.from_conn_string(str(database)) as saver:
        second_graph = create_alert_analysis_graph(
            model=second_model,
            tools=[counted_history],
            max_steps=4,
            output_schema=AgentAnalysis,
            checkpointer=saver,
        )
        result = await second_graph.ainvoke(None, config=config)

    assert result["status"] == "completed"
    assert tool_calls == ["persistent scan"]


@pytest.mark.asyncio
async def test_new_thread_does_not_inherit_completed_run_messages():
    model = StructuredQueuedToolModel(
        [AIMessage(content="first done"), AIMessage(content="second done")],
        [_valid_analysis(), _valid_analysis()],
    )
    graph = create_alert_analysis_graph(
        model=model,
        tools=[],
        max_steps=4,
        output_schema=AgentAnalysis,
        checkpointer=InMemorySaver(),
    )
    initial = lambda text: {
        "messages": [HumanMessage(content=text)],
        "iteration": 0,
        "exhausted": False,
        "evidence": {"historical": {}, "knowledge": {}, "splunk": {}},
    }

    await graph.ainvoke(
        initial("first alert"),
        config={"configurable": {"thread_id": "alert-3:run-1"}},
    )
    second = await graph.ainvoke(
        initial("second alert"),
        config={"configurable": {"thread_id": "alert-3:run-2"}},
    )

    contents = [str(message.content) for message in second["messages"]]
    assert any("second alert" in item for item in contents)
    assert all("first alert" not in item for item in contents)


def test_agents_package_exports_graph_factories():
    import app.agents as agents

    assert agents.create_alert_analysis_graph is create_alert_analysis_graph
    assert callable(agents.create_alert_processing_graph)


def test_incomplete_run_identity_is_stable_and_completed_reanalysis_is_fresh():
    alert = RawAlert(
        alert_name="Stable identity",
        results=[AlertResult(id="asset-1", count="1")],
    )

    first = resolve_agent_run_id(
        alert,
        alert_id="alert-identity",
        formal_output_exists=False,
    )
    retry = resolve_agent_run_id(
        alert,
        alert_id="alert-identity",
        formal_output_exists=False,
    )
    changed = resolve_agent_run_id(
        alert.model_copy(update={"trigger_reason": "changed"}),
        alert_id="alert-identity",
        formal_output_exists=False,
    )
    reanalysis_one = resolve_agent_run_id(
        alert,
        alert_id="alert-identity",
        formal_output_exists=True,
    )
    reanalysis_two = resolve_agent_run_id(
        alert,
        alert_id="alert-identity",
        formal_output_exists=True,
    )

    assert first == retry
    assert first != changed
    assert reanalysis_one != reanalysis_two
    assert reanalysis_one != first


@pytest.mark.asyncio
async def test_active_reanalysis_retry_reuses_run_until_business_completion(
    tmp_path,
):
    registry = AgentRunRegistry(tmp_path / "checkpoints.sqlite3")
    alert = RawAlert(
        alert_name="Reanalysis identity",
        results=[AlertResult(id="asset-1", count="1")],
    )

    active = await registry.acquire(
        alert,
        alert_id="alert-reanalysis",
        formal_output_exists=True,
    )
    retry = await registry.acquire(
        alert,
        alert_id="alert-reanalysis",
        formal_output_exists=True,
    )
    await registry.mark_completed("alert-reanalysis", active)
    next_reanalysis = await registry.acquire(
        alert,
        alert_id="alert-reanalysis",
        formal_output_exists=True,
    )

    assert retry == active
    assert next_reanalysis != active


@pytest.mark.asyncio
async def test_agent_graph_executes_only_model_requested_tool():
    model = QueuedToolModel([
        AIMessage(
            content="",
            tool_calls=[{
                "name": "sample_history",
                "args": {"query": "login failure"},
                "id": "call-1",
                "type": "tool_call",
            }],
        ),
        AIMessage(content="基于历史证据完成分析"),
    ])
    graph = create_alert_analysis_graph(
        model=model,
        tools=[sample_history, forbidden_knowledge],
        max_steps=4,
    )

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="分析告警")],
        "iteration": 0,
        "exhausted": False,
    })

    tool_messages = [
        message for message in result["messages"]
        if isinstance(message, ToolMessage)
    ]
    assert model.bound_tool_names == [
        "sample_history",
        "forbidden_knowledge",
    ]
    assert [message.name for message in tool_messages] == ["sample_history"]
    assert json.loads(tool_messages[0].content)["results"][0]["case_id"] == "h-1"
    assert result["messages"][-1].content == "基于历史证据完成分析"
    assert result["iteration"] == 2


@pytest.mark.asyncio
async def test_agent_graph_converts_tool_exception_to_tool_message():
    model = QueuedToolModel([
        AIMessage(
            content="",
            tool_calls=[{
                "name": "failing_history",
                "args": {"query": "database timeout"},
                "id": "failed-call",
                "type": "tool_call",
            }],
        ),
        AIMessage(content="历史查询不可用，按证据缺口处理。"),
    ])
    graph = create_alert_analysis_graph(
        model=model,
        tools=[failing_history],
        max_steps=4,
    )

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="分析告警")],
        "iteration": 0,
        "exhausted": False,
    })

    tool_messages = [
        message for message in result["messages"]
        if isinstance(message, ToolMessage)
    ]
    assert len(tool_messages) == 1
    assert tool_messages[0].name == "failing_history"
    assert tool_messages[0].status == "error"
    assert "history unavailable" in str(tool_messages[0].content)
    assert result["messages"][-1].content == (
        "历史查询不可用，按证据缺口处理。"
    )


@pytest.mark.asyncio
async def test_agent_graph_stops_after_max_model_steps():
    model = QueuedToolModel([
        AIMessage(
            content="",
            tool_calls=[{
                "name": "sample_history",
                "args": {"query": "repeat"},
                "id": "call-1",
                "type": "tool_call",
            }],
        ),
    ])
    graph = create_alert_analysis_graph(
        model=model,
        tools=[sample_history],
        max_steps=1,
    )

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="分析告警")],
        "iteration": 0,
        "exhausted": False,
    })

    assert model.calls == 1
    assert result["exhausted"] is True
    assert result["messages"][-1].content == (
        "已达到最大调查步数，按现有证据降级输出。"
    )


@pytest.mark.asyncio
async def test_alert_analysis_agent_uses_langgraph_and_only_requested_tools():
    model = StructuredQueuedToolModel(
        [
            AIMessage(
                content="",
                tool_calls=[{
                    "name": "search_historical_alerts",
                    "args": {"query": "suspicious scan", "top_k": 2},
                    "id": "history-call",
                    "type": "tool_call",
                }],
            ),
            AIMessage(
                content="调查完成",
                usage_metadata={
                    "input_tokens": 8,
                    "output_tokens": 5,
                    "total_tokens": 13,
                },
            ),
        ],
        [_valid_analysis(evidence_refs=[EvidenceReference(
            source="historical",
            reference="historical:history-1",
            claim="存在相似扫描案例",
        )])],
    )
    agent = AlertAnalysisAgent(
        model=model,
        tools=[search_historical_alerts],
        max_steps=4,
        checkpoint_enabled=False,
    )
    alert = RawAlert(
        alert_name="WAF scan",
        results=[AlertResult(
            id="AGW-PRD-01",
            properties_hostname="api.example.internal",
            properties_requestUri="/.env",
            properties_action="Blocked",
            count="20",
        )],
    )

    result = await agent.analyze(alert, alert_id="2026-08-17/agent-test")

    assert result.analysis is not None
    assert result.analysis.conclusion in result.analysis_result
    assert result.status == "completed"
    assert result.validation_repair_count == 0
    assert result.thread_id.endswith(result.run_id)
    assert result.evidence["historical"]["success"] is True
    assert result.evidence["knowledge"] == {}
    assert result.evidence["splunk"] == {}
    assert [step["name"] for step in result.steps if step["name"].startswith("tool:")] == [
        "tool:search_historical_alerts"
    ]
    assert result.execution_token_usage.total_tokens == 13
    assert result.planning_token_usage.total_tokens == 0
