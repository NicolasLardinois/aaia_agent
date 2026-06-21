import asyncio
from unittest.mock import AsyncMock, MagicMock

from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from agents.stock_deep_dive.bond.bond_metrics_agent import BondMetricsAgent
from agents.stock_deep_dive.bond.bond_duration_agent import BondDurationAgent
from agents.stock_deep_dive.bond.bond_spread_agent import BondSpreadAgent
from core.domain.models import (
    Signal, SignalStatus, RiskAffinity,
    BondMetricsSnapshot, BondDurationSnapshot, BondCreditSnapshot, BondSpreadSnapshot,
)


def _metrics(signal, status):
    return BondMetricsSnapshot(bond_type="corporate", current_price=None, coupon=None,
        maturity_years=None, ytm=None, ytc=None, current_yield=None, real_yield=None,
        country=None, breakeven_inflation=None, issuer=None, sector=None,
        signal=signal, status=status)


def _duration(signal, status):
    return BondDurationSnapshot(macaulay_duration=None, modified_duration=None,
        convexity=None, dv01=None, signal=signal, status=status)


def _spread(signal, status):
    return BondSpreadSnapshot(spread_bps=None, oas=None, z_spread=None,
        spread_trend="stable", signal=signal, status=status)


def _credit(sp):
    return BondCreditSnapshot(moodys=None, sp=sp, fitch=None, category="high_yield",
        trend="stable", default_probability=None, signal=Signal.NEUTRAL)


# ── Chief: unverfügbare Komponenten werden ausgeschlossen (§3.4) ──────────────

def test_chief_excludes_unavailable_components():
    """UNAVAILABLE metrics/duration/spread fließen NICHT als neutrale 0-Stimme ein,
    sondern werden weggelassen und der Rest re-normalisiert."""
    chief = BondChiefAgent(MagicMock(), MagicMock(), MagicMock())
    chief.bond_metrics_agent.run  = AsyncMock(return_value=_metrics(Signal.BULLISH, SignalStatus.AVAILABLE))
    chief.bond_duration_agent.run = AsyncMock(return_value=_duration(Signal.NEUTRAL, SignalStatus.UNAVAILABLE))
    chief.bond_spread_agent.run   = AsyncMock(return_value=_spread(Signal.NEUTRAL, SignalStatus.UNAVAILABLE))
    chief.bond_credit_agent.run   = AsyncMock(return_value=_credit("BB"))  # → Band MITTEL
    res = asyncio.run(chief.run("X", "corporate", "stable", RiskAffinity.NEUTRAL))
    # Verfügbar: metrics +1, credit MITTEL/neutral -0.5 → (1-0.5)/2 = 0.25 → BULLISH.
    # Würde man die zwei UNAVAILABLE als 0 mitzählen: (1+0+0-0.5)/4 = 0.125 → NEUTRAL.
    assert res.overall_signal == Signal.BULLISH


# ── Agenten setzen den Status anhand der Signal-treibenden Daten ──────────────

def test_metrics_agent_unavailable_without_data():
    prov = MagicMock(); prov.get_bond_data.return_value = {}
    macro = MagicMock(); macro.get_economic_state.return_value = {}
    snap = asyncio.run(BondMetricsAgent(prov, macro, MagicMock()).run("X", "corporate"))
    assert snap.status == SignalStatus.UNAVAILABLE


def test_metrics_agent_available_with_real_yield():
    prov = MagicMock(); prov.get_bond_data.return_value = {
        "current_price": 95, "coupon_rate": 0.04, "maturity_years": 10, "face": 100, "frequency": 2}
    macro = MagicMock(); macro.get_economic_state.return_value = {"inflation": 0.02}
    snap = asyncio.run(BondMetricsAgent(prov, macro, MagicMock()).run("X", "corporate"))
    assert snap.real_yield is not None
    assert snap.status == SignalStatus.AVAILABLE


def test_duration_agent_unavailable_without_data():
    prov = MagicMock(); prov.get_bond_data.return_value = {}
    snap = asyncio.run(BondDurationAgent(prov, MagicMock()).run("X", "rising"))
    assert snap.status == SignalStatus.UNAVAILABLE


def test_duration_agent_available_with_data():
    prov = MagicMock(); prov.get_bond_data.return_value = {
        "current_price": 100, "coupon_rate": 0.05, "maturity_years": 10, "face": 100, "frequency": 2}
    snap = asyncio.run(BondDurationAgent(prov, MagicMock()).run("X", "rising"))
    assert snap.modified_duration is not None
    assert snap.status == SignalStatus.AVAILABLE


def test_spread_agent_unavailable_without_data():
    prov = MagicMock(); prov.get_bond_data.return_value = {}
    snap = asyncio.run(BondSpreadAgent(prov, MagicMock()).run("X"))
    assert snap.status == SignalStatus.UNAVAILABLE


def test_spread_agent_available_with_spread():
    prov = MagicMock(); prov.get_bond_data.return_value = {"spread_bps": 150, "spread_trend": "widening"}
    snap = asyncio.run(BondSpreadAgent(prov, MagicMock()).run("X"))
    assert snap.status == SignalStatus.AVAILABLE
    assert snap.signal == Signal.BEARISH


def test_default_snapshots_are_unavailable():
    """Die No-Data-Fallbacks (default()) gelten als unverfügbar."""
    assert BondMetricsAgent.default().status == SignalStatus.UNAVAILABLE
    assert BondDurationAgent.default().status == SignalStatus.UNAVAILABLE
    assert BondSpreadAgent.default().status == SignalStatus.UNAVAILABLE
