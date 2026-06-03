"""pytest 配置：把 rd-llm-adapter 包根加入 sys.path。

让测试可以 `from scripts.validate_model_adapter_fixtures import ...`，
而无需安装 scripts/ 为独立包。
"""
from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))
