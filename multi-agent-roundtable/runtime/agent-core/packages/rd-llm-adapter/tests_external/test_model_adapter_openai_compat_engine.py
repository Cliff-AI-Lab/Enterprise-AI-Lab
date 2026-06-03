from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from rd_llm_adapter.anthropic_transport import AnthropicNativeTransport
from rd_llm_adapter.recorder import StreamRecorder
from rd_llm_adapter.transports import OpenAICompatTransport

try:  # pragma: no cover - dependency exists only in codesphere-saas.
    from app.services.agent_runner.claude_client import (  # type: ignore[import-not-found]
        LLMClientError,
        create_streaming_turn,
    )
    from app.services.agent_runner.model_profile import (  # type: ignore[import-not-found]
        ResolvedModelProfile,
    )

    _HAS_ENGINE_DEPS = True
except ImportError:  # pragma: no cover
    _HAS_ENGINE_DEPS = False
    LLMClientError = None  # type: ignore[assignment]
    create_streaming_turn = None  # type: ignore[assignment]
    ResolvedModelProfile = None  # type: ignore[assignment]

pytestmark = pytest.mark.skipif(
    not _HAS_ENGINE_DEPS,
    reason=(
        "External engine integration tests require codesphere-saas "
        "claude_client/model_profile dependencies."
    ),
)


def _chunk(
    *,
    content: str | None = None,
    reasoning: str | None = None,
    tool_calls: list[Any] | None = None,
    finish_reason: str | None = None,
    usage: Any | None = None,
    choices: list[Any] | None = None,
) -> Any:
    if choices is None:
        delta = SimpleNamespace(
            content=content,
            model_extra=(
                {"reasoning_content": reasoning} if reasoning is not None else {}
            ),
            tool_calls=tool_calls,
        )
        choices = [SimpleNamespace(delta=delta, finish_reason=finish_reason)]
    return SimpleNamespace(choices=choices, usage=usage)


def _tool_delta(
    *,
    index: int = 0,
    call_id: str | None = None,
    name: str | None = None,
    arguments: str | None = None,
) -> Any:
    return SimpleNamespace(
        index=index,
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


@pytest.mark.asyncio
async def test_create_streaming_turn_uses_shim_and_preserves_legacy_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks = [
        _chunk(reasoning="think", content="hi "),
        _chunk(
            tool_calls=[
                _tool_delta(call_id="call_1", name="search", arguments='{"q":"x"}')
            ],
            finish_reason="tool_calls",
        ),
        _chunk(
            usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            choices=[],
        ),
    ]

    async def fake_stream(
        self: OpenAICompatTransport, request_body: dict[str, Any], **kwargs: Any
    ):
        assert request_body["model"] == "fake-model"
        for chunk in chunks:
            yield chunk

    monkeypatch.setattr(OpenAICompatTransport, "stream", fake_stream)
    seen: list[dict[str, Any]] = []

    response = await create_streaming_turn(
        api_key="sk-test",
        model="fake-model",
        system_prompt="sys",
        messages=[{"role": "user", "content": "hello"}],
        tools=[
            {
                "name": "search",
                "description": "Search",
                "input_schema": {"type": "object"},
            }
        ],
        max_tokens=128,
        on_stream_event=seen.append,
        profile=None,
    )

    assert [event["type"] for event in seen] == [
        "reasoning_delta",
        "text_delta",
        "tool_use_delta",
        "reasoning",
        "text",
        "tool_use",
    ]
    assert seen[2]["name_delta"] == "search"
    assert seen[2]["arguments_delta"] == '{"q":"x"}'
    assert response["stop_reason"] == "tool_calls"
    assert response["reasoning_text"] == "think"
    assert response["text_content"] == "hi "
    assert response["usage"] == {
        "input_tokens": 2,
        "output_tokens": 3,
        "total_tokens": 5,
    }


@pytest.mark.asyncio
async def test_create_streaming_turn_falls_back_to_openai_runtime_when_native_flag_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("MODEL_ADAPTER_ENABLE_NATIVE_RUNTIME", raising=False)
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_TURNS", "1")
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_DIR", str(tmp_path))
    chunks = [_chunk(content="hi", finish_reason="stop")]

    async def fake_stream(
        self: OpenAICompatTransport, request_body: dict[str, Any], **kwargs: Any
    ):
        assert request_body["messages"][0] == {"role": "system", "content": "sys"}
        assert request_body["messages"][1] == {"role": "user", "content": "hello"}
        assert "system" not in request_body
        for chunk in chunks:
            yield chunk

    monkeypatch.setattr(OpenAICompatTransport, "stream", fake_stream)
    profile = ResolvedModelProfile(
        requested_model="claude-sonnet-4-5",
        provider_model_name="claude-sonnet-4-5",
        base_url="https://api.anthropic.com",
        api_key="sk-test",
        max_output_tokens=128,
        adapter_kind="anthropic_native",
    )

    response = await create_streaming_turn(
        api_key="sk-test",
        model="claude-sonnet-4-5",
        system_prompt="sys",
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        max_tokens=128,
        on_stream_event=None,
        profile=profile,
    )

    assert response["stop_reason"] == "stop"
    assert response["text_content"] == "hi"
    recorded_files = list(tmp_path.glob("*.jsonl.gz"))
    assert len(recorded_files) == 1
    recorded = StreamRecorder().load_turn(recorded_files[0])
    assert recorded.profile_snapshot["adapter_kind"] == "openai_compat"


@pytest.mark.asyncio
async def test_create_streaming_turn_can_use_anthropic_native_runtime_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ADAPTER_ENABLE_NATIVE_RUNTIME", "1")

    async def fake_stream(
        self: AnthropicNativeTransport, request_body: dict[str, Any], **kwargs: Any
    ):
        assert request_body == {
            "model": "claude-sonnet-4-5",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "hello"}],
                }
            ],
            "max_tokens": 128,
            "stream": True,
            "system": [{"type": "text", "text": "sys"}],
        }
        assert kwargs["base_url"] == "https://api.anthropic.com"
        for chunk in [
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "hi"},
            },
            {"type": "content_block_stop", "index": 0},
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"input_tokens": 2, "output_tokens": 3},
            },
            {"type": "message_stop"},
        ]:
            yield chunk

    monkeypatch.setattr(AnthropicNativeTransport, "stream", fake_stream)
    seen: list[dict[str, Any]] = []
    profile = ResolvedModelProfile(
        requested_model="claude-sonnet-4-5",
        provider_model_name="claude-sonnet-4-5",
        base_url="https://api.anthropic.com",
        api_key="sk-test",
        max_output_tokens=128,
        adapter_kind="anthropic_native",
    )

    response = await create_streaming_turn(
        api_key="sk-test",
        model="claude-sonnet-4-5",
        system_prompt="sys",
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        max_tokens=128,
        on_stream_event=seen.append,
        profile=profile,
    )

    assert seen == [
        {"type": "text_delta", "text": "hi"},
        {"type": "text", "text": "hi"},
    ]
    assert response["stop_reason"] == "stop"
    assert response["text_content"] == "hi"
    assert response["usage"] == {
        "input_tokens": 2,
        "output_tokens": 3,
        "total_tokens": 5,
    }


