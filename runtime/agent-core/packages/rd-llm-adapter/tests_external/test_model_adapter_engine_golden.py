from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

# 整个 engine_golden 是 codesphere-saas AgentEngine 端到端 golden 测试，
# 依赖 engine / claude_client / model_profile 三个 codesphere-saas 私有模块。
# rd-llm-adapter 是底层抽象（Adapter / Transport / ParserSession），不持有
# AgentEngine 抽象——这一层 golden 测试在 codesphere-saas 端继续运行。
# 在独立包内整体 skip，保留代码以便 codesphere-saas 那边继续维护对应基线。
_engine_module: Any = None
_LLMClientError: Any = None
_AgentEngine: Any = None
_ResolvedModelProfile: Any = None
try:  # pragma: no cover - 依赖只在 codesphere-saas 主仓存在
    import app.services.agent_runner.engine as _engine_module  # type: ignore[import-not-found,no-redef]
    from app.services.agent_runner.claude_client import (  # type: ignore[import-not-found,no-redef]
        LLMClientError as _LLMClientError,
    )
    from app.services.agent_runner.engine import (  # type: ignore[import-not-found,no-redef]
        AgentEngine as _AgentEngine,
    )
    from app.services.agent_runner.model_profile import (  # type: ignore[import-not-found,no-redef]
        ResolvedModelProfile as _ResolvedModelProfile,
    )

    _HAS_ENGINE_DEPS = True
except ImportError:  # pragma: no cover
    _HAS_ENGINE_DEPS = False

pytestmark = pytest.mark.skipif(
    not _HAS_ENGINE_DEPS,
    reason="engine golden 测试依赖 codesphere-saas 的 AgentEngine 整链路，"
    "在 rd-llm-adapter 独立包内不可用；该覆盖由 codesphere-saas 端测试维持。",
)

# 旧名字 alias（让 skipif 后还能 import 解析；真正运行时全部 skip）
engine_module = _engine_module
LLMClientError = _LLMClientError
AgentEngine = _AgentEngine
ResolvedModelProfile = _ResolvedModelProfile


class _SessionContext:
    def __enter__(self):
        return SimpleNamespace(commit=lambda: None)

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeLockManager:
    def acquire(self, db, project_id: str, actor: str, holder: str, ttl_s: int):
        return SimpleNamespace(lease_id="lease-golden")

    def release(self, db, lease) -> None:
        return None

    def renew(self, db, lease_id: str, ttl_s: int):
        return SimpleNamespace(expires_at=datetime(2099, 1, 1))


class _FakeWorkspaceManager:
    def __init__(self, repo_path):
        self._repo_path = repo_path

    def exists(self, project_id: str) -> bool:
        return True

    def open(self, project_id: str):
        return SimpleNamespace(generation=1)

    def bootstrap(self, project_id: str):
        return SimpleNamespace(generation=1)

    def list_dir(self, workspace, path: str):
        return []

    def repo_path(self, project_id: str):
        return self._repo_path

    def increment_generation(self, workspace) -> int:
        return workspace.generation + 1


class _FakeCheckpointScheduler:
    def is_dirty(self, project_id: str) -> bool:
        return False

    def mark_dirty(self, project_id: str) -> None:
        return None


def _build_engine(tmp_path) -> AgentEngine:
    engine = AgentEngine(
        session_factory=lambda: _SessionContext(),
        workspace_manager=_FakeWorkspaceManager(tmp_path),
        lock_manager=_FakeLockManager(),
        checkpoint_scheduler=_FakeCheckpointScheduler(),
        lease_renew_interval_s=3600,
        record_mutation_journal=False,
    )
    engine._assemble_context = lambda _workspace: ""
    engine._retrieve_memories = lambda _project_id, _instruction: []
    return engine


