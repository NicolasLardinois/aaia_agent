import dataclasses

from core.domain.models import (
    SignalStatus,
    MacroChiefResult, CommodityChiefResult, SentimentChiefResult,
    YieldCurveChiefResult, SectorChiefResult,
)
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent


def test_each_chief_default_is_unavailable():
    # is-Vergleich: Enum-Mitglieder sind Singletons (Identitaet, nicht nur Wertgleichheit)
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


def test_status_field_defaults_to_available_on_all_chief_results():
    # Vertrag: ein ECHTES Ergebnis ist AVAILABLE; nur der default()-Ausfall ist
    # UNAVAILABLE. Wir pinnen den Feld-Default fuer alle fuenf Chief-Results,
    # damit eine spaetere Aenderung des Defaults sofort auffaellt.
    for cls in (
        MacroChiefResult, CommodityChiefResult, SentimentChiefResult,
        YieldCurveChiefResult, SectorChiefResult,
    ):
        field = {f.name: f for f in dataclasses.fields(cls)}["status"]
        assert field.default is SignalStatus.AVAILABLE
