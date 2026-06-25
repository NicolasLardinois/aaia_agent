import asyncio
from datetime import date, timedelta
from unittest.mock import MagicMock

import agents.market_cockpit.sentiment.put_call_agent as pc_mod
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

def _run(agent):
    return asyncio.run(agent.run())


def test_persistent_history_used_without_network_refetch(monkeypatch):
    """Mit genug gespeicherten Werten (≥ min_n) zieht der Agent KEINE Netz-Historie
    mehr — genau das Ziel der Aufgabe (Tages-Refetch eliminiert im Steady State)."""
    monkeypatch.setattr(pc_mod, "_fetch_cboe_put_call", lambda: 1.5)
    called = {"history": 0}

    def _boom():
        called["history"] += 1
        return [1.0] * 90

    monkeypatch.setattr(pc_mod, "_fetch_cboe_put_call_history", _boom)
    base = date.today() - timedelta(days=40)
    seed = {_SERIES: [(base + timedelta(days=i), 0.9) for i in range(25)]}  # 25 ≥ min_n=20
    hist = InMemoryDatedHistory(seed)
    agent = PutCallAgent(MagicMock(), MagicMock(), history=hist)

    result = _run(agent)

    assert called["history"] == 0, "Netz-Historie darf bei genug persistenter Reihe nicht gezogen werden"
    assert result.ratio == 1.5


def test_persistent_history_appends_today(monkeypatch):
    """Der heutige Wert wird für künftige Läufe in der Reihe protokolliert."""
    monkeypatch.setattr(pc_mod, "_fetch_cboe_put_call", lambda: 1.23)
    monkeypatch.setattr(pc_mod, "_fetch_cboe_put_call_history", lambda: [])
    hist = InMemoryDatedHistory()
    agent = PutCallAgent(MagicMock(), MagicMock(), history=hist)

    _run(agent)

    today_vals = [v for d, v in hist.values(_SERIES) if d == date.today()]
    assert today_vals == [1.23]


def test_warmup_falls_back_to_network_seed(monkeypatch):
    """Persistente Reihe < min_n → einmaliges Netz-Seeding (kein Signal-Regress in
    der Warm-up-Phase, bis die persistente Reihe lang genug ist)."""
    monkeypatch.setattr(pc_mod, "_fetch_cboe_put_call", lambda: 1.5)
    called = {"history": 0}

    def _seed():
        called["history"] += 1
        return [1.0] * 90

    monkeypatch.setattr(pc_mod, "_fetch_cboe_put_call_history", _seed)
    hist = InMemoryDatedHistory()  # leer → Warm-up
    agent = PutCallAgent(MagicMock(), MagicMock(), history=hist)

    _run(agent)

    assert called["history"] == 1, "bei zu kurzer persistenter Reihe muss einmal geseedet werden"


def test_no_history_port_uses_network_refetch(monkeypatch):
    """history=None (Altpfad/Backtester) → wie bisher Netz-Refetch (rückwärtskompatibel)."""
    monkeypatch.setattr(pc_mod, "_fetch_cboe_put_call", lambda: 1.5)
    called = {"history": 0}

    def _net():
        called["history"] += 1
        return [1.0] * 90

    monkeypatch.setattr(pc_mod, "_fetch_cboe_put_call_history", _net)
    agent = PutCallAgent(MagicMock(), MagicMock())  # kein history

    _run(agent)

    assert called["history"] == 1
