from core.domain.models import SignalStatus
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent


def test_each_chief_default_is_unavailable():
    assert MacroChiefAgent.default().status is SignalStatus.UNAVAILABLE
    assert CommodityChiefAgentMakro.default().status is SignalStatus.UNAVAILABLE
    assert SentimentChiefAgent.default().status is SignalStatus.UNAVAILABLE
    assert YieldCurveChiefAgent.default().status is SignalStatus.UNAVAILABLE
    assert SectorChiefAgent.default().status is SignalStatus.UNAVAILABLE


def test_sector_result_defaults_to_available_when_built_normally():
    # Ein normal konstruiertes Result ist verfügbar (Default-Feldwert).
    from core.domain.models import SectorChiefResult, SectorPerformanceSnapshot, SectorRotationSnapshot, Signal
    perf = SectorPerformanceSnapshot(usa={}, eurozone={}, leading_usa="", lagging_usa="", leading_eu="", lagging_eu="")
    rot = SectorRotationSnapshot(recommended=[], avoid=[], alignment="neutral", signal=Signal.NEUTRAL)
    result = SectorChiefResult(performance=perf, rotation=rot)
    assert result.status is SignalStatus.AVAILABLE
