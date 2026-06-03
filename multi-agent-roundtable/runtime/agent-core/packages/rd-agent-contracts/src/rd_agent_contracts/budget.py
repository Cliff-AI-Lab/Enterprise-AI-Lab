"""BudgetEnvelope — 嵌套预算建模（数据），分配算法在 P5。

P1 只放结构。subagent 嵌套时 parent_budget_id 形成树，P5 分配，P8 持久化。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetEnvelope:
    budget_id: str
    parent_budget_id: str | None
    allocated_tokens: int
    allocated_credits: int
    tool_budget: int
    hard_limit_tokens: int
    soft_limit_tokens: int
    spent_tokens: int

    def __post_init__(self) -> None:
        if self.soft_limit_tokens > self.hard_limit_tokens:
            raise ValueError("soft_limit_tokens must be <= hard_limit_tokens")

    def is_root(self) -> bool:
        return self.parent_budget_id is None

    def remaining_tokens(self) -> int:
        return max(0, self.allocated_tokens - self.spent_tokens)

    def is_hard_limit_exceeded(self) -> bool:
        return self.spent_tokens >= self.hard_limit_tokens
