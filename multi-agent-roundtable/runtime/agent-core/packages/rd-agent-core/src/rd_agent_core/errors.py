"""Stable error classification helpers for core boundaries."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class CoreErrorCategory(StrEnum):
    PROVIDER = "provider"
    TOOL_ERROR = "tool_error"
    TOOL_POLICY = "tool_policy"
    TOOL_UNAVAILABLE = "tool_unavailable"
    INVALID_TOOL_CALL = "invalid_tool_call"
    RUN_LIMIT = "run_limit"
    CANCELLED = "cancelled"
    INTERNAL = "internal"


class CoreErrorType(StrEnum):
    CANCELLED = "cancelled"
    MAX_TOOL_CALLS = "max_tool_calls"
    REPEATED_TOOL_CALL = "repeated_tool_call"
    TOOL_BLOCKED = "tool_blocked"
    TOOL_CONFIRMATION_REQUIRED = "tool_confirmation_required"
    TOOL_EXECUTOR_MISSING = "tool_executor_missing"
    TOOL_NOT_ALLOWED = "tool_not_allowed"
    TOOL_NOT_DECLARED = "tool_not_declared"
    TOOL_SKIPPED_AFTER_PAUSE = "tool_skipped_after_pause"


_ERROR_TYPE_CATEGORIES: dict[str, CoreErrorCategory] = {
    CoreErrorType.CANCELLED.value: CoreErrorCategory.CANCELLED,
    CoreErrorType.MAX_TOOL_CALLS.value: CoreErrorCategory.RUN_LIMIT,
    CoreErrorType.REPEATED_TOOL_CALL.value: CoreErrorCategory.RUN_LIMIT,
    CoreErrorType.TOOL_BLOCKED.value: CoreErrorCategory.TOOL_POLICY,
    CoreErrorType.TOOL_CONFIRMATION_REQUIRED.value: CoreErrorCategory.TOOL_POLICY,
    CoreErrorType.TOOL_EXECUTOR_MISSING.value: CoreErrorCategory.TOOL_UNAVAILABLE,
    CoreErrorType.TOOL_NOT_ALLOWED.value: CoreErrorCategory.TOOL_POLICY,
    CoreErrorType.TOOL_NOT_DECLARED.value: CoreErrorCategory.TOOL_UNAVAILABLE,
    CoreErrorType.TOOL_SKIPPED_AFTER_PAUSE.value: CoreErrorCategory.TOOL_POLICY,
}


def classify_core_error(error_type: str | None) -> CoreErrorCategory:
    if not error_type:
        return CoreErrorCategory.INTERNAL
    return _ERROR_TYPE_CATEGORIES.get(str(error_type), CoreErrorCategory.TOOL_ERROR)


def core_error(
    error_type: str,
    message: str,
    *,
    category: CoreErrorCategory | str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_category = (
        CoreErrorCategory(str(category))
        if category is not None
        else classify_core_error(error_type)
    )
    payload: dict[str, Any] = {
        "type": error_type,
        "message": message,
        "category": resolved_category.value,
    }
    if details:
        payload["details"] = details
    return payload
