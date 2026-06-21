import asyncio
from unittest.mock import AsyncMock, MagicMock
from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from core.domain.models import (
    Signal, RiskAffinity, CreditBand,
    BondMetricsSnapshot, BondDurationSnapshot, BondCreditSnapshot, BondSpreadSnapshot,
)


def _bb_chief():
    chief = BondChiefAgent(MagicMock(), MagicMock(), MagicMock())
    m = BondMetricsSnapshot(bond_type="corporate", current_price=None, coupon=None,
        maturity_years=None, ytm=None, ytc=None, current_yield=None, real_yield=None,
        country=None, breakeven_inflation=None, issuer=None, sector=None, signal=Signal.BULLISH)
    d = BondDurationSnapshot(macaulay_duration=None, modified_duration=None, convexity=None, dv01=None, signal=Signal.NEUTRAL)
    c = BondCreditSnapshot(moodys=None, sp="BB", fitch=None, category="high_yield", trend="stable", default_probability=None, signal=Signal.NEUTRAL)
    s = BondSpreadSnapshot(spread_bps=None, oas=None, z_spread=None, spread_trend="stable", signal=Signal.NEUTRAL)
    chief.bond_metrics_agent.run  = AsyncMock(return_value=m)
    chief.bond_duration_agent.run = AsyncMock(return_value=d)
    chief.bond_credit_agent.run   = AsyncMock(return_value=c)
    chief.bond_spread_agent.run   = AsyncMock(return_value=s)
    return chief


def test_bond_chief_risikofreudig_macht_bb_bullish():
    chief = _bb_chief()
    res = asyncio.run(chief.run("X", "corporate", "stable", RiskAffinity.RISIKOFREUDIG))
    assert res.overall_signal == Signal.BULLISH
    assert res.risk_affinity == RiskAffinity.RISIKOFREUDIG
    assert res.credit_band == CreditBand.MITTEL


def test_bond_chief_konservativ_macht_bb_neutral():
    chief = _bb_chief()
    res = asyncio.run(chief.run("X", "corporate", "stable", RiskAffinity.KONSERVATIV))
    assert res.overall_signal == Signal.NEUTRAL


def test_chief_publishes_overall_in_payload():
    """Payload-Wiring: bus.publish wird mit BondChiefReady aufgerufen (overall_signal im Payload)."""
    chief = _bb_chief()
    bus = MagicMock()
    chief.bus = bus
    asyncio.run(chief.run("X", "government", "stable", RiskAffinity.NEUTRAL))
    chief_calls = [c.args[0] for c in bus.publish.call_args_list
                   if type(c.args[0]).__name__ == "BondChiefReady"]
    assert chief_calls and "overall_signal" in chief_calls[-1].payload
