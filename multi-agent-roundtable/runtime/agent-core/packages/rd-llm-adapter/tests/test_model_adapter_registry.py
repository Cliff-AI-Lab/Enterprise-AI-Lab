from __future__ import annotations

from types import SimpleNamespace

import pytest
from rd_llm_adapter.anthropic_native import (
    AnthropicNativeAdapter,
)
from rd_llm_adapter.anthropic_transport import (
    AnthropicNativeTransport,
)
from rd_llm_adapter.openai_compat import OpenAICompatAdapter
from rd_llm_adapter.registry import (
    AdapterNotSupportedError,
    TransportNotSupportedError,
    resolve_adapter,
    resolve_adapter_for_profile,
    resolve_transport,
    resolve_transport_for_profile,
    supported_adapter_kinds,
    supported_transport_kinds,
)
from rd_llm_adapter.transports import OpenAICompatTransport


# 注：registry 只通过 getattr(profile, "adapter_kind") 读取 profile，所以测试
# 这里用 SimpleNamespace 模拟 ResolvedModelProfile 的最小接口，避免反向依赖
# codesphere-saas 的 model_profile 模块（rd-llm-adapter 不持有该抽象）。
def _profile(adapter_kind: str = "anthropic_native") -> SimpleNamespace:
    return SimpleNamespace(
        requested_model="claude-sonnet-4-5",
        provider_model_name="claude-sonnet-4-5",
        base_url="https://api.anthropic.com",
        api_key="sk-test",
        adapter_kind=adapter_kind,
    )


def test_supported_adapter_kinds_are_explicit() -> None:
    assert supported_adapter_kinds() == ("anthropic_native", "openai_compat")


def test_supported_transport_kinds_are_explicit() -> None:
    assert supported_transport_kinds() == ("anthropic_native", "openai_compat")


def test_resolve_adapter_returns_implemented_adapter_instances() -> None:
    assert isinstance(resolve_adapter("openai_compat"), OpenAICompatAdapter)
    assert isinstance(resolve_adapter("anthropic_native"), AnthropicNativeAdapter)


def test_resolve_transport_returns_implemented_transport_instances() -> None:
    assert isinstance(resolve_transport("openai_compat"), OpenAICompatTransport)
    assert isinstance(resolve_transport("anthropic_native"), AnthropicNativeTransport)


def test_resolve_adapter_for_profile_uses_adapter_kind() -> None:
    profile = _profile(adapter_kind="anthropic_native")

    assert isinstance(resolve_adapter_for_profile(profile), AnthropicNativeAdapter)


def test_resolve_transport_for_profile_uses_adapter_kind() -> None:
    profile = _profile(adapter_kind="anthropic_native")

    assert isinstance(resolve_transport_for_profile(profile), AnthropicNativeTransport)


def test_resolve_adapter_fails_for_unimplemented_adapter_kind() -> None:
    with pytest.raises(AdapterNotSupportedError, match="openai_responses"):
        resolve_adapter("openai_responses")


def test_resolve_transport_fails_for_unimplemented_adapter_kind() -> None:
    with pytest.raises(TransportNotSupportedError, match="openai_responses"):
        resolve_transport("openai_responses")
