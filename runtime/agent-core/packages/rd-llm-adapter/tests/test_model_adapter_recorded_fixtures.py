from __future__ import annotations

import os
from pathlib import Path

import pytest
from rd_llm_adapter.recorder import StreamRecorder
from rd_llm_adapter.registry import resolve_adapter

DEFAULT_RECORDED_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "recorded" / "model_adapter"


def _recorded_fixture_paths() -> list[Path]:
    fixture_dir = Path(
        os.getenv(
            "MODEL_ADAPTER_RECORDED_FIXTURES_DIR",
            str(DEFAULT_RECORDED_FIXTURE_DIR),
        )
    )
    if not fixture_dir.exists():
        return []
    return sorted(
        [
            *fixture_dir.glob("*.jsonl"),
            *fixture_dir.glob("*.jsonl.gz"),
        ]
    )


def test_recorded_model_adapter_fixtures_replay_without_diff() -> None:
    paths = _recorded_fixture_paths()
    if not paths:
        pytest.skip(
            "no recorded model adapter fixtures; set MODEL_ADAPTER_RECORDED_FIXTURES_DIR"
        )

    recorder = StreamRecorder()
    failures: list[str] = []

    for path in paths:
        recorded = recorder.load_turn(path)
        adapter = resolve_adapter(
            str(recorded.profile_snapshot.get("adapter_kind", "openai_compat"))
        )
        events, _turn_done = recorder.replay_through_adapter(recorded, adapter)
        diffs = recorder.diff_against_legacy(recorded, events)
        if diffs:
            failures.append(f"{path}: {'; '.join(diffs)}")

    assert failures == []
