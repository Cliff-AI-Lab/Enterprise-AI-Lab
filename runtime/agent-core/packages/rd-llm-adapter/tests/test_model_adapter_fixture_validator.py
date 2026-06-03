from __future__ import annotations

import json
from pathlib import Path

import pytest
from rd_llm_adapter.recorder import (
    RecordedTurn,
    StreamRecorder,
)
from scripts.validate_model_adapter_fixtures import (
    main,
    validate_anthropic_fixtures,
    validate_recorded_fixtures,
)

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_ANTHROPIC_FIXTURES = _FIXTURES_DIR / "anthropic_native"


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


def _anthropic_text_chunks(text: str) -> list[dict]:
    return [
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": text},
        },
        {"type": "content_block_stop", "index": 0},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"input_tokens": 1, "output_tokens": 2},
        },
        {"type": "message_stop"},
    ]


def test_validate_recorded_fixtures_replays_tmp_recording(tmp_path) -> None:
    turn = RecordedTurn.create(
        turn_id="validator-recorded",
        profile_snapshot={"requested_model": "fake"},
        request_body={},
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    StreamRecorder().record_turn(turn, tmp_path)

    result = validate_recorded_fixtures(tmp_path)

    assert result.ok is True
    assert result.checked == 1
    assert result.skipped is False
    assert result.raw_chunks == 1
    assert result.by_adapter_kind == {"openai_compat": 1}
    assert result.by_model == {"fake": 1}
    assert {"text", "stop_reason", "stop_reason:stop"}.issubset(result.scenarios)


def test_validate_recorded_fixtures_uses_recorded_adapter_kind(tmp_path) -> None:
    turn = RecordedTurn.create(
        turn_id="validator-recorded-anthropic",
        profile_snapshot={
            "requested_model": "claude-sonnet-4-5",
            "adapter_kind": "anthropic_native",
        },
        request_body={},
        raw_chunks=_anthropic_text_chunks("hello"),
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    StreamRecorder().record_turn(turn, tmp_path)

    result = validate_recorded_fixtures(tmp_path)

    assert result.ok is True
    assert result.checked == 1
    assert result.skipped is False
    assert result.by_adapter_kind == {"anthropic_native": 1}


def test_validate_recorded_fixtures_can_require_samples(tmp_path) -> None:
    result = validate_recorded_fixtures(tmp_path, require=True)

    assert result.ok is False
    assert result.skipped is True
    assert "no recorded fixtures" in result.failures[0]


def test_validate_recorded_fixtures_can_require_adapter_counts(tmp_path) -> None:
    turn = RecordedTurn.create(
        turn_id="validator-recorded-counts",
        profile_snapshot={"requested_model": "fake"},
        request_body={},
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    StreamRecorder().record_turn(turn, tmp_path)

    result = validate_recorded_fixtures(
        tmp_path,
        required_adapter_counts={"openai_compat": 2, "anthropic_native": 1},
    )

    assert result.ok is False
    assert result.checked == 1
    assert result.by_adapter_kind == {"openai_compat": 1}
    assert "anthropic_native>=1, observed 0" in result.failures[0]
    assert "openai_compat>=2, observed 1" in result.failures[1]


def test_validate_recorded_fixtures_can_require_model_counts(tmp_path) -> None:
    turn = RecordedTurn.create(
        turn_id="validator-recorded-model-counts",
        profile_snapshot={"requested_model": "deepseek-reasoner"},
        request_body={},
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    StreamRecorder().record_turn(turn, tmp_path)

    result = validate_recorded_fixtures(
        tmp_path,
        required_model_counts={"deepseek*": 2, "kimi*": 1},
    )

    assert result.ok is False
    assert result.by_model == {"deepseek-reasoner": 1}
    assert "deepseek*>=2, observed 1" in result.failures[0]
    assert "kimi*>=1, observed 0" in result.failures[1]


def test_validate_recorded_fixtures_can_require_scenarios(tmp_path) -> None:
    turn = RecordedTurn.create(
        turn_id="validator-recorded-scenarios",
        profile_snapshot={"requested_model": "deepseek-reasoner"},
        request_body={},
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    StreamRecorder().record_turn(turn, tmp_path)

    result = validate_recorded_fixtures(
        tmp_path,
        required_scenarios={"text", "stop_reason", "missing_case"},
    )

    assert result.ok is False
    assert {"text", "stop_reason", "stop_reason:stop"}.issubset(result.scenarios)
    assert result.failures == [
        "recorded fixtures missing required scenarios: missing_case"
    ]


def test_validate_recorded_fixtures_can_require_redacted_request_body(
    tmp_path,
) -> None:
    turn = RecordedTurn.create(
        turn_id="validator-recorded-redacted",
        profile_snapshot={"requested_model": "deepseek-reasoner"},
        request_body={
            "messages": [
                {"role": "user", "content": "[redacted:6 chars]"},
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_1",
                            "name": "search",
                            "input": "[redacted:14 chars]",
                        }
                    ],
                    "tool_calls": [
                        {
                            "function": {
                                "name": "search",
                                "arguments": "[redacted:14 chars]",
                            }
                        }
                    ],
                },
            ]
        },
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    StreamRecorder().record_turn(turn, tmp_path)

    result = validate_recorded_fixtures(
        tmp_path,
        require_redacted_request=True,
    )

    assert result.ok is True


def test_validate_recorded_fixtures_reports_unredacted_request_body(
    tmp_path,
) -> None:
    turn = RecordedTurn.create(
        turn_id="validator-recorded-unredacted",
        profile_snapshot={"requested_model": "deepseek-reasoner"},
        request_body={
            "messages": [
                {"role": "user", "content": "secret prompt"},
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_1",
                            "name": "search",
                            "input": {"query": "secret"},
                        }
                    ],
                    "tool_calls": [
                        {
                            "function": {
                                "name": "search",
                                "arguments": '{"query":"secret"}',
                            }
                        }
                    ],
                },
            ]
        },
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    StreamRecorder().record_turn(turn, tmp_path)

    result = validate_recorded_fixtures(
        tmp_path,
        require_redacted_request=True,
    )

    assert result.ok is False
    assert "request body is not redacted" in result.failures[0]
    assert "messages[0].content" in result.failures[0]
    assert "messages[1].content[0].input" in result.failures[0]
    assert "messages[1].tool_calls[0].function.arguments" in result.failures[0]


def test_validate_anthropic_fixtures_replays_committed_fixture() -> None:
    result = validate_anthropic_fixtures(_ANTHROPIC_FIXTURES)

    assert result.ok is True
    assert result.checked >= 1
    assert result.raw_chunks >= 1
    assert {
        "signed_thinking",
        "redacted_thinking",
        "tool_use",
        "tool_result",
        "usage",
        "stop_reason",
    }.issubset(result.scenarios)
    assert result.skipped is False


def test_validate_anthropic_fixtures_can_require_raw_chunks() -> None:
    result = validate_anthropic_fixtures(
        _ANTHROPIC_FIXTURES,
        require_min_raw_chunks=10_000,
    )

    assert result.ok is False
    assert result.raw_chunks >= 1
    assert "raw_chunks>=10000" in result.failures[0]


def test_validate_anthropic_fixtures_can_require_scenarios() -> None:
    result = validate_anthropic_fixtures(
        _ANTHROPIC_FIXTURES,
        required_scenarios={"signed_thinking", "redacted_thinking", "unknown_case"},
    )

    assert result.ok is False
    assert "unknown_case" in result.failures[0]
    assert "redacted_thinking" not in result.failures[0]
    assert "signed_thinking" not in result.failures[0]


def test_main_can_write_json_report(tmp_path) -> None:
    turn = RecordedTurn.create(
        turn_id="validator-json-report",
        profile_snapshot={"requested_model": "deepseek-reasoner"},
        request_body={},
        raw_chunks=[_content_chunk("hello", "stop")],
        expected_events=[
            {"type": "text_delta", "text": "hello"},
            {"type": "text", "text": "hello"},
        ],
        expected_legacy_dict={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {},
            "stop_reason": "stop",
            "latency_ms": 0,
            "first_chunk_latency_ms": None,
            "reasoning_text": "",
            "text_content": "hello",
        },
        timestamp="2026-04-30T00:00:00+00:00",
    )
    StreamRecorder().record_turn(turn, tmp_path)
    report_path = tmp_path / "reports" / "model-adapter.json"

    exit_code = main(
        [
            "--recorded-dir",
            str(tmp_path),
            "--skip-anthropic",
            "--json-report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 1
    assert report["ok"] is True
    assert report["summary"] == {
        "categories": 1,
        "checked": 1,
        "failures": 0,
        "raw_chunks": 1,
        "skipped": 0,
    }
    assert report["results"][0]["name"] == "recorded_model_adapter"
    assert report["results"][0]["by_model"] == {"deepseek-reasoner": 1}
    assert report["results"][0]["raw_chunks"] == 1
    assert report["results"][0]["scenarios"] == [
        "stop_reason",
        "stop_reason:stop",
        "text",
    ]


def test_main_rejects_empty_validation_run() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--skip-recorded", "--skip-anthropic"])

    assert exc_info.value.code == 2


def test_main_can_fail_on_skipped_categories(tmp_path) -> None:
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--recorded-dir",
            str(tmp_path / "missing-recorded"),
            "--skip-anthropic",
            "--fail-on-skipped",
            "--json-report",
            str(report_path),
        ]
    )

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is False
    assert report["summary"]["skipped"] == 1
    assert report["summary"]["failures"] == 1
    assert report["results"][0]["status"] == "failed"
    assert "--fail-on-skipped" in report["results"][0]["failures"][0]
