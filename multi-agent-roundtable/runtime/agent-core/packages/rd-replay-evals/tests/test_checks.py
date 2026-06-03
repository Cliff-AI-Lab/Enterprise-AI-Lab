"""5 条 replay 通过条件的检查器测试。"""
import pytest
from rd_agent_contracts import AgentEvent, StopReason, Usage
from rd_replay_evals.checks import (
    ReplayMismatch,
    check_event_sequence_match,
    check_stop_reason_match,
    check_tool_call_set_match,
    check_transcript_hash_match,
    check_usage_match,
)


def _make_event(seq: int, event_type: str, **payload):
    return AgentEvent(
        seq=seq,
        timestamp_ms=seq,
        run_id="r",
        turn_id="t",
        event_type=event_type,
        payload=payload,
    )


def test_event_sequence_match_pass():
    expected = [
        _make_event(1, "text_delta", text="a"),
        _make_event(2, "text_delta", text="b"),
    ]
    actual = [
        _make_event(1, "text_delta", text="a"),
        _make_event(2, "text_delta", text="b"),
    ]
    check_event_sequence_match(expected, actual)


def test_event_sequence_mismatch_raises():
    expected = [_make_event(1, "text_delta", text="a")]
    actual = [_make_event(1, "text_delta", text="DIFFERENT")]
    with pytest.raises(ReplayMismatch, match="event"):
        check_event_sequence_match(expected, actual)


def test_tool_call_set_match():
    expected = [
        _make_event(1, "tool_use", tool_use_id="tu_1"),
        _make_event(2, "tool_use", tool_use_id="tu_2"),
    ]
    actual = [
        _make_event(1, "tool_use", tool_use_id="tu_2"),
        _make_event(2, "tool_use", tool_use_id="tu_1"),
    ]
    # set 相等即通过（顺序不同 OK）
    check_tool_call_set_match(expected, actual)


def test_tool_call_set_mismatch():
    expected = [_make_event(1, "tool_use", tool_use_id="tu_1")]
    actual = [_make_event(1, "tool_use", tool_use_id="tu_OTHER")]
    with pytest.raises(ReplayMismatch, match="tool_call"):
        check_tool_call_set_match(expected, actual)


def test_transcript_hash_match():
    events = [
        _make_event(1, "text_delta", text="a"),
        _make_event(2, "text_delta", text="b"),
    ]
    check_transcript_hash_match(events, events)


def test_stop_reason_match():
    check_stop_reason_match(StopReason.END_TURN, StopReason.END_TURN)
    with pytest.raises(ReplayMismatch, match="stop_reason"):
        check_stop_reason_match(StopReason.END_TURN, StopReason.MAX_TURNS)


def test_usage_match_with_zero_tolerance():
    """usage 缺失/为 0 都算通过（contracts 容错语义）。"""
    check_usage_match(
        Usage(input_tokens=100, output_tokens=50),
        Usage(input_tokens=100, output_tokens=50),
    )
    # 0 vs 0 通过
    check_usage_match(Usage(), Usage())
    # 不同 tokens 失败
    with pytest.raises(ReplayMismatch):
        check_usage_match(
            Usage(input_tokens=100, output_tokens=0),
            Usage(input_tokens=200, output_tokens=0),
        )
