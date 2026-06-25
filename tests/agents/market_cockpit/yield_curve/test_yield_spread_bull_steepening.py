"""§D1: Bull-Steepening-Timing-Signal verdrahten.

Die Logik in `_point` (frisch invertiert → NEUTRAL/Warnung; Bewegung AUS der
Inversion heraus nach oben → BEARISH-Timing-Signal) war vorhanden, aber `run()`
übergab `prev_10y3m=None` → der BEARISH-Zweig feuerte nie. Jetzt liest der Agent
die Vorperiode aus einer injizierten `DatedHistoryPort` und protokolliert den
heutigen Wert für den nächsten Lauf.
"""
import asyncio
from datetime import date
from unittest.mock import MagicMock

from agents.market_cockpit.yield_curve.yield_spread_agent import YieldSpreadAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory
from core.domain.models import Signal


def _macro(usa_10y2y=None, usa_10y3m=None):
    m = MagicMock()
    m.get_economic_state.return_value = {"yield_curve": usa_10y2y}
    m.get_extended_state.return_value = {"yield_curve_3m10y": usa_10y3m}
    return m


def _empty_provider():
    p = MagicMock()
    p.get_yield_spreads.return_value = {}
    return p


def test_bull_steepening_feuert_bearish_mit_historie():
    """Vorperiode invertiert (-0.30), heute höher (-0.10) → Bewegung aus der
    Inversion heraus → BEARISH-Timing-Signal."""
    macro = _macro(usa_10y2y=-0.20, usa_10y3m=-0.10)
    hist = InMemoryDatedHistory({"usa_10y3m": [(date(2026, 1, 1), -0.30)]})
    agent = YieldSpreadAgent(macro, _empty_provider(), _empty_provider(), MagicMock(), history=hist)
    result = asyncio.run(agent.run())
    assert result.usa.signal == Signal.BEARISH


def test_ohne_historie_unveraendert_neutral():
    """Ohne injizierte Historie (Default None) bleibt eine laufende Inversion eine
    Warnung (NEUTRAL) — kein verfrühtes BEARISH (verhaltens-erhaltend)."""
    macro = _macro(usa_10y2y=-0.20, usa_10y3m=-0.10)
    agent = YieldSpreadAgent(macro, _empty_provider(), _empty_provider(), MagicMock())  # history=None
    result = asyncio.run(agent.run())
    assert result.usa.signal == Signal.NEUTRAL


def test_heutiger_wert_wird_protokolliert():
    """Der heutige usa_10y3m wird für den nächsten Lauf in die Historie geschrieben."""
    macro = _macro(usa_10y2y=0.5, usa_10y3m=0.4)
    hist = InMemoryDatedHistory()
    agent = YieldSpreadAgent(macro, _empty_provider(), _empty_provider(), MagicMock(), history=hist)
    asyncio.run(agent.run())
    assert hist.latest("usa_10y3m") == (date.today(), 0.4)


def test_inversion_ohne_vorperiode_bleibt_neutral():
    """Erste Beobachtung (leere Historie) einer Inversion → kein prev → NEUTRAL,
    aber der Wert wird protokolliert (nächster Lauf kann Bull-Steepening erkennen)."""
    macro = _macro(usa_10y2y=-0.20, usa_10y3m=-0.30)
    hist = InMemoryDatedHistory()
    agent = YieldSpreadAgent(macro, _empty_provider(), _empty_provider(), MagicMock(), history=hist)
    result = asyncio.run(agent.run())
    assert result.usa.signal == Signal.NEUTRAL
    assert hist.latest("usa_10y3m") == (date.today(), -0.30)


# ── DI-Verdrahtung: Chief reicht die Historie an den Sub-Agenten durch ────────

def test_history_durch_chief_verdrahtet():
    sentinel = InMemoryDatedHistory()
    chief = YieldCurveChiefAgent(MagicMock(), MagicMock(), MagicMock(), MagicMock(), history=sentinel)
    assert chief.yield_spread_agent.history is sentinel
