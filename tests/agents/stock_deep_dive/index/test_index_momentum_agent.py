import pandas as pd
from agents.stock_deep_dive.index.index_momentum_agent import _compute_rsi
from core.domain.models import Signal


# Hinweis: Das Trend-/RSI-Signal (`momentum_signal`) und die Cross-Erkennung
# (`detect_crossover`) liegen geteilt in core/utils/momentum.py und sind dort
# umfassend getestet (tests/utils/test_momentum.py — inkl. None/NaN). Hier nur
# noch die index-spezifischen Teile: der Wilder-RSI-Helfer und das End-to-End-
# Verhalten von run() (insb. der NaN-MA-Pfad bei kurzer Historie, Fix I1).


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


# ── Fix I1: kurze Historie → MA200 NaN → Signal NEUTRAL (nicht BEARISH) ──

import asyncio
from unittest.mock import MagicMock


def _make_momentum_agent(prices: pd.Series):
    """Erzeugt einen IndexMomentumAgent mit einer Fake-Preishistorie."""
    from agents.stock_deep_dive.index.index_momentum_agent import IndexMomentumAgent
    hist_df = pd.DataFrame({"Close": prices})
    market = MagicMock()
    market.get_price_history.return_value = hist_df
    bus = MagicMock()
    return IndexMomentumAgent(market, bus)


def test_kurze_preishistorie_nan_ma200_ergibt_neutral_nicht_bearish():
    """Fix I1: Bei < 200 Bars → MA200 = NaN → _signal soll NEUTRAL zurückgeben, nicht BEARISH.
    VOR dem Fix ergibt NaN > NaN = False → run() liefert BEARISH.
    """
    # 30 Bars: genug für RSI, aber MA50=NaN und MA200=NaN
    prices = pd.Series([100.0 + i * 0.5 for i in range(30)])
    agent = _make_momentum_agent(prices)
    result = asyncio.run(agent.run("TEST"))
    assert result.signal == Signal.NEUTRAL, (
        f"Kurze Geschichte (<50 Bars) sollte NEUTRAL ergeben, war {result.signal}"
    )
