from __future__ import annotations

from rd_agent_contracts import (
    SubagentWorkspaceHandle,
    SubagentWorkspaceMergeResult,
    SubagentWorkspacePort,
    SubagentWorkspaceSpec,
    decide_subagent_workspace_isolation,
    should_merge_subagent_workspace,
)


class _InMemoryWorkspaceHandle:
    project_id = "proj-1"
    task_id = "task-1"
    run_id = "run-1"
    write_scope_paths = ["src"]

    def merge_back(self, *, cleanup: bool = True) -> SubagentWorkspaceMergeResult:
        return SubagentWorkspaceMergeResult(
            changed=True,
            merged_paths=self.write_scope_paths,
            generation=1,
        )

    def cleanup(self) -> None:
        return None


class _InMemoryWorkspacePort:
    def prepare_workspace(
        self,
        spec: SubagentWorkspaceSpec,
    ) -> SubagentWorkspaceHandle:
        return _InMemoryWorkspaceHandle()


def test_subagent_workspace_port_runtime_protocol():
    port: SubagentWorkspacePort = _InMemoryWorkspacePort()  # type: ignore[assignment]
    assert isinstance(port, SubagentWorkspacePort)

    handle = port.prepare_workspace(
        SubagentWorkspaceSpec(
            project_id="proj-1",
            task_id="task-1",
            run_id="run-1",
            write_scope_json={"paths": ["src"]},
        )
    )

    assert isinstance(handle, SubagentWorkspaceHandle)
    assert handle.merge_back().merged_paths == ["src"]


def test_decide_subagent_workspace_isolation_normalizes_scope_and_reasons():
    enabled = decide_subagent_workspace_isolation(
        agent_kind="subagent",
        write_scope_json={"paths": ["./src", "src/", "api\\v1"]},
        workspace_isolation_enabled=True,
        inline_parallel_enabled=True,
    )
    assert enabled.enabled is True
    assert enabled.write_scope_paths == ["src", "api/v1"]
    assert enabled.reason is None

    disabled = decide_subagent_workspace_isolation(
        agent_kind="orchestrator",
        write_scope_json={"paths": ["src"]},
        workspace_isolation_enabled=True,
        inline_parallel_enabled=True,
    )
    assert disabled.enabled is False
    assert disabled.reason == "agent_kind_not_subagent"

    configured_off = decide_subagent_workspace_isolation(
        agent_kind="subagent",
        write_scope_json={"paths": ["src"]},
        workspace_isolation_enabled=False,
        inline_parallel_enabled=True,
    )
    assert configured_off.enabled is False
    assert configured_off.write_scope_paths == ["src"]
    assert configured_off.reason == "workspace_isolation_disabled"

    inline_parallel_off = decide_subagent_workspace_isolation(
        agent_kind="subagent",
        write_scope_json={"paths": ["src"]},
        workspace_isolation_enabled=True,
        inline_parallel_enabled=False,
    )
    assert inline_parallel_off.enabled is False
    assert inline_parallel_off.write_scope_paths == ["src"]
    assert inline_parallel_off.reason == "inline_parallel_disabled"

    no_scope = decide_subagent_workspace_isolation(
        agent_kind="subagent",
        write_scope_json=None,
        workspace_isolation_enabled=True,
        inline_parallel_enabled=True,
    )
    assert no_scope.enabled is False
    assert no_scope.reason == "write_scope_empty"


def test_should_merge_subagent_workspace_policy():
    assert should_merge_subagent_workspace(
        will_queue_continuation=True,
        needs_attention=True,
        retryable_needs_attention=False,
    )
    assert should_merge_subagent_workspace(
        will_queue_continuation=False,
        needs_attention=False,
        retryable_needs_attention=False,
    )
    assert should_merge_subagent_workspace(
        will_queue_continuation=False,
        needs_attention=True,
        retryable_needs_attention=True,
    )
    assert not should_merge_subagent_workspace(
        will_queue_continuation=False,
        needs_attention=True,
        retryable_needs_attention=False,
    )
