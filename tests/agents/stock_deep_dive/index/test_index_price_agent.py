import asyncio
from unittest.mock import MagicMock

import pandas as pd

from agents.stock_deep_dive.index.index_price_agent import IndexPriceAgent, _signal, _52w
from core.domain.models import Signal, SignalStatus


def _hist(values):
    idx = pd.date_range("2020-01-02", periods=len(values), freq="B")
    return pd.DataFrame({"Close": pd.Series(values, index=idx, dtype=float)})


def test_signal_strong_uptrend_is_bullish():
    assert _signal(perf_1y=20.0, perf_3m=4.0, dist_52w_high=-2.0) == Signal.BULLISH


def test_signal_deep_drawdown_is_bearish():
    assert _signal(perf_1y=-20.0, perf_3m=-5.0, dist_52w_high=-25.0) == Signal.BEARISH


def test_52w_from_history():
    values = [float(100 + i) for i in range(300)]
    high, low = _52w(_hist(values)["Close"])
    assert high == max(values[-252:])
    assert low == min(values[-252:])


def test_uses_price_history_and_52w_from_history():
    provider = MagicMock()
    provider.get_price_history.return_value = _hist([float(100 + i) for i in range(300)])
    provider.get_info.return_value = {}
    agent = IndexPriceAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.high_52w is not None  # aus Historie, nicht info


def test_price_return_path():
    provider = MagicMock()
    provider.get_price_history.return_value = _hist([float(100 + i) for i in range(300)])
    provider.get_info.return_value = {}
    agent = IndexPriceAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.current_price is not None


def test_unavailable_without_any_history():
    provider = MagicMock()
    provider.get_price_history.return_value = None
    provider.get_info.return_value = {}
    agent = IndexPriceAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.UNAVAILABLE


def test_all_nan_close_returns_unavailable_no_crash():
    """Komplett NaN Close-Reihe → close.empty → kein iloc-Crash, UNAVAILABLE."""
    import numpy as np
    provider = MagicMock()
    nan_hist = pd.DataFrame(
        {"Close": pd.Series([np.nan, np.nan], index=pd.date_range("2023-01-01", periods=2, freq="B"))}
    )
    provider.get_price_history.return_value = nan_hist
    agent = IndexPriceAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.UNAVAILABLE


def test_ytd_uses_timezone_aware_now():
    """Stellt sicher, dass der Agent mit tz-aware Index keinen TypeError wirft (m1-Guard)."""
    import pandas as pd
    provider = MagicMock()
    # Erzeuge tz-aware Index (UTC) — searchsorted mit String-Jahr muss trotzdem funktionieren
    idx = pd.date_range("2020-01-02", periods=300, freq="B", tz="UTC")
    provider.get_price_history.return_value = pd.DataFrame(
        {"Close": pd.Series([float(100 + i) for i in range(300)], index=idx)}
    )
    agent = IndexPriceAgent(provider, MagicMock())
    # Kein TypeError, kein Crash — Ergebnis ist AVAILABLE oder UNAVAILABLE, nie Exception
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status in (SignalStatus.AVAILABLE, SignalStatus.UNAVAILABLE)


# ── Bug #42: YTD-Basis nur bei echtem Jahresanfangs-Kurs ───────────────────
# Liegt der 1.1. VOR dem ersten Datenpunkt (searchsorted == 0), gibt es keinen
# echten Jahresanfangs-Kurs; iloc[0] wäre ein Mid-Year-Kurs → verzerrte YTD.
# Das Jahr wird dynamisch berechnet, damit die Tests zeitstabil bleiben.

def _agent_with_history(idx):
    provider = MagicMock()
    provider.get_price_history.return_value = pd.DataFrame(
        {"Close": pd.Series([float(100 + i) for i in range(len(idx))], index=idx)}
    )
    provider.get_info.return_value = {}
    return IndexPriceAgent(provider, MagicMock())


def test_ytd_none_when_history_starts_after_year_begin():
    """Historie beginnt erst im März des laufenden Jahres → kein Jahresanfangs-Kurs
    → perf_ytd muss None sein (nicht iloc[0], ein Mid-Year-Kurs, als Basis nehmen)."""
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    idx = pd.date_range(f"{year}-03-01", periods=80, freq="B")  # 1.1. liegt vor allen Daten
    result = asyncio.run(_agent_with_history(idx).run("^IDX"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.perf_ytd is None, (
        f"Ohne Jahresanfangs-Basis muss YTD None sein, war {result.perf_ytd}"
    )


def test_ytd_computed_when_history_spans_year_begin():
    """Positiv-Guard: Historie reicht über den Jahreswechsel → echter Jahresanfangs-Kurs
    → YTD wird gesetzt (der Fix darf den Normalfall nicht kaputtmachen)."""
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    idx = pd.date_range(f"{year - 1}-06-02", periods=280, freq="B")  # Vorjahr → laufendes Jahr
    result = asyncio.run(_agent_with_history(idx).run("^IDX"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.perf_ytd is not None, "YTD muss bei vorhandenem Jahresanfangs-Kurs gesetzt sein"