@pytest.mark.asyncio
async def test_engine_golden_preserves_legacy_events_and_messages(monkeypatch, tmp_path):
    calls: list[dict[str, Any]] = []

    async def fake_create_streaming_turn(**kwargs):
        turn_index = len(calls)
        calls.append(kwargs)
        on_stream_event = kwargs["on_stream_event"]

        if turn_index == 0:
            maybe = on_stream_event({"type": "reasoning_delta", "text": "plan"})
            if maybe is not None:
                await maybe
            maybe = on_stream_event(
                {
                    "type": "tool_use_delta",
                    "tool_use_id": "call_1",
                    "index": 0,
                    "name_delta": "lookup_fact",
                    "arguments_delta": '{"query":"adapter"}',
                }
            )
            if maybe is not None:
                await maybe
            maybe = on_stream_event(
                {
                    "type": "tool_use",
                    "id": "call_1",
                    "name": "lookup_fact",
                    "input": {"query": "adapter"},
                }
            )
            if maybe is not None:
                await maybe
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call_1",
                        "name": "lookup_fact",
                        "input": {"query": "adapter"},
                    }
                ],
                "usage": {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
                "stop_reason": "tool_calls",
                "latency_ms": 11,
                "first_chunk_latency_ms": 2,
                "reasoning_text": "plan",
                "text_content": "",
            }

        assert any(
            msg.get("role") == "assistant" and msg.get("reasoning_content") == "plan"
            for msg in kwargs["messages"]
        )
        assert any(
            msg.get("role") == "user"
            and isinstance(msg.get("content"), list)
            and msg["content"][0].get("type") == "tool_result"
            for msg in kwargs["messages"]
        )
        maybe = on_stream_event({"type": "text_delta", "text": "done"})
        if maybe is not None:
            await maybe
        return {
            "content": [{"type": "text", "text": "done"}],
            "usage": {"input_tokens": 5, "output_tokens": 6, "total_tokens": 11},
            "stop_reason": "stop",
            "latency_ms": 13,
            "first_chunk_latency_ms": 3,
            "reasoning_text": "",
            "text_content": "done",
        }

    monkeypatch.setattr(engine_module, "create_streaming_turn", fake_create_streaming_turn)

    tool_calls: list[dict[str, Any]] = []

    def lookup_fact(_ctx, tool_input):
        tool_calls.append(dict(tool_input))
        return {"ok": True, "content": "fact: adapter works"}

    events: list[dict[str, Any]] = []
    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="fake-model",
        provider_model_name="fake-provider-model",
        base_url="https://example.test/v1",
        api_key="sk-test",
        max_output_tokens=128,
        request_timeout_s=30,
        total_timeout_s=30,
    )

    result = await engine.execute(
        project_id="project-golden",
        instruction="check adapter",
        session_messages=[],
        profile=profile,
        tools=[
            {
                "name": "lookup_fact",
                "description": "Lookup a fact",
                "input_schema": {"type": "object", "properties": {}},
                "handler": lookup_fact,
            }
        ],
        on_event=events.append,
        max_turns=3,
        user_request_id="request-golden",
        agent_run_id="run-golden",
        session_id="session-golden",
    )

    stream_event_types = [
        event["event"]["type"]
        for event in events
        if event.get("type") == "assistant_stream"
    ]
    assert stream_event_types == [
        "message_start",
        "reasoning_delta",
        "tool_use_delta",
        "tool_use",
        "reasoning",
        "message_start",
        "text_delta",
        "text",
    ]

    ended_reasons = [
        event["reason"] for event in events if event.get("type") == "assistant_turn_ended"
    ]
    assert ended_reasons == ["tool_use", "chat"]
    assert [event["type"] for event in events if event["type"] == "llm_metrics"] == [
        "llm_metrics",
        "llm_metrics",
    ]

    assert tool_calls == [{"query": "adapter"}]
    assert result.stop_reason == "stop"
    assert result.usage == {"input_tokens": 8, "output_tokens": 10, "total_tokens": 18}
    assert result.tool_calls_count == 1
    assert result.turns_count == 2
    assert result.messages[1]["role"] == "assistant"
    assert result.messages[1]["reasoning_content"] == "plan"
    assert result.messages[1]["content"][0]["type"] == "tool_use"
    assert result.messages[2]["content"][0]["type"] == "tool_result"
    assert result.messages[-1] == {
        "role": "assistant",
        "content": [{"type": "text", "text": "done"}],
    }


