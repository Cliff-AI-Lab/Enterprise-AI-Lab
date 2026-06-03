from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from .events import (
    ReasoningDelta,
    StandardEvent,
    TextDelta,
    ToolCallArgsDelta,
    ToolCallEnd,
    ToolCallStart,
    TurnDone,
    UsageUpdate,
)
from .messages import (
    InvalidToolCall,
    ReasoningBlock,
    StandardToolCall,
    TextBlock,
    ToolUseBlock,
)


def _field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class AnthropicNativeAdapter:
    """Phase 2 PoC adapter for Anthropic native request/parser validation."""

    adapter_kind = "anthropic_native"

    def build_request(
        self,
        *,
        model: str,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
        profile: Any | None = None,
        thinking_budget_tokens: int | None = None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": model,
            "messages": [_anthropic_message(msg) for msg in messages],
            "max_tokens": max_tokens,
            "stream": True,
        }
        if system_prompt:
            request["system"] = [{"type": "text", "text": system_prompt}]
        if tools:
            request["tools"] = [_anthropic_tool(tool) for tool in tools]

        budget = thinking_budget_tokens or _profile_thinking_budget_tokens(profile)
        if budget:
            request["thinking"] = {"type": "enabled", "budget_tokens": int(budget)}
        return request

    def create_parser_session(
        self, profile: Any | None = None
    ) -> AnthropicNativeParserSession:
        return AnthropicNativeParserSession(profile)


