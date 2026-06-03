from __future__ import annotations

from rd_agent_contracts import (
    AgentTimeline,
    TimelineReadPort,
    TimelineRequest,
    TimelineRun,
    TimelineSubagentTask,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutorPort,
    ToolObservabilityPort,
    ToolObservabilityRecord,
    ToolRegistryPort,
)


class _Timeline:
    def load_agent_timeline(self, *, project_id: str, request_id: str | None = None):
        return AgentTimeline(
            project_id=project_id,
            request=TimelineRequest(
                request_id=request_id or "req-1",
                project_id=project_id,
                session_id="session-1",
                instruction="build",
            ),
            runs=[
                TimelineRun(
                    run_id="run-1",
                    user_request_id=request_id or "req-1",
                    project_id=project_id,
                    session_id="session-1",
                    agent_kind="orchestrator",
                    status="completed",
                )
            ],
            subagent_tasks=[
                TimelineSubagentTask(
                    task_id="task-1",
                    user_request_id=request_id or "req-1",
                    project_id=project_id,
                    name="verify",
                    description="verify app",
                    status="completed",
                )
            ],
        )


class _Tools:
    def list_tools(self, *, context: ToolExecutionContext) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="read_file",
                description="Read a file",
                input_schema={"type": "object"},
            )
        ]

    def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        return ToolExecutionResult(ok=True, content=f"ran {request.tool_name}")


class _ToolObservability:
    def __init__(self):
        self.records: list[ToolObservabilityRecord] = []

    def record_tool_calls(self, records: list[ToolObservabilityRecord]) -> None:
        self.records.extend(records)


def test_timeline_read_port_runtime_protocol():
    port: TimelineReadPort = _Timeline()
    timeline = port.load_agent_timeline(project_id="proj-1")
    assert timeline is not None
    assert timeline.request.request_id == "req-1"
    assert timeline.runs[0].run_id == "run-1"


def test_tool_ports_runtime_protocol():
    tools = _Tools()
    registry: ToolRegistryPort = tools
    executor: ToolExecutorPort = tools
    context = ToolExecutionContext(project_id="proj-1")
    assert registry.list_tools(context=context)[0].name == "read_file"
    result = executor.execute_tool(
        ToolExecutionRequest(
            tool_name="read_file",
            tool_input={"path": "README.md"},
            context=context,
        )
    )
    assert result.ok

    observability: ToolObservabilityPort = _ToolObservability()
    observability.record_tool_calls(
        [
            ToolObservabilityRecord(
                project_id="proj-1",
                session_id="session-1",
                tool_name="read_file",
                tool_input={"path": "README.md"},
                tool_output="ok",
                ok=True,
            )
        ]
    )
