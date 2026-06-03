"""Reference ``LLMClientPort`` implementations backed by rd-llm-adapter."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

from rd_agent_contracts import Message, ToolDefinition, ToolResult
from rd_llm_adapter import (
    AnthropicNativeAdapter,
    AnthropicNativeTransport,
    OpenAICompatAdapter,
    OpenAICompatTransport,
)
from rd_llm_adapter.base import StreamParserSession, Transport
from rd_llm_adapter.events import StandardEvent

from .turn import TurnRequest


@dataclass(frozen=True)
class ProviderClientConfig:
    model: str
    api_key: str
    base_url: str
    timeout: float = 60.0
    max_tokens: int = 4096
    extra_headers: Mapping[str, str] | None = None
    profile: Any | None = None


class OpenAICompatLLMClient:
    def __init__(
        self,
        config: ProviderClientConfig,
        *,
        adapter: OpenAICompatAdapter | None = None,
        transport: Transport | None = None,
        supports_function_calling: bool = True,
        supports_stream_usage: bool = True,
        reasoning_effort: Literal["low", "medium", "high"] | None = None,
    ) -> None:
        self.config = config
        self.adapter = adapter or OpenAICompatAdapter()
        self.transport = transport or OpenAICompatTransport()
        self.supports_function_calling = supports_function_calling
        self.supports_stream_usage = supports_stream_usage
        self.reasoning_effort = reasoning_effort

    async def stream_turn(self, request: TurnRequest) -> AsyncIterable[StandardEvent]:
        session = self.adapter.create_parser_session(self.config.profile)
        body = self.adapter.build_request(
            model=request.model or self.config.model,
            system_prompt=request.system_prompt or "",
            messages=_messages_to_adapter_messages(request.messages),
            tools=_tools_to_adapter_tools(request.tools),
            max_tokens=self.config.max_tokens,
            supports_function_calling=self.supports_function_calling,
            supports_stream_usage=self.supports_stream_usage,
            reasoning_effort=self.reasoning_effort,
        )
        async for event in _stream_with_recovery(
            transport=self.transport,
            session=session,
            request_body=body,
            config=self.config,
        ):
            yield event


class AnthropicNativeLLMClient:
    def __init__(
        self,
        config: ProviderClientConfig,
        *,
        adapter: AnthropicNativeAdapter | None = None,
        transport: Transport | None = None,
        thinking_budget_tokens: int | None = None,
    ) -> None:
        self.config = config
        self.adapter = adapter or AnthropicNativeAdapter()
        self.transport = transport or AnthropicNativeTransport()
        self.thinking_budget_tokens = thinking_budget_tokens

    async def stream_turn(self, request: TurnRequest) -> AsyncIterable[StandardEvent]:
        session = self.adapter.create_parser_session(self.config.profile)
        body = self.adapter.build_request(
            model=request.model or self.config.model,
            system_prompt=request.system_prompt or "",
            messages=_messages_to_adapter_messages(request.messages),
            tools=_tools_to_adapter_tools(request.tools),
            max_tokens=self.config.max_tokens,
            profile=self.config.profile,
            thinking_budget_tokens=self.thinking_budget_tokens,
        )
        async for event in _stream_with_recovery(
            transport=self.transport,
            session=session,
            request_body=body,
            config=self.config,
        ):
            yield event


async def _stream_with_recovery(
    *,
    transport: Transport,
    session: StreamParserSession,
    request_body: dict[str, Any],
    config: ProviderClientConfig,
) -> AsyncIterator[StandardEvent]:
    try:
        async for chunk in transport.stream(
            request_body,
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            extra_headers=dict(config.extra_headers or {}),
        ):
            for event in session.feed(chunk):
                yield event
    except Exception:
        recovered = tuple(session.finalize_on_error())
        if recovered:
            for event in recovered:
                yield event
            return
        raise
    else:
        for event in session.finalize():
            yield event


def _messages_to_adapter_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
    return [_message_to_adapter_message(message) for message in messages]


def _message_to_adapter_message(message: Message) -> dict[str, Any]:
    if message.tool_results:
        return {
            "role": "user",
            "content": [
                _tool_result_block(result)
                for result in message.tool_results
            ],
        }

    payload: dict[str, Any] = {"role": message.role}
    content = message.content
    if isinstance(content, str):
        payload["content"] = content
        return payload

    blocks = [dict(block) for block in content]
    reasoning_blocks = [
        block for block in blocks if block.get("type") == "reasoning"
    ]
    visible_blocks = [
        block for block in blocks if block.get("type") != "reasoning"
    ]
    payload["content"] = visible_blocks
    if reasoning_blocks:
        payload["reasoning_blocks"] = reasoning_blocks
        payload["reasoning_content"] = "".join(
            str(block.get("text") or "") for block in reasoning_blocks
        )
    return payload


def _tool_result_block(result: ToolResult) -> dict[str, Any]:
    block: dict[str, Any] = {
        "type": "tool_result",
        "tool_use_id": result.tool_use_id,
        "content": result.content,
    }
    if not result.ok:
        block["is_error"] = True
        if result.error is not None:
            block["error"] = result.error
    return block


def _tools_to_adapter_tools(tools: Sequence[ToolDefinition]) -> list[dict[str, Any]]:
    return [asdict(tool) for tool in tools]
