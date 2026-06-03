"""Host-neutral subagent task and profile contracts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class SubagentTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_USER = "waiting_user"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


TERMINAL_SUBAGENT_STATUSES = frozenset(
    {
        SubagentTaskStatus.COMPLETED.value,
        SubagentTaskStatus.FAILED.value,
        SubagentTaskStatus.CANCELLED.value,
        SubagentTaskStatus.DEAD_LETTER.value,
    }
)


class SubagentProfileId(StrEnum):
    GENERAL = "general"
    PLANNER = "planner"
    FRONTEND_EDITOR = "frontend_editor"
    BACKEND_EDITOR = "backend_editor"
    DEBUGGER = "debugger"
    BROWSER_VERIFIER = "browser_verifier"


def normalize_write_scope_paths(write_scope_json: Mapping[str, Any] | None) -> list[str]:
    if not write_scope_json:
        return []
    raw_paths = write_scope_json.get("paths")
    if not isinstance(raw_paths, Sequence) or isinstance(raw_paths, (str, bytes)):
        return []
    paths: list[str] = []
    for raw_path in raw_paths:
        path = str(raw_path or "").strip().replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        path = path.strip("/")
        if path and path != "." and path not in paths:
            paths.append(path)
    return paths


def normalize_subagent_scope_path(path: str) -> str:
    normalized = str(path or "").strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def is_path_in_write_scope(path: str, scope_paths: Sequence[str]) -> bool:
    normalized = normalize_subagent_scope_path(path)
    if not normalized:
        return False
    return any(
        normalized == scope_path or normalized.startswith(f"{scope_path}/")
        for scope_path in scope_paths
    )


def find_write_scope_violations(
    paths: Iterable[str],
    write_scope_json: Mapping[str, Any] | None,
) -> list[str]:
    scope_paths = normalize_write_scope_paths(write_scope_json)
    if not scope_paths:
        return []
    return [
        path
        for path in paths
        if str(path or "").strip() and not is_path_in_write_scope(path, scope_paths)
    ]


def write_scopes_overlap(left: Sequence[str], right: Sequence[str]) -> bool:
    if not left or not right:
        return True
    for left_path in left:
        for right_path in right:
            if (
                left_path == right_path
                or left_path.startswith(f"{right_path}/")
                or right_path.startswith(f"{left_path}/")
            ):
                return True
    return False


@dataclass(frozen=True)
class SubagentProfile:
    profile_id: str
    label: str
    purpose: str
    tool_allowlist: tuple[str, ...] = ()
    tool_denylist: tuple[str, ...] = ()
    model_profile: str | None = None
    requires_write_scope: bool = False
    can_run_commands: bool = True
    can_ask_user: bool = False
    verification_required: bool = False
    system_guidance: str = ""

    def allows_tool(self, tool_name: str) -> bool:
        if self.tool_allowlist and tool_name not in self.tool_allowlist:
            return False
        return tool_name not in self.tool_denylist


READ_ONLY_TOOLS = ("read_file", "list_dir", "glob_search", "grep_search")
WRITE_TOOLS = (
    "append_file",
    "write_file",
    "edit_file",
    "replace_range",
    "apply_patch",
    "delete_file",
    "move_file",
    "copy_file",
    "create_directory",
)
DIAGNOSTIC_TOOLS = (
    "run_command",
    "start_server",
    "get_preview_status",
    "get_server_logs",
    "run_tests",
    "run_lint",
    "run_build",
    "run_typecheck",
    "run_verification",
)
BROWSER_TOOLS = (
    "browser_open_preview",
    "browser_snapshot",
    "browser_click",
    "browser_fill",
    "browser_assert_text",
    "browser_console_logs",
    "browser_network_errors",
    "browser_close",
)
TASK_TOOLS = ("set_task_plan", "update_task_plan", "get_task_plan")
WEB_TOOLS = ("web_search", "web_fetch")


STANDARD_SUBAGENT_PROFILES: dict[str, SubagentProfile] = {
    SubagentProfileId.GENERAL.value: SubagentProfile(
        profile_id=SubagentProfileId.GENERAL.value,
        label="General",
        purpose="General bounded task execution.",
        tool_denylist=("ask_user", "create_subagent_task", "list_subagent_tasks"),
        system_guidance="Execute only the assigned task scope and summarize changes and risks.",
    ),
    SubagentProfileId.PLANNER.value: SubagentProfile(
        profile_id=SubagentProfileId.PLANNER.value,
        label="Planner",
        purpose="Read-only planning, decomposition, and risk analysis.",
        tool_allowlist=READ_ONLY_TOOLS + TASK_TOOLS + WEB_TOOLS,
        can_run_commands=False,
        verification_required=False,
        system_guidance="Plan and inspect only. Do not mutate files or run services.",
    ),
    SubagentProfileId.FRONTEND_EDITOR.value: SubagentProfile(
        profile_id=SubagentProfileId.FRONTEND_EDITOR.value,
        label="Frontend Editor",
        purpose="Frontend implementation within declared UI/client scopes.",
        tool_allowlist=READ_ONLY_TOOLS + WRITE_TOOLS + DIAGNOSTIC_TOOLS + TASK_TOOLS,
        requires_write_scope=True,
        verification_required=True,
        system_guidance=(
            "Focus on UI/client changes inside write_scope and run focused verification."
        ),
    ),
    SubagentProfileId.BACKEND_EDITOR.value: SubagentProfile(
        profile_id=SubagentProfileId.BACKEND_EDITOR.value,
        label="Backend Editor",
        purpose="Backend, API, data, and service implementation within declared scopes.",
        tool_allowlist=READ_ONLY_TOOLS + WRITE_TOOLS + DIAGNOSTIC_TOOLS + TASK_TOOLS,
        requires_write_scope=True,
        verification_required=True,
        system_guidance=(
            "Focus on backend/API changes inside write_scope and run focused verification."
        ),
    ),
    SubagentProfileId.DEBUGGER.value: SubagentProfile(
        profile_id=SubagentProfileId.DEBUGGER.value,
        label="Debugger",
        purpose="Failure triage and targeted fixes with diagnostics.",
        tool_allowlist=READ_ONLY_TOOLS + WRITE_TOOLS + DIAGNOSTIC_TOOLS + TASK_TOOLS + WEB_TOOLS,
        verification_required=True,
        system_guidance="Reproduce or inspect the failure, make the smallest fix, then verify.",
    ),
    SubagentProfileId.BROWSER_VERIFIER.value: SubagentProfile(
        profile_id=SubagentProfileId.BROWSER_VERIFIER.value,
        label="Browser Verifier",
        purpose="Preview and browser-based validation.",
        tool_allowlist=READ_ONLY_TOOLS + DIAGNOSTIC_TOOLS + BROWSER_TOOLS + TASK_TOOLS,
        can_run_commands=True,
        verification_required=True,
        system_guidance="Validate the running app in a browser and report concrete failures.",
    ),
}


_PROFILE_ALIASES = {
    "": SubagentProfileId.GENERAL.value,
    "default": SubagentProfileId.GENERAL.value,
    "generic": SubagentProfileId.GENERAL.value,
    "general": SubagentProfileId.GENERAL.value,
    "plan": SubagentProfileId.PLANNER.value,
    "planner": SubagentProfileId.PLANNER.value,
    "frontend": SubagentProfileId.FRONTEND_EDITOR.value,
    "front-end": SubagentProfileId.FRONTEND_EDITOR.value,
    "frontend_editor": SubagentProfileId.FRONTEND_EDITOR.value,
    "ui": SubagentProfileId.FRONTEND_EDITOR.value,
    "backend": SubagentProfileId.BACKEND_EDITOR.value,
    "back-end": SubagentProfileId.BACKEND_EDITOR.value,
    "backend_editor": SubagentProfileId.BACKEND_EDITOR.value,
    "api": SubagentProfileId.BACKEND_EDITOR.value,
    "server": SubagentProfileId.BACKEND_EDITOR.value,
    "debug": SubagentProfileId.DEBUGGER.value,
    "debugger": SubagentProfileId.DEBUGGER.value,
    "test": SubagentProfileId.BROWSER_VERIFIER.value,
    "tests": SubagentProfileId.BROWSER_VERIFIER.value,
    "qa": SubagentProfileId.BROWSER_VERIFIER.value,
    "review": SubagentProfileId.BROWSER_VERIFIER.value,
    "browser": SubagentProfileId.BROWSER_VERIFIER.value,
    "browser_verifier": SubagentProfileId.BROWSER_VERIFIER.value,
    "verifier": SubagentProfileId.BROWSER_VERIFIER.value,
}


def normalize_subagent_profile_id(raw_profile: str | None) -> str:
    normalized = " ".join(str(raw_profile or "").strip().lower().replace("-", "_").split())
    normalized = normalized.replace(" ", "_")
    if normalized in STANDARD_SUBAGENT_PROFILES:
        return normalized
    return _PROFILE_ALIASES.get(normalized, SubagentProfileId.GENERAL.value)


def resolve_subagent_profile(raw_profile: str | None) -> SubagentProfile:
    return STANDARD_SUBAGENT_PROFILES[normalize_subagent_profile_id(raw_profile)]


def subagent_profile_schema_values() -> list[str]:
    return list(STANDARD_SUBAGENT_PROFILES.keys())


def subagent_profile_allows_tool(
    tool_name: str,
    *,
    agent_profile: str | None,
) -> bool:
    return resolve_subagent_profile(agent_profile).allows_tool(str(tool_name or ""))


def filter_subagent_tools_for_profile[T](
    tools: Iterable[T],
    *,
    agent_profile: str | None,
) -> list[T]:
    return [
        tool
        for tool in tools
        if subagent_profile_allows_tool(
            _tool_definition_name(tool),
            agent_profile=agent_profile,
        )
    ]


def validate_subagent_profile_scope(
    *,
    agent_profile: str | None,
    write_scope_json: Mapping[str, Any] | None,
) -> str | None:
    profile = resolve_subagent_profile(agent_profile)
    scope_paths = normalize_write_scope_paths(write_scope_json)
    if profile.profile_id == SubagentProfileId.BROWSER_VERIFIER.value and scope_paths:
        return (
            "browser_verifier 子任务需要执行构建、启动和浏览器验证，"
            "write_scope 必须留空，由系统串行保护执行"
        )
    if profile.requires_write_scope and not scope_paths:
        return (
            f"{profile.profile_id} 子任务必须声明 write_scope，"
            "否则无法安全并行或限制写入范围"
        )
    return None


def _tool_definition_name(tool: Any) -> str:
    if isinstance(tool, Mapping):
        return str(tool.get("name") or "")
    return str(getattr(tool, "name", "") or "")


@dataclass(frozen=True)
class SubagentTaskSpec:
    user_request_id: str
    project_id: str
    name: str
    description: str
    parent_run_id: str | None = None
    agent_profile: str | None = None
    write_scope_json: dict[str, Any] | None = None
    depends_on_task_ids: list[str] = field(default_factory=list)
    correlation_id: str | None = None
    max_attempts: int = 3
    available_at_ms: int | None = None


@dataclass(frozen=True)
class SubagentTaskRecord:
    task_id: str
    user_request_id: str
    project_id: str
    name: str
    description: str
    status: str
    parent_run_id: str | None = None
    agent_profile: str | None = None
    write_scope_json: dict[str, Any] | None = None
    attempts: int = 0
    max_attempts: int = 3
    worker_id: str | None = None
    result_summary: str | None = None
    outcome_json: dict[str, Any] | None = None
    depends_on_task_ids: list[str] = field(default_factory=list)
    error_message: str | None = None
    correlation_id: str | None = None
    created_at_ms: int | None = None
    available_at_ms: int | None = None
    started_at_ms: int | None = None
    heartbeat_at_ms: int | None = None
    completed_at_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SubagentRunRecord:
    task_id: str
    run_id: str
    user_request_id: str
    project_id: str
    session_id: str | None = None
    parent_run_id: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SubagentTaskPort(Protocol):
    """Persistence and dispatch boundary for subagent task orchestration."""

    def create_task(
        self,
        spec: SubagentTaskSpec,
        *,
        task_id: str | None = None,
    ) -> SubagentTaskRecord: ...

    def list_tasks(self, *, user_request_id: str) -> list[SubagentTaskRecord]: ...

    def load_task(self, task_id: str) -> SubagentTaskRecord | None: ...

    def claim_next_pending(
        self,
        *,
        user_request_id: str | None = None,
        worker_id: str | None = None,
        started_at_ms: int | None = None,
        parent_completed_grace_seconds: float | None = None,
        skip_user_requests_with_running: bool = False,
    ) -> SubagentTaskRecord | None: ...

    def claim_pending_batch(
        self,
        *,
        user_request_id: str,
        worker_id: str | None = None,
        max_count: int = 1,
        candidate_limit: int | None = None,
        started_at_ms: int | None = None,
    ) -> list[SubagentTaskRecord]: ...

    def mark_attempt_started(self, *, task_id: str) -> SubagentTaskRecord | None: ...

    def heartbeat(self, *, task_id: str, heartbeat_at_ms: int | None = None) -> None: ...

    def release_for_retry(
        self,
        *,
        task_id: str,
        error_message: str,
        delay_seconds: int | None = None,
    ) -> SubagentTaskRecord | None: ...

    def reclaim_stale(self, *, stale_threshold_seconds: int | None = None) -> int: ...

    def mark_completed(
        self,
        *,
        task_id: str,
        result_summary: str | None = None,
        outcome_json: dict[str, Any] | None = None,
        completed_at_ms: int | None = None,
    ) -> SubagentTaskRecord | None: ...

    def mark_failed(
        self,
        *,
        task_id: str,
        error_message: str,
        outcome_json: dict[str, Any] | None = None,
        completed_at_ms: int | None = None,
    ) -> SubagentTaskRecord | None: ...

    def mark_waiting(
        self,
        *,
        task_id: str,
        result_summary: str | None = None,
        outcome_json: dict[str, Any] | None = None,
    ) -> SubagentTaskRecord | None: ...

    def mark_running(self, *, task_id: str) -> SubagentTaskRecord | None: ...

    def record_failure(
        self,
        *,
        task_id: str,
        error_message: str,
        outcome_json: dict[str, Any] | None = None,
        delay_seconds: int | None = None,
        completed_at_ms: int | None = None,
    ) -> SubagentTaskRecord | None: ...


@runtime_checkable
class SubagentRunPort(Protocol):
    """Run creation boundary for claimed subagent tasks."""

    def create_run_for_task(
        self,
        task: SubagentTaskRecord,
        *,
        session_id: str | None = None,
    ) -> SubagentRunRecord: ...
