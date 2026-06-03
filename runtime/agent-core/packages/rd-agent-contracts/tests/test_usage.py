from rd_agent_contracts.usage import Usage, normalize_usage


def test_usage_basic():
    u = Usage(input_tokens=100, output_tokens=50)
    assert u.input_tokens == 100
    assert u.output_tokens == 50
    assert u.total() == 150


def test_usage_zero_is_valid():
    """provider 缺失/为 0 都合法（Codex 风险点）。"""
    u = Usage(input_tokens=0, output_tokens=0)
    assert u.total() == 0


def test_normalize_usage_missing_fields():
    """provider 返回部分缺失时，normalize 补 0。"""
    u = normalize_usage({"input_tokens": 100})
    assert u.input_tokens == 100
    assert u.output_tokens == 0


def test_normalize_usage_none_returns_zero_usage():
    """provider 完全没返回 usage chunk 时，给一个 zero usage 占位。"""
    u = normalize_usage(None)
    assert u.input_tokens == 0
    assert u.output_tokens == 0


def test_normalize_usage_with_cache_tokens():
    u = normalize_usage({
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_creation_input_tokens": 200,
        "cache_read_input_tokens": 300,
    })
    assert u.cache_creation_input_tokens == 200
    assert u.cache_read_input_tokens == 300
