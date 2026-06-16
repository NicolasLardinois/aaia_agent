from datetime import date
from agents.market_cockpit.macro.interest_rate_agent import _direction, _signal
from core.domain.models import Signal
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory


def test_direction_rising_from_dated_history():
    h = InMemoryDatedHistory({"fed_rate": [(date(2026, 1, 1), 4.0), (date(2026, 6, 1), 4.5)]})
    # today injiziert → deterministisch: ref = 2026-06-01 − 3M = 2026-03-01 → prev = 4.0
    assert _direction(current=4.5, history=h, series="fed_rate", months_back=3, today=date(2026, 6, 1)) == "rising"


def test_direction_falling_from_dated_history():
    h = InMemoryDatedHistory({"fed_rate": [(date(2026, 1, 1), 5.0), (date(2026, 6, 1), 4.0)]})
    assert _direction(current=4.0, history=h, series="fed_rate", months_back=3, today=date(2026, 6, 1)) == "falling"


def test_direction_stable_without_history():
    assert _direction(current=4.0, history=None, series="fed_rate", months_back=3) == "stable"


def test_signal_falling_negative_real_is_bullish():
    assert _signal(rate=2.0, direction="falling", real_rate=-0.5) == Signal.BULLISH


def test_signal_rising_high_real_is_bearish_for_eu_too():
    # real_rate jetzt auch für EU gesetzt → der Zweig ist kein toter Code mehr
    assert _signal(rate=3.5, direction="rising", real_rate=2.5) == Signal.BEARISH
