from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")


@dataclass(frozen=True)
class WorkspacePackage:
    name: str
    version: str
    package_dir: Path
    dependencies: tuple[str, ...]

    @property
    def module_name(self) -> str:
        return self.name.replace("-", "_")


def canonicalize_name(name: str) -> str:
    return name.replace("_", "-").lower()


def parse_requirement_name(requirement: str) -> str:
    match = _REQ_NAME_RE.match(requirement)
    if match is None:
        raise ValueError(f"could not parse requirement name: {requirement!r}")
    return canonicalize_name(match.group(1))


def read_project_metadata(pyproject_path: Path) -> dict[str, Any]:
    if not pyproject_path.exists():
        raise ValueError(f"pyproject.toml not found: {pyproject_path}")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise ValueError(f"missing [project] table: {pyproject_path}")
    return project


def discover_workspace_packages(repo_root: Path) -> dict[str, WorkspacePackage]:
    package_dirs = sorted((repo_root / "packages").glob("rd-*/pyproject.toml"))
    package_dirs.append(repo_root / "tools" / "pyproject.toml")

    packages: dict[str, WorkspacePackage] = {}
    for pyproject_path in package_dirs:
        project = read_project_metadata(pyproject_path)
        name = str(project["name"])
        version = str(project["version"])
        dependencies = tuple(
            parse_requirement_name(str(item))
            for item in project.get("dependencies", [])
        )
        packages[canonicalize_name(name)] = WorkspacePackage(
            name=name,
            version=version,
            package_dir=pyproject_path.parent,
            dependencies=dependencies,
        )
    return packages


def resolve_local_install_order(
    package_name: str,
    packages: dict[str, WorkspacePackage],
) -> tuple[WorkspacePackage, ...]:
    target_name = canonicalize_name(package_name)
    if target_name not in packages:
        raise ValueError(f"workspace package not found: {package_name}")

    ordered: list[WorkspacePackage] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise ValueError(f"cycle in local workspace dependencies at {name}")
        visiting.add(name)
        package = packages[name]
        for dependency in package.dependencies:
            if dependency in packages:
                visit(dependency)
        visiting.remove(name)
        visited.add(name)
        ordered.append(package)

    visit(target_name)
    return tuple(ordered)


def find_wheel(package: WorkspacePackage, *, dist_dir: Path) -> Path:
    wheel_prefix = package.name.replace("-", "_")
    matches = sorted(dist_dir.glob(f"{wheel_prefix}-{package.version}-*.whl"))
    if not matches:
        raise ValueError(
            f"wheel not found for {package.name}=={package.version} in {dist_dir}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"multiple wheels found for {package.name}=={package.version}: {matches}"
        )
    return matches[0]


def smoke_code_for(package: WorkspacePackage) -> str:
    if package.name == "rd-agent-core":
        return """
import asyncio

from rd_agent_contracts import TextBlock
from rd_agent_core import (
    AgentRunner,
    AnthropicNativeLLMClient,
    OpenAICompatLLMClient,
    ProviderClientConfig,
    ToolSafetyPolicy,
)
from rd_agent_core.testing import AgentCoreHarness, ScriptedLLMClient
from rd_llm_adapter import TurnDone


def final_turn(_request):
    text = TextBlock("wheel-smoke")
    return [
        TurnDone(
            stop_reason="end_turn",
            content=[text],
            text_blocks=[text],
            reasoning_blocks=[],
            tool_calls=[],
            invalid_tool_calls=[],
            raw_stop_reason="stop",
        )
    ]


async def main():
    harness = AgentCoreHarness(llm_client=ScriptedLLMClient([final_turn]))
    result = await harness.run()
    assert result.completed.stop_reason == "end_turn"
    assert result.events


asyncio.run(main())
assert AgentRunner
assert AnthropicNativeLLMClient
assert OpenAICompatLLMClient
assert ProviderClientConfig
assert ToolSafetyPolicy
"""
    if package.name == "rd-agent-contracts":
        return """
from rd_agent_contracts import EventDraft, Usage

event = EventDraft(event_type="wheel_smoke", payload={"ok": True}).to_event(
    run_id="run-wheel-smoke",
    seq=1,
    timestamp_ms=1,
)
assert event.event_type == "wheel_smoke"
assert Usage(input_tokens=1).input_tokens == 1
"""
    if package.name == "rd-llm-adapter":
        return """
from rd_llm_adapter import OpenAICompatAdapter, TurnDone, supported_adapter_kinds

assert "openai_compat" in supported_adapter_kinds()
session = OpenAICompatAdapter().create_parser_session()
events = list(session.finalize())
assert isinstance(events[-1], TurnDone)
"""
    return f"import {package.module_name}\n"


def verify_wheel_install(
    package_name: str,
    *,
    repo_root: Path,
    dist_dir: Path,
) -> None:
    packages = discover_workspace_packages(repo_root)
    install_order = resolve_local_install_order(package_name, packages)
    wheel_paths = [find_wheel(package, dist_dir=dist_dir) for package in install_order]
    target = packages[canonicalize_name(package_name)]

    with tempfile.TemporaryDirectory(prefix="rd-wheel-smoke-") as temp_dir:
        venv_dir = Path(temp_dir) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        python_bin = _venv_python(venv_dir)
        subprocess.run(
            [
                str(python_bin),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--find-links",
                str(dist_dir),
                *(str(path) for path in wheel_paths),
            ],
            check=True,
        )
        subprocess.run(
            [str(python_bin), "-c", smoke_code_for(target)],
            check=True,
        )


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", help="Workspace package name, e.g. rd-agent-core")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=Path("dist"),
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    dist_dir = args.dist_dir
    if not dist_dir.is_absolute():
        dist_dir = repo_root / dist_dir
    dist_dir = dist_dir.resolve()

    verify_wheel_install(
        args.package,
        repo_root=repo_root,
        dist_dir=dist_dir,
    )
    print(f"Verified wheel install smoke for {args.package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
