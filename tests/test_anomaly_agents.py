from unittest.mock import MagicMock
from agents.anomaly.top_down_anomaly_agent import TopDownAnomalyAgent
from core.domain.models import Signal


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
    return cockpit


def test_no_anomalies_normal_conditions():
    agent = TopDownAnomalyAgent()
    history = [
        {"indicators_snapshot": {"vix": 18.0, "fear_greed": 52.0,
                                 "yield_spread_10y2y": 1.1, "inflation_cpi_usa": 3.1}}
        for _ in range(10)
    ]
    report = agent.run(_make_cockpit(), history)
    assert report.severity == "none"
    assert report.has_anomalies is False


def test_statistical_anomaly_high_vix():
    agent = TopDownAnomalyAgent()
    history = [
        {"indicators_snapshot": {"vix": 18.0 + i*0.5, "fear_greed": 50.0,
                                 "yield_spread_10y2y": 1.0, "inflation_cpi_usa": 3.0}}
        for i in range(10)
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
        for i in range(10)
    ]
    cockpit = _make_cockpit(
        vix=50.0,
        macro_signal=Signal.BULLISH,
        sentiment_signal=Signal.BEARISH,
        yield_signal=Signal.BEARISH,
    )
    report = agent.run(cockpit, history)
    assert report.severity == "high"
