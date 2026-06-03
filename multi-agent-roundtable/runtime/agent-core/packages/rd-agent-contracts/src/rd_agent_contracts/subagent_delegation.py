"""Host-neutral subagent delegation policy."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .run_persistence import AgentKind


@dataclass(frozen=True)
class SubagentDelegationContext:
    instruction: str
    session_messages: list[Mapping[str, Any]] = field(default_factory=list)
    file_count: int = 0
    available_tool_names: set[str] = field(default_factory=set)
    agent_kind: str = "orchestrator"
    has_open_subagent_tasks: bool = False
    has_satisfied_subagent_tasks: bool = False


@dataclass(frozen=True)
class SubagentDelegationDecision:
    required: bool
    reason: str | None = None


@dataclass(frozen=True)
class SubagentDelegationRuleSet:
    """Configurable heuristic rules for host-owned subagent delegation.

    The contracts package owns the generic decision shape and safety gates. Product
    hosts own domain terms such as frontend/backend/database/product-generation
    keywords by passing a rule set.
    """

    orchestrator_agent_kind: str = AgentKind.ORCHESTRATOR
    create_task_tool_name: str = "create_subagent_task"
    recent_history_window: int = 10
    max_short_instruction_chars: int = 12
    large_project_file_threshold: int = 80
    backend_complex_min_score: int = 3
    large_project_complex_min_score: int = 2
    short_continuation_words: frozenset[str] = frozenset({
        "继续",
        "确认",
        "执行",
        "开始",
        "可以",
        "好的",
        "好",
        "yes",
        "ok",
        "go",
    })
    explicit_subagent_terms: tuple[str, ...] = (
        "subagent",
        "sub-agent",
        "子agent",
        "子 agent",
        "多agent",
        "多 agent",
        "multi-agent",
        "并行",
    )
    frontend_terms: tuple[str, ...] = ()
    backend_terms: tuple[str, ...] = ()
    complex_product_terms: tuple[str, ...] = ()
    product_generation_terms: tuple[str, ...] = ()
    product_scope_terms: tuple[str, ...] = ()
    database_terms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.orchestrator_agent_kind:
            raise ValueError("orchestrator_agent_kind must be non-empty")
        if not self.create_task_tool_name:
            raise ValueError("create_task_tool_name must be non-empty")
        for field_name in (
            "recent_history_window",
            "max_short_instruction_chars",
            "large_project_file_threshold",
            "backend_complex_min_score",
            "large_project_complex_min_score",
        ):
            if getattr(self, field_name) < 1:
                raise ValueError(f"{field_name} must be >= 1")


def decide_subagent_delegation(
    context: SubagentDelegationContext,
    *,
    rules: SubagentDelegationRuleSet | None = None,
) -> SubagentDelegationDecision:
    resolved_rules = rules or SubagentDelegationRuleSet()
    if context.agent_kind != resolved_rules.orchestrator_agent_kind:
        return SubagentDelegationDecision(required=False)
    if resolved_rules.create_task_tool_name not in context.available_tool_names:
        return SubagentDelegationDecision(required=False)
    if context.has_open_subagent_tasks:
        return SubagentDelegationDecision(
            required=True,
            reason="已有子 Agent 任务尚未完成，root orchestrator 需要等待或检查子任务状态",
        )
    if context.has_satisfied_subagent_tasks:
        return SubagentDelegationDecision(required=False)

    current_instruction = " ".join(str(context.instruction or "").split())
    if not current_instruction:
        return SubagentDelegationDecision(required=False)

    should_use_history = (
        len(current_instruction) <= resolved_rules.max_short_instruction_chars
        or current_instruction.lower() in resolved_rules.short_continuation_words
    )
    signal_text = current_instruction
    if should_use_history:
        recent_user_texts = [
            _message_text(message)
            for message in context.session_messages[-resolved_rules.recent_history_window :]
            if message.get("role") == "user"
        ]
        signal_text = "\n".join([*recent_user_texts, current_instruction])

    if _contains_any(signal_text, resolved_rules.explicit_subagent_terms):
        return SubagentDelegationDecision(
            required=True,
            reason="用户明确要求子 Agent、多 Agent或并行任务",
        )
    has_frontend = _contains_any(signal_text, resolved_rules.frontend_terms)
    has_backend = _contains_any(signal_text, resolved_rules.backend_terms)
    if has_frontend and has_backend:
        return SubagentDelegationDecision(
            required=True,
            reason="任务同时包含前端和后端/API工作流",
        )

    has_database = _contains_any(signal_text, resolved_rules.database_terms)
    has_product_generation = _contains_any(
        signal_text, resolved_rules.product_generation_terms
    )
    has_product_scope = _contains_any(signal_text, resolved_rules.product_scope_terms)
    if has_backend and has_database and has_product_generation and has_product_scope:
        return SubagentDelegationDecision(
            required=True,
            reason="任务要求后端/数据库且属于产品级应用生成",
        )

    complex_score = sum(
        1
        for term in resolved_rules.complex_product_terms
        if term.lower() in signal_text.lower()
    )
    if has_backend and complex_score >= resolved_rules.backend_complex_min_score:
        return SubagentDelegationDecision(
            required=True,
            reason="任务包含后端/API及多个产品级复杂能力",
        )
    if (
        context.file_count >= resolved_rules.large_project_file_threshold
        and has_backend
        and complex_score >= resolved_rules.large_project_complex_min_score
    ):
        return SubagentDelegationDecision(
            required=True,
            reason="现有项目较大且任务涉及后端/API复杂改动",
        )
    return SubagentDelegationDecision(required=False)


def _message_text(message: Mapping[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, Mapping):
                text = block.get("text") or block.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)
