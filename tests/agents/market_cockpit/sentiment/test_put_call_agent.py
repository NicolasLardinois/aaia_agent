import asyncio
from datetime import date, timedelta
from unittest.mock import MagicMock

from agents.market_cockpit.sentiment.put_call_agent import PutCallAgent, _SERIES, _signal
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory
from core.domain.models import Signal


def test_none_is_neutral():
    assert _signal(None) == Signal.NEUTRAL


def test_high_z_is_bullish_contrarian():
    # P/C deutlich über rollierendem Mittel (z > +1) = Pessimismus → BULLISH
    assert _signal(1.2) == Signal.BULLISH


def test_low_z_is_bearish_contrarian():
    # P/C deutlich unter Mittel (z < -1) = Sorglosigkeit → BEARISH
    assert _signal(-1.2) == Signal.BEARISH


def test_mid_z_is_neutral():
    assert _signal(0.3) == Signal.NEUTRAL


# ── Persistente Historie statt I/O-intensivem Tages-Refetch ──────────────────

class _FakeSource:
    """Fake-Port (CBOE): fester aktueller Wert + Seed-Historie; zählt die Abrufe."""
    def __init__(self, latest=None, history=None):
        self._latest = latest
        self._history = history if history is not None else []
        self.latest_calls = 0
        self.history_calls = 0

    def get_latest(self):
        self.latest_calls += 1
        return self._latest

    def get_history(self, n_days: int = 90):
        self.history_calls += 1
        return self._history


def _run(agent):
    return asyncio.run(agent.run())


def test_persistent_history_used_without_network_refetch():
    """Mit genug gespeicherten Werten (≥ min_n) zieht der Agent KEINE Netz-Historie
    mehr über den Port — genau das Ziel (Tages-Refetch eliminiert im Steady State)."""
    source = _FakeSource(latest=1.5, history=[1.0] * 90)
    base = date.today() - timedelta(days=40)
    seed = {_SERIES: [(base + timedelta(days=i), 0.9) for i in range(25)]}  # 25 ≥ min_n=20
    hist = InMemoryDatedHistory(seed)
    agent = PutCallAgent(MagicMock(), MagicMock(), history=hist, source=source)

    result = _run(agent)

    assert source.history_calls == 0, "Port-Historie darf bei genug persistenter Reihe nicht gezogen werden"
    assert result.ratio == 1.5


def test_persistent_history_appends_today():
    """Der heutige Wert wird für künftige Läufe in der Reihe protokolliert."""
    source = _FakeSource(latest=1.23)
    hist = InMemoryDatedHistory()
    agent = PutCallAgent(MagicMock(), MagicMock(), history=hist, source=source)

    _run(agent)

    today_vals = [v for d, v in hist.values(_SERIES) if d == date.today()]
    assert today_vals == [1.23]


def test_warmup_falls_back_to_network_seed():
    """Persistente Reihe < min_n → einmaliges Seeding über den Port (kein
    Signal-Regress in der Warm-up-Phase, bis die persistente Reihe lang genug ist)."""
    source = _FakeSource(latest=1.5, history=[1.0] * 90)
    hist = InMemoryDatedHistory()  # leer → Warm-up
    agent = PutCallAgent(MagicMock(), MagicMock(), history=hist, source=source)

    _run(agent)

    assert source.history_calls == 1, "bei zu kurzer persistenter Reihe muss einmal geseedet werden"


def test_no_history_port_uses_source_seed():
    """history=None (Altpfad/Backtester) → wie bisher Seed über den Port (kompatibel)."""
    source = _FakeSource(latest=1.5, history=[1.0] * 90)
    agent = PutCallAgent(MagicMock(), MagicMock(), source=source)  # kein history

    _run(agent)

    assert source.history_calls == 1


def test_ohne_source_kein_netz_neutral():
    """Kein Port + kein history → defensiv: ratio None, NEUTRAL, kein Netz/Crash."""
    agent = PutCallAgent(MagicMock(), MagicMock())  # weder source noch history
    result = _run(agent)
    assert result.ratio is None
    assert result.signal == Signal.NEUTRAL
