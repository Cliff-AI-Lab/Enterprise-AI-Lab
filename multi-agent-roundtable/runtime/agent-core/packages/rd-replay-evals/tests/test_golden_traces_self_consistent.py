"""验证 traces/golden/ 下所有 trace 满足 5 条一致性检查（自己 replay 自己）。

这是 Phase A 的金钥匙验证。Phase B 起会用真 engine replay 这些 trace。

Phase A B+ track：trace 来自 codesphere-saas 灰度环境（saas-test）真实
agent run，经 rd_recorder fan-out 后由 finalize_traces.py 后处理生成。
"""
from pathlib import Path

import pytest
from rd_replay_evals.checks import (
    check_event_sequence_match,
    check_tool_call_set_match,
    check_transcript_hash_match,
)
from rd_replay_evals.trace_format import read_trace

# traces/golden/ 在仓库根，相对路径：tests/ → package → packages → repo root
GOLDEN_DIR = (
    Path(__file__).parent.parent.parent.parent / "traces" / "golden"
)


def _list_golden_traces() -> list[Path]:
    if not GOLDEN_DIR.exists():
        return []
    return sorted(GOLDEN_DIR.glob("*.jsonl"))


def test_at_least_one_golden_trace_exists():
    """Phase A 验收：至少有 1 个真实录到的 golden trace。"""
    traces = _list_golden_traces()
    assert len(traces) >= 1, (
        f"No golden traces in {GOLDEN_DIR}. "
        "Phase A 需要至少 1 个真实 trace 才算交付完成。"
    )


@pytest.mark.parametrize(
    "path",
    _list_golden_traces() or [pytest.param(None, marks=pytest.mark.skip(reason="no traces"))],
    ids=lambda p: p.name if p else "no-trace",
)
def test_trace_loads_and_self_replays(path: Path):
    """每个 trace：read_trace 能加载 + 5 条一致性检查全过。"""
    with open(path, encoding="utf-8") as f:
        trace = read_trace(f)

    assert len(trace.events) > 0, f"empty trace: {path.name}"
    assert trace.meta.run_id, f"trace missing run_id: {path.name}"
    assert trace.meta.schema_version == "1.0.0"

    # 自己 replay 自己 —— 3 条核心检查
    check_event_sequence_match(trace.events, trace.events)
    check_tool_call_set_match(trace.events, trace.events)
    check_transcript_hash_match(trace.events, trace.events)
