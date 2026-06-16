from agents.backtester.top_down_backtester_agent import _regime_expectation, _regime_correct, TopDownBacktesterAgent
from unittest.mock import MagicMock
import asyncio
from datetime import datetime, timedelta, timezone


def test_regime_expectation_risk_on_off():
    assert _regime_expectation("Boom") > 0
    assert _regime_expectation("Aufschwung") > 0
    assert _regime_expectation("Erholung") > 0
    assert _regime_expectation("Abschwung") < 0
    assert _regime_expectation("Rezession") < 0
    assert _regime_expectation("Depression") < 0


def test_regime_correct_matches_sign():
    # Boom (risk-on) + Markt +5 % → korrekt
    assert _regime_correct("Boom", 0.05) is True
    assert _regime_correct("Boom", -0.05) is False
    # Rezession (risk-off) + Markt −5 % → korrekt
    assert _regime_correct("Rezession", -0.05) is True


def test_topdown_prognostic_accuracy():
    memory = MagicMock()
    now = datetime.now(timezone.utc)
    hist = [
        {"regime": "Boom", "timestamp": now - timedelta(days=100), "market": "USA"},
        {"regime": "Rezession", "timestamp": now - timedelta(days=100), "market": "USA"},
    ]
    memory.load_global_history.return_value = hist
    # Boom-Eintrag: Markt +5 % (korrekt); Rezession-Eintrag: Markt +5 % (falsch)
    agent = TopDownBacktesterAgent(memory, benchmark_return=lambda *a: 0.05)
    asyncio.run(agent.run())
    report = memory.save_backtester_report.call_args_list[0].args[0]
    assert report["backtester_type"] == "topdown"
    assert report["accuracy_90d"] == 0.5


from agents.backtester.judgment_backtester_agent import JudgmentBacktesterAgent


def _j_entry(ticker, rec, price, days_ago, market="USA"):
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "ticker": ticker, "recommendation": rec,
        "price_at_analysis": price, "timestamp": ts, "market": market,
    }


def test_judgment_buy_correct_when_alpha_positive():
    memory = MagicMock()
    memory.load_global_history.return_value = [_j_entry("AAA", "BUY", 100.0, 100)]
    agent = JudgmentBacktesterAgent(
        memory,
        price_on_horizon=lambda t, d, h: 112.0,
        benchmark_return=lambda *a: 0.04,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    per = [r for r in reports if r.get("ticker") == "AAA"]
    assert per and per[0]["verdict"] == "correct"


def test_judgment_short_correct_when_alpha_negative():
    memory = MagicMock()
    memory.load_global_history.return_value = [_j_entry("BBB", "SHORT", 100.0, 100)]
    agent = JudgmentBacktesterAgent(
        memory,
        price_on_horizon=lambda t, d, h: 90.0,
        benchmark_return=lambda *a: 0.0,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    per = [r for r in reports if r.get("ticker") == "BBB"]
    assert per and per[0]["verdict"] == "correct"


def test_judgment_hold_excluded_from_hitrate():
    memory = MagicMock()
    hist = [_j_entry("H", "HOLD", 100.0, 100)] + [
        _j_entry(f"B{i}", "BUY", 100.0, 100) for i in range(11)
    ]
    memory.load_global_history.return_value = hist
    agent = JudgmentBacktesterAgent(
        memory,
        price_on_horizon=lambda t, d, h: 110.0,
        benchmark_return=lambda *a: 0.0,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    agg = [r for r in reports if r.get("ticker") is None]
    assert agg and agg[0]["sample_size"] == 11  # HOLD nicht mitgezählt


from agents.backtester.bottom_up_backtester_agent import BottomUpBacktesterAgent


def _entry(ticker, signal, price, days_ago, market="USA"):
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "ticker": ticker, "dominant_signal": signal,
        "price_at_analysis": price, "timestamp": ts, "market": market,
    }


def _price_fn(forward_prices):
    # forward_prices: {(ticker, horizon): price_or_None}
    def fn(ticker, entry_date, horizon_days):
        return forward_prices.get((ticker, horizon_days))
    return fn


def test_bottomup_skips_entries_younger_than_min_horizon():
    memory = MagicMock()
    # 10 Tage alt → kein 30/60/90-Window abgeschlossen → nicht auswertbar
    memory.load_global_history.return_value = [_entry("AAA", "bullish", 100.0, 10)]
    agent = BottomUpBacktesterAgent(
        memory, price_on_horizon=_price_fn({}), benchmark_return=lambda *a: 0.0,
    )
    asyncio.run(agent.run())
    memory.save_backtester_report.assert_not_called()


def test_bottomup_market_adjusted_correct():
    memory = MagicMock()
    memory.load_global_history.return_value = [_entry("AAA", "bullish", 100.0, 100)]
    # Asset +10 % über 30 Tage, Benchmark +4 % → Alpha +6 % → bullish correct
    prices = _price_fn({("AAA", 30): 110.0, ("AAA", 60): 110.0, ("AAA", 90): 110.0})
    agent = BottomUpBacktesterAgent(
        memory, price_on_horizon=prices, benchmark_return=lambda market, d, h: 0.04,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    per_entry = [r for r in reports if r.get("ticker") == "AAA"]
    assert per_entry and per_entry[0]["verdict"] == "correct"


def test_bottomup_delisted_counts_as_total_loss():
    memory = MagicMock()
    memory.load_global_history.return_value = [_entry("DEAD", "bullish", 100.0, 100)]
    # Forward-Preis None → Totalverlust → bullish incorrect (nicht übersprungen!)
    prices = _price_fn({})  # alle None
    agent = BottomUpBacktesterAgent(
        memory, price_on_horizon=prices, benchmark_return=lambda *a: 0.0,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    per_entry = [r for r in reports if r.get("ticker") == "DEAD"]
    assert per_entry and per_entry[0]["verdict"] == "incorrect"


def test_bottomup_aggregate_report_has_metrics_and_ci():
    memory = MagicMock()
    hist = [_entry(f"T{i}", "bullish", 100.0, 100) for i in range(12)]
    memory.load_global_history.return_value = hist
    # alle +10 %, Benchmark 0 → alle correct
    def price_fn(ticker, d, h):
        return 110.0
    agent = BottomUpBacktesterAgent(
        memory, price_on_horizon=price_fn, benchmark_return=lambda *a: 0.0,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    agg = [r for r in reports if r.get("ticker") is None]
    assert agg, "Aggregat-Report fehlt"
    a = agg[0]
    assert "sharpe" in a and "max_drawdown" in a and "profit_factor" in a
    assert "hit_rate_ci_low" in a and "hit_rate_ci_high" in a
    assert a["sample_size"] >= 10
