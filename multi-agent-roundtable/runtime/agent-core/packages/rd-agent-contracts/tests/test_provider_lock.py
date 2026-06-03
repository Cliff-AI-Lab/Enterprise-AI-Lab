from rd_agent_contracts.provider_lock import ProviderLock


def test_provider_lock_anthropic():
    lock = ProviderLock(
        provider_id="anthropic-direct",
        adapter_family="anthropic",
        tool_protocol="anthropic_tool_use",
        reasoning_protocol="anthropic_thinking",
        locked_at_run_id="run_123",
    )
    assert lock.provider_id == "anthropic-direct"
    assert lock.adapter_family == "anthropic"


def test_provider_lock_openai_compat():
    lock = ProviderLock(
        provider_id="openrouter-claude",
        adapter_family="openai_compat",
        tool_protocol="openai_tool_calls",
        reasoning_protocol=None,
        locked_at_run_id="run_456",
    )
    assert lock.reasoning_protocol is None


def test_provider_lock_compatible_adapter():
    """同一 transcript 内只能换"协议族相同"的 provider。"""
    lock = ProviderLock(
        provider_id="anthropic-direct",
        adapter_family="anthropic",
        tool_protocol="anthropic_tool_use",
        reasoning_protocol="anthropic_thinking",
        locked_at_run_id="run_123",
    )
    assert lock.is_compatible_with(
        adapter_family="anthropic",
        tool_protocol="anthropic_tool_use",
        reasoning_protocol="anthropic_thinking",
    )
    assert not lock.is_compatible_with(
        adapter_family="openai_compat", tool_protocol="openai_tool_calls"
    )
    assert not lock.is_compatible_with(
        adapter_family="anthropic",
        tool_protocol="anthropic_tool_use",
        reasoning_protocol=None,
    )


def test_provider_lock_reasoning_protocol_mismatch_rejects():
    """跨 turn 切换 reasoning protocol 会丢 signed thinking signature，必须拒绝。"""
    lock = ProviderLock(
        provider_id="anthropic-direct",
        adapter_family="anthropic",
        tool_protocol="anthropic_tool_use",
        reasoning_protocol="anthropic_thinking",
        locked_at_run_id="run_123",
    )
    # 同 family + tool，但 reasoning 协议不同 → 拒绝
    # （anthropic_thinking 用 signed block，openai_field 用 reasoning_content 字段）
    assert not lock.is_compatible_with(
        adapter_family="anthropic",
        tool_protocol="anthropic_tool_use",
        reasoning_protocol="openai_field",
    )


def test_provider_lock_tool_protocol_mismatch_rejects():
    """tool_protocol 不一致会让 tool_use_id 解析错位，必须拒绝。"""
    lock = ProviderLock(
        provider_id="anthropic-direct",
        adapter_family="anthropic",
        tool_protocol="anthropic_tool_use",
        reasoning_protocol="anthropic_thinking",
        locked_at_run_id="run_123",
    )
    assert not lock.is_compatible_with(
        adapter_family="anthropic",
        tool_protocol="openai_tool_calls",
        reasoning_protocol="anthropic_thinking",
    )