@pytest.mark.asyncio
async def test_create_streaming_turn_respects_native_runtime_adapter_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ADAPTER_ENABLE_NATIVE_RUNTIME", "1")
    monkeypatch.setenv("MODEL_ADAPTER_NATIVE_RUNTIME_ADAPTERS", "gemini_native")

    async def fake_stream(
        self: OpenAICompatTransport, request_body: dict[str, Any], **kwargs: Any
    ):
        assert request_body["messages"][0] == {"role": "user", "content": "hello"}
        for chunk in [_chunk(content="hi", finish_reason="stop")]:
            yield chunk

    monkeypatch.setattr(OpenAICompatTransport, "stream", fake_stream)
    profile = ResolvedModelProfile(
        requested_model="claude-sonnet-4-5",
        provider_model_name="claude-sonnet-4-5",
        base_url="https://api.anthropic.com",
        api_key="sk-test",
        max_output_tokens=128,
        adapter_kind="anthropic_native",
    )

    response = await create_streaming_turn(
        api_key="sk-test",
        model="claude-sonnet-4-5",
        system_prompt="",
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        max_tokens=128,
        on_stream_event=None,
        profile=profile,
    )

    assert response["stop_reason"] == "stop"
    assert response["text_content"] == "hi"


@pytest.mark.asyncio
async def test_create_streaming_turn_native_request_build_error_is_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_ADAPTER_ENABLE_NATIVE_RUNTIME", "1")
    profile = ResolvedModelProfile(
        requested_model="claude-sonnet-4-5",
        provider_model_name="claude-sonnet-4-5",
        base_url="https://api.anthropic.com",
        api_key="sk-test",
        max_output_tokens=128,
        adapter_kind="anthropic_native",
    )

    with pytest.raises(LLMClientError) as exc_info:
        await create_streaming_turn(
            api_key="sk-test",
            model="claude-sonnet-4-5",
            system_prompt="sys",
            messages=[
                {
                    "role": "assistant",
                    "content": "previous",
                    "reasoning_content": "unsigned thinking",
                },
                {"role": "user", "content": "hello"},
            ],
            tools=[],
            max_tokens=128,
            on_stream_event=None,
            profile=profile,
        )

    assert exc_info.value.details["error_code"] == "MODEL_PROTOCOL_ERROR"
    assert exc_info.value.details["retryable"] is False
    assert exc_info.value.details["partial_output"] is False


@pytest.mark.asyncio
async def test_create_streaming_turn_records_fixture_when_env_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    chunks = [
        _chunk(content="hi", finish_reason="stop"),
        _chunk(
            usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            choices=[],
        ),
    ]

    async def fake_stream(
        self: OpenAICompatTransport, request_body: dict[str, Any], **kwargs: Any
    ):
        for chunk in chunks:
            yield chunk

    monkeypatch.setattr(OpenAICompatTransport, "stream", fake_stream)
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_TURNS", "1")
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_DIR", str(tmp_path))

    seen: list[dict[str, Any]] = []
    response = await create_streaming_turn(
        api_key="sk-test",
        model="fake-model",
        system_prompt="sys",
        messages=[{"role": "user", "content": "sensitive input"}],
        tools=[],
        max_tokens=128,
        on_stream_event=seen.append,
        profile=None,
    )

    files = list(tmp_path.glob("*.jsonl.gz"))
    assert len(files) == 1
    recorded = StreamRecorder().load_turn(files[0])
    assert recorded.expected_events == seen
    assert recorded.expected_legacy_dict == response
    assert recorded.request_body["messages"][1]["content"] == "[redacted:15 chars]"
    assert recorded.raw_chunks[0]["choices"][0]["delta"]["content"] == "hi"
