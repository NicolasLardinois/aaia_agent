import asyncio
from datetime import datetime, timedelta, timezone

from agents.backtester.short_backtester_agent import ShortBacktesterAgent


class _FakeMemory:
    def __init__(self, rows):
        self._rows = rows
        self.reports = []

    def load_global_history(self, days=180):
        return self._rows

    def save_backtester_report(self, report):
        self.reports.append(report)


def _row(action, price, days_ago, meta, ticker="AAA"):
    return {
        "ticker": ticker,
        "short_action": action,
        "price_at_analysis": price,
        "market": "USA",
        "timestamp": datetime.now(timezone.utc) - timedelta(days=days_ago),
        "short_meta": meta,
    }


def test_short_entry_that_fell_is_graded_correct():
    rows = [_row("SHORT", 100.0, days_ago=40, meta={"archetypes": ["distress"]})]
    mem = _FakeMemory(rows)
    agent = ShortBacktesterAgent(
        mem,
        price_on_horizon=lambda t, d, h: 90.0,      # Aktie fiel 100 → 90
        benchmark_return=lambda m, d, h: 0.0,        # kein Markt-Drift
    )
    asyncio.run(agent.run())
    entry_reports = [r for r in mem.reports
                     if r["original_recommendation"] == "entry:distress"]
    assert len(entry_reports) == 1
    assert entry_reports[0]["return_pct"] > 0       # Short verdiente


def test_missing_forward_price_is_skipped_not_crash():
    rows = [_row("SHORT", 100.0, days_ago=40, meta={"archetypes": ["distress"]})]
    mem = _FakeMemory(rows)
    agent = ShortBacktesterAgent(
        mem,
        price_on_horizon=lambda t, d, h: None,       # kein Folgekurs
        benchmark_return=lambda m, d, h: 0.0,
    )
    asyncio.run(agent.run())                          # darf nicht crashen
    assert mem.reports == []


def test_hold_and_none_are_ignored():
    rows = [
        _row("HOLD", 100.0, days_ago=40, meta={"archetypes": ["x"]}),
        _row("NONE", 100.0, days_ago=40, meta={"archetypes": ["x"]}),
    ]
    mem = _FakeMemory(rows)
    agent = ShortBacktesterAgent(mem, price_on_horizon=lambda t, d, h: 90.0,
                                 benchmark_return=lambda m, d, h: 0.0)
    asyncio.run(agent.run())
    assert mem.reports == []
