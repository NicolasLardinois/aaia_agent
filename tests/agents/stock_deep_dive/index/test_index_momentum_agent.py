import pandas as pd
from agents.stock_deep_dive.index.index_momentum_agent import _signal, _detect_crossover, _compute_rsi
from core.domain.models import Signal


# ── Status-basiertes Signal (MA50/MA200 + RSI-Extreme) ────────────────────

def test_ueber_ma200_rsi_normal_ist_bullish():
    """ma50 > ma200 (Aufwärtstrend) + RSI nicht überkauft → BULLISH."""
    assert _signal(ma50=110.0, ma200=100.0, rsi=55.0) == Signal.BULLISH


def test_ueber_ma200_aber_ueberkauft_ist_neutral():
    """Aufwärtstrend, aber RSI > 70 (überkauft) → NEUTRAL (kein frischer Einstieg)."""
    assert _signal(ma50=110.0, ma200=100.0, rsi=78.0) == Signal.NEUTRAL


def test_unter_ma200_ist_bearish():
    """ma50 < ma200 (Abwärtstrend) → BEARISH — unabhängig von einem frischen Cross-Event."""
    assert _signal(ma50=95.0, ma200=100.0, rsi=50.0) == Signal.BEARISH


def test_unter_ma200_ueberverkauft_ist_neutral():
    """Abwärtstrend, aber RSI < 30 (überverkauft) → NEUTRAL (Downside verbraucht)."""
    assert _signal(ma50=95.0, ma200=100.0, rsi=22.0) == Signal.NEUTRAL


def test_fehlende_mas_ist_neutral():
    assert _signal(ma50=None, ma200=100.0, rsi=50.0) == Signal.NEUTRAL


def test_compute_rsi_nutzt_wilder():
    """_compute_rsi delegiert an Wilder (ewm) — weicht vom SMA-RSI ab."""
    import math
    vals = [100.0] * 20 + [80.0] + [101.0 + i for i in range(20)]
    prices = pd.Series(vals)
    delta = prices.diff().dropna()
    gain_sma = delta.clip(lower=0).rolling(14).mean()
    loss_sma = (-delta.clip(upper=0)).rolling(14).mean()
    rs_sma = gain_sma / loss_sma.replace(0, float("nan"))
    sma_rsi_val = float((100 - 100 / (1 + rs_sma)).iloc[-1])
    computed = _compute_rsi(prices)
    assert computed is not None
    if math.isnan(sma_rsi_val):
        assert computed < 100.0   # Wilder erinnert sich an den Einbruch
    else:
        assert abs(computed - round(sma_rsi_val, 2)) > 0.01


# ── Crossover-Erkennung (unverändert) ─────────────────────────────────────

def _make_series(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


def test_detect_golden_cross():
    ma50  = _make_series([98, 99, 100, 101, 102, 103])
    ma200 = _make_series([101, 101, 101, 101, 101, 101])
    assert _detect_crossover(ma50, ma200) is True


def test_detect_death_cross():
    ma50  = _make_series([103, 102, 101, 100, 99, 98])
    ma200 = _make_series([101, 101, 101, 101, 101, 101])
    assert _detect_crossover(ma50, ma200) is False


def test_detect_no_cross_stable_above():
    ma50  = _make_series([105, 105, 105, 105, 105, 105])
    ma200 = _make_series([100, 100, 100, 100, 100, 100])
    assert _detect_crossover(ma50, ma200) is None


def test_detect_no_cross_stable_below():
    ma50  = _make_series([95, 95, 95, 95, 95, 95])
    ma200 = _make_series([100, 100, 100, 100, 100, 100])
    assert _detect_crossover(ma50, ma200) is None
