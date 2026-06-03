from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any, Literal

from ._usage import normalize_usage
from .events import (
    ReasoningDelta,
    StandardEvent,
    TextDelta,
    ToolCallArgsDelta,
    ToolCallEnd,
    ToolCallIdDelta,
    ToolCallNameDelta,
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


def _reasoning_delta_from_delta(delta: Any) -> str:
    extra = _field(delta, "model_extra") or {}
    direct = (
        _field(delta, "reasoning_content")
        or _field(extra, "reasoning_content")
        or _field(delta, "reasoning")
        or _field(extra, "reasoning")
    )
    if direct:
        return str(direct)

    details = _field(delta, "reasoning_details") or _field(
        extra, "reasoning_details", []
    )
    if not isinstance(details, list):
        return ""
    return "".join(
        str(text)
        for item in details
        if (text := _field(item, "text")) is not None and str(text)
    )


def build_openai_messages(
    system_prompt: str,
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert AgentRunner legacy Anthropic-style messages to OpenAI messages."""
    oai_messages: list[dict[str, Any]] = []
    if system_prompt:
        oai_messages.append({"role": "system", "content": system_prompt})

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        has_reasoning_content = role == "assistant" and "reasoning_content" in msg
        reasoning_content = (
            ""
            if msg.get("reasoning_content") is None
            else str(msg.get("reasoning_content"))
        )

        if isinstance(content, list):
            tool_use_blocks = [
                b
                for b in content
                if isinstance(b, dict) and b.get("type") == "tool_use"
            ]
            tool_result_blocks = [
                b
                for b in content
                if isinstance(b, dict) and b.get("type") == "tool_result"
            ]
            text_blocks = [
                b for b in content if isinstance(b, dict) and b.get("type") == "text"
            ]

            if tool_use_blocks and role == "assistant":
                text_content = " ".join(b.get("text", "") for b in text_blocks) or None
                tool_calls = []
                for tool_use in tool_use_blocks:
                    tool_calls.append(
                        {
                            "id": tool_use.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tool_use.get("name", ""),
                                "arguments": json.dumps(
                                    tool_use.get("input", {}), ensure_ascii=False
                                ),
                            },
                        }
                    )
                oai_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": text_content,
                    "tool_calls": tool_calls,
                }
                if has_reasoning_content:
                    oai_msg["reasoning_content"] = reasoning_content
                oai_messages.append(oai_msg)
            elif tool_result_blocks:
                for block in tool_result_blocks:
                    result_content = block.get("content", "")
                    if not isinstance(result_content, str):
                        result_content = json.dumps(result_content, ensure_ascii=False)
                    oai_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id", ""),
                            "content": result_content,
                        }
                    )
            else:
                for block in text_blocks:
                    oai_msg = {"role": role, "content": block.get("text", "")}
                    if has_reasoning_content:
                        oai_msg["reasoning_content"] = reasoning_content
                        has_reasoning_content = False
                    oai_messages.append(oai_msg)
        elif isinstance(content, str):
            oai_msg = {"role": role, "content": content}
            if has_reasoning_content:
                oai_msg["reasoning_content"] = reasoning_content
            oai_messages.append(oai_msg)

    return oai_messages


def build_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get(
                    "input_schema", {"type": "object", "properties": {}}
                ),
            },
        }
        for tool in tools
    ]


class OpenAICompatAdapter:
    adapter_kind = "openai_compat"

    def build_request(
        self,
        *,
        model: str,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
        supports_function_calling: bool,
        supports_stream_usage: bool,
        reasoning_effort: Literal["low", "medium", "high"] | None = None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": model,
            "messages": build_openai_messages(system_prompt, messages),
            "max_tokens": max_tokens,
            "stream": True,
        }
        if supports_stream_usage:
            request["stream_options"] = {"include_usage": True}

        oai_tools = build_openai_tools(tools) if supports_function_calling else []
        if oai_tools:
            request["tools"] = oai_tools

        # `is not None` 而非 falsy 检查：reasoning_effort 没有“零值等同关闭”语义
        # （对比 AnthropicNativeAdapter.thinking_budget_tokens 的 `if budget:`，
        # budget=0 等同未开 thinking）。Literal 类型签名已确保非空合法字符串。
        if reasoning_effort is not None:
            request["reasoning_effort"] = reasoning_effort
        return request

    def create_parser_session(
        self, profile: Any | None = None
    ) -> OpenAICompatParserSession:
        return OpenAICompatParserSession(profile)


class OpenAICompatParserSession:
    """Stateful parser for one OpenAI-compatible streaming turn."""

    def __init__(self, profile: Any | None = None) -> None:
        self.profile = profile
        self.text_buffer = ""
        self.reasoning_buffer = ""
        self.tool_calls_by_index: dict[int, dict[str, Any]] = {}
        self.usage: UsageUpdate | None = None
        self.finish_reason: str | None = None
        self.turn_done_emitted = False

    @property
    def has_partial_output(self) -> bool:
        return bool(
            self.text_buffer or self.reasoning_buffer or self.tool_calls_by_index
        )

    def feed(self, chunk: Any) -> Iterable[StandardEvent]:
        parsed = normalize_usage(_field(chunk, "usage"))
        if (
            parsed.input_tokens
            or parsed.output_tokens
            or parsed.cached_input_tokens
            or parsed.cache_read_input_tokens
            or parsed.cache_creation_input_tokens
            or parsed.reasoning_tokens
        ):
            self.usage = UsageUpdate(
                input_tokens=parsed.input_tokens,
                output_tokens=parsed.output_tokens,
                total_tokens=parsed.total_tokens,
                cache_read_input_tokens=parsed.cache_read_input_tokens,
                cache_creation_input_tokens=parsed.cache_creation_input_tokens,
                reasoning_tokens=parsed.reasoning_tokens,
            )
            yield self.usage

        choices = _field(chunk, "choices") or []
        if not choices:
            return

        choice = choices[0]
        delta = _field(choice, "delta")
        finish_reason = _field(choice, "finish_reason")
        if finish_reason:
            self.finish_reason = finish_reason

        reasoning_delta = _reasoning_delta_from_delta(delta)
        if reasoning_delta:
            self.reasoning_buffer += reasoning_delta
            yield ReasoningDelta(text=reasoning_delta, block_index=0)

        content_delta = _field(delta, "content")
        if content_delta:
            self.text_buffer += content_delta
            yield TextDelta(text=content_delta, block_index=0)

        tool_call_deltas = _field(delta, "tool_calls")
        if not tool_call_deltas:
            return

        for tc_delta in tool_call_deltas:
            idx = _field(tc_delta, "index")
            if idx is None:
                idx = 0
            if idx not in self.tool_calls_by_index:
                initial_id = _field(tc_delta, "id") or None
                function_delta = _field(tc_delta, "function")
                initial_name = (
                    _field(function_delta, "name")
                    if function_delta is not None
                    else None
                )
                self.tool_calls_by_index[idx] = {
                    "id": initial_id or "",
                    "name": initial_name or "",
                    "arguments": "",
                    "encoding": "native_json",
                }
                yield ToolCallStart(
                    index=idx,
                    call_id=initial_id,
                    name=initial_name,
                    encoding_hint="native_json",
                )

            entry = self.tool_calls_by_index[idx]
            call_id = _field(tc_delta, "id")
            if call_id:
                entry["id"] = call_id
                yield ToolCallIdDelta(index=idx, call_id=call_id)

            function_delta = _field(tc_delta, "function")
            if function_delta is None:
                continue

            name_delta = _field(function_delta, "name")
            if name_delta:
                entry["name"] = name_delta
                yield ToolCallNameDelta(
                    index=idx,
                    name_delta=name_delta,
                    call_id=entry.get("id") or None,
                )

            arguments_delta = _field(function_delta, "arguments")
            if arguments_delta:
                entry["arguments"] += arguments_delta
                yield ToolCallArgsDelta(
                    index=idx,
                    delta=arguments_delta,
                    call_id=entry.get("id") or None,
                )

    def finalize(self) -> Iterable[StandardEvent]:
        if self.turn_done_emitted:
            return
        self.turn_done_emitted = True

        content_blocks = self._content_blocks_from_buffers()

        for idx in sorted(self.tool_calls_by_index.keys()):
            event, block = self._finalize_tool_entry(
                idx, self.tool_calls_by_index[idx]
            )
            yield event
            content_blocks.append(block)

        yield self._build_turn_done(
            content_blocks=content_blocks,
            stop_reason=_map_finish_reason(self.finish_reason),
            raw_stop_reason=self.finish_reason or "",
        )

    def finalize_on_error(self) -> Iterable[StandardEvent]:
        if self.turn_done_emitted:
            return
        if not self.has_partial_output:
            return
        self.turn_done_emitted = True

        content_blocks = self._content_blocks_from_buffers()
        for idx in sorted(self.tool_calls_by_index.keys()):
            event, block = self._finalize_tool_entry(
                idx, self.tool_calls_by_index[idx]
            )
            yield event
            content_blocks.append(block)

        yield self._build_turn_done(
            content_blocks=content_blocks,
            stop_reason="error",
            raw_stop_reason="error",
        )

    def _content_blocks_from_buffers(self) -> list[Any]:
        content_blocks: list[Any] = []
        if self.reasoning_buffer:
            content_blocks.append(ReasoningBlock(text=self.reasoning_buffer))
        if self.text_buffer:
            content_blocks.append(TextBlock(text=self.text_buffer))
        return content_blocks

    def _finalize_tool_entry(
        self,
        idx: int,
        entry: dict[str, Any],
    ) -> tuple[ToolCallEnd, ToolUseBlock | InvalidToolCall]:
        raw_args = str(entry.get("arguments") or "")
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

        call_id = str(entry.get("id") or "")
        name = str(entry.get("name") or "")
        event = ToolCallEnd(
            call_id=call_id,
            name=name,
            index=idx,
            encoding="native_json",
            raw_args=raw_args,
            parsed_input=parsed_input,
            parse_error=parse_error,
        )
        if parse_error is None and parsed_input is not None:
            return event, ToolUseBlock(id=call_id, name=name, input=parsed_input)
        return event, InvalidToolCall(
            id=call_id,
            name=name,
            raw_args=raw_args,
            parse_error=parse_error or "invalid tool arguments",
            index=idx,
            encoding="native_json",
        )

    def _build_turn_done(
        self,
        *,
        content_blocks: list[Any],
        stop_reason: str,
        raw_stop_reason: str,
    ) -> TurnDone:
        return TurnDone(
            stop_reason=stop_reason,
            content=content_blocks,
            text_blocks=[b for b in content_blocks if isinstance(b, TextBlock)],
            reasoning_blocks=[
                b for b in content_blocks if isinstance(b, ReasoningBlock)
            ],
            tool_calls=[
                StandardToolCall(
                    id=b.id, name=b.name, input=b.input, encoding="native_json"
                )
                for b in content_blocks
                if isinstance(b, ToolUseBlock)
            ],
            invalid_tool_calls=[
                b for b in content_blocks if isinstance(b, InvalidToolCall)
            ],
            sources=[],
            usage=self.usage,
            provider_state=None,
            raw_stop_reason=raw_stop_reason,
        )


def _map_finish_reason(finish_reason: str | None) -> str:
    if finish_reason == "tool_calls":
        return "tool_use"
    if finish_reason in {"stop", "length", "content_filter"}:
        return finish_reason
    return finish_reason or "end_turn"


def _legacy_stop_reason(turn_done: TurnDone) -> str:
    if turn_done.stop_reason == "tool_use":
        return "tool_calls"
    return turn_done.stop_reason


def standard_event_to_legacy_delta(event: StandardEvent) -> dict[str, Any] | None:
    if isinstance(event, TextDelta):
        return {"type": "text_delta", "text": event.text}
    if isinstance(event, ReasoningDelta):
        return {"type": "reasoning_delta", "text": event.text}
    if isinstance(event, ToolCallNameDelta):
        return {
            "type": "tool_use_delta",
            "tool_use_id": event.call_id or "",
            "index": event.index,
            "name_delta": event.name_delta,
            "arguments_delta": None,
        }
    if isinstance(event, ToolCallArgsDelta):
        return {
            "type": "tool_use_delta",
            "tool_use_id": event.call_id or "",
            "index": event.index,
            "name_delta": None,
            "arguments_delta": event.delta,
        }
    return None


def standard_events_to_legacy_deltas(
    events: Iterable[StandardEvent],
) -> list[dict[str, Any]]:
    """Translate standard events from one raw chunk back to legacy stream events.

    The legacy path emitted at most one ``tool_use_delta`` per provider
    ``tool_calls[]`` delta, with name and arguments in the same payload when
    both arrived together. Standard events are intentionally more granular, so
    the shim recombines adjacent name/args deltas for behavior compatibility.
    """
    legacy: list[dict[str, Any]] = []
    pending_tool: dict[str, Any] | None = None

    def flush_pending() -> None:
        nonlocal pending_tool
        if pending_tool is not None:
            legacy.append(pending_tool)
            pending_tool = None

    for event in events:
        if isinstance(event, TextDelta):
            flush_pending()
            legacy.append({"type": "text_delta", "text": event.text})
            continue
        if isinstance(event, ReasoningDelta):
            flush_pending()
            legacy.append({"type": "reasoning_delta", "text": event.text})
            continue
        if isinstance(event, ToolCallNameDelta):
            flush_pending()
            pending_tool = {
                "type": "tool_use_delta",
                "tool_use_id": event.call_id or "",
                "index": event.index,
                "name_delta": event.name_delta,
                "arguments_delta": None,
            }
            continue
        if isinstance(event, ToolCallArgsDelta):
            if pending_tool is not None and pending_tool.get("index") == event.index:
                if event.call_id:
                    pending_tool["tool_use_id"] = event.call_id
                pending_tool["arguments_delta"] = event.delta
                flush_pending()
            else:
                flush_pending()
                legacy.append(
                    {
                        "type": "tool_use_delta",
                        "tool_use_id": event.call_id or "",
                        "index": event.index,
                        "name_delta": None,
                        "arguments_delta": event.delta,
                    }
                )
            continue

        # Start/id/end/usage/turn-done have no direct legacy delta payload.
    flush_pending()
    return legacy


def legacy_content_from_turn_done(turn_done: TurnDone) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    for block in turn_done.content:
        if isinstance(block, TextBlock):
            content.append({"type": "text", "text": block.text})
        elif isinstance(block, ToolUseBlock):
            content.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }
            )
        elif isinstance(block, InvalidToolCall):
            content.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": {},
                    "input_parse_error": True,
                    "raw_args": block.raw_args,
                    "parse_error": block.parse_error,
                    "index": block.index,
                }
            )
    return content


def terminal_events_from_turn_done(turn_done: TurnDone) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    reasoning_text = "".join(
        block.text for block in turn_done.reasoning_blocks if not block.redacted
    )
    text_content = "".join(block.text for block in turn_done.text_blocks)
    if reasoning_text:
        events.append({"type": "reasoning", "text": reasoning_text})
    if text_content:
        events.append({"type": "text", "text": text_content})
    for block in turn_done.content:
        if isinstance(block, ToolUseBlock):
            events.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }
            )
        elif isinstance(block, InvalidToolCall):
            events.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": {},
                    "input_parse_error": True,
                    "raw_args": block.raw_args,
                    "parse_error": block.parse_error,
                    "index": block.index,
                }
            )
    return events


def legacy_response_from_turn_done(
    turn_done: TurnDone,
    *,
    latency_ms: int,
    first_chunk_latency_ms: int | None,
) -> dict[str, Any]:
    reasoning_text = "".join(
        block.text for block in turn_done.reasoning_blocks if not block.redacted
    )
    text_content = "".join(block.text for block in turn_done.text_blocks)
    return {
        "content": legacy_content_from_turn_done(turn_done),
        "usage": turn_done.usage.to_dict() if turn_done.usage is not None else {},
        "stop_reason": _legacy_stop_reason(turn_done),
        "latency_ms": latency_ms,
        "first_chunk_latency_ms": first_chunk_latency_ms,
        "reasoning_text": reasoning_text,
        "text_content": text_content,
    }
