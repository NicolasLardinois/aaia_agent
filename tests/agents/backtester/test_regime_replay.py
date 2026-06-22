from datetime import date
from core.domain.models import MarketRegime
from agents.backtester.regime_replay import run_replay
from core.domain.regime import RegimeDetector
from core.domain.regime_inputs import assemble_regime_inputs


class _FakeProvider:
    """Liefert je Stichtag einen konstanten, klar bullischen Makro-Zustand."""
    def __init__(self, as_of): self.as_of = as_of; self.quality = "revised"
    def get_economic_state(self):
        return {"gdp_growth": 3.5, "unemployment": 3.5, "inflation": 2.0,
                "industrial_production": 4.0, "consumer_sentiment": 95.0,
                "fed_rate": 1.5, "yield_curve": 0.5}
    def get_extended_state(self):
        return {"credit_growth": 5.0, "nominal_wage_growth": 4.0, "real_wage_growth": 2.0,
                "money_velocity": 1.4, "m2_growth": 5.0}
    def get_yield_spreads(self): return {"10y2y": 0.5, "10y3m": 0.8}
    def get_buffett_data(self): return {"market_cap_bn": None, "gdp_bn": None}
    def get_buffett_history(self, years=10): return []


def test_run_replay_liefert_urteile_je_stichtag():
    stichtage = [date(2000, 1, 1), date(2000, 2, 1), date(2000, 3, 1)]
    urteile = run_replay(lambda d: _FakeProvider(d), stichtage)
    assert len(urteile) == 3
    assert all(isinstance(u["regime"], MarketRegime) for u in urteile)
    assert all(u["data_quality"] == "revised" for u in urteile)
    # klar bullischer Zustand → Wachstums-/Boom-Phase
    assert urteile[-1]["regime"] in {MarketRegime.EXPANSION, MarketRegime.BOOM, MarketRegime.RECOVERY}


def test_composite_in_urteil_stimmt_mit_detect_ueberein():
    """Der vom Harness gemeldete Composite (gerundet auf 4) entspricht EXAKT dem
    evidence['composite'] aus RegimeDetector.detect() — kein Abweichen durch Rekonstruktion."""
    from agents.backtester.regime_replay import replay_step, _NullBus
    from adapters.data.ecb_snb_stub import EcbStubProvider, SnbStubProvider

    # Referenz: detect direkt für den ersten Stichtag (history=[] wie im ersten Replay-Schritt).
    prov = _FakeProvider(date(2000, 1, 1))
    raw = replay_step(prov, _NullBus(), EcbStubProvider(), SnbStubProvider())
    state, sub_signals = assemble_regime_inputs(
        raw["economic_state"], raw["usa_10y3m"], {}, {}, raw["sub_signal_map"],
    )
    _, _, evidence = RegimeDetector().detect(state, sub_signals, history=[])

    # run_replay über denselben ersten Stichtag (gleiche Stub-Quellen) muss exakt den
    # gerundeten evidence['composite'] melden — NICHT eine abweichende Rekonstruktion.
    urteile = run_replay(
        lambda d: _FakeProvider(d), [date(2000, 1, 1)],
        ecb_factory=lambda d: EcbStubProvider(), snb_factory=lambda d: SnbStubProvider(),
    )
    assert urteile[0]["composite"] == round(evidence["composite"], 4)
