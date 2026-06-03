from rd_agent_contracts.run_persistence import AgentKind, RunStatus
from rd_agent_contracts.run_policy import (
    CONTINUABLE_STOP_REASONS,
    NEEDS_ATTENTION_STOP_REASONS,
    TERMINAL_WAIT_REASONS,
    completion_status_for_stop_reason,
    is_continuable_stop_reason,
    is_terminal_wait_stop_reason,
    needs_attention_for_stop_reason,
    should_auto_continue_run,
)


def test_run_policy_stop_reason_sets_match_current_lifecycle_contract():
    assert CONTINUABLE_STOP_REASONS == frozenset({"max_turns", "loop_break:max_turns"})
    assert TERMINAL_WAIT_REASONS == frozenset({"ask_user"})
    assert NEEDS_ATTENTION_STOP_REASONS == frozenset(
        {
            "max_turns",
            "max_wall_clock",
            "timeout_ms",
            "loop_break:max_turns",
            "loop_break:no_progress",
            "loop_break:max_tool_calls",
            "loop_break:max_wall_clock",
            "loop_break:repeated_tool_call",
            "repeated_tool_call",
            "empty_response",
        }
    )


def test_run_policy_stop_reason_predicates():
    assert is_continuable_stop_reason("max_turns") is True
    assert is_terminal_wait_stop_reason("ask_user") is True
    assert needs_attention_for_stop_reason("loop_break:no_progress") is True
    assert needs_attention_for_stop_reason("loop_break:repeated_tool_call") is True
    assert needs_attention_for_stop_reason("max_wall_clock") is True
    assert needs_attention_for_stop_reason("timeout_ms") is True

    assert is_continuable_stop_reason("ask_user") is False
    assert is_terminal_wait_stop_reason("max_turns") is False
    assert needs_attention_for_stop_reason(None) is False


def test_should_auto_continue_run_requires_root_orchestrator_capacity():
    assert should_auto_continue_run(
        auto_continue_enabled=True,
        agent_kind=AgentKind.ORCHESTRATOR,
        subagent_task_id=None,
        stop_reason="max_turns",
        continuation_index=0,
        max_continuations=1,
    )

    assert not should_auto_continue_run(
        auto_continue_enabled=False,
        agent_kind=AgentKind.ORCHESTRATOR,
        subagent_task_id=None,
        stop_reason="max_turns",
        continuation_index=0,
        max_continuations=1,
    )
    assert not should_auto_continue_run(
        auto_continue_enabled=True,
        agent_kind=AgentKind.SUBAGENT,
        subagent_task_id="sub_1",
        stop_reason="max_turns",
        continuation_index=0,
        max_continuations=1,
    )
    assert not should_auto_continue_run(
        auto_continue_enabled=True,
        agent_kind=AgentKind.ORCHESTRATOR,
        subagent_task_id=None,
        stop_reason="max_turns",
        continuation_index=1,
        max_continuations=1,
    )


def test_completion_status_for_stop_reason():
    assert (
        completion_status_for_stop_reason(
            stop_reason="ask_user",
            can_auto_continue=False,
        )
        == RunStatus.WAITING_USER
    )
    assert (
        completion_status_for_stop_reason(
            stop_reason="max_turns",
            can_auto_continue=True,
        )
        == RunStatus.CONTINUABLE
    )
    assert (
        completion_status_for_stop_reason(
            stop_reason="loop_break:no_progress",
            can_auto_continue=False,
        )
        == RunStatus.NEEDS_ATTENTION
    )
    assert (
        completion_status_for_stop_reason(
            stop_reason="max_turns",
            can_auto_continue=False,
        )
        == RunStatus.NEEDS_ATTENTION
    )
    assert (
        completion_status_for_stop_reason(
            stop_reason="loop_break:repeated_tool_call",
            can_auto_continue=False,
        )
        == RunStatus.NEEDS_ATTENTION
    )
    assert (
        completion_status_for_stop_reason(
            stop_reason="max_wall_clock",
            can_auto_continue=False,
        )
        == RunStatus.NEEDS_ATTENTION
    )
    assert (
        completion_status_for_stop_reason(
            stop_reason="timeout_ms",
            can_auto_continue=False,
        )
        == RunStatus.NEEDS_ATTENTION
    )
    assert (
        completion_status_for_stop_reason(
            stop_reason="end_turn",
            can_auto_continue=False,
        )
        == RunStatus.COMPLETED
    )
