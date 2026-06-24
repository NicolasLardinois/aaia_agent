import asyncio
from datetime import datetime, timedelta, timezone

from agents.backtester.conflict_backtester_agent import ConflictBacktesterAgent


class _Item:
    def __init__(self, ticker, direction, verdict, created_at):
        self.ticker, self.direction, self.verdict, self.created_at = (
            ticker, direction, verdict, created_at)


class _FakeStore:
    def __init__(self, items): self._items = items
    def load_for_backtest(self, days=180): return self._items


class _FakeMemory:
    def __init__(self): self.reports = []
    def save_backtester_report(self, report): self.reports.append(report)


def _created(days_ago):
    return str(datetime.now(timezone.utc) - timedelta(days=days_ago))


def test_exit_on_long_that_fell_is_correct_and_reported():
    store = _FakeStore([_Item("AAA", "long", "EXIT", _created(40))])
    mem = _FakeMemory()
    agent = ConflictBacktesterAgent(
        store, mem,
        price_on_horizon=lambda t, d, h: 100.0 if h == 0 else 90.0,  # fiel 100→90
        benchmark_return=lambda m, d, h: 0.0,
    )
    asyncio.run(agent.run())
    exit_rows = [r for r in mem.reports if r["original_recommendation"] == "EXIT"]
    assert len(exit_rows) == 1
    assert exit_rows[0]["return_pct"] > 0           # EXIT richtig → positive Auszahlung


def test_missing_entry_price_is_skipped_not_crash():
    # Fehlender EINSTIEGSpreis (h==0 → None) → übersprungen (kein gültiger Basispreis).
    store = _FakeStore([_Item("AAA", "long", "HOLD", _created(40))])
    mem = _FakeMemory()
    agent = ConflictBacktesterAgent(
        store, mem,
        price_on_horizon=lambda t, d, h: None if h == 0 else 90.0,
        benchmark_return=lambda m, d, h: 0.0,
    )
    asyncio.run(agent.run())
    assert mem.reports == []


def test_delisting_missing_forward_price_counts_as_total_loss():
    # Fehlender FOLGEkurs (delistet/insolvent) wird NICHT übersprungen, sondern als
    # Totalverlust (-100 %) gewertet: ein gehaltenes Long, das auf null ging, ist ein
    # katastrophal falsches HOLD — darf nicht still wegfallen (Survivorship-Bias).
    store = _FakeStore([_Item("AAA", "long", "HOLD", _created(40))])
    mem = _FakeMemory()
    agent = ConflictBacktesterAgent(
        store, mem,
        price_on_horizon=lambda t, d, h: 100.0 if h == 0 else None,  # Einstieg da, Folgekurs weg
        benchmark_return=lambda m, d, h: 0.0,
    )
    asyncio.run(agent.run())
    hold_rows = [r for r in mem.reports if r["original_recommendation"] == "HOLD"]
    assert len(hold_rows) == 1                       # gezählt, nicht übersprungen
    assert hold_rows[0]["return_pct"] == -100.0      # Totalverlust → HOLD katastrophal falsch


def test_unknown_verdict_and_unripe_are_skipped():
    store = _FakeStore([
        _Item("AAA", "long", "WEITER", _created(40)),   # unbekanntes Verdikt
        _Item("BBB", "long", "HOLD", _created(5)),        # zu jung (< 30d Horizont)
    ])
    mem = _FakeMemory()
    agent = ConflictBacktesterAgent(
        store, mem, price_on_horizon=lambda t, d, h: 100.0 if h == 0 else 90.0,
        benchmark_return=lambda m, d, h: 0.0)
    asyncio.run(agent.run())
    assert mem.reports == []