@pytest.mark.asyncio
async def test_engine_normalizes_loose_tool_input_before_execution(monkeypatch, tmp_path):
    calls: list[dict[str, Any]] = []

    async def fake_create_streaming_turn(**kwargs):
        turn_index = len(calls)
        calls.append(kwargs)

        if turn_index == 0:
            maybe = kwargs["on_stream_event"](
                {
                    "type": "tool_use",
                    "id": "call_loose",
                    "name": "lookup_fact",
                    "input": "adapter",
                }
            )
            if maybe is not None:
                await maybe
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call_loose",
                        "name": "lookup_fact",
                        "input": "adapter",
                    }
                ],
                "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
                "stop_reason": "tool_calls",
                "latency_ms": 10,
                "first_chunk_latency_ms": 1,
                "reasoning_text": "",
                "text_content": "",
            }

        return {
            "content": [{"type": "text", "text": "done"}],
            "usage": {"input_tokens": 4, "output_tokens": 5, "total_tokens": 9},
            "stop_reason": "stop",
            "latency_ms": 12,
            "first_chunk_latency_ms": 2,
            "reasoning_text": "",
            "text_content": "done",
        }

    monkeypatch.setattr(engine_module, "create_streaming_turn", fake_create_streaming_turn)

    tool_calls: list[dict[str, Any]] = []

    def lookup_fact(_ctx, tool_input):
        tool_calls.append(dict(tool_input))
        return {"ok": True, "content": "fact"}

    events: list[dict[str, Any]] = []
    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="fake-model",
        provider_model_name="fake-provider-model",
        base_url="https://example.test/v1",
        api_key="sk-test",
        request_timeout_s=30,
        total_timeout_s=30,
    )

    result = await engine.execute(
        project_id="project-loose-input",
        instruction="check loose tool args",
        session_messages=[],
        profile=profile,
        tools=[
            {
                "name": "lookup_fact",
                "description": "Lookup a fact",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                "handler": lookup_fact,
            }
        ],
        on_event=events.append,
        max_turns=3,
        user_request_id="request-loose-input",
        agent_run_id="run-loose-input",
        session_id="session-loose-input",
    )

    assert tool_calls == [{"query": "adapter"}]
    assert result.stop_reason == "stop"
    tool_started = next(event for event in events if event.get("type") == "tool_started")
    assert tool_started["input"] == {"query": "adapter"}


@pytest.mark.asyncio
async def test_engine_deepseek_roundtrips_empty_reasoning_for_tool_calls(
    monkeypatch, tmp_path
):
    calls: list[dict[str, Any]] = []

    async def fake_create_streaming_turn(**kwargs):
        turn_index = len(calls)
        calls.append(kwargs)

        if turn_index == 0:
            maybe = kwargs["on_stream_event"](
                {
                    "type": "tool_use",
                    "id": "call_empty_reasoning",
                    "name": "lookup_fact",
                    "input": {"query": "adapter"},
                }
            )
            if maybe is not None:
                await maybe
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call_empty_reasoning",
                        "name": "lookup_fact",
                        "input": {"query": "adapter"},
                    }
                ],
                "usage": {"input_tokens": 3, "output_tokens": 1, "total_tokens": 4},
                "stop_reason": "tool_calls",
                "latency_ms": 11,
                "first_chunk_latency_ms": 2,
                "reasoning_text": "",
                "text_content": "",
            }

        assert any(
            msg.get("role") == "assistant"
            and msg.get("content", [{}])[0].get("type") == "tool_use"
            and "reasoning_content" in msg
            and msg["reasoning_content"] == ""
            for msg in kwargs["messages"]
        )
        return {
            "content": [{"type": "text", "text": "done"}],
            "usage": {"input_tokens": 5, "output_tokens": 6, "total_tokens": 11},
            "stop_reason": "stop",
            "latency_ms": 13,
            "first_chunk_latency_ms": 3,
            "reasoning_text": "",
            "text_content": "done",
        }

    monkeypatch.setattr(engine_module, "create_streaming_turn", fake_create_streaming_turn)

    def lookup_fact(_ctx, _tool_input):
        return {"ok": True, "content": "fact"}

    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="deepseek-v4-pro",
        provider_model_name="deepseek-v4-pro",
        base_url="https://example.test/v1",
        api_key="sk-test",
        max_output_tokens=128,
        request_timeout_s=30,
        total_timeout_s=30,
    )

    result = await engine.execute(
        project_id="project-deepseek-empty-reasoning",
        instruction="check adapter",
        session_messages=[],
        profile=profile,
        tools=[
            {
                "name": "lookup_fact",
                "description": "Lookup a fact",
                "input_schema": {"type": "object", "properties": {}},
                "handler": lookup_fact,
            }
        ],
        on_event=lambda _event: None,
        max_turns=3,
        user_request_id="request-deepseek-empty-reasoning",
        agent_run_id="run-deepseek-empty-reasoning",
        session_id="session-deepseek-empty-reasoning",
    )

    assert result.messages[1]["role"] == "assistant"
    assert result.messages[1]["reasoning_content"] == ""
    assert result.messages[1]["content"][0]["type"] == "tool_use"


