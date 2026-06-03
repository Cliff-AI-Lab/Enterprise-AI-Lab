"""Model adapter primitives used by the AgentRunner LLM boundary."""

__version__ = "1.1.2"

from .anthropic_native import AnthropicNativeAdapter
from .anthropic_transport import AnthropicNativeTransport
from .base import StreamParserSession, Transport
from .capabilities import ModelCapabilities, ProtocolLimits, ThinkingExtractionConfig
from .events import (
    ReasoningDelta,
    TextDelta,
    ToolCallArgsDelta,
    ToolCallEnd,
    ToolCallIdDelta,
    ToolCallNameDelta,
    ToolCallStart,
    TurnDone,
    UsageUpdate,
)
from .openai_compat import OpenAICompatAdapter
from .recorder import RecordedTurn, ReplayEvents, StreamRecorder
from .registry import (
    AdapterNotSupportedError,
    TransportNotSupportedError,
    resolve_adapter,
    resolve_adapter_for_profile,
    resolve_transport,
    resolve_transport_for_profile,
    supported_adapter_kinds,
    supported_transport_kinds,
)
from .transports import OpenAICompatTransport

__all__ = [
    "AdapterNotSupportedError",
    "AnthropicNativeAdapter",
    "AnthropicNativeTransport",
    "OpenAICompatAdapter",
    "OpenAICompatTransport",
    "RecordedTurn",
    "ReplayEvents",
    "StreamParserSession",
    "StreamRecorder",
    "Transport",
    "TransportNotSupportedError",
    "resolve_adapter",
    "resolve_adapter_for_profile",
    "resolve_transport",
    "resolve_transport_for_profile",
    "supported_adapter_kinds",
    "supported_transport_kinds",
    "ModelCapabilities",
    "ProtocolLimits",
    "ReasoningDelta",
    "TextDelta",
    "ThinkingExtractionConfig",
    "ToolCallArgsDelta",
    "ToolCallEnd",
    "ToolCallIdDelta",
    "ToolCallNameDelta",
    "ToolCallStart",
    "TurnDone",
    "UsageUpdate",
]