class AnthropicNativeParserSession:
    """Stateful parser for one Anthropic native streaming turn."""

    def __init__(self, profile: Any | None = None) -> None:
        self.profile = profile
        self.block_kinds: dict[int, str] = {}
        self.text_buffers: dict[int, str] = {}
        self.reasoning_state: dict[int, dict[str, Any]] = {}
        self.tool_state: dict[int, dict[str, Any]] = {}
        self.completed_blocks: list[Any] = []
        self.completed_indices: set[int] = set()
        self.usage: UsageUpdate | None = None
        self.raw_stop_reason: str | None = None
        self.turn_done_emitted = False

    @property
    def has_partial_output(self) -> bool:
        return bool(self.text_buffers or self.reasoning_state or self.tool_state)

    def feed(self, chunk: Any) -> Iterable[StandardEvent]:
        event_type = _field(chunk, "type")
        if event_type == "message_start":
            self.usage = _merge_usage(
                self.usage, _field(_field(chunk, "message") or {}, "usage")
            )
            if self.usage is not None:
                yield self.usage
            return
        if event_type == "content_block_start":
            yield from self._on_content_block_start(chunk)
            return
        if event_type == "content_block_delta":
            yield from self._on_content_block_delta(chunk)
            return
        if event_type == "content_block_stop":
            yield from self._on_content_block_stop(chunk)
            return
        if event_type == "message_delta":
            delta = _field(chunk, "delta") or {}
            self.raw_stop_reason = _field(delta, "stop_reason") or self.raw_stop_reason
            self.usage = _merge_usage(self.usage, _field(chunk, "usage"))
            if self.usage is not None:
                yield self.usage
            return
        if event_type == "message_stop":
            if not self.turn_done_emitted:
                self.turn_done_emitted = True
                yield self._build_turn_done()
            return
        if event_type in {"ping", None}:
            return
        if event_type == "error":
            error = _field(chunk, "error") or {}
            message = _field(error, "message", "Anthropic stream error")
            raise RuntimeError(message)

    def finalize(self) -> Iterable[StandardEvent]:
        if self.turn_done_emitted:
            return
        self.turn_done_emitted = True
        yield self._build_turn_done()

    def finalize_on_error(self) -> Iterable[StandardEvent]:
        if self.turn_done_emitted:
            return
        partial_events, partial_blocks = self._partial_error_output()
        if not partial_blocks:
            return
        self.turn_done_emitted = True
        yield from partial_events
        yield self._build_turn_done(
            content_blocks=partial_blocks,
            raw_stop_reason="error",
        )

    def _on_content_block_start(self, chunk: Any) -> Iterable[StandardEvent]:
        index = int(_field(chunk, "index", 0) or 0)
        content_block = _field(chunk, "content_block") or {}
        block_type = _field(content_block, "type", "")
        self.block_kinds[index] = block_type

        if block_type == "text":
            self.text_buffers[index] = ""
            return
        if block_type == "thinking":
            self.reasoning_state[index] = {
                "text": "",
                "signature": _field(content_block, "signature"),
                "redacted": False,
                "data": None,
            }
            return
        if block_type == "redacted_thinking":
            self.reasoning_state[index] = {
                "text": "",
                "signature": None,
                "redacted": True,
                "data": _field(content_block, "data"),
            }
            return
        if block_type == "tool_use":
            call_id = str(_field(content_block, "id", "") or "")
            name = str(_field(content_block, "name", "") or "")
            self.tool_state[index] = {
                "id": call_id,
                "name": name,
                "args": "",
            }
            yield ToolCallStart(
                index=index,
                call_id=call_id,
                name=name,
                encoding_hint="native_json",
            )

    def _on_content_block_delta(self, chunk: Any) -> Iterable[StandardEvent]:
        index = int(_field(chunk, "index", 0) or 0)
        block_kind = self.block_kinds.get(index)
        delta = _field(chunk, "delta") or {}
        delta_type = _field(delta, "type")

        if block_kind == "text" and delta_type == "text_delta":
            text = str(_field(delta, "text", "") or "")
            self.text_buffers[index] = self.text_buffers.get(index, "") + text
            yield TextDelta(text=text, block_index=index)
            return

        if block_kind == "thinking":
            if delta_type == "thinking_delta":
                text = str(_field(delta, "thinking", "") or "")
                state = self.reasoning_state[index]
                state["text"] = str(state.get("text") or "") + text
                yield ReasoningDelta(text=text, block_index=index)
                return
            if delta_type == "signature_delta":
                self.reasoning_state[index]["signature"] = _field(delta, "signature")
                return

        if block_kind == "tool_use" and delta_type == "input_json_delta":
            partial_json = str(_field(delta, "partial_json", "") or "")
            state = self.tool_state[index]
            state["args"] = str(state.get("args") or "") + partial_json
            yield ToolCallArgsDelta(
                index=index,
                delta=partial_json,
                call_id=state.get("id") or None,
            )

    def _on_content_block_stop(self, chunk: Any) -> Iterable[StandardEvent]:
        index = int(_field(chunk, "index", 0) or 0)
        block_kind = self.block_kinds.get(index)

        if block_kind == "text":
            self.completed_blocks.append(
                TextBlock(text=self.text_buffers.get(index, ""))
            )
            self.completed_indices.add(index)
            return
        if block_kind in {"thinking", "redacted_thinking"}:
            state = self.reasoning_state[index]
            self.completed_blocks.append(
                ReasoningBlock(
                    text=str(state.get("text") or ""),
                    signature=state.get("signature"),
                    redacted=bool(state.get("redacted")),
                    data=state.get("data"),
                )
            )
            self.completed_indices.add(index)
            return
        if block_kind == "tool_use":
            state = self.tool_state[index]
            event, block = _finalize_tool_state(index, state)
            self.completed_blocks.append(block)
            self.completed_indices.add(index)
            yield event

    def _partial_error_output(self) -> tuple[list[StandardEvent], list[Any]]:
        events: list[StandardEvent] = []
        blocks = list(self.completed_blocks)
        for index in sorted(self.block_kinds):
            if index in self.completed_indices:
                continue
            block_kind = self.block_kinds.get(index)
            if block_kind == "text":
                text = self.text_buffers.get(index, "")
                if text:
                    blocks.append(TextBlock(text=text))
                continue
            if block_kind == "thinking":
                state = self.reasoning_state.get(index) or {}
                text = str(state.get("text") or "")
                signature = state.get("signature")
                if text or signature:
                    blocks.append(ReasoningBlock(text=text, signature=signature))
                continue
            if block_kind == "redacted_thinking":
                state = self.reasoning_state.get(index) or {}
                data = state.get("data")
                if data:
                    blocks.append(ReasoningBlock(redacted=True, data=data))
                continue
            if block_kind == "tool_use":
                state = self.tool_state.get(index)
                if state is None:
                    continue
                event, block = _finalize_tool_state(index, state)
                events.append(event)
                blocks.append(block)
        return events, blocks

    def _build_turn_done(
        self,
        *,
        content_blocks: list[Any] | None = None,
        raw_stop_reason: str | None = None,
    ) -> TurnDone:
        blocks = list(self.completed_blocks if content_blocks is None else content_blocks)
        raw_reason = self.raw_stop_reason if raw_stop_reason is None else raw_stop_reason
        tool_calls = [
            StandardToolCall(id=block.id, name=block.name, input=block.input)
            for block in blocks
            if isinstance(block, ToolUseBlock)
        ]
        return TurnDone(
            stop_reason=_map_anthropic_stop_reason(raw_reason),
            content=blocks,
            text_blocks=[
                block for block in blocks if isinstance(block, TextBlock)
            ],
            reasoning_blocks=[
                block
                for block in blocks
                if isinstance(block, ReasoningBlock)
            ],
            tool_calls=tool_calls,
            invalid_tool_calls=[
                block
                for block in blocks
                if isinstance(block, InvalidToolCall)
            ],
            usage=self.usage,
            raw_stop_reason=raw_reason or "",
        )


