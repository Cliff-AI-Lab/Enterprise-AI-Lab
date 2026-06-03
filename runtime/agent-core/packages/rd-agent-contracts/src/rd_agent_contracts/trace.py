from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

TRACE_HEADER_PREFIX = "X-RD-"


@dataclass(frozen=True)
class CostAttributionTags:
    """Stable dimensions for cost and quality attribution."""

    feature: str = "agent_chat"
    route: str = "primary_agent"
    environment: str = "unknown"
    harness_variant: str = "default"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class TraceContext:
    """Cross-service trace identity shared by SaaS, Agent Core, and gateway."""

    trace_id: str
    correlation_id: str
    tenant_id: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    session_id: str | None = None
    user_request_id: str | None = None
    agent_run_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    tags: CostAttributionTags = CostAttributionTags()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tags"] = self.tags.to_dict()
        return payload

    def to_gateway_headers(self) -> dict[str, str]:
        headers = {
            "X-RD-Trace-Id": self.trace_id,
            "X-RD-Correlation-Id": self.correlation_id,
            "X-RD-Feature": self.tags.feature,
            "X-RD-Route": self.tags.route,
            "X-RD-Environment": self.tags.environment,
            "X-RD-Harness-Variant": self.tags.harness_variant,
        }
        optional = {
            "X-RD-Tenant-Id": self.tenant_id,
            "X-RD-User-Id": self.user_id,
            "X-RD-Project-Id": self.project_id,
            "X-RD-Session-Id": self.session_id,
            "X-RD-User-Request-Id": self.user_request_id,
            "X-RD-Agent-Run-Id": self.agent_run_id,
            "X-RD-Span-Id": self.span_id,
            "X-RD-Parent-Span-Id": self.parent_span_id,
        }
        for key, value in optional.items():
            if value:
                headers[key] = str(value)
        return headers


@dataclass(frozen=True)
class LLMCallRecord:
    """Metadata-only record for one model call.

    Prompts and responses are intentionally excluded from this contract. Callers
    should store redacted previews or hashes separately if they need debugging
    material.
    """

    trace: TraceContext
    turn: int
    requested_model: str
    provider_model: str
    provider: str = ""
    adapter_kind: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None
    latency_ms: int | None = None
    first_token_ms: int | None = None
    status: str = "success"
    stop_reason: str | None = None
    error_type: str | None = None
    retry_attempt: int = 0
    fallback_from: str | None = None
    fallback_to: str | None = None
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trace"] = self.trace.to_dict()
        if self.created_at is not None:
            payload["created_at"] = self.created_at.isoformat()
        return payload
