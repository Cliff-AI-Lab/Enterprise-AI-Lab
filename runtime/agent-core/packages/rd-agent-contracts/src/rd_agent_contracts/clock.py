"""Clock protocol —— replay/test 时用 FrozenClock 保 determinism。"""
from __future__ import annotations

import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def now_ms(self) -> int: ...


class SystemClock:
    """生产实现。"""

    def now_ms(self) -> int:
        return int(time.time() * 1000)


class FrozenClock:
    """replay 实现，时间手动推进。"""

    def __init__(self, initial_ms: int) -> None:
        self._now = initial_ms

    def now_ms(self) -> int:
        return self._now

    def advance(self, delta_ms: int) -> None:
        self._now += delta_ms
