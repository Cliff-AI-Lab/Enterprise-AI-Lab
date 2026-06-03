"""OpenAI-compatible adapter（覆盖 OpenAI / OpenRouter / 自建 OpenAI 兼容网关）。

Phase A 只做 chunk 解析层；Provider httpx 调用在 Task 19 加。
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..normalizer import StreamNormalizer
from ..types import ChatRequest, StreamChunk


def parse_openai_sse_chunk(
    raw: dict[str, Any],
    normalizer: StreamNormalizer,
) -> list[StreamChunk]:
    """解析一个 OpenAI SSE chunk，输出归一化 StreamChunk 列表。

    一个 raw chunk 可能产出多个归一化 chunk（如 delta.content + delta.tool_calls）。
    """
    out: list[StreamChunk] = []
    choices = raw.get("choices") or []
    if not choices:
        # 末尾的 usage chunk
        if "usage" in raw:
            out.append(normalizer.usage(_remap_openai_usage(raw["usage"])))
        return out

    choice = choices[0]
    delta = choice.get("delta") or {}
    finish_reason = choice.get("finish_reason")

    # text content
    if delta.get("content"):
        out.append(normalizer.text_delta(delta["content"], raw=raw))

    # tool_calls
    for tc in delta.get("tool_calls") or []:
        tool_use_id = tc.get("id") or ""
        fn = tc.get("function") or {}
        name = fn.get("name") or ""
        args = fn.get("arguments") or ""
        if finish_reason == "length":
            out.append(
                normalizer.tool_use_partial(tool_use_id, name, args, raw=raw)
            )
        else:
            try:
                if args:
                    json.loads(args)
                out.append(
                    normalizer.tool_use_complete(
                        tool_use_id, name, args, raw=raw
                    )
                )
            except json.JSONDecodeError:
                out.append(
                    normalizer.tool_use_invalid(
                        tool_use_id, name, args, raw_chunk=raw
                    )
                )

    # usage（OpenAI 通常在最后一个 chunk）
    if "usage" in raw:
        out.append(normalizer.usage(_remap_openai_usage(raw["usage"])))

    return out


def _remap_openai_usage(u: dict[str, Any]) -> dict[str, Any]:
    """OpenAI 字段名映射到 contracts.Usage。"""
    return {
        "input_tokens": u.get("prompt_tokens", 0),
        "output_tokens": u.get("completion_tokens", 0),
    }


class OpenAICompatProvider:
    """OpenAI-compatible chat completions provider。

    构造时传 base_url + api_key + 可选 extra_headers。stream_chat 返回
    AsyncIterator[StreamChunk]，全部 chunk 已归一化（含 seq）。
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        extra_headers: dict[str, str] | None = None,
        timeout_s: float = 600.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._extra_headers = extra_headers or {}
        self._timeout_s = timeout_s

    async def stream_chat(
        self, req: ChatRequest
    ) -> AsyncIterator[StreamChunk]:
        normalizer = StreamNormalizer()

        body: dict[str, Any] = {
            "model": req.model,
            "messages": (
                [{"role": "system", "content": req.system}, *req.messages]
                if req.system
                else req.messages
            ),
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if req.tools:
            body["tools"] = req.tools

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }

        async def gen() -> AsyncIterator[StreamChunk]:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    json=body,
                    headers=headers,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        payload = line[6:]
                        if payload == "[DONE]":
                            break
                        try:
                            raw = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        for chunk in parse_openai_sse_chunk(raw, normalizer):
                            yield chunk

        return gen()
