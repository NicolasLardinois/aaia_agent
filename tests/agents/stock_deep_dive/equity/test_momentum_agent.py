import asyncio
import pandas as pd
from unittest.mock import MagicMock
from core.domain.models import Signal, MomentumSnapshot
from agents.stock_deep_dive.equity.momentum_agent import EquityMomentumAgent, _benchmark_for


def _series(vals): return pd.DataFrame({"Close": vals})


def _market(country, ticker_prices, bench_prices):
    m = MagicMock()
    m.get_info.return_value = {"country": country}
    def _hist(sym, period):
        return _series(bench_prices) if sym.startswith("^") else _series(ticker_prices)
    m.get_price_history.side_effect = _hist
    return m


def test_benchmark_map():
    assert _benchmark_for("United States") == "^GSPC"
    assert _benchmark_for("Switzerland") == "^SSMI"
    assert _benchmark_for("Germany") == "^STOXX50E"
    assert _benchmark_for("Brazil") == "^GSPC"
    assert _benchmark_for(None) == "^GSPC"


def test_relative_strength_and_signal():
    up = [100.0] * 200 + [120.0] * 60
    bench = [100.0] * 200 + [110.0] * 60
    snap = asyncio.run(EquityMomentumAgent(_market("United States", up, bench), MagicMock()).run("AAPL"))
    assert snap.relative_strength is not None and round(snap.relative_strength, 2) == 0.10
    assert snap.signal in (Signal.BULLISH, Signal.NEUTRAL)


def test_default_on_price_error():
    m = MagicMock()
    m.get_info.return_value = {"country": "United States"}
    m.get_price_history.side_effect = Exception("net")
    snap = asyncio.run(EquityMomentumAgent(m, MagicMock()).run("AAPL"))
    assert snap.signal == Signal.NEUTRAL and snap.ma50 is None
