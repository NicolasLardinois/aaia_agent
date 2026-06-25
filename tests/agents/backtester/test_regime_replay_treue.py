import asyncio
from datetime import date

import pytest

from agents.backtester.regime_replay import replay_step, _NullBus
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from adapters.data.ecb_snb_stub import EcbStubProvider, SnbStubProvider
from core.domain.regime import RegimeDetector
from core.domain.regime_inputs import assemble_regime_inputs


# Zwei Szenarien, damit der Treue-Beweis nicht nur an einem Regime hängt:
# ein schwaches (Abschwung-nah) und ein klar bullisches.
_BEARISH = {
    "economic_state": {"gdp_growth": 1.0, "unemployment": 5.5, "inflation": 3.5,
                       "industrial_production": -1.0, "consumer_sentiment": 60.0,
                       "fed_rate": 4.5, "yield_curve": -0.2},
    "extended_state": {"credit_growth": 1.0, "nominal_wage_growth": 2.0, "real_wage_growth": -1.5,
                       "money_velocity": 1.3, "m2_growth": 1.0},
    "spreads": {"10y2y": -0.2, "10y3m": -0.3},
}
_BULLISH = {
    "economic_state": {"gdp_growth": 3.8, "unemployment": 3.5, "inflation": 2.0,
                       "industrial_production": 4.0, "consumer_sentiment": 95.0,
                       "fed_rate": 1.5, "yield_curve": 0.6},
    "extended_state": {"credit_growth": 6.0, "nominal_wage_growth": 4.0, "real_wage_growth": 2.0,
                       "money_velocity": 1.4, "m2_growth": 6.0},
    "spreads": {"10y2y": 0.6, "10y3m": 0.9},
}


class _FakeProvider:
    """Konstanter Makro-Zustand je Szenario (kopiert die Dicts, mutiert die Vorlage nicht)."""
    def __init__(self, data): self._d = data; self.quality = "revised"
    def get_economic_state(self): return dict(self._d["economic_state"])
    def get_extended_state(self): return dict(self._d["extended_state"])
    def get_yield_spreads(self): return dict(self._d["spreads"])
    def get_buffett_data(self): return {"market_cap_bn": None, "gdp_bn": None}
    def get_buffett_history(self, years=10): return []
    def get_cpi_history(self, months=6): return []  # Port-Default: kein CPI-Trend → "stable"


@pytest.mark.parametrize("data", [_BEARISH, _BULLISH], ids=["bearish", "bullish"])
def test_replay_pfad_gleich_produktionspfad(monkeypatch, data):
    """Gleiche Roh-Daten durch MacroChiefAgent (echt) und Replay → identisches Regime UND Confidence.

    Neutralisierung der Datei-Historie: Der Produktionspfad (MacroChiefAgent) ruft detect() ohne
    history= auf → liest/schreibt die Cache-Datei. Der Replay-Pfad übergibt history=[]. Damit beide
    Pfade denselben Trend (None, da len<2) sehen, patchen wir _load_history → [] und _save_history →
    No-Op. Ziel: Gleichheit von Input-Montage + Regime-/Confidence-Ableitung, nicht des Datei-Trends.
    """
    import core.domain.regime as regime_module
    monkeypatch.setattr(regime_module, "_load_history", lambda: [])
    monkeypatch.setattr(regime_module, "_save_history", lambda history, current, today=None: None)

    prov = _FakeProvider(data)
    bus = _NullBus()

    # Produktionspfad: echter MacroChiefAgent, buffett-Agent netzfrei gemacht.
    chief = MacroChiefAgent(prov, EcbStubProvider(), SnbStubProvider(), bus)
    chief.buffett_indicator_agent = type(chief.buffett_indicator_agent)(
        prov, bus, wb_fetch=lambda: {})
    prod_result = asyncio.run(chief.run())

    # Replay-Pfad (ECB/SNB-Stubs explizit injiziert).
    raw = replay_step(prov, bus, EcbStubProvider(), SnbStubProvider())
    state, subs = assemble_regime_inputs(
        raw["economic_state"], raw["usa_10y3m"], {}, {}, raw["sub_signal_map"])
    replay_regime, replay_conf, _ = RegimeDetector().detect(state, subs, history=[])

    assert replay_regime == prod_result.regime
    assert replay_conf == prod_result.regime_confidence