@pytest.mark.asyncio
async def test_engine_golden_error_path_closes_turn_without_terminal_events(
    monkeypatch, tmp_path
):
    async def fake_create_streaming_turn(**kwargs):
        maybe = kwargs["on_stream_event"]({"type": "reasoning_delta", "text": "partial"})
        if maybe is not None:
            await maybe
        raise LLMClientError(
            {
                "type": "api_error",
                "error_code": "API_ERROR",
                "message": "upstream failed",
                "retryable": False,
                "partial_output": True,
            }
        )

    monkeypatch.setattr(engine_module, "create_streaming_turn", fake_create_streaming_turn)

    events: list[dict[str, Any]] = []
    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="fake-model",
        provider_model_name="fake-provider-model",
        base_url="https://example.test/v1",
        api_key="sk-test",
        request_timeout_s=30,
        total_timeout_s=30,
    )

    with pytest.raises(LLMClientError):
        await engine.execute(
            project_id="project-golden-error",
            instruction="trigger failure",
            session_messages=[],
            profile=profile,
            tools=[],
            on_event=events.append,
            max_turns=1,
            user_request_id="request-golden-error",
            agent_run_id="run-golden-error",
            session_id="session-golden-error",
        )

    stream_event_types = [
        event["event"]["type"]
        for event in events
        if event.get("type") == "assistant_stream"
    ]
    assert stream_event_types == ["message_start", "reasoning_delta"]

    turn_end_events = [
        event for event in events if event.get("type") == "assistant_turn_ended"
    ]
    assert len(turn_end_events) == 1
    assert turn_end_events[0]["reason"] == "error"
    assert turn_end_events[0]["incomplete"] is True

    failed = next(event for event in events if event.get("type") == "run_failed")
    assert failed["state"] == "failed"
    assert failed["error"]["error_code"] == "API_ERROR"
    assert not any(event.get("type") == "llm_metrics" for event in events)


@pytest.mark.asyncio
async def test_engine_golden_length_continuation_emits_single_terminal_text(
    monkeypatch, tmp_path
):
    calls: list[dict[str, Any]] = []

    async def fake_create_streaming_turn(**kwargs):
        turn_index = len(calls)
        calls.append(kwargs)
        on_stream_event = kwargs["on_stream_event"]

        if turn_index == 0:
            maybe = on_stream_event({"type": "reasoning_delta", "text": "think1 "})
            if maybe is not None:
                await maybe
            maybe = on_stream_event({"type": "text_delta", "text": "part1 "})
            if maybe is not None:
                await maybe
            return {
                "content": [{"type": "text", "text": "part1 "}],
                "usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
                "stop_reason": "length",
                "latency_ms": 10,
                "first_chunk_latency_ms": 1,
                "reasoning_text": "think1 ",
                "text_content": "part1 ",
            }

        assert any(
            msg.get("role") == "assistant"
            and msg.get("reasoning_content") == "think1 "
            and msg.get("content") == [{"type": "text", "text": "part1 "}]
            for msg in kwargs["messages"]
        )
        assert kwargs["messages"][-1]["role"] == "user"
        assert "previous response was truncated" in kwargs["messages"][-1]["content"]

        maybe = on_stream_event({"type": "reasoning_delta", "text": "think2"})
        if maybe is not None:
            await maybe
        maybe = on_stream_event({"type": "text_delta", "text": "part2"})
        if maybe is not None:
            await maybe
        return {
            "content": [{"type": "text", "text": "part2"}],
            "usage": {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
            "stop_reason": "stop",
            "latency_ms": 12,
            "first_chunk_latency_ms": 2,
            "reasoning_text": "think2",
            "text_content": "part2",
        }

    monkeypatch.setattr(engine_module, "create_streaming_turn", fake_create_streaming_turn)

    events: list[dict[str, Any]] = []
    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="fake-model",
        provider_model_name="fake-provider-model",
        base_url="https://example.test/v1",
        api_key="sk-test",
        request_timeout_s=30,
        total_timeout_s=30,
    )

    result = await engine.execute(
        project_id="project-golden-length",
        instruction="write long answer",
        session_messages=[],
        profile=profile,
        tools=[],
        on_event=events.append,
        max_turns=3,
        user_request_id="request-golden-length",
        agent_run_id="run-golden-length",
        session_id="session-golden-length",
    )

    stream_event_types = [
        event["event"]["type"]
        for event in events
        if event.get("type") == "assistant_stream"
    ]
    assert stream_event_types == [
        "message_start",
        "reasoning_delta",
        "text_delta",
        "reasoning_delta",
        "text_delta",
        "reasoning",
        "text",
    ]

    terminal_streams = [
        event["event"] for event in events if event.get("type") == "assistant_stream"
    ]
    assert terminal_streams[-2] == {"type": "reasoning", "text": "think1 think2"}
    assert terminal_streams[-1] == {"type": "text", "text": "part1 part2"}
    assert [event["reason"] for event in events if event.get("type") == "assistant_turn_ended"] == ["chat"]  # noqa: E501

    assert result.stop_reason == "stop"
    assert result.usage == {"input_tokens": 4, "output_tokens": 6, "total_tokens": 10}
    assert result.turns_count == 2
    assert result.messages[1] == {
        "role": "assistant",
        "content": [{"type": "text", "text": "part1 "}],
        "reasoning_content": "think1 ",
    }
    assert result.messages[2]["role"] == "user"
    assert "previous response was truncated" in result.messages[2]["content"]
    assert result.messages[-1] == {
        "role": "assistant",
        "content": [{"type": "text", "text": "part2"}],
        "reasoning_content": "think2",
    }


