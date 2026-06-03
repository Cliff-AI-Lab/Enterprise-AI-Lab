from __future__ import annotations

from pathlib import Path

import rd_agent_core

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_recommended_public_exports_are_documented() -> None:
    docs = (REPO_ROOT / "docs" / "API-REFERENCE.md").read_text(encoding="utf-8")
    required = {
        "AgentRunner",
        "AgentRunnerRequest",
        "AgentRunnerResult",
        "CoreErrorCategory",
        "CoreErrorType",
        "RunKernel",
        "RunObserverPort",
        "RunRequest",
        "RunSummary",
        "ToolSafetyPolicy",
        "TurnKernel",
        "TurnRequest",
        "assert_event_log_port_conformance",
        "assert_run_persistence_port_conformance",
        "assert_tool_executor_port_conformance",
    }

    exports = set(rd_agent_core.__all__)
    for name in required:
        assert name in exports
        assert f"`{name}`" in docs
