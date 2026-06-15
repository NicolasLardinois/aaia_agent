import pandas as pd
from agents.stock_deep_dive.index.index_momentum_agent import _signal, _detect_crossover
from core.domain.models import Signal


# ── RSI-Guard (Bug #35) ───────────────────────────────────────────────────

def test_death_cross_rsi_50_is_neutral():
    """Death Cross + normaler RSI → NEUTRAL, kein falsches BEARISH."""
    assert _signal(golden_cross=False, rsi=50) == Signal.NEUTRAL


def test_death_cross_rsi_80_is_bearish():
    """Death Cross + überkaufter Markt → BEARISH (klassische Topbildung)."""
    assert _signal(golden_cross=False, rsi=80) == Signal.BEARISH


def test_death_cross_rsi_25_is_neutral():
    """Death Cross + bereits überverkauft → NEUTRAL (Downside verbraucht)."""
    assert _signal(golden_cross=False, rsi=25) == Signal.NEUTRAL


def test_golden_cross_rsi_50_is_bullish():
    """Golden Cross + normaler RSI → BULLISH."""
    assert _signal(golden_cross=True, rsi=50) == Signal.BULLISH


def test_golden_cross_rsi_80_is_neutral():
    """Golden Cross + bereits überkauft → NEUTRAL."""
    assert _signal(golden_cross=True, rsi=80) == Signal.NEUTRAL


def test_no_crossover_is_neutral():
    """Kein Kreuzungspunkt in letzten 5 Tagen → NEUTRAL."""
    assert _signal(golden_cross=None, rsi=50) == Signal.NEUTRAL


# ── Crossover-Erkennung ───────────────────────────────────────────────────

def _make_series(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


def test_detect_golden_cross():
    """MA50 kreuzt MA200 von unten nach oben → True."""
    ma50  = _make_series([98, 99, 100, 101, 102, 103])
    ma200 = _make_series([101, 101, 101, 101, 101, 101])
    assert _detect_crossover(ma50, ma200) is True


def test_detect_death_cross():
    """MA50 kreuzt MA200 von oben nach unten → False."""
    ma50  = _make_series([103, 102, 101, 100, 99, 98])
    ma200 = _make_series([101, 101, 101, 101, 101, 101])
    assert _detect_crossover(ma50, ma200) is False


def test_detect_no_cross_stable_above():
    """MA50 durchgehend über MA200 → None (kein Kreuzungspunkt)."""
    ma50  = _make_series([105, 105, 105, 105, 105, 105])
    ma200 = _make_series([100, 100, 100, 100, 100, 100])
    assert _detect_crossover(ma50, ma200) is None


def test_detect_no_cross_stable_below():
    """MA50 durchgehend unter MA200 → None."""
    ma50  = _make_series([95, 95, 95, 95, 95, 95])
    ma200 = _make_series([100, 100, 100, 100, 100, 100])
    assert _detect_crossover(ma50, ma200) is None
