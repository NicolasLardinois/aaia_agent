"""Tests für die Hexagonal-Umstellung der Backtester-Kursquelle.

Statt hardcoded `yfinance` im Agent-Modul liegt das I/O jetzt im Adapter
`YahooPriceHistoryProvider`; die Ableitung der Benchmark-Rendite ist ein reiner
Helfer (`make_benchmark_return`) über einer injizierten Kurs-Lookup-Funktion.
Ohne Injektion fallen die Agenten auf No-Op-Defaults zurück (kein Netz, kein
Crash) — verhaltens-identisch zum bisherigen geblockten-Netz-Pfad.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from agents.backtester.bottom_up_backtester_agent import BottomUpBacktesterAgent
from agents.backtester.top_down_backtester_agent import TopDownBacktesterAgent
from agents.backtester.short_backtester_agent import ShortBacktesterAgent
from agents.backtester.judgment_backtester_agent import JudgmentBacktesterAgent
from core.utils.backtest import (
    make_benchmark_return, no_benchmark_return, no_price_on_horizon,
)

_D = datetime(2024, 1, 1, tzinfo=timezone.utc)


# ── Reiner Helfer make_benchmark_return ──────────────────────────────────────

def test_make_benchmark_return_computes_forward_return():
    """Benchmark-Return = Forward-Return des Markt-Benchmarks aus der injizierten
    Kurs-Lookup-Funktion (horizon 0 = Entry, horizon = Forward)."""
    def price(ticker, entry_date, horizon_days):
        return 100.0 if horizon_days == 0 else 110.0  # +10 %
    bench = make_benchmark_return(price)
    assert bench("USA", _D, 30) == 0.1


def test_make_benchmark_return_none_entry_is_none():
    """Kein Entry-Kurs (None) → kein Benchmark (None), kein Crash."""
    bench = make_benchmark_return(lambda t, d, h: None)
    assert bench("USA", _D, 30) is None


def test_no_price_on_horizon_is_none():
    assert no_price_on_horizon("AAPL", _D, 30) is None


def test_no_benchmark_return_is_none():
    assert no_benchmark_return("USA", _D, 30) is None


# ── No-Op-Defaults ohne Injektion (verhaltens-identisch zum Netzblock) ────────

def test_bottom_up_default_callables_are_noops():
    agent = BottomUpBacktesterAgent(MagicMock())
    assert agent.price_on_horizon("AAPL", _D, 30) is None
    assert agent.benchmark_return("USA", _D, 30) is None


def test_top_down_default_benchmark_is_noop():
    agent = TopDownBacktesterAgent(MagicMock())
    assert agent.benchmark_return("USA", _D, 30) is None


def test_short_default_callables_are_noops():
    agent = ShortBacktesterAgent(MagicMock())
    assert agent.price_on_horizon("AAPL", _D, 30) is None
    assert agent.benchmark_return("USA", _D, 30) is None


def test_judgment_default_callables_are_noops():
    agent = JudgmentBacktesterAgent(MagicMock())
    assert agent.price_on_horizon("AAPL", _D, 30) is None
    assert agent.benchmark_return("USA", _D, 30) is None


def test_injected_callable_is_used_over_default():
    """Explizit injizierte Kursfunktion hat Vorrang vor dem No-Op-Default."""
    agent = BottomUpBacktesterAgent(MagicMock(), price_on_horizon=lambda t, d, h: 42.0)
    assert agent.price_on_horizon("AAPL", _D, 30) == 42.0
