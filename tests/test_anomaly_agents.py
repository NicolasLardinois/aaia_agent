from unittest.mock import MagicMock
from agents.anomaly.top_down_anomaly_agent import TopDownAnomalyAgent
from agents.anomaly.bottom_up_anomaly_agent import BottomUpAnomalyAgent
from core.domain.models import Signal
from core.domain.taxonomy import Underlying, Wrapper, legacy_to_taxonomy


def _make_cockpit(vix=18.0, fear_greed=50.0, spread=1.2,
                  macro_signal=Signal.BULLISH, sentiment_signal=Signal.BULLISH,
                  yield_signal=Signal.BULLISH, commodity_signal=Signal.BULLISH,
                  regime_confidence=0.75):
    cockpit = MagicMock()
    cockpit.sentiment.vix.vix = vix
    cockpit.sentiment.vix.signal = sentiment_signal
    cockpit.sentiment.fear_greed.value = fear_greed
    cockpit.sentiment.fear_greed.signal = sentiment_signal
    cockpit.sentiment.put_call.signal = sentiment_signal
    cockpit.yield_curve.yield_spreads.usa.spread_10y2y = spread
    cockpit.yield_curve.yield_spreads.usa.signal = yield_signal
    cockpit.macro.regime_confidence = regime_confidence
    cockpit.macro.inflation.usa.cpi = 3.2
    cockpit.macro.inflation.usa.signal = macro_signal
    cockpit.macro.gdp.usa.signal = macro_signal
    cockpit.commodities.energy.signal = commodity_signal
    cockpit.commodities.industrial_metals.signal = commodity_signal
    cockpit.sectors.rotation.signal = Signal.NEUTRAL
    cockpit.macro.buffett_indicator.countries = {}
    return cockpit


def test_no_anomalies_normal_conditions():
    agent = TopDownAnomalyAgent()
    history = [
        {"indicators_snapshot": {"vix": 18.0, "fear_greed": 52.0,
                                 "yield_spread_10y2y": 1.1, "inflation_cpi_usa": 3.1}}
        for _ in range(25)
    ]
    report = agent.run(_make_cockpit(), history)
    assert report.severity == "none"
    assert report.has_anomalies is False


def test_statistical_anomaly_high_vix():
    agent = TopDownAnomalyAgent()
    history = [
        {"indicators_snapshot": {"vix": 18.0 + i*0.5, "fear_greed": 50.0,
                                 "yield_spread_10y2y": 1.0, "inflation_cpi_usa": 3.0}}
        for i in range(25)
    ]
    report = agent.run(_make_cockpit(vix=45.0), history)
    assert report.has_anomalies is True
    assert any("VIX" in s for s in report.statistical)


def test_contradiction_macro_vs_sentiment():
    agent = TopDownAnomalyAgent()
    cockpit = _make_cockpit(
        macro_signal=Signal.BULLISH,
        sentiment_signal=Signal.BEARISH,
        yield_signal=Signal.BEARISH,
    )
    report = agent.run(cockpit, [])
    assert report.has_anomalies is True
    assert len(report.contradictions) >= 1


def test_high_severity_both_types():
    agent = TopDownAnomalyAgent()
    history = [
        {"indicators_snapshot": {"vix": 18.0 + i*0.5, "fear_greed": 50.0,
                                 "yield_spread_10y2y": 1.0, "inflation_cpi_usa": 3.0}}
        for i in range(25)
    ]
    cockpit = _make_cockpit(
        vix=50.0,
        macro_signal=Signal.BULLISH,
        sentiment_signal=Signal.BEARISH,
        yield_signal=Signal.BEARISH,
    )
    report = agent.run(cockpit, history)
    assert report.severity == "high"