def _finalize_tool_state(
    index: int,
    state: dict[str, Any],
) -> tuple[ToolCallEnd, ToolUseBlock | InvalidToolCall]:
    raw_args = str(state.get("args") or "")
    parsed_input: dict[str, Any] | None
    parse_error: str | None = None
    try:
        parsed = json.loads(raw_args) if raw_args else {}
        if not isinstance(parsed, dict):
            raise ValueError("tool arguments must decode to a JSON object")
        parsed_input = parsed
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        parsed_input = None
        parse_error = str(exc)

    call_id = str(state.get("id") or "")
    name = str(state.get("name") or "")
    event = ToolCallEnd(
        call_id=call_id,
        name=name,
        index=index,
        encoding="native_json",
        raw_args=raw_args,
        parsed_input=parsed_input,
        parse_error=parse_error,
    )
    if parsed_input is None:
        return event, InvalidToolCall(
            id=call_id,
            name=name,
            raw_args=raw_args,
            parse_error=parse_error or "invalid tool arguments",
            index=index,
            encoding="native_json",
        )
    return event, ToolUseBlock(id=call_id, name=name, input=parsed_input)


def _merge_usage(
    existing: UsageUpdate | None,
    raw_usage: Any | None,
) -> UsageUpdate | None:
    if not raw_usage:
        return existing
    input_tokens = int(_field(raw_usage, "input_tokens", 0) or 0)
    output_tokens = int(_field(raw_usage, "output_tokens", 0) or 0)
    cache_read_input_tokens = int(_field(raw_usage, "cache_read_input_tokens", 0) or 0)
    cache_creation_input_tokens = int(
        _field(raw_usage, "cache_creation_input_tokens", 0) or 0
    )
    cached_input_tokens = int(_field(raw_usage, "cached_input_tokens", 0) or 0)
    if cached_input_tokens and not (
        cache_read_input_tokens or cache_creation_input_tokens
    ):
        cache_read_input_tokens = cached_input_tokens
    if existing is not None:
        input_tokens = input_tokens or existing.input_tokens
        output_tokens = output_tokens or existing.output_tokens
        cache_read_input_tokens = (
            cache_read_input_tokens or existing.cache_read_input_tokens
        )
        cache_creation_input_tokens = (
            cache_creation_input_tokens or existing.cache_creation_input_tokens
        )
    total_tokens = input_tokens + output_tokens
    return UsageUpdate(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
    )


def _anthropic_message(message: dict[str, Any]) -> dict[str, Any]:
    role = "assistant" if message.get("role") == "assistant" else "user"
    content_blocks: list[dict[str, Any]] = []

    if message.get("reasoning_content") and not message.get("reasoning_blocks"):
        raise ValueError(
            "Anthropic native cannot serialize legacy reasoning_content without "
            "thinking signature; use reasoning_blocks"
        )

    if role == "assistant":
        for block in message.get("reasoning_blocks") or []:
            content_blocks.append(_anthropic_reasoning_block(block))

    content = message.get("content", "")
    if isinstance(content, str):
        if content:
            content_blocks.append({"type": "text", "text": content})
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                content_blocks.append({"type": "text", "text": str(block)})
                continue
            block_type = block.get("type")
            if block_type == "text":
                content_blocks.append({"type": "text", "text": block.get("text", "")})
            elif block_type == "tool_use":
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "input": block.get("input") or {},
                    }
                )
            elif block_type == "tool_result":
                result_content = block.get("content", "")
                if not isinstance(result_content, str):
                    result_content = json.dumps(result_content, ensure_ascii=False)
                tool_result: dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": block.get("tool_use_id", ""),
                    "content": result_content,
                }
                if block.get("is_error"):
                    tool_result["is_error"] = True
                content_blocks.append(tool_result)

    return {"role": role, "content": content_blocks}


def _anthropic_reasoning_block(block: dict[str, Any]) -> dict[str, Any]:
    if block.get("redacted"):
        data = block.get("data")
        if not data:
            raise ValueError("redacted Anthropic reasoning block requires data")
        return {"type": "redacted_thinking", "data": data}

    signature = block.get("signature")
    if not signature:
        raise ValueError("Anthropic thinking block requires signature")
    return {
        "type": "thinking",
        "thinking": block.get("text", ""),
        "signature": signature,
    }


def _anthropic_tool(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": tool.get("name", ""),
        "description": tool.get("description", ""),
        "input_schema": tool.get("input_schema", {"type": "object", "properties": {}}),
    }


def _profile_thinking_budget_tokens(profile: Any | None) -> int | None:
    capabilities = _field(profile, "capabilities") if profile is not None else None
    thinking = _field(capabilities, "thinking") if capabilities is not None else None
    budget = _field(thinking, "budget_tokens") if thinking is not None else None
    return int(budget) if budget else None


def _map_anthropic_stop_reason(raw_stop_reason: str | None) -> str:
    if raw_stop_reason in {None, "", "end_turn", "stop_sequence"}:
        return "stop"
    if raw_stop_reason == "max_tokens":
        return "length"
    if raw_stop_reason == "tool_use":
        return "tool_use"
    if raw_stop_reason == "refusal":
        return "content_filter"
    return raw_stop_reason
