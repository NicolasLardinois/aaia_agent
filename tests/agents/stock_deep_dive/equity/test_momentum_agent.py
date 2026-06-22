import asyncio
import threading
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


def test_get_info_runs_off_event_loop_thread():
    """get_info ist ein blockierender Netz-Call (yf.Ticker(...).info) und muss
    via asyncio.to_thread ausgelagert werden, sonst blockiert er die Event-Loop
    und serialisiert die parallel laufenden Equity-Sub-Agenten (AGENTS.md §2)."""
    main_ident = threading.get_ident()
    recorded: dict[str, int] = {}

    def _info(ticker):
        recorded["ident"] = threading.get_ident()
        return {"country": "United States"}

    m = MagicMock()
    m.get_info.side_effect = _info
    m.get_price_history.return_value = _series([100.0] * 260)

    asyncio.run(EquityMomentumAgent(m, MagicMock()).run("AAPL"))

    assert recorded["ident"] != main_ident, (
        "get_info muss off-thread laufen (asyncio.to_thread), nicht auf dem Event-Loop-Thread"
    )


def test_relative_strength_uses_common_date_window():
    """RS muss auf dem GEMEINSAMEN Datumsbereich von Titel und Benchmark rechnen.
    Titel und Heimatmarkt haben oft versetzte Historien (anderer Börsenkalender,
    junges Listing) — sonst vergleicht RS zwei unterschiedliche Zeitfenster."""
    bench_idx = pd.date_range("2022-01-01", periods=260, freq="D")
    tkr_idx   = bench_idx[60:]                       # Titel startet 60 Handelstage später

    # Benchmark steigt 90→100 VOR dem Titel-Start, dann flach 100, dann 100→110.
    bench_close = [90.0] * 60 + [100.0] * 140 + [110.0] * 60
    # Titel über das gemeinsame Fenster: 100 → 120 (+20 %).
    tkr_close   = [100.0] * 140 + [120.0] * 60

    bench_df = pd.DataFrame({"Close": bench_close}, index=bench_idx)
    tkr_df   = pd.DataFrame({"Close": tkr_close},   index=tkr_idx)

    m = MagicMock()
    m.get_info.return_value = {"country": "United States"}
    m.get_price_history.side_effect = (
        lambda sym, period: bench_df if sym.startswith("^") else tkr_df
    )

    snap = asyncio.run(EquityMomentumAgent(m, MagicMock()).run("AAPL"))

    # Gemeinsames Fenster = Titel-Zeitraum: Benchmark 100→110 (+0.10), Titel 100→120 (+0.20)
    # → RS = +0.10. Der alte Bug (volle, versetzte Reihen) ergäbe Benchmark 90→110
    # (+0.222) → RS ≈ -0.02.
    assert snap.relative_strength == 0.10
