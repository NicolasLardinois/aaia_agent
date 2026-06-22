import pandas as pd
from core.domain.models import Signal
from core.utils.momentum import momentum_signal, detect_crossover


def test_momentum_signal_uptrend_bullish():
    assert momentum_signal(110.0, 100.0, 55.0) == Signal.BULLISH

def test_momentum_signal_uptrend_overbought_neutral():
    assert momentum_signal(110.0, 100.0, 75.0) == Signal.NEUTRAL

def test_momentum_signal_downtrend_bearish():
    assert momentum_signal(90.0, 100.0, 45.0) == Signal.BEARISH

def test_momentum_signal_downtrend_oversold_neutral():
    assert momentum_signal(90.0, 100.0, 25.0) == Signal.NEUTRAL

def test_momentum_signal_none_or_nan_neutral():
    assert momentum_signal(None, 100.0, 50.0) == Signal.NEUTRAL
    assert momentum_signal(float("nan"), 100.0, 50.0) == Signal.NEUTRAL

def test_detect_crossover_golden_and_death():
    # Golden Cross: MA50 kreuzt MA200 von unten nach oben
    assert detect_crossover(pd.Series([8, 9, 11, 12]), pd.Series([10, 10, 10, 10])) is True
    # Death Cross: MA50 kreuzt MA200 von oben nach unten
    assert detect_crossover(pd.Series([12, 11, 9, 8]), pd.Series([10, 10, 10, 10])) is False
    # Kein Kreuz: MA50 durchgehend ueber MA200
    assert detect_crossover(pd.Series([11, 11, 11, 11]), pd.Series([10, 10, 10, 10])) is None
