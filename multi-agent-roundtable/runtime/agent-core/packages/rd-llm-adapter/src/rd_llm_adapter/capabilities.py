from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ThinkingExtractionConfig:
    mode: Literal[
        "none", "openai_field", "xml_tag", "anthropic_block", "openai_responses"
    ] = "none"
    open_tag: str | None = None
    close_tag: str | None = None
    has_signature: bool = False
    must_roundtrip: bool = False
    budget_tokens: int | None = None


@dataclass(frozen=True)
class ModelCapabilities:
    thinking: ThinkingExtractionConfig = field(default_factory=ThinkingExtractionConfig)
    supports_tool_use: bool = True
    tool_call_style: Literal[
        "openai_native", "anthropic_blocks", "gemini_functions"
    ] = "openai_native"
    supports_parallel_tool_calls: bool = True
    max_tool_calls_per_turn: int = 64
    max_parallel_tool_calls: int = 10
    max_context: int = 128000
    max_output: int = 8192
    supports_vision: bool = False
    supports_audio: bool = False
    supports_prompt_caching: bool = False
    prompt_caching_style: Literal["none", "anthropic_marker", "openai_implicit"] = (
        "none"
    )
    supports_stream_usage: bool = True
    supports_partial_retry: bool = False
    supports_grounding: bool = False
    grounding_style: Literal["none", "gemini_search", "anthropic_citations"] = "none"


@dataclass(frozen=True)
class ProtocolLimits:
    max_tool_arg_bytes: int = 256 * 1024
    max_tool_calls_per_turn_hard: int = 256
    max_xml_nesting_depth: int = 32
    max_json_depth: int = 64
    max_json_keys: int = 4096
