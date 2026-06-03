from __future__ import annotations

from rd_agent_core import (
    RunLimits,
    RunLimitState,
    evaluate_run_limits,
    has_repeated_tool_call,
    tool_call_signature,
)


def test_evaluate_run_limits_allows_when_no_limit_is_exhausted() -> None:
    decision = evaluate_run_limits(
        RunLimits(max_turns=3, max_tool_calls=10, timeout_ms=1000),
        RunLimitState(turns_used=2, tool_calls_used=9, elapsed_ms=999),
    )

    assert decision.allowed
    assert decision.limit_name is None


def test_evaluate_run_limits_blocks_first_exhausted_limit() -> None:
    decision = evaluate_run_limits(
        RunLimits(max_turns=3, max_tool_calls=10),
        RunLimitState(turns_used=3, tool_calls_used=0),
    )

    assert not decision.allowed
    assert decision.limit_name == "max_turns"


def test_evaluate_run_limits_uses_lifecycle_stop_reason_for_timeout() -> None:
    decision = evaluate_run_limits(
        RunLimits(timeout_ms=1000),
        RunLimitState(elapsed_ms=1000),
    )

    assert not decision.allowed
    assert decision.reason == "max_wall_clock reached"
    assert decision.limit_name == "max_wall_clock"


def test_tool_call_signature_is_stable_for_equivalent_inputs() -> None:
    first = tool_call_signature("write_file", {"path": "a.txt", "content": "x"})
    second = tool_call_signature("write_file", {"content": "x", "path": "a.txt"})

    assert first == second
    assert first.to_key().startswith("write_file:")


def test_repeated_tool_call_detection_uses_threshold() -> None:
    candidate = tool_call_signature("read_file", {"path": "README.md"})
    other = tool_call_signature("read_file", {"path": "pyproject.toml"})

    assert has_repeated_tool_call([candidate, other, candidate], candidate=candidate, threshold=2)
    assert not has_repeated_tool_call([candidate, other], candidate=candidate, threshold=2)
