from __future__ import annotations

from types import SimpleNamespace

from rd_llm_adapter.openai_compat import OpenAICompatAdapter
from rd_llm_adapter.recorder import (
    RecordedTurn,
    StreamRecorder,
    legacy_events_from_standard_events,
    record_turn_if_enabled,
)


def _content_chunk(text: str, finish_reason: str | None = None) -> dict:
    return {
        "choices": [
            {
                "delta": {"content": text, "model_extra": {}, "tool_calls": None},
                "finish_reason": finish_reason,
            }
        ],
        "usage": None,
    }


def _usage_chunk(
    *,
    input_tokens: int = 1,
    output_tokens: int = 2,
    total_tokens: int = 3,
) -> dict:
    return {
        "choices": [],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": total_tokens,
        },
    }


def _tool_chunk(
    *,
    call_id: str | None = None,
    name: str | None = None,
    arguments: str | None = None,
    finish_reason: str | None = None,
) -> dict:
    return {
        "choices": [
            {
                "delta": {
                    "content": None,
                    "model_extra": {},
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": call_id,
                            "function": {"name": name, "arguments": arguments},
                        }
                    ],
                },
                "finish_reason": finish_reason,
            }
        ],
        "usage": None,
    }


def test_record_turn_redacts_profile_secrets_and_round_trips_gzip(tmp_path) -> None:
    turn = RecordedTurn.create(
        turn_id="turn/with spaces",
        profile_snapshot={
            "requested_model": "deepseek",
            "api_key": "sk-1234567890",
            "nested": {"authorization": "Bearer abcdefgh"},
        },
        request_body={"messages": [{"role": "user", "content": "hello"}]},
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[{"type": "text_delta", "text": "hello"}],
        expected_legacy_dict={"content": [{"type": "text", "text": "hello"}]},
        timestamp="2026-04-30T00:00:00+00:00",
    )
    recorder = StreamRecorder()

    path = recorder.record_turn(turn, tmp_path)
    loaded = recorder.load_turn(path)

    assert path.name == "turn_with_spaces.jsonl.gz"
    assert loaded.turn_id == "turn/with spaces"
    assert loaded.profile_snapshot["api_key"] == "sk-1...7890"
    assert loaded.profile_snapshot["nested"]["authorization"] == "Bear...efgh"
    assert loaded.request_body == {"messages": [{"role": "user", "content": "hello"}]}
    assert loaded.raw_chunks == [_content_chunk("hello", "stop")]