@pytest.mark.asyncio
async def test_engine_golden_ask_user_preserves_pause_contract(monkeypatch, tmp_path):
    ask_input = {
        "context": "Need a product choice",
        "questions": [
            {
                "id": "product",
                "question": "Which product?",
                "type": "select",
                "options": ["A", "B"],
                "default": "A",
            }
        ],
    }

    async def fake_create_streaming_turn(**kwargs):
        on_stream_event = kwargs["on_stream_event"]
        maybe = on_stream_event({"type": "reasoning_delta", "text": "need user"})
        if maybe is not None:
            await maybe
        maybe = on_stream_event(
            {
                "type": "tool_use",
                "id": "ask_1",
                "name": "ask_user",
                "input": ask_input,
            }
        )
        if maybe is not None:
            await maybe
        return {
            "content": [
                {
                    "type": "tool_use",
                    "id": "ask_1",
                    "name": "ask_user",
                    "input": ask_input,
                }
            ],
            "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            "stop_reason": "tool_calls",
            "latency_ms": 10,
            "first_chunk_latency_ms": 1,
            "reasoning_text": "need user",
            "text_content": "",
        }

    monkeypatch.setattr(engine_module, "create_streaming_turn", fake_create_streaming_turn)

    def ask_user_handler(_ctx, tool_input):
        assert tool_input == ask_input
        return {"ok": True, "content": "question sent"}

    events: list[dict[str, Any]] = []
    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="fake-model",
        provider_model_name="fake-provider-model",
        base_url="https://example.test/v1",
        api_key="sk-test",
        request_timeout_s=30,
        total_timeout_s=30,
    )

    result = await engine.execute(
        project_id="project-golden-ask",
        instruction="ask before proceeding",
        session_messages=[],
        profile=profile,
        tools=[
            {
                "name": "ask_user",
                "description": "Ask the user",
                "input_schema": {"type": "object", "properties": {}},
                "handler": ask_user_handler,
            }
        ],
        on_event=events.append,
        max_turns=2,
        user_request_id="request-golden-ask",
        agent_run_id="run-golden-ask",
        session_id="session-golden-ask",
    )

    assert result.stop_reason == "ask_user"
    assert result.tool_calls_count == 1
    assert result.usage == {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5}

    ask_event = next(event for event in events if event.get("type") == "ask_user")
    assert ask_event["action_id"] == "ask_1"
    assert ask_event["questions"] == ask_input["questions"]
    assert ask_event["context"] == ask_input["context"]

    ended = next(event for event in events if event.get("type") == "assistant_turn_ended")
    assert ended["reason"] == "ask_user"
    assert ended["incomplete"] is False
    completed = next(event for event in events if event.get("type") == "run_completed")
    assert completed["stop_reason"] == "ask_user"

    assert result.messages[1]["role"] == "assistant"
    assert result.messages[1]["reasoning_content"] == "need user"
    assert result.messages[1]["content"][0]["type"] == "tool_use"
    assert result.messages[2]["content"][0]["type"] == "tool_result"
    assert result.messages[-1]["role"] == "assistant"
    assert result.messages[-1]["reasoning_content"] == "need user"
    assert "Need a product choice" in result.messages[-1]["content"][0]["text"]
    assert "**1. Which product?**" in result.messages[-1]["content"][0]["text"]


