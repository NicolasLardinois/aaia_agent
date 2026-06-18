from unittest.mock import MagicMock
from agents.anomaly.top_down_anomaly_agent import TopDownAnomalyAgent
from core.domain.models import Signal


def _make_cockpit(
    macro_signal=Signal.NEUTRAL,
    sentiment_vix=Signal.NEUTRAL,
    sentiment_fg=Signal.NEUTRAL,
    sentiment_pc=Signal.NEUTRAL,
    yield_signal=Signal.NEUTRAL,
    commodity_energy=Signal.NEUTRAL,
    commodity_metals=Signal.NEUTRAL,
):
    cockpit = MagicMock()
    # Sentiment sub-signals
    cockpit.sentiment.vix.vix = 18.0
    cockpit.sentiment.vix.signal = sentiment_vix
    cockpit.sentiment.fear_greed.value = 50.0
    cockpit.sentiment.fear_greed.signal = sentiment_fg
    cockpit.sentiment.put_call.signal = sentiment_pc
    # Yield curve (USA default)
    cockpit.yield_curve.yield_spreads.usa.spread_10y2y = 1.0
    cockpit.yield_curve.yield_spreads.usa.signal = yield_signal
    # Macro
    cockpit.macro.regime_confidence = 0.75
    cockpit.macro.inflation.usa.cpi = 3.0
    cockpit.macro.inflation.usa.signal = macro_signal
    cockpit.macro.gdp.usa.signal = macro_signal
    cockpit.macro.buffett_indicator.countries = {}
    # Commodities
    cockpit.commodities.energy.signal = commodity_energy
    cockpit.commodities.industrial_metals.signal = commodity_metals
    # Sectors (unused but present)
    cockpit.sectors.rotation.signal = Signal.NEUTRAL
    return cockpit


def test_direction_bearish_majority():
    """
    3 von 4 Bereichs-Signale BEARISH → direction == 'bearish'.

    Signale:
    - macro_sig:     BEARISH  (inflation=BEARISH, gdp=BEARISH → 2:0)
    - sentiment_sig: BEARISH  (vix=BEARISH, fg=BEARISH, pc=BEARISH → 3:0)
    - yield_sig:     BEARISH  (yield_signal=BEARISH)
    - commodity_sig: BULLISH  (energy=BULLISH, metals=BULLISH → 0:2)
    → 3 BEARISH, 1 BULLISH → bearish
    """
    cockpit = _make_cockpit(
        macro_signal=Signal.BEARISH,
        sentiment_vix=Signal.BEARISH,
        sentiment_fg=Signal.BEARISH,
        sentiment_pc=Signal.BEARISH,
        yield_signal=Signal.BEARISH,
        commodity_energy=Signal.BULLISH,
        commodity_metals=Signal.BULLISH,
    )
    agent = TopDownAnomalyAgent()
    report = agent.run(cockpit, [])
    assert report.direction == "bearish"


def test_direction_bullish_majority():
    """
    3 von 4 Bereichs-Signale BULLISH → direction == 'bullish'.

    Signale:
    - macro_sig:     BULLISH  (inflation=BULLISH, gdp=BULLISH)
    - sentiment_sig: BULLISH  (vix=BULLISH, fg=BULLISH, pc=BULLISH)
    - yield_sig:     BULLISH
    - commodity_sig: BEARISH  (energy=BEARISH, metals=BEARISH)
    → 3 BULLISH, 1 BEARISH → bullish
    """
    cockpit = _make_cockpit(
        macro_signal=Signal.BULLISH,
        sentiment_vix=Signal.BULLISH,
        sentiment_fg=Signal.BULLISH,
        sentiment_pc=Signal.BULLISH,
        yield_signal=Signal.BULLISH,
        commodity_energy=Signal.BEARISH,
        commodity_metals=Signal.BEARISH,
    )
    agent = TopDownAnomalyAgent()
    report = agent.run(cockpit, [])
    assert report.direction == "bullish"


def test_direction_neutral_on_tie():
    """
    Gleichstand: 2 BEARISH, 2 BULLISH → direction == 'neutral'.

    Signale:
    - macro_sig:     BEARISH  (inflation=BEARISH, gdp=BEARISH)
    - sentiment_sig: BULLISH  (vix=BULLISH, fg=BULLISH, pc=BULLISH)
    - yield_sig:     BEARISH
    - commodity_sig: BULLISH  (energy=BULLISH, metals=BULLISH)
    → 2 BEARISH, 2 BULLISH → neutral
    """
    cockpit = _make_cockpit(
        macro_signal=Signal.BEARISH,
        sentiment_vix=Signal.BULLISH,
        sentiment_fg=Signal.BULLISH,
        sentiment_pc=Signal.BULLISH,
        yield_signal=Signal.BEARISH,
        commodity_energy=Signal.BULLISH,
        commodity_metals=Signal.BULLISH,
    )
    agent = TopDownAnomalyAgent()
    report = agent.run(cockpit, [])
    assert report.direction == "neutral"
