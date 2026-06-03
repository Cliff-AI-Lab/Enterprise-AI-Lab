from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src" / "rd_agent_core"


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", maxsplit=1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])
    return roots


def test_core_package_has_no_host_or_transport_framework_imports() -> None:
    forbidden = {
        "app",
        "fastapi",
        "sqlalchemy",
        "boto3",
        "redis",
        "rd_llm_gateway",
    }
    violations: dict[str, set[str]] = {}

    for path in SOURCE_ROOT.rglob("*.py"):
        imports = _imported_roots(path)
        matched = imports & forbidden
        if matched:
            violations[str(path.relative_to(PACKAGE_ROOT))] = matched

    assert violations == {}


def test_core_package_dependencies_stay_at_contract_and_adapter_layer() -> None:
    pyproject = (PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "rd-agent-contracts" in pyproject
    assert "rd-llm-adapter" in pyproject
    assert "rd-llm-gateway" not in pyproject
    assert "sqlalchemy" not in pyproject
    assert "fastapi" not in pyproject
