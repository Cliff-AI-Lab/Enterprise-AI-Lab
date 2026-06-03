"""验证 6 个横切 ports protocol 是 runtime_checkable，
且测试用 mock 实现满足契约。"""
from __future__ import annotations

from typing import Any

from rd_agent_contracts.events import AgentEvent
from rd_agent_contracts.ports import (
    BlobWriter,
    BudgetGate,
    CancellationToken,
    EventSink,
    Meter,
    PolicyGate,
)
from rd_agent_contracts.usage import Usage


class _StubEventSink:
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []

    async def emit(self, event: AgentEvent) -> None:
        self.events.append(event)


class _StubMeter:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, Usage, str]] = []

    async def record_usage(
        self, run_id: str, turn_id: str, usage: Usage, idempotency_key: str
    ) -> None:
        self.records.append((run_id, turn_id, usage, idempotency_key))


class _StubBudgetGate:
    async def before_turn(self, run_id: str) -> bool:
        return True

    async def after_turn(self, run_id: str, usage: Usage) -> None:
        pass


class _StubPolicyGate:
    async def before_tool(
        self, run_id: str, tool_name: str, tool_input: dict[str, Any]
    ) -> bool:
        return True

    async def before_llm(
        self, run_id: str, messages: list[dict[str, Any]]
    ) -> bool:
        return True

    async def redact_event(self, event: AgentEvent) -> AgentEvent:
        return event


class _StubCancellationToken:
    def __init__(self) -> None:
        self._cancelled = False

    def is_cancelled(self) -> bool:
        return self._cancelled

    def request_cancel(self) -> None:
        self._cancelled = True


class _StubBlobWriter:
    async def write_large_payload(
        self, content: bytes, mime_type: str
    ) -> tuple[str, str]:
        return ("s3://stub/x", "sha256:0")


def test_event_sink_protocol():
    sink: EventSink = _StubEventSink()
    assert isinstance(sink, EventSink)


def test_meter_protocol():
    meter: Meter = _StubMeter()
    assert isinstance(meter, Meter)


def test_budget_gate_protocol():
    gate: BudgetGate = _StubBudgetGate()
    assert isinstance(gate, BudgetGate)


def test_policy_gate_protocol():
    gate: PolicyGate = _StubPolicyGate()
    assert isinstance(gate, PolicyGate)


def test_cancellation_token_protocol():
    tok: CancellationToken = _StubCancellationToken()
    assert isinstance(tok, CancellationToken)
    assert tok.is_cancelled() is False
    tok.request_cancel()
    assert tok.is_cancelled() is True


def test_blob_writer_protocol():
    writer: BlobWriter = _StubBlobWriter()
    assert isinstance(writer, BlobWriter)
