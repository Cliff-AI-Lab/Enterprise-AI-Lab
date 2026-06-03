from __future__ import annotations

import json
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any
from urllib.parse import urlsplit, urlunsplit

ANTHROPIC_VERSION = "2023-06-01"


class AnthropicNativeTransport:
    """Phase 2 PoC transport for Anthropic Messages streaming."""

    async def stream(
        self,
        request_body: dict[str, Any],
        *,
        api_key: str,
        base_url: str,
        timeout: float,
        anthropic_version: str = ANTHROPIC_VERSION,
        extra_headers: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("httpx package not installed") from exc

        headers = {
            "x-api-key": api_key,
            "anthropic-version": anthropic_version,
            "content-type": "application/json",
            "accept": "text/event-stream",
        }
        if extra_headers:
            headers.update(extra_headers)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                anthropic_messages_url(base_url),
                headers=headers,
                json=request_body,
            ) as response:
                response.raise_for_status()
                async for event in iter_anthropic_sse_json(response.aiter_lines()):
                    yield event


def anthropic_messages_url(base_url: str) -> str:
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        cleaned = "https://api.anthropic.com"

    parsed = urlsplit(cleaned)
    if not parsed.scheme or not parsed.netloc:
        return cleaned
    if parsed.path.endswith("/v1/messages"):
        return cleaned
    if parsed.path.endswith("/v1"):
        return urlunsplit(
            (parsed.scheme, parsed.netloc, f"{parsed.path}/messages", "", "")
        )
    if parsed.path in {"", "/"}:
        return urlunsplit((parsed.scheme, parsed.netloc, "/v1/messages", "", ""))
    return urlunsplit(
        (parsed.scheme, parsed.netloc, f"{parsed.path}/v1/messages", "", "")
    )


async def iter_anthropic_sse_json(
    lines: AsyncIterable[str],
) -> AsyncIterator[dict[str, Any]]:
    event_type: str | None = None
    data_lines: list[str] = []

    async for raw_line in lines:
        line = raw_line.strip("\r")
        if not line:
            event = _decode_sse_event(event_type, data_lines)
            event_type = None
            data_lines = []
            if event is not None:
                yield event
            continue

        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_type = line.removeprefix("event:").strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").lstrip())

    event = _decode_sse_event(event_type, data_lines)
    if event is not None:
        yield event


def _decode_sse_event(
    event_type: str | None,
    data_lines: list[str],
) -> dict[str, Any] | None:
    if not data_lines:
        return None
    data = "\n".join(data_lines)
    if data == "[DONE]":
        return None
    payload = json.loads(data)
    if not isinstance(payload, dict):
        return None
    if event_type and "type" not in payload:
        payload["type"] = event_type
    return payload
