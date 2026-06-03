from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from rd_agent_contracts import ToolDefinition, ToolExecutionContext
from rd_agent_core import (
    ArtifactDescriptor,
    ArtifactManifest,
    BusinessAgentAdapter,
    BusinessAgentProfile,
    BusinessTask,
    PromptSection,
    VerificationPlan,
)


class _PresentationBusinessAgent:
    @property
    def profile(self) -> BusinessAgentProfile:
        return BusinessAgentProfile(
            kind="presentation",
            display_name="Presentation Agent",
            description="Builds presentation deliverables",
        )

    def build_prompt_sections(
        self,
        *,
        task: BusinessTask,
        tool_context: ToolExecutionContext,
    ) -> Sequence[PromptSection]:
        return [
            PromptSection("goal", task.instruction, priority=100),
            PromptSection("project", tool_context.project_id, priority=10),
        ]

    def list_tools(
        self,
        *,
        task: BusinessTask,
        tool_context: ToolExecutionContext,
    ) -> Sequence[ToolDefinition]:
        return [
            ToolDefinition(
                name="render_deck",
                description="Render an editable deck artifact",
                input_schema={"type": "object"},
                mutates_workspace=True,
            )
        ]

    def build_verification_plan(
        self,
        *,
        task: BusinessTask,
        tool_context: ToolExecutionContext,
    ) -> VerificationPlan:
        return VerificationPlan(required=True, tool_names=("visual_qa",), max_attempts=2)

    def extract_manifest(
        self,
        *,
        task: BusinessTask,
        content: Sequence[Any],
        tool_context: ToolExecutionContext,
    ) -> ArtifactManifest:
        return ArtifactManifest(
            artifacts=(
                ArtifactDescriptor(
                    artifact_id="deck-1",
                    name="strategy.pptx",
                    kind="presentation",
                    uri="s3://tenant/project/strategy.pptx",
                ),
            )
        )


def test_business_agent_adapter_keeps_business_shape_outside_core_runtime() -> None:
    adapter: BusinessAgentAdapter = _PresentationBusinessAgent()
    task = BusinessTask(instruction="make an investor deck", project_id="project-1")
    context = ToolExecutionContext(project_id="project-1")

    sections = adapter.build_prompt_sections(task=task, tool_context=context)
    tools = adapter.list_tools(task=task, tool_context=context)
    verification = adapter.build_verification_plan(task=task, tool_context=context)
    manifest = adapter.extract_manifest(task=task, content=[], tool_context=context)

    assert isinstance(adapter, BusinessAgentAdapter)
    assert adapter.profile.kind == "presentation"
    assert [section.name for section in sections] == ["goal", "project"]
    assert [tool.name for tool in tools] == ["render_deck"]
    assert verification.required
    assert verification.tool_names == ("visual_qa",)
    assert manifest.artifacts[0].kind == "presentation"


def test_verification_plan_rejects_invalid_attempt_count() -> None:
    try:
        VerificationPlan(max_attempts=0)
    except ValueError as exc:
        assert "max_attempts" in str(exc)
    else:
        raise AssertionError("expected max_attempts validation failure")
