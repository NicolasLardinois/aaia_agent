from types import SimpleNamespace as NS

from agents.conflict.portfolio_conflict_scan import scan_portfolio_conflicts


class _Store:
    """Minimaler Fake-Store: record_conflict braucht find_open/find_latest_resolved/save."""

    def __init__(self):
        self.saved = []

    def find_open(self, t, d):
        return None

    def find_latest_resolved(self, t, d):
        return None

    def save(self, i):
        self.saved.append(i)


def test_scan_records_only_conflicts():
    # Zwei gehaltene Positionen; nur AAPL meldet einen Konflikt → nur AAPL wird protokolliert.
    pos = [NS(ticker="AAPL", direction="long"), NS(ticker="MSFT", direction="long")]

    def judge_fn(ticker, direction):
        if ticker == "AAPL":
            return NS(conflict=True, conflict_resolution=NS(verdict="EXIT", reasoning="r"))
        return NS(conflict=False, conflict_resolution=None)

    store = _Store()
    scan_portfolio_conflicts(pos, judge_fn, store)
    assert [i.ticker for i in store.saved] == ["AAPL"]


def test_scan_skips_none_and_errors():
    # A liefert None (keine gecachte Analyse), B wirft einen Fehler → beide übersprungen, kein Crash.
    pos = [NS(ticker="A", direction="long"), NS(ticker="B", direction="short")]

    def judge_fn(ticker, direction):
        if ticker == "A":
            return None                       # keine gecachte Analyse
        raise RuntimeError("boom")            # Fehler je Position

    store = _Store()
    scan_portfolio_conflicts(pos, judge_fn, store)   # darf NICHT crashen
    assert store.saved == []
