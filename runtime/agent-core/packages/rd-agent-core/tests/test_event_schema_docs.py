from __future__ import annotations

from pathlib import Path

from rd_agent_core import CoreEventType

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_event_payload_schema_documents_every_core_event_type() -> None:
    docs = (REPO_ROOT / "docs" / "EVENT-PAYLOAD-SCHEMA.md").read_text(
        encoding="utf-8"
    )

    for event_type in CoreEventType:
        assert f"`{event_type.value}`" in docs
