from __future__ import annotations

from rd_llm_adapter._usage import UsageRecord, normalize_usage


def test_normalize_usage_preserves_cache_token_breakdown() -> None:
    usage = normalize_usage(
        {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_read_input_tokens": 3,
            "cache_creation_input_tokens": 7,
        }
    )

    assert usage.cache_read_input_tokens == 3
    assert usage.cache_creation_input_tokens == 7
    assert usage.cached_input_tokens == 10


def test_normalize_usage_maps_legacy_cached_tokens_to_cache_read() -> None:
    usage = normalize_usage(
        {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "prompt_tokens_details": {"cached_tokens": 4},
        }
    )

    assert usage.cache_read_input_tokens == 4
    assert usage.cache_creation_input_tokens == 0
    assert usage.cached_input_tokens == 4


def test_usage_record_add_computes_total_from_component_tokens() -> None:
    usage = UsageRecord(input_tokens=10, output_tokens=5, total_tokens=15) + UsageRecord(
        input_tokens=4,
        output_tokens=1,
        total_tokens=0,
    )

    assert usage.input_tokens == 14
    assert usage.output_tokens == 6
    assert usage.total_tokens == 20


def test_usage_record_add_preserves_cache_token_breakdown() -> None:
    usage = UsageRecord(
        input_tokens=10,
        output_tokens=5,
        cache_read_input_tokens=3,
        cache_creation_input_tokens=7,
    ) + UsageRecord(
        input_tokens=4,
        output_tokens=1,
        cache_read_input_tokens=2,
        cache_creation_input_tokens=11,
    )

    assert usage.cache_read_input_tokens == 5
    assert usage.cache_creation_input_tokens == 18
    assert usage.cached_input_tokens == 23


def test_usage_record_roundtrip_serialization_does_not_double_count_cache() -> None:
    original = UsageRecord(
        input_tokens=10,
        output_tokens=5,
        cache_read_input_tokens=3,
        cache_creation_input_tokens=7,
    )

    usage = normalize_usage(original.to_dict())

    assert usage.input_tokens == 10
    assert usage.output_tokens == 5
    assert usage.cache_read_input_tokens == 3
    assert usage.cache_creation_input_tokens == 7
    assert usage.cached_input_tokens == 10


def test_normalize_usage_prefers_split_cache_fields_over_legacy_cached_total() -> None:
    usage = normalize_usage(
        {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_read_input_tokens": 3,
            "cache_creation_input_tokens": 7,
            "cached_input_tokens": 10,
        }
    )

    assert usage.cache_read_input_tokens == 3
    assert usage.cache_creation_input_tokens == 7
    assert usage.cached_input_tokens == 10
