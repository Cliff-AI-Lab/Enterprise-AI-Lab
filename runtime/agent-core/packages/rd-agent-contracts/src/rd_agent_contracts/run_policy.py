"""Shared AgentRun lifecycle policy helpers."""
from __future__ import annotations

from .enums import StopReason
from .run_persistence import AgentKind, RunStatus

CONTINUABLE_STOP_REASONS = frozenset({
    StopReason.MAX_TURNS.value,
    "loop_break:max_turns",
})
TERMINAL_WAIT_REASONS = frozenset({StopReason.ASK_USER.value})
NEEDS_ATTENTION_STOP_REASONS = frozenset({
    StopReason.MAX_TURNS.value,
    StopReason.MAX_WALL_CLOCK.value,
    StopReason.LOOP_BREAK_NO_PROGRESS.value,
    "timeout_ms",
    "loop_break:max_turns",
    "loop_break:max_tool_calls",
    "loop_break:max_wall_clock",
    "loop_break:repeated_tool_call",
    "repeated_tool_call",
    "empty_response",
})


def is_continuable_stop_reason(stop_reason: str | None) -> bool:
    return stop_reason in CONTINUABLE_STOP_REASONS


def is_terminal_wait_stop_reason(stop_reason: str | None) -> bool:
    return stop_reason in TERMINAL_WAIT_REASONS


def needs_attention_for_stop_reason(stop_reason: str | None) -> bool:
    return stop_reason in NEEDS_ATTENTION_STOP_REASONS


def should_auto_continue_run(
    *,
    auto_continue_enabled: bool,
    agent_kind: str,
    subagent_task_id: str | None,
    stop_reason: str | None,
    continuation_index: int,
    max_continuations: int,
) -> bool:
    if not auto_continue_enabled:
        return False
    if agent_kind != AgentKind.ORCHESTRATOR:
        return False
    if subagent_task_id is not None:
        return False
    if not is_continuable_stop_reason(stop_reason):
        return False
    return continuation_index < max_continuations


def completion_status_for_stop_reason(
    *,
    stop_reason: str | None,
    can_auto_continue: bool,
) -> str:
    if is_terminal_wait_stop_reason(stop_reason):
        return RunStatus.WAITING_USER.value
    if can_auto_continue:
        return RunStatus.CONTINUABLE.value
    if needs_attention_for_stop_reason(stop_reason):
        return RunStatus.NEEDS_ATTENTION.value
    return RunStatus.COMPLETED.value
