from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_packages_ship_py_typed_markers() -> None:
    markers = [
        REPO_ROOT / "packages" / "rd-agent-contracts" / "src" / "rd_agent_contracts" / "py.typed",
        REPO_ROOT / "packages" / "rd-llm-adapter" / "src" / "rd_llm_adapter" / "py.typed",
        REPO_ROOT / "packages" / "rd-agent-core" / "src" / "rd_agent_core" / "py.typed",
    ]

    for marker in markers:
        assert marker.is_file()
