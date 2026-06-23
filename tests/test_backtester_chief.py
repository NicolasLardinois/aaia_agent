import asyncio
from unittest.mock import AsyncMock, MagicMock
from agents.backtester_chief_agent import BacktesterChiefAgent
from agents.backtester.short_backtester_agent import ShortBacktesterAgent


def test_chief_injects_providers_into_subagents():
    memory = MagicMock()
    memory.load_global_history.return_value = []
    bus = MagicMock()
    price_fn = lambda t, d, h: 100.0
    bench_fn = lambda *a: 0.0
    chief = BacktesterChiefAgent(memory, bus, price_on_horizon=price_fn, benchmark_return=bench_fn)
    assert chief.bu_backtester.price_on_horizon is price_fn
    assert chief.j_backtester.benchmark_return is bench_fn
    assert chief.td_backtester.benchmark_return is bench_fn


def test_chief_wires_short_backtester_with_providers():
    # Der Short-Backtester muss als Sub-Agent des Chiefs existieren und dieselben
    # injizierten Provider erhalten wie die anderen Backtester (sonst läuft die
    # Short-Auswertung nie im Betrieb).
    memory = MagicMock()
    memory.load_global_history.return_value = []
    bus = MagicMock()
    price_fn = lambda t, d, h: 100.0
    bench_fn = lambda *a: 0.0
    chief = BacktesterChiefAgent(memory, bus, price_on_horizon=price_fn, benchmark_return=bench_fn)
    assert isinstance(chief.short_backtester, ShortBacktesterAgent)
    assert chief.short_backtester.price_on_horizon is price_fn
    assert chief.short_backtester.benchmark_return is bench_fn


def test_chief_run_executes_short_backtester():
    # chief.run() muss short_backtester.run() tatsächlich starten (im gather).
    memory = MagicMock()
    memory.load_global_history.return_value = []
    bus = MagicMock()
    chief = BacktesterChiefAgent(memory, bus)
    chief.short_backtester.run = AsyncMock()
    asyncio.run(chief.run())
    chief.short_backtester.run.assert_awaited_once()


def test_chief_run_publishes_ready():
    memory = MagicMock()
    memory.load_global_history.return_value = []
    bus = MagicMock()
    chief = BacktesterChiefAgent(memory, bus)
    asyncio.run(chief.run())
    assert bus.publish.called
