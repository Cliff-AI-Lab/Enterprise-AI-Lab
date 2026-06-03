from __future__ import annotations

from rd_agent_core import CoreErrorCategory, classify_core_error, core_error


def test_core_error_adds_stable_category() -> None:
    assert core_error("tool_blocked", "blocked") == {
        "type": "tool_blocked",
        "message": "blocked",
        "category": "tool_policy",
    }


def test_classify_core_error_defaults_unknown_tool_errors() -> None:
    assert classify_core_error("ValueError") == CoreErrorCategory.TOOL_ERROR
    assert classify_core_error(None) == CoreErrorCategory.INTERNAL
