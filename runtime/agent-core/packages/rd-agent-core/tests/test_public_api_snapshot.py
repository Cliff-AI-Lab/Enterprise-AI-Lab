from __future__ import annotations

import inspect
from dataclasses import fields

import rd_agent_core
from rd_agent_core import (
    AgentRunner,
    AgentRunnerRequest,
    CoreToolPolicy,
    RunKernel,
    RunRequest,
    ToolSafetyPolicy,
    TurnKernel,
    TurnRequest,
)
from rd_agent_core.llm_clients import (
    AnthropicNativeLLMClient,
    OpenAICompatLLMClient,
    ProviderClientConfig,
)


def _keyword_only_names(callable_obj) -> tuple[str, ...]:
    signature = inspect.signature(callable_obj)
    return tuple(
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
    )


def _dataclass_field_names(cls) -> tuple[str, ...]:
    return tuple(field.name for field in fields(cls))


def test_public_core_exports_snapshot() -> None:
    expected = {
        "AgentRunner",
        "AgentRunnerRequest",
        "AgentRunnerResult",
        "CoreErrorCategory",
        "CoreErrorType",
        "RunKernel",
        "RunObserverPort",
        "RunRequest",
        "RunSummary",
        "ToolSafetyPolicy",
        "TurnKernel",
        "TurnRequest",
        "assert_event_log_port_conformance",
        "assert_run_persistence_port_conformance",
        "assert_tool_executor_port_conformance",
    }

    assert expected.issubset(set(rd_agent_core.__all__))


def test_public_constructor_signature_snapshot() -> None:
    assert _keyword_only_names(AgentRunner.__init__) == (
        "run_persistence",
        "event_log",
        "llm_client",
        "tool_executor",
        "tool_observability",
        "tool_policy",
        "run_observer",
        "id_generator",
    )
    assert _keyword_only_names(RunKernel.__init__) == (
        "llm_client",
        "event_writer",
        "tool_executor",
        "tool_observability",
        "tool_policy",
        "id_generator",
        "clock",
    )
    assert _keyword_only_names(TurnKernel.__init__) == (
        "llm_client",
        "event_writer",
        "tool_executor",
        "tool_observability",
        "tool_policy",
    )


def test_public_dataclass_field_snapshot() -> None:
    assert _dataclass_field_names(AgentRunnerRequest) == (
        "scope",
        "budget",
        "messages",
        "tools",
        "tool_context",
        "run_id",
        "max_continuations",
        "model",
        "system_prompt",
        "limits",
        "metadata",
        "cancellation_token",
    )
    assert _dataclass_field_names(RunRequest) == (
        "run_id",
        "messages",
        "tool_context",
        "tools",
        "model",
        "system_prompt",
        "limits",
        "metadata",
        "turn_offset",
        "cancellation_token",
    )
    assert _dataclass_field_names(TurnRequest) == (
        "run_id",
        "turn_id",
        "messages",
        "tool_context",
        "model",
        "system_prompt",
        "tools",
        "turn_index",
        "metadata",
        "cancellation_token",
    )
    assert _dataclass_field_names(ToolSafetyPolicy) == (
        "allowed_tool_names",
        "blocked_tool_names",
        "require_confirmation_for_mutating_tools",
        "confirmed_tool_use_ids",
    )
    assert _dataclass_field_names(CoreToolPolicy) == (
        "pause_tool_names",
        "pause_stop_reason",
        "safety_policy",
    )
    assert _dataclass_field_names(ProviderClientConfig) == (
        "model",
        "api_key",
        "base_url",
        "timeout",
        "max_tokens",
        "extra_headers",
        "profile",
    )


def test_provider_client_init_signature_snapshot() -> None:
    assert tuple(inspect.signature(OpenAICompatLLMClient.__init__).parameters) == (
        "self",
        "config",
        "adapter",
        "transport",
        "supports_function_calling",
        "supports_stream_usage",
        "reasoning_effort",
    )
    assert tuple(inspect.signature(AnthropicNativeLLMClient.__init__).parameters) == (
        "self",
        "config",
        "adapter",
        "transport",
        "thinking_budget_tokens",
    )
