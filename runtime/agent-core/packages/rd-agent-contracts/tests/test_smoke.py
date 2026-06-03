"""Smoke test：验证 package 能被 import + 版本常量与 pyproject metadata 对齐。"""
from importlib.metadata import version

from rd_agent_contracts import SCHEMA_VERSION, __version__


def test_package_importable():
    """__version__ 常量必须与 wheel metadata 同步（Phase B-1 ship report 教训）。"""
    assert __version__ == version("rd-agent-contracts")


def test_schema_version_is_canonical():
    """SCHEMA_VERSION 反映 contract schema 版本，仅在字段/类型 breaking change 时 bump。
    当前 1.2.0（Phase B-1 Task 1-3 加 typed transcript blocks 时升的）。"""
    assert SCHEMA_VERSION == "1.2.0"