@pytest.mark.asyncio
async def test_engine_golden_recovers_ask_user_parse_error(monkeypatch, tmp_path):
    async def fake_create_streaming_turn(**kwargs):
        on_stream_event = kwargs["on_stream_event"]
        maybe = on_stream_event(
            {
                "type": "tool_use",
                "id": "ask_bad_json",
                "name": "ask_user",
                "input": {},
                "input_parse_error": True,
                "raw_args": '{"questions":',
                "parse_error": "Expecting value",
                "index": 0,
            }
        )
        if maybe is not None:
            await maybe
        return {
            "content": [
                {
                    "type": "tool_use",
                    "id": "ask_bad_json",
                    "name": "ask_user",
                    "input": {},
                    "input_parse_error": True,
                    "raw_args": '{"questions":',
                    "parse_error": "Expecting value",
                    "index": 0,
                }
            ],
            "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            "stop_reason": "tool_calls",
            "latency_ms": 10,
            "first_chunk_latency_ms": 1,
            "reasoning_text": "",
            "text_content": "",
        }

    monkeypatch.setattr(
        engine_module, "create_streaming_turn", fake_create_streaming_turn
    )

    def ask_user_handler(_ctx, tool_input):
        assert (
            tool_input["questions"][0]["question"]
            == "请补充必要信息，我将继续执行。"
        )
        return {"ok": True, "content": "question sent"}

    events: list[dict[str, Any]] = []
    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="fake-model",
        provider_model_name="fake-provider-model",
        base_url="https://example.test/v1",
        api_key="sk-test",
        request_timeout_s=30,
        total_timeout_s=30,
    )

    result = await engine.execute(
        project_id="project-golden-ask-parse-error",
        instruction="ask before proceeding",
        session_messages=[],
        profile=profile,
        tools=[
            {
                "name": "ask_user",
                "description": "Ask the user",
                "input_schema": {"type": "object", "properties": {}},
                "handler": ask_user_handler,
            }
        ],
        on_event=events.append,
        max_turns=2,
        user_request_id="request-golden-ask-parse-error",
        agent_run_id="run-golden-ask-parse-error",
        session_id="session-golden-ask-parse-error",
    )

    assert result.stop_reason == "ask_user"
    ask_event = next(event for event in events if event.get("type") == "ask_user")
    assert ask_event["questions"][0]["question"] == "请补充必要信息，我将继续执行。"
    assert not any(
        event.get("type") == "tool_completed"
        and (event.get("error") or {}).get("type") == "tool_arguments_parse_error"
        for event in events
    )


@pytest.mark.asyncio
async def test_engine_golden_empty_response_retries_once(monkeypatch, tmp_path):
    calls: list[dict[str, Any]] = []

    async def fake_create_streaming_turn(**kwargs):
        turn_index = len(calls)
        calls.append(kwargs)

        if turn_index == 0:
            return {
                "content": [],
                "usage": {"input_tokens": 1, "output_tokens": 0, "total_tokens": 1},
                "stop_reason": "stop",
                "latency_ms": 8,
                "first_chunk_latency_ms": 1,
                "reasoning_text": "",
                "text_content": "",
            }

        assert kwargs["messages"][-1] == {
            "role": "user",
            "content": "你的回复为空，请重新回答。",
        }
        maybe = kwargs["on_stream_event"]({"type": "text_delta", "text": "recovered"})
        if maybe is not None:
            await maybe
        return {
            "content": [{"type": "text", "text": "recovered"}],
            "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            "stop_reason": "stop",
            "latency_ms": 9,
            "first_chunk_latency_ms": 2,
            "reasoning_text": "",
            "text_content": "recovered",
        }

    monkeypatch.setattr(engine_module, "create_streaming_turn", fake_create_streaming_turn)

    events: list[dict[str, Any]] = []
    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="fake-model",
        provider_model_name="fake-provider-model",
        base_url="https://example.test/v1",
        api_key="sk-test",
        request_timeout_s=30,
        total_timeout_s=30,
    )

    result = await engine.execute(
        project_id="project-golden-empty",
        instruction="answer eventually",
        session_messages=[],
        profile=profile,
        tools=[],
        on_event=events.append,
        max_turns=3,
        user_request_id="request-golden-empty",
        agent_run_id="run-golden-empty",
        session_id="session-golden-empty",
    )

    stream_event_types = [
        event["event"]["type"]
        for event in events
        if event.get("type") == "assistant_stream"
    ]
    assert stream_event_types == ["message_start", "message_start", "text_delta", "text"]
    assert [
        event["reason"] for event in events if event.get("type") == "assistant_turn_ended"
    ] == ["empty_response_retry", "chat"]
    assert [event["type"] for event in events if event["type"] == "llm_metrics"] == [
        "llm_metrics",
        "llm_metrics",
    ]

    assert len(calls) == 2
    assert result.stop_reason == "stop"
    assert result.turns_count == 2
    assert result.usage == {"input_tokens": 3, "output_tokens": 3, "total_tokens": 6}
    assert result.messages[1] == {
        "role": "user",
        "content": "你的回复为空，请重新回答。",
    }
    assert result.messages[-1] == {
        "role": "assistant",
        "content": [{"type": "text", "text": "recovered"}],
    }