def test_record_turn_if_enabled_uses_active_adapter_kind(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_TURNS", "1")
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_DIR", str(tmp_path))

    path = record_turn_if_enabled(
        profile=SimpleNamespace(
            requested_model="claude-sonnet-4-5",
            provider_model_name="claude-sonnet-4-5",
            base_url="https://api.anthropic.com",
            adapter_kind="anthropic_native",
        ),
        requested_model="claude-sonnet-4-5",
        provider_model="claude-sonnet-4-5",
        base_url="https://api.anthropic.com",
        adapter_kind="openai_compat",
        request_body={},
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[],
        expected_legacy_dict={},
    )

    assert path is not None
    recorded = StreamRecorder().load_turn(path)
    assert recorded.profile_snapshot["adapter_kind"] == "openai_compat"


def test_record_turn_if_enabled_skips_non_matching_model_pattern(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_TURNS", "1")
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_DIR", str(tmp_path))
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_MODEL_PATTERNS", "kimi*,claude*")

    path = record_turn_if_enabled(
        profile=None,
        requested_model="deepseek-reasoner",
        provider_model="deepseek-r1",
        base_url="https://example.test/v1",
        request_body={},
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[],
        expected_legacy_dict={},
    )

    assert path is None
    assert list(tmp_path.iterdir()) == []


def test_record_turn_if_enabled_matches_provider_model_pattern(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_TURNS", "1")
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_DIR", str(tmp_path))
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_MODEL_PATTERNS", "provider-*")

    path = record_turn_if_enabled(
        profile=None,
        requested_model="friendly-name",
        provider_model="provider-model-v1",
        base_url="https://example.test/v1",
        request_body={},
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[],
        expected_legacy_dict={},
    )

    assert path is not None
    recorded = StreamRecorder().load_turn(path)
    assert recorded.profile_snapshot["requested_model"] == "friendly-name"
    assert recorded.profile_snapshot["provider_model_name"] == "provider-model-v1"


def test_replay_through_adapter_returns_events_and_turn_done() -> None:
    recorded = RecordedTurn.create(
        turn_id="turn-replay",
        profile_snapshot={"requested_model": "deepseek"},
        request_body={},
        raw_chunks=[
            _content_chunk("hello", "stop"),
            _usage_chunk(input_tokens=3, output_tokens=4, total_tokens=7),
        ],
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
            "stop_reason": "stop",
            "latency_ms": 9,
            "first_chunk_latency_ms": 1,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )

    events, turn_done = StreamRecorder().replay_through_adapter(
        recorded, OpenAICompatAdapter()
    )

    assert turn_done.stop_reason == "stop"
    assert legacy_events_from_standard_events(events) == recorded.expected_events


def test_replay_preserves_raw_chunk_boundaries_for_legacy_tool_deltas() -> None:
    recorded = RecordedTurn.create(
        turn_id="turn-tool-boundary",
        profile_snapshot={"requested_model": "deepseek"},
        request_body={},
        raw_chunks=[
            _tool_chunk(call_id="call_1", name="search"),
            _tool_chunk(arguments='{"q":"x"}', finish_reason="tool_calls"),
        ],
        expected_events=[
            {
                "type": "tool_use_delta",
                "tool_use_id": "call_1",
                "index": 0,
                "name_delta": "search",
                "arguments_delta": None,
            },
            {
                "type": "tool_use_delta",
                "tool_use_id": "call_1",
                "index": 0,
                "name_delta": None,
                "arguments_delta": '{"q":"x"}',
            },
            {
                "type": "tool_use",
                "id": "call_1",
                "name": "search",
                "input": {"q": "x"},
            },
        ],
        expected_legacy_dict={
            "content": [
                {
                    "type": "tool_use",
                    "id": "call_1",
                    "name": "search",
                    "input": {"q": "x"},
                }
            ],
            "usage": {},
            "stop_reason": "tool_calls",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    recorder = StreamRecorder()

    events, _turn_done = recorder.replay_through_adapter(
        recorded, OpenAICompatAdapter()
    )

    assert events.legacy_events == recorded.expected_events
    assert legacy_events_from_standard_events(events) != recorded.expected_events
    assert recorder.diff_against_legacy(recorded, events) == []


def test_diff_against_legacy_reports_no_diffs_for_matching_recording() -> None:
    recorded = RecordedTurn.create(
        turn_id="turn-diff",
        profile_snapshot={"requested_model": "deepseek"},
        request_body={},
        raw_chunks=[
            _content_chunk("hello", "stop"),
            _usage_chunk(input_tokens=3, output_tokens=4, total_tokens=7),
        ],
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
            "stop_reason": "stop",
            "latency_ms": 9,
            "first_chunk_latency_ms": 1,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    recorder = StreamRecorder()

    events, _turn_done = recorder.replay_through_adapter(
        recorded, OpenAICompatAdapter()
    )

    assert recorder.diff_against_legacy(recorded, events) == []


def test_diff_against_legacy_accepts_new_invalid_tool_call_details() -> None:
    recorded = RecordedTurn.create(
        turn_id="turn-invalid-tool-compat",
        profile_snapshot={"requested_model": "deepseek"},
        request_body={},
        raw_chunks=[
            _tool_chunk(
                call_id="ask_1",
                name="ask_user",
                arguments='{"questions":',
                finish_reason="tool_calls",
            ),
        ],
        expected_events=[
            {
                "type": "tool_use_delta",
                "tool_use_id": "ask_1",
                "index": 0,
                "name_delta": "ask_user",
                "arguments_delta": '{"questions":',
            },
            {
                "type": "tool_use",
                "id": "ask_1",
                "name": "ask_user",
                "input": {},
                "input_parse_error": True,
            },
        ],
        expected_legacy_dict={
            "content": [
                {
                    "type": "tool_use",
                    "id": "ask_1",
                    "name": "ask_user",
                    "input": {},
                    "input_parse_error": True,
                }
            ],
            "usage": {},
            "stop_reason": "tool_calls",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    recorder = StreamRecorder()

    events, _turn_done = recorder.replay_through_adapter(
        recorded, OpenAICompatAdapter()
    )

    assert events.legacy_events[-1]["raw_args"] == '{"questions":'
    assert recorder.diff_against_legacy(recorded, events) == []


def test_diff_against_legacy_accepts_new_usage_detail_tokens() -> None:
    recorded = RecordedTurn.create(
        turn_id="turn-usage-detail-compat",
        profile_snapshot={"requested_model": "deepseek"},
        request_body={},
        raw_chunks=[
            _content_chunk("hello", "stop"),
            {
                "choices": [],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 4,
                    "total_tokens": 7,
                    "prompt_tokens_details": {"cached_tokens": 2},
                    "completion_tokens_details": {"reasoning_tokens": 1},
                },
            },
        ],
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    recorder = StreamRecorder()

    events, turn_done = recorder.replay_through_adapter(
        recorded, OpenAICompatAdapter()
    )

    assert turn_done.usage is not None
    assert turn_done.usage.cached_input_tokens == 2
    assert turn_done.usage.reasoning_tokens == 1
    assert recorder.diff_against_legacy(recorded, events) == []


def test_diff_against_legacy_accepts_new_reasoning_fields() -> None:
    recorded = RecordedTurn.create(
        turn_id="turn-reasoning-compat",
        profile_snapshot={"requested_model": "qwen"},
        request_body={},
        raw_chunks=[
            {
                "choices": [
                    {
                        "delta": {
                            "content": None,
                            "reasoning": "hidden ",
                            "tool_calls": None,
                        },
                        "finish_reason": None,
                    }
                ],
                "usage": None,
            },
            _content_chunk("answer", "stop"),
        ],
        expected_events=[
            {"type": "text_delta", "text": "answer"},
            {"type": "text", "text": "answer"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "answer"}],
            "usage": {},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "answer",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    recorder = StreamRecorder()

    events, turn_done = recorder.replay_through_adapter(
        recorded, OpenAICompatAdapter()
    )

    assert turn_done.reasoning_blocks[0].text == "hidden "
    assert recorder.diff_against_legacy(recorded, events) == []


def test_diff_against_legacy_reports_event_and_response_diffs() -> None:
    recorded = RecordedTurn.create(
        turn_id="turn-diff-fail",
        profile_snapshot={"requested_model": "deepseek"},
        request_body={},
        raw_chunks=[_content_chunk("actual", "stop")],
        expected_events=[{"type": "text_delta", "text": "expected"}],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "expected"}],
            "usage": {},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "expected",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    recorder = StreamRecorder()

    events, _turn_done = recorder.replay_through_adapter(
        recorded, OpenAICompatAdapter()
    )

    diffs = recorder.diff_against_legacy(recorded, events)
    assert len(diffs) == 2
    assert diffs[0].startswith("events differ")
    assert diffs[1].startswith("legacy response differs")


def test_record_turn_if_enabled_noops_when_env_off(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("MODEL_ADAPTER_RECORD_TURNS", raising=False)
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_DIR", str(tmp_path))

    path = record_turn_if_enabled(
        profile=None,
        requested_model="fake",
        provider_model="fake-provider",
        base_url="https://example.test/v1",
        request_body={"messages": [{"role": "user", "content": "secret"}]},
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[],
        expected_legacy_dict={},
    )

    assert path is None
    assert list(tmp_path.iterdir()) == []


def test_record_turn_if_enabled_writes_redacted_fixture(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_TURNS", "1")
    monkeypatch.setenv("MODEL_ADAPTER_RECORD_DIR", str(tmp_path))

    path = record_turn_if_enabled(
        profile=SimpleNamespace(
            requested_model="fake",
            provider_model_name="fake-provider",
            base_url="https://example.test/v1",
            api_key="sk-prod-secret",
        ),
        requested_model="fake",
        provider_model="fake-provider",
        base_url="https://example.test/v1",
        request_body={
            "model": "fake-provider",
            "messages": [
                {"role": "system", "content": "system secret"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "search",
                                "arguments": '{"query":"secret"}',
                            },
                        }
                    ],
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_2",
                            "name": "search",
                            "input": {"query": "secret"},
                        }
                    ],
                },
            ],
            "stream": True,
        },
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[{"type": "text_delta", "text": "hello"}],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {},
            "stop_reason": "stop",
            "latency_ms": 1,
            "first_chunk_latency_ms": 1,
            "reasoning_text": "",
            "text_content": "hello",
        },
    )

    assert path is not None
    loaded = StreamRecorder().load_turn(path)
    assert loaded.profile_snapshot["api_key"] == "sk-p...cret"
    assert loaded.request_body["messages"][0]["content"] == "[redacted:13 chars]"
    assert (
        loaded.request_body["messages"][1]["tool_calls"][0]["function"]["arguments"]
        == "[redacted:18 chars]"
    )
    assert loaded.request_body["messages"][2]["content"][0]["input"].startswith(
        "[redacted:"
    )
    assert loaded.raw_chunks == [_content_chunk("hello", "stop")]
