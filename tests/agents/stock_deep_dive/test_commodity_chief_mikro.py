import asyncio
from unittest.mock import AsyncMock, MagicMock

from agents.stock_deep_dive.commodity_chief_agent_mikro import CommodityChiefAgentMikro
from core.domain.models import (
    Signal, SignalStatus,
    SupplyDemandSnapshot, SeasonalitySnapshot, COTSnapshot, CommodityValuationRangeSnapshot,
)


def _sd(signal, status=SignalStatus.AVAILABLE):
    return SupplyDemandSnapshot(
        inventory_current=None, inventory_avg_5y=None, inventory_pct_vs_avg=None,
        production_change_yoy=None, stock_to_flow=None, stock_to_flow_signal=None,
        signal=signal, status=status)


def _seas(signal, status=SignalStatus.AVAILABLE):
    return SeasonalitySnapshot(
        current_month_bias="neutral", avg_return_this_month=None,
        positive_years_pct=None, signal=signal, status=status)


def _cot(signal, status=SignalStatus.AVAILABLE):
    return COTSnapshot(net_speculative_long=None, net_speculative_pct_oi=None,
                       signal=signal, status=status)


def _vr(signal, status=SignalStatus.AVAILABLE):
    return CommodityValuationRangeSnapshot(
        current_price=None, price_low_5y=None, price_high_5y=None,
        percentile_5y=None, percentile_10y=None, production_cost_low=None,
        production_cost_high=None, position="fair", signal=signal, status=status)


def _chief(sd, seas, cot, vr):
    chief = CommodityChiefAgentMikro(MagicMock(), MagicMock())
    chief.supply_demand_agent.run             = AsyncMock(return_value=sd)
    chief.seasonality_agent.run               = AsyncMock(return_value=seas)
    chief.cot_agent.run                       = AsyncMock(return_value=cot)
    chief.commodity_valuation_range_agent.run = AsyncMock(return_value=vr)
    return chief


def test_chief_aggregiert_overall_signal():
    """Alle Sub-Signale BULLISH (verfügbar) → Gesamtsignal BULLISH + Confidence > 0."""
    chief = _chief(_sd(Signal.BULLISH), _seas(Signal.BULLISH), _cot(Signal.BULLISH), _vr(Signal.BULLISH))
    res = asyncio.run(chief.run("CL=F"))
    assert res.overall_signal == Signal.BULLISH
    assert res.confidence > 0.0


def test_saisonalitaet_schwaecher_als_supply_demand():
    """supply_demand BEARISH (hohes Gewicht) schlägt seasonality BULLISH (niedriges Gewicht)
    → Gesamt BEARISH. Beweist, dass Saisonalität geringer gewichtet ist."""
    chief = _chief(_sd(Signal.BEARISH), _seas(Signal.BULLISH), _cot(Signal.NEUTRAL), _vr(Signal.NEUTRAL))
    res = asyncio.run(chief.run("CL=F"))
    assert res.overall_signal == Signal.BEARISH


def test_unavailable_wird_ignoriert():
    """supply_demand + cot UNAVAILABLE (Produktions-Normalfall ohne Adapter) → Gesamtsignal
    nur aus seasonality + valuation_range, Gewichte re-normalisiert."""
    chief = _chief(
        _sd(Signal.BULLISH, SignalStatus.UNAVAILABLE),
        _seas(Signal.NEUTRAL),
        _cot(Signal.BULLISH, SignalStatus.UNAVAILABLE),
        _vr(Signal.BEARISH),
    )
    res = asyncio.run(chief.run("CL=F"))
    assert res.overall_signal == Signal.BEARISH
