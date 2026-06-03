from __future__ import annotations

from typing import Any

from .anthropic_native import AnthropicNativeAdapter
from .anthropic_transport import AnthropicNativeTransport
from .openai_compat import OpenAICompatAdapter
from .transports import OpenAICompatTransport


class AdapterNotSupportedError(RuntimeError):
    """Raised when an adapter kind is known by profile config but not implemented."""


class TransportNotSupportedError(RuntimeError):
    """Raised when an adapter transport is known by profile config but not implemented."""


_ADAPTER_FACTORIES = {
    "openai_compat": OpenAICompatAdapter,
    "anthropic_native": AnthropicNativeAdapter,
}


_TRANSPORT_FACTORIES = {
    "openai_compat": OpenAICompatTransport,
    "anthropic_native": AnthropicNativeTransport,
}


def supported_adapter_kinds() -> tuple[str, ...]:
    return tuple(sorted(_ADAPTER_FACTORIES))


def supported_transport_kinds() -> tuple[str, ...]:
    return tuple(sorted(_TRANSPORT_FACTORIES))


def resolve_adapter(adapter_kind: str) -> Any:
    kind = (adapter_kind or "").strip()
    factory = _ADAPTER_FACTORIES.get(kind)
    if factory is None:
        raise AdapterNotSupportedError(f"model adapter is not implemented: {kind}")
    return factory()


def resolve_transport(adapter_kind: str) -> Any:
    kind = (adapter_kind or "").strip()
    factory = _TRANSPORT_FACTORIES.get(kind)
    if factory is None:
        raise TransportNotSupportedError(
            f"model adapter transport is not implemented: {kind}"
        )
    return factory()


def resolve_adapter_for_profile(profile: Any) -> Any:
    return resolve_adapter(str(getattr(profile, "adapter_kind", "openai_compat")))


def resolve_transport_for_profile(profile: Any) -> Any:
    return resolve_transport(str(getattr(profile, "adapter_kind", "openai_compat")))