def _make_cockpit_ch(yield_signal=Signal.BEARISH, spread_10y3m=-0.20):
    cockpit = MagicMock()
    cockpit.sentiment.vix.vix = 18.0
    cockpit.sentiment.vix.signal = Signal.NEUTRAL
    cockpit.sentiment.fear_greed.value = 50.0
    cockpit.sentiment.fear_greed.signal = Signal.NEUTRAL
    cockpit.sentiment.put_call.signal = Signal.NEUTRAL
    cockpit.yield_curve.yield_spreads.switzerland.spread_10y2y = None
    cockpit.yield_curve.yield_spreads.switzerland.spread_10y3m = spread_10y3m
    cockpit.yield_curve.yield_spreads.switzerland.signal = yield_signal
    cockpit.yield_curve.yield_spreads.usa.spread_10y2y = 1.5
    cockpit.yield_curve.yield_spreads.usa.signal = Signal.BULLISH
    cockpit.macro.regime_confidence = 0.75
    cockpit.macro.inflation.usa.cpi = 3.2
    cockpit.macro.inflation.usa.signal = Signal.NEUTRAL
    cockpit.macro.gdp.usa.signal = Signal.NEUTRAL
    cockpit.commodities.energy.signal = Signal.NEUTRAL
    cockpit.commodities.industrial_metals.signal = Signal.NEUTRAL
    cockpit.sectors.rotation.signal = Signal.NEUTRAL
    cockpit.macro.buffett_indicator.countries = {}
    return cockpit


def test_anomaly_agent_ch_uses_switzerland_yield_signal():
    """market='CH': Widerspruch prüft Schweizer Zinskurve, nicht USA."""
    agent = TopDownAnomalyAgent()
    cockpit = _make_cockpit_ch(yield_signal=Signal.BEARISH)
    cockpit.macro.inflation.usa.signal = Signal.BULLISH
    cockpit.macro.gdp.usa.signal = Signal.BULLISH
    report = agent.run(cockpit, [], market="CH")
    # Macro=BULLISH vs YieldCurve=BEARISH → Widerspruch
    assert any("YieldCurve" in c for c in report.contradictions)


def test_anomaly_agent_ch_ignores_usa_yield_signal():
    """market='CH' + USA Yield BULLISH + CH Yield BEARISH: USA soll nicht als YieldSig verwendet werden."""
    agent = TopDownAnomalyAgent()
    cockpit = MagicMock()
    cockpit.sentiment.vix.vix = 18.0
    cockpit.sentiment.vix.signal = Signal.NEUTRAL
    cockpit.sentiment.fear_greed.value = 50.0
    cockpit.sentiment.fear_greed.signal = Signal.NEUTRAL
    cockpit.sentiment.put_call.signal = Signal.NEUTRAL
    cockpit.yield_curve.yield_spreads.switzerland.spread_10y2y = None
    cockpit.yield_curve.yield_spreads.switzerland.spread_10y3m = -0.30
    cockpit.yield_curve.yield_spreads.switzerland.signal = Signal.BEARISH
    cockpit.yield_curve.yield_spreads.usa.signal = Signal.BULLISH
    cockpit.macro.regime_confidence = 0.75
    cockpit.macro.inflation.usa.cpi = 3.2
    cockpit.macro.inflation.usa.signal = Signal.BEARISH
    cockpit.macro.gdp.usa.signal = Signal.BEARISH
    cockpit.commodities.energy.signal = Signal.NEUTRAL
    cockpit.commodities.industrial_metals.signal = Signal.NEUTRAL
    cockpit.sectors.rotation.signal = Signal.NEUTRAL
    cockpit.macro.buffett_indicator.countries = {}
    # Macro=BEARISH, CH Yield=BEARISH → kein Widerspruch erwartet
    report = agent.run(cockpit, [], market="CH")
    yield_contradictions = [c for c in report.contradictions if "YieldCurve" in c]
    assert len(yield_contradictions) == 0


def _make_bottom_up(pe=22.0, short_float=3.0, insider_tx=2,
                    fund_signal=Signal.BULLISH, val_signal=Signal.BULLISH,
                    earn_signal=Signal.BULLISH, quality_signal=Signal.BULLISH,
                    asset_class="equity"):
    bu = MagicMock()
    # Task 8: underlying/wrapper statt asset_class-Property setzen.
    bu.underlying, bu.wrapper = legacy_to_taxonomy(asset_class)
    bu.fundamentals.pe_ratio = pe
    bu.fundamentals.signal = fund_signal
    bu.short_interest.short_float_pct = short_float
    bu.short_interest.signal = Signal.NEUTRAL
    bu.insider.recent_transactions = insider_tx
    bu.insider.signal = Signal.NEUTRAL
    bu.earnings_trend.signal = earn_signal
    bu.moat.signal = Signal.NEUTRAL
    bu.valuation_range.signal = val_signal
    bu.quality.signal = quality_signal
    return bu


