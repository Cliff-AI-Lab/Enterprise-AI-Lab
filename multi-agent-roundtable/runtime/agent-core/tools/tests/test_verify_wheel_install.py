from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "tools" / "scripts" / "verify_wheel_install.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_wheel_install", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_discover_workspace_packages_includes_runtime_packages() -> None:
    module = _load_module()

    packages = module.discover_workspace_packages(REPO_ROOT)

    assert packages["rd-agent-contracts"].version == "1.14.1"
    assert packages["rd-llm-adapter"].version == "1.1.2"
    assert packages["rd-agent-core"].version == "0.1.3"
    assert packages["rd-tools"].package_dir == REPO_ROOT / "tools"


def test_resolve_local_install_order_for_agent_core() -> None:
    module = _load_module()
    packages = module.discover_workspace_packages(REPO_ROOT)

    order = module.resolve_local_install_order("rd-agent-core", packages)

    assert [package.name for package in order] == [
        "rd-agent-contracts",
        "rd-llm-adapter",
        "rd-agent-core",
    ]


def test_parse_requirement_name_handles_version_specifiers_and_extras() -> None:
    module = _load_module()

    assert module.parse_requirement_name("rd-agent-contracts>=1.14.1,<2") == (
        "rd-agent-contracts"
    )
    assert module.parse_requirement_name("openai[realtime]>=2.0") == "openai"
    assert module.parse_requirement_name("httpx >= 0.27 ; python_version >= '3.12'") == (
        "httpx"
    )


def test_find_wheel_uses_distribution_name_and_version(tmp_path: Path) -> None:
    module = _load_module()
    package = module.WorkspacePackage(
        name="rd-agent-core",
        version="0.1.3",
        package_dir=REPO_ROOT / "packages" / "rd-agent-core",
        dependencies=(),
    )
    wheel = tmp_path / "rd_agent_core-0.1.3-py3-none-any.whl"
    wheel.write_text("", encoding="utf-8")

    assert module.find_wheel(package, dist_dir=tmp_path) == wheel


def test_find_wheel_rejects_missing_wheel(tmp_path: Path) -> None:
    module = _load_module()
    package = module.WorkspacePackage(
        name="rd-agent-core",
        version="0.1.3",
        package_dir=REPO_ROOT / "packages" / "rd-agent-core",
        dependencies=(),
    )

    with pytest.raises(ValueError, match="wheel not found"):
        module.find_wheel(package, dist_dir=tmp_path)


def test_smoke_code_for_core_exercises_harness() -> None:
    module = _load_module()
    packages = module.discover_workspace_packages(REPO_ROOT)

    smoke = module.smoke_code_for(packages["rd-agent-core"])

    assert "AgentCoreHarness" in smoke
    assert "ScriptedLLMClient" in smoke
