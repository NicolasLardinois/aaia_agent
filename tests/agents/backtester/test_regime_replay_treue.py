import asyncio
from datetime import date

import pytest

from agents.backtester.regime_replay import replay_step, _NullBus
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from adapters.data.ecb_snb_stub import EcbStubProvider, SnbStubProvider
from core.domain.regime import RegimeDetector
from core.domain.regime_inputs import assemble_regime_inputs


class _FakeProvider:
    def __init__(self, as_of=None): self.quality = "revised"
    def get_economic_state(self):
        return {"gdp_growth": 1.0, "unemployment": 5.5, "inflation": 3.5,
                "industrial_production": -1.0, "consumer_sentiment": 60.0,
                "fed_rate": 4.5, "yield_curve": -0.2}
    def get_extended_state(self):
        return {"credit_growth": 1.0, "nominal_wage_growth": 2.0, "real_wage_growth": -1.5,
                "money_velocity": 1.3, "m2_growth": 1.0}
    def get_yield_spreads(self): return {"10y2y": -0.2, "10y3m": -0.3}
    def get_buffett_data(self): return {"market_cap_bn": None, "gdp_bn": None}
    def get_buffett_history(self, years=10): return []


def test_replay_pfad_gleich_produktionspfad(monkeypatch):
    """Gleiche Roh-Daten durch MacroChiefAgent (echt) und Replay → identisches Regime.

    Neutralisierung der Datei-Historie: Der Produktionspfad (MacroChiefAgent) ruft
    detect() ohne history= auf → liest/schreibt die Cache-Datei. Der Replay-Pfad übergibt
    history=[]. Damit beide Pfade denselben Trend (None, da len<2) sehen, patchen wir
    _load_history → [] und _save_history → No-Op, sodass die Datei-Historie unsichtbar
    wird. Das Ziel des Tests ist die Gleichheit von Input-Montage + Regime-Ableitung,
    nicht des Datei-Trends.
    """
    import core.domain.regime as regime_module

    # Datei-Historie neutralisieren: beide Pfade sehen leere Historie → trend=None
    monkeypatch.setattr(regime_module, "_load_history", lambda: [])
    monkeypatch.setattr(regime_module, "_save_history", lambda history, current, today=None: None)

    prov = _FakeProvider()
    bus = _NullBus()

    # Produktionspfad: echter MacroChiefAgent, aber Detector mit injizierter (leerer) Historie
    chief = MacroChiefAgent(prov, EcbStubProvider(), SnbStubProvider(), bus)
    # buffett-Agent im Chief netzfrei machen:
    chief.buffett_indicator_agent = type(chief.buffett_indicator_agent)(
        prov, bus, wb_fetch=lambda: {})
    prod_result = asyncio.run(chief.run())

    # Replay-Pfad (ECB/SNB-Stubs explizit injiziert — wie der Default in run_replay)
    raw = replay_step(prov, bus, EcbStubProvider(), SnbStubProvider())
    state, subs = assemble_regime_inputs(raw["economic_state"], raw["usa_10y3m"], {}, {}, raw["sub_signal_map"])
    replay_regime, _, _ = RegimeDetector().detect(state, subs, history=[])

    # Produktion nutzt im run() die Datei-Historie; für den Vergleich nur das Regime-Mapping
    # bei leerer Historie heranziehen → beide mit history=[] auf identischem state.
    assert replay_regime == prod_result.regime