@pytest.mark.asyncio
async def test_engine_golden_length_limit_keeps_single_accumulated_terminal_text(
    monkeypatch, tmp_path
):
    calls: list[dict[str, Any]] = []

    async def fake_create_streaming_turn(**kwargs):
        turn_index = len(calls)
        calls.append(kwargs)
        part = f"part{turn_index + 1} "

        maybe = kwargs["on_stream_event"]({"type": "text_delta", "text": part})
        if maybe is not None:
            await maybe
        return {
            "content": [{"type": "text", "text": part}],
            "usage": {
                "input_tokens": turn_index + 1,
                "output_tokens": turn_index + 1,
                "total_tokens": (turn_index + 1) * 2,
            },
            "stop_reason": "length",
            "latency_ms": 10 + turn_index,
            "first_chunk_latency_ms": 1,
            "reasoning_text": "",
            "text_content": part,
        }

    monkeypatch.setattr(engine_module, "create_streaming_turn", fake_create_streaming_turn)

    events: list[dict[str, Any]] = []
    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="fake-model",
        provider_model_name="fake-provider-model",
        base_url="https://example.test/v1",
        api_key="sk-test",
        request_timeout_s=30,
        total_timeout_s=30,
    )

    result = await engine.execute(
        project_id="project-golden-length-limit",
        instruction="write a too-long answer",
        session_messages=[],
        profile=profile,
        tools=[],
        on_event=events.append,
        max_turns=5,
        user_request_id="request-golden-length-limit",
        agent_run_id="run-golden-length-limit",
        session_id="session-golden-length-limit",
    )

    stream_events = [
        event["event"] for event in events if event.get("type") == "assistant_stream"
    ]
    assert [event["type"] for event in stream_events] == [
        "message_start",
        "text_delta",
        "text_delta",
        "text_delta",
        "text_delta",
        "text",
    ]
    assert stream_events[-1] == {"type": "text", "text": "part1 part2 part3 part4 "}

    turn_end_events = [
        event for event in events if event.get("type") == "assistant_turn_ended"
    ]
    assert len(turn_end_events) == 1
    assert turn_end_events[0]["reason"] == "length_limit"
    assert turn_end_events[0]["incomplete"] is True

    assert len(calls) == 4
    assert result.stop_reason == "length_limit"
    assert result.usage == {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}
    assert result.messages[-1] == {
        "role": "assistant",
        "content": [{"type": "text", "text": "part4 "}],
    }


