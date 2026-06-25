import asyncio
from unittest.mock import MagicMock

import pandas as pd
import pytest

from agents.stock_deep_dive.precious_metals.precious_metal_price_agent import (
    PreciousMetalPriceAgent, _wilder_rsi, _performance, _price_signal,
)
from core.domain.models import Signal, SignalStatus


def _series(values):
    idx = pd.date_range("2019-06-01", periods=len(values), freq="B")
    return pd.Series(values, index=idx, dtype=float)


def test_wilder_rsi_all_gains_is_100():
    rsi = _wilder_rsi(_series([i for i in range(1, 60)]), period=14)
    assert rsi > 99.0


def test_wilder_rsi_all_losses_is_low():
    rsi = _wilder_rsi(_series([60 - i for i in range(50)]), period=14)
    assert rsi < 1.0


def test_performance_1m():
    s = _series([100.0] * 21 + [110.0])
    perf = _performance(s)
    assert perf["1m"] == pytest.approx(10.0, abs=0.5)


def test_price_signal_uptrend_not_overbought_is_bullish():
    # Preis über MA200, RSI moderat → bullish
    assert _price_signal(price=2000, ma200=1800, rsi=55) == Signal.BULLISH


def test_price_signal_below_ma200_is_bearish():
    assert _price_signal(price=1500, ma200=1800, rsi=45) == Signal.BEARISH


def test_price_signal_overbought_is_neutral():
    assert _price_signal(price=2000, ma200=1800, rsi=82) == Signal.NEUTRAL


def _make_agent(history, real_rate_hist=None):
    provider = MagicMock()
    provider.get_current_price.return_value = float(history[-1])
    provider.get_price_history.return_value = pd.DataFrame({"Close": _series(history)})
    provider.get_real_rate_history.return_value = real_rate_hist or []
    return PreciousMetalPriceAgent(provider, MagicMock())


def test_run_fills_rsi_ma_performance():
    agent = _make_agent([float(1500 + i) for i in range(300)])
    result = asyncio.run(agent.run("gold"))
    assert result.rsi is not None
    assert result.ma50 is not None
    assert result.ma200 is not None
    assert "1m" in result.performance
    assert result.status == SignalStatus.AVAILABLE


def test_real_yield_correlation_none_when_no_history():
    agent = _make_agent([float(1500 + i) for i in range(300)], real_rate_hist=[])
    result = asyncio.run(agent.run("gold"))
    assert result.real_yield_correlation is None
    # Preis/RSI/MA trotzdem vorhanden
    assert result.status == SignalStatus.AVAILABLE


def test_empty_close_returns_unavailable_no_crash():
    """Alle NaN-Kurse → close.empty → kein iloc-Crash, UNAVAILABLE."""
    import numpy as np
    provider = MagicMock()
    provider.get_current_price.return_value = 1800.0
    provider.get_price_history.return_value = pd.DataFrame(
        {"Close": pd.Series([np.nan, np.nan], index=pd.date_range("2023-01-01", periods=2, freq="B"))}
    )
    provider.get_real_rate_history.return_value = []
    agent = PreciousMetalPriceAgent(provider, MagicMock())
    result = asyncio.run(agent.run("gold"))
    assert result.status == SignalStatus.UNAVAILABLE


def test_inverse_returns_give_negative_correlation():
    """Fachliche Erwartung: an Tagen, an denen der Preis steigt, fällt der Zins (und umgekehrt)
    → die return-basierte Korrelation ist deutlich negativ (stützt das Edelmetall-Argument)."""
    import numpy as np
    rng = np.random.default_rng(42)
    n = 300
    # Gemeinsamer Faktor: an +Tagen steigt Preis, fällt Zins → Tages-Returns echt invers
    factor = rng.standard_normal(n)
    prices = 1500.0 + (factor.cumsum() * 10)
    rates = 2.0 + (-factor).cumsum() * 0.05  # gegenläufig
    dates = pd.date_range("2019-06-01", periods=n, freq="B")
    rr = [{"date": d.strftime("%Y-%m-%d"), "real_rate_10y": float(rates[i])}
          for i, d in enumerate(dates)]
    agent = _make_agent(list(prices), real_rate_hist=rr)
    result = asyncio.run(agent.run("gold"))
    assert result.real_yield_correlation is not None
    assert result.real_yield_correlation < -0.5


def test_monotone_inverse_levels_but_uncorrelated_returns_is_near_zero():
    """I3-Trennschärfe: gegenläufige LEVEL-Trends (Preis steigt monoton, Zins fällt monoton)
    → Level-Korrelation ≈ −1, ABER unabhängiges Tagesrauschen → Return-Korrelation ≈ 0.

    Da die Implementierung return-basiert rechnet (pct_change/diff), muss das Ergebnis nahe 0
    liegen. Würde jemand versehentlich auf die Level-Korrelation zurückfallen, käme ≈ −1 heraus
    und dieser Test bräche — genau das macht ihn trennscharf (vorher liefen Level- und
    Return-Korrelation beide auf −1, sodass eine Level-Regression unbemerkt durchging)."""
    import numpy as np
    rng = np.random.default_rng(7)
    n = 300
    i = np.arange(n)
    # Trends dominieren die Level-Varianz (→ Level-Korr ≈ −1); das Tagesrauschen ist
    # zwischen Preis und Zins unabhängig (→ Return-Korr ≈ 0).
    prices = 1500.0 + i * 1.0 + rng.normal(0, 3.0, n)    # stark steigend
    rates = 2.0 - i * 0.01 + rng.normal(0, 0.05, n)      # stark fallend, eigenes Rauschen
    dates = pd.date_range("2019-06-01", periods=n, freq="B")
    rr = [{"date": d.strftime("%Y-%m-%d"), "real_rate_10y": float(rates[k])}
          for k, d in enumerate(dates)]
    agent = _make_agent(list(prices), real_rate_hist=rr)
    result = asyncio.run(agent.run("gold"))
    assert result.real_yield_correlation is not None
    # Return-basiert ≈ 0; eine Level-Regression (≈ −1) würde diese Schranke verletzen.
    assert abs(result.real_yield_correlation) < 0.3


def test_common_uptrend_levels_but_uncorrelated_returns_is_near_zero():
    """Gegenstück von oben mit GLEICH gerichtetem Trend: beide Serien steigen monoton
    → Level-Korr ≈ +1, Tagesrauschen unabhängig → Return-Korr ≈ 0. Return-basiert ⇒ Ergebnis
    nahe 0; eine Level-Regression käme bei ≈ +1 heraus und bräche den Test (Trennschärfe von
    der +1-Seite)."""
    import numpy as np
    rng = np.random.default_rng(0)
    n = 300
    i = np.arange(n)
    prices = 1500.0 + i * 1.0 + rng.normal(0, 3.0, n)    # steigt
    rates = 1.0 + i * 0.01 + rng.normal(0, 0.05, n)      # steigt ebenfalls
    dates = pd.date_range("2019-06-01", periods=n, freq="B")
    rr = [{"date": d.strftime("%Y-%m-%d"), "real_rate_10y": float(rates[k])}
          for k, d in enumerate(dates)]
    agent = _make_agent(list(prices), real_rate_hist=rr)
    result = asyncio.run(agent.run("gold"))
    assert result.real_yield_correlation is not None
    assert abs(result.real_yield_correlation) < 0.3
