import pytest
from rd_agent_contracts.budget import BudgetEnvelope


def test_budget_envelope_root():
    b = BudgetEnvelope(
        budget_id="budget_1",
        parent_budget_id=None,
        allocated_tokens=10000,
        allocated_credits=1000,
        tool_budget=50,
        hard_limit_tokens=20000,
        soft_limit_tokens=15000,
        spent_tokens=0,
    )
    assert b.parent_budget_id is None
    assert b.is_root()


def test_budget_envelope_subagent():
    b = BudgetEnvelope(
        budget_id="budget_2",
        parent_budget_id="budget_1",
        allocated_tokens=5000,
        allocated_credits=500,
        tool_budget=20,
        hard_limit_tokens=8000,
        soft_limit_tokens=6000,
        spent_tokens=0,
    )
    assert not b.is_root()


def test_budget_remaining():
    b = BudgetEnvelope(
        budget_id="budget_1",
        parent_budget_id=None,
        allocated_tokens=10000,
        allocated_credits=1000,
        tool_budget=50,
        hard_limit_tokens=20000,
        soft_limit_tokens=15000,
        spent_tokens=3000,
    )
    assert b.remaining_tokens() == 7000


def test_budget_exceeded():
    b = BudgetEnvelope(
        budget_id="budget_1",
        parent_budget_id=None,
        allocated_tokens=10000,
        allocated_credits=1000,
        tool_budget=50,
        hard_limit_tokens=20000,
        soft_limit_tokens=15000,
        spent_tokens=22000,
    )
    assert b.is_hard_limit_exceeded()


def test_budget_invalid_when_soft_gt_hard():
    with pytest.raises(ValueError, match="soft_limit"):
        BudgetEnvelope(
            budget_id="x",
            parent_budget_id=None,
            allocated_tokens=10,
            allocated_credits=1,
            tool_budget=1,
            hard_limit_tokens=100,
            soft_limit_tokens=200,
            spent_tokens=0,
        )
