from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "tools" / "scripts" / "verify_release_tag.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_release_tag", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_release_tag_accepts_workspace_package_names() -> None:
    module = _load_module()

    assert module.parse_release_tag("rd-agent-core-v0.1.0") == (
        "rd-agent-core",
        "0.1.0",
    )
    assert module.parse_release_tag("rd-tools-v1.0.0") == ("rd-tools", "1.0.0")


def test_verify_release_tag_matches_pyproject_version() -> None:
    module = _load_module()
    pyproject = module.read_project_metadata(
        REPO_ROOT / "packages" / "rd-agent-core" / "pyproject.toml"
    )

    release = module.verify_release_tag(
        f"rd-agent-core-v{pyproject['version']}",
        repo_root=REPO_ROOT,
    )

    assert release.package == "rd-agent-core"
    assert release.version == pyproject["version"]
    assert release.package_dir == REPO_ROOT / "packages" / "rd-agent-core"


def test_verify_release_tag_supports_tools_package() -> None:
    module = _load_module()
    pyproject = module.read_project_metadata(REPO_ROOT / "tools" / "pyproject.toml")

    release = module.verify_release_tag(
        f"rd-tools-v{pyproject['version']}",
        repo_root=REPO_ROOT,
    )

    assert release.package == "rd-tools"
    assert release.package_dir == REPO_ROOT / "tools"


def test_verify_release_tag_rejects_version_drift() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="does not match"):
        module.verify_release_tag("rd-agent-core-v999.0.0", repo_root=REPO_ROOT)


def test_verify_release_tag_rejects_malformed_tag() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="release tag must match"):
        module.parse_release_tag("agent-core-0.1.0")
