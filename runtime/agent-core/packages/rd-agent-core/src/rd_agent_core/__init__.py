"""rd-agent-core — host-neutral agent runtime kernel."""

from .business import (
    ArtifactDescriptor,
    ArtifactExtractorPort,
    ArtifactManifest,
    BusinessAgentAdapter,
    BusinessAgentProfile,
    BusinessTask,
    BusinessToolProviderPort,
    ContextProviderPort,
    PromptSection,
    VerificationPlan,
    VerificationPolicyPort,
)
from .conformance import (
    assert_event_log_port_conformance,
    assert_run_persistence_port_conformance,
    assert_tool_executor_port_conformance,
)
from .errors import CoreErrorCategory, CoreErrorType, classify_core_error, core_error
from .events import CoreEventType, CoreEventWriter
from .llm_clients import (
    AnthropicNativeLLMClient,
    OpenAICompatLLMClient,
    ProviderClientConfig,
)
from .observability import (
    AsyncRunObserverPort,
    RunObserverLike,
    RunObserverPort,
    notify_run_observer,
)
from .policies import (
    RunLimitDecision,
    RunLimits,
    RunLimitState,
    ToolCallSignature,
    evaluate_run_limits,
    has_repeated_tool_call,
    tool_call_signature,
)
from .run import (
    RunKernel,
    RunKernelResult,
    RunRequest,
    build_messages_after_turn,
)
from .runner import AgentRunner, AgentRunnerRequest, AgentRunnerResult
from .summary import RunSummary, summarize_failed_run, summarize_kernel_result
from .turn import (
    AsyncToolExecutorPort,
    CoreToolPolicy,
    LLMClientPort,
    ToolExecutorLike,
    ToolSafetyPolicy,
    TurnKernel,
    TurnKernelResult,
    TurnRequest,
)

__version__ = "0.1.3"

__all__ = [
    "ArtifactDescriptor",
    "ArtifactExtractorPort",
    "ArtifactManifest",
    "AgentRunner",
    "AgentRunnerRequest",
    "AgentRunnerResult",
    "AnthropicNativeLLMClient",
    "AsyncRunObserverPort",
    "BusinessAgentAdapter",
    "BusinessAgentProfile",
    "BusinessTask",
    "BusinessToolProviderPort",
    "ContextProviderPort",
    "AsyncToolExecutorPort",
    "CoreEventType",
    "CoreEventWriter",
    "CoreErrorCategory",
    "CoreErrorType",
    "CoreToolPolicy",
    "LLMClientPort",
    "OpenAICompatLLMClient",
    "PromptSection",
    "ProviderClientConfig",
    "RunLimitDecision",
    "RunKernel",
    "RunKernelResult",
    "RunLimitState",
    "RunLimits",
    "RunObserverLike",
    "RunObserverPort",
    "RunRequest",
    "RunSummary",
    "ToolCallSignature",
    "ToolExecutorLike",
    "ToolSafetyPolicy",
    "TurnKernel",
    "TurnKernelResult",
    "TurnRequest",
    "VerificationPlan",
    "VerificationPolicyPort",
    "assert_event_log_port_conformance",
    "assert_run_persistence_port_conformance",
    "assert_tool_executor_port_conformance",
    "build_messages_after_turn",
    "classify_core_error",
    "core_error",
    "evaluate_run_limits",
    "has_repeated_tool_call",
    "notify_run_observer",
    "summarize_failed_run",
    "summarize_kernel_result",
    "tool_call_signature",
]