@pytest.mark.asyncio
async def test_engine_golden_max_turns_emits_synthetic_closing(monkeypatch, tmp_path):
    async def fake_create_streaming_turn(**kwargs):
        maybe = kwargs["on_stream_event"](
            {
                "type": "tool_use",
                "id": "call_max",
                "name": "lookup_fact",
                "input": {"query": "limit"},
            }
        )
        if maybe is not None:
            await maybe
        return {
            "content": [
                {
                    "type": "tool_use",
                    "id": "call_max",
                    "name": "lookup_fact",
                    "input": {"query": "limit"},
                }
            ],
            "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            "stop_reason": "tool_calls",
            "latency_ms": 10,
            "first_chunk_latency_ms": 1,
            "reasoning_text": "",
            "text_content": "",
        }

    monkeypatch.setattr(engine_module, "create_streaming_turn", fake_create_streaming_turn)

    def lookup_fact(_ctx, tool_input):
        assert tool_input == {"query": "limit"}
        return {"ok": True, "content": "fact"}

    events: list[dict[str, Any]] = []
    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="fake-model",
        provider_model_name="fake-provider-model",
        base_url="https://example.test/v1",
        api_key="sk-test",
        request_timeout_s=30,
        total_timeout_s=30,
    )

    result = await engine.execute(
        project_id="project-golden-max-turns",
        instruction="use a tool",
        session_messages=[],
        profile=profile,
        tools=[
            {
                "name": "lookup_fact",
                "description": "Lookup a fact",
                "input_schema": {"type": "object", "properties": {}},
                "handler": lookup_fact,
            }
        ],
        on_event=events.append,
        max_turns=1,
        user_request_id="request-golden-max-turns",
        agent_run_id="run-golden-max-turns",
        session_id="session-golden-max-turns",
    )

    stream_events = [
        event["event"] for event in events if event.get("type") == "assistant_stream"
    ]
    assert [event["type"] for event in stream_events] == [
        "message_start",
        "tool_use",
        "message_start",
        "text",
    ]
    assert stream_events[-1]["text"] == "本轮执行到此结束（已达到最大轮次）。如需继续，请发送下一步指令。"  # noqa: E501

    turn_end_events = [
        event for event in events if event.get("type") == "assistant_turn_ended"
    ]
    assert [event["reason"] for event in turn_end_events] == ["tool_use", "max_turns"]
    assert turn_end_events[-1]["loop_breaker"] == "max_turns"
    assert turn_end_events[-1]["incomplete"] is True

    assert result.stop_reason == "max_turns"
    assert result.tool_calls_count == 1
    assert result.usage == {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5}
    assert result.messages[-1] == {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "本轮执行到此结束（已达到最大轮次）。如需继续，请发送下一步指令。",
            }
        ],
    }


@pytest.mark.asyncio
async def test_engine_golden_partial_stream_retry_replays_whole_llm_call(
    monkeypatch, tmp_path
):
    calls: list[dict[str, Any]] = []

    async def fake_create_streaming_turn(**kwargs):
        turn_index = len(calls)
        calls.append(kwargs)

        if turn_index == 0:
            maybe = kwargs["on_stream_event"]({"type": "text_delta", "text": "partial "})
            if maybe is not None:
                await maybe
            raise LLMClientError(
                {
                    "type": "api_error",
                    "error_code": "MODEL_TIMEOUT",
                    "message": "stream interrupted",
                    "retryable": True,
                    "partial_output": True,
                }
            )

        assert kwargs["messages"] is calls[0]["messages"]
        maybe = kwargs["on_stream_event"]({"type": "text_delta", "text": "replayed"})
        if maybe is not None:
            await maybe
        return {
            "content": [{"type": "text", "text": "replayed"}],
            "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            "stop_reason": "stop",
            "latency_ms": 10,
            "first_chunk_latency_ms": 2,
            "reasoning_text": "",
            "text_content": "replayed",
        }

    monkeypatch.setattr(engine_module, "create_streaming_turn", fake_create_streaming_turn)

    events: list[dict[str, Any]] = []
    engine = _build_engine(tmp_path)
    profile = ResolvedModelProfile(
        requested_model="fake-model",
        provider_model_name="fake-provider-model",
        base_url="https://example.test/v1",
        api_key="sk-test",
        request_timeout_s=30,
        total_timeout_s=30,
    )

    result = await engine.execute(
        project_id="project-golden-partial-retry",
        instruction="survive a partial stream retry",
        session_messages=[],
        profile=profile,
        tools=[],
        on_event=events.append,
        max_turns=1,
        user_request_id="request-golden-partial-retry",
        agent_run_id="run-golden-partial-retry",
        session_id="session-golden-partial-retry",
    )

    stream_events = [
        event["event"] for event in events if event.get("type") == "assistant_stream"
    ]
    assert [event["type"] for event in stream_events] == [
        "message_start",
        "text_delta",
        "text_delta",
        "text",
    ]
    assert stream_events[1]["text"] == "partial "
    assert stream_events[2]["text"] == "replayed"
    assert stream_events[-1] == {"type": "text", "text": "replayed"}

    retry_event = next(event for event in events if event.get("type") == "llm_retrying")
    assert retry_event["error_code"] == "MODEL_TIMEOUT"
    assert retry_event["attempt"] == 1
    assert [event["type"] for event in events if event.get("type") == "llm_metrics"] == [
        "llm_metrics"
    ]
    assert [event["reason"] for event in events if event.get("type") == "assistant_turn_ended"] == [
        "chat"
    ]

    assert len(calls) == 2
    assert result.stop_reason == "stop"
    assert result.usage == {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5}
    assert result.messages[-1] == {
        "role": "assistant",
        "content": [{"type": "text", "text": "replayed"}],
    }
