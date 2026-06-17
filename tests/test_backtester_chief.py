import asyncio
from unittest.mock import MagicMock
from agents.backtester_chief_agent import BacktesterChiefAgent


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


def test_chief_run_publishes_ready():
    memory = MagicMock()
    memory.load_global_history.return_value = []
    bus = MagicMock()
    chief = BacktesterChiefAgent(memory, bus)
    asyncio.run(chief.run())
    assert bus.publish.called
