import time

from rd_agent_contracts.clock import Clock, FrozenClock, SystemClock


def test_system_clock_now_ms():
    c: Clock = SystemClock()
    a = c.now_ms()
    time.sleep(0.01)
    b = c.now_ms()
    assert b > a
    assert isinstance(a, int)


def test_frozen_clock_for_replay():
    """replay/test 用 FrozenClock，时间不动。"""
    c = FrozenClock(initial_ms=1714377600000)
    assert c.now_ms() == 1714377600000
    assert c.now_ms() == 1714377600000  # 不变


def test_frozen_clock_advance():
    c = FrozenClock(initial_ms=1000)
    c.advance(500)
    assert c.now_ms() == 1500
