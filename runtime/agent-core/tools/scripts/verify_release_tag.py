from __future__ import annotations

import argparse
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TAG_RE = re.compile(r"^(rd-[a-z0-9][a-z0-9-]*)-v([^/]+)$")


@dataclass(frozen=True)
class ReleaseTag:
    package: str
    version: str
    package_dir: Path


def parse_release_tag(tag: str) -> tuple[str, str]:
    match = _TAG_RE.fullmatch(tag)
    if match is None:
        raise ValueError(
            "release tag must match rd-<package-name>-v<version>, "
            f"got {tag!r}"
        )
    return match.group(1), match.group(2)


def resolve_package_dir(package: str, *, repo_root: Path) -> Path:
    if package == "rd-tools":
        return repo_root / "tools"
    return repo_root / "packages" / package


def read_project_metadata(pyproject_path: Path) -> dict[str, Any]:
    if not pyproject_path.exists():
        raise ValueError(f"pyproject.toml not found: {pyproject_path}")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise ValueError(f"missing [project] table: {pyproject_path}")
    return project


def verify_release_tag(tag: str, *, repo_root: Path) -> ReleaseTag:
    package, tag_version = parse_release_tag(tag)
    package_dir = resolve_package_dir(package, repo_root=repo_root)
    if not package_dir.is_dir():
        raise ValueError(f"package directory not found: {package_dir}")

    project = read_project_metadata(package_dir / "pyproject.toml")
    project_name = project.get("name")
    if project_name != package:
        raise ValueError(
            f"tag package {package!r} does not match pyproject name {project_name!r}"
        )

    project_version = project.get("version")
    if project_version != tag_version:
        raise ValueError(
            f"tag version {tag_version!r} does not match "
            f"{package_dir / 'pyproject.toml'} version {project_version!r}"
        )
    return ReleaseTag(package=package, version=tag_version, package_dir=package_dir)


def emit_github_outputs(release: ReleaseTag) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write(f"pkg={release.package}\n")
        output.write(f"version={release.version}\n")
        output.write(f"pkg_dir={release.package_dir.as_posix()}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", help="Release tag, for example rd-agent-core-v0.1.0")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args(argv)

    release = verify_release_tag(args.tag, repo_root=args.repo_root.resolve())
    emit_github_outputs(release)
    print(
        "Verified release tag: "
        f"pkg={release.package} "
        f"version={release.version} "
        f"pkg_dir={release.package_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
