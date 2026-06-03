"""Business-agent adapter contracts.

These contracts keep PPT, document, data-analysis, and future agents outside the
runtime kernel while still giving each business agent a typed way to supply
prompt context, tools, verification policy, and artifact manifests.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from rd_agent_contracts import ToolDefinition, ToolExecutionContext


@dataclass(frozen=True)
class BusinessAgentProfile:
    kind: str
    display_name: str
    description: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BusinessTask:
    instruction: str
    project_id: str
    session_id: str | None = None
    request_id: str | None = None
    agent_kind: str = "orchestrator"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PromptSection:
    name: str
    content: str
    priority: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationPlan:
    required: bool = False
    tool_names: tuple[str, ...] = ()
    criteria: tuple[str, ...] = ()
    max_attempts: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")


@dataclass(frozen=True)
class ArtifactDescriptor:
    artifact_id: str
    name: str
    kind: str
    uri: str
    mime_type: str | None = None
    version: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArtifactManifest:
    artifacts: tuple[ArtifactDescriptor, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class ContextProviderPort(Protocol):
    def build_prompt_sections(
        self,
        *,
        task: BusinessTask,
        tool_context: ToolExecutionContext,
    ) -> Sequence[PromptSection]: ...


@runtime_checkable
class BusinessToolProviderPort(Protocol):
    def list_tools(
        self,
        *,
        task: BusinessTask,
        tool_context: ToolExecutionContext,
    ) -> Sequence[ToolDefinition]: ...


@runtime_checkable
class VerificationPolicyPort(Protocol):
    def build_verification_plan(
        self,
        *,
        task: BusinessTask,
        tool_context: ToolExecutionContext,
    ) -> VerificationPlan: ...


@runtime_checkable
class ArtifactExtractorPort(Protocol):
    def extract_manifest(
        self,
        *,
        task: BusinessTask,
        content: Sequence[Any],
        tool_context: ToolExecutionContext,
    ) -> ArtifactManifest: ...


@runtime_checkable
class BusinessAgentAdapter(
    ContextProviderPort,
    BusinessToolProviderPort,
    VerificationPolicyPort,
    ArtifactExtractorPort,
    Protocol,
):
    @property
    def profile(self) -> BusinessAgentProfile: ...