def test_bottomup_no_anomalies():
    agent = BottomUpAnomalyAgent()
    history = [
        {"indicators_snapshot": {"pe_ratio": 22.0, "short_float_pct": 3.0}}
        for _ in range(25)
    ]
    report = agent.run(_make_bottom_up(), history)
    assert report.severity == "none"


def test_bottomup_pe_statistical_anomaly():
    agent = BottomUpAnomalyAgent()
    history = [
        {"indicators_snapshot": {"pe_ratio": 22.0 + i*0.5, "short_float_pct": 3.0}}
        for i in range(25)
    ]
    report = agent.run(_make_bottom_up(pe=85.0), history)
    assert report.has_anomalies is True
    assert any("KGV" in s for s in report.statistical)


def test_bottomup_contradiction():
    agent = BottomUpAnomalyAgent()
    report = agent.run(
        _make_bottom_up(fund_signal=Signal.BULLISH, val_signal=Signal.BEARISH,
                        earn_signal=Signal.BEARISH, quality_signal=Signal.BEARISH),
        []
    )
    assert report.has_anomalies is True
    assert len(report.contradictions) >= 1


def test_bottomup_non_equity_skips_z_score():
    agent = BottomUpAnomalyAgent()
    bu = MagicMock()
    # Task 8: underlying direkt setzen (BOND → Z-Score-Checks werden übersprungen)
    bu.underlying, bu.wrapper = legacy_to_taxonomy("bond")
    bu.fundamentals = None
    bu.short_interest = None
    bu.insider = None
    bu.earnings_trend.signal = Signal.NEUTRAL
    bu.moat.signal = Signal.NEUTRAL
    bu.valuation_range.signal = Signal.NEUTRAL
    bu.quality.signal = Signal.NEUTRAL
    history = [{"indicators_snapshot": {"pe_ratio": 22.0}} for _ in range(25)]
    report = agent.run(bu, history)
    assert report.severity == "none"


def test_bottomup_pe_robust_anomaly_with_min_n():
    agent = BottomUpAnomalyAgent()
    history = [
        {"indicators_snapshot": {"pe_ratio": 22.0 + (i % 3) * 0.3, "short_float_pct": 3.0}}
        for i in range(25)
    ]
    report = agent.run(_make_bottom_up(pe=120.0), history)
    assert report.has_anomalies is True
    assert any("KGV" in s for s in report.statistical)


def test_bottomup_below_min_n_skips_zscore():
    agent = BottomUpAnomalyAgent()
    history = [{"indicators_snapshot": {"pe_ratio": 22.0, "short_float_pct": 3.0}}
               for _ in range(15)]  # < 20
    report = agent.run(_make_bottom_up(pe=200.0), history)
    assert not any("KGV" in s for s in report.statistical)


def test_bottomup_insider_direction_aware():
    # Viele Transaktionen, aber net_direction = "net_buy" → KEIN bearisches Anomalie-Flag,
    # sondern als auffälliger Kauf-Cluster markiert (Richtung berücksichtigt).
    agent = BottomUpAnomalyAgent()
    bu = _make_bottom_up(insider_tx=40)
    bu.insider.net_direction = "net_buy"
    report = agent.run(bu, [{"indicators_snapshot": {"insider_transactions": 3}} for _ in range(25)])
    insider_flags = [s for s in report.statistical if "Insider" in s]
    assert insider_flags and "Kauf" in insider_flags[0]


def test_topdown_below_min_n_skips_zscore():
    agent = TopDownAnomalyAgent()
    history = [
        {"indicators_snapshot": {"vix": 18.0, "fear_greed": 50.0,
                                 "yield_spread_10y2y": 1.0, "inflation_cpi_usa": 3.0}}
        for _ in range(15)  # < 20
    ]
    report = agent.run(_make_cockpit(vix=80.0), history)
    assert not any("VIX" in s for s in report.statistical)


def test_topdown_robust_vix_anomaly_min_n():
    agent = TopDownAnomalyAgent()
    history = [
        {"indicators_snapshot": {"vix": 18.0 + (i % 3) * 0.4, "fear_greed": 50.0,
                                 "yield_spread_10y2y": 1.0, "inflation_cpi_usa": 3.0}}
        for i in range(25)
    ]
    report = agent.run(_make_cockpit(vix=70.0), history)
    assert any("VIX" in s for s in report.statistical)
