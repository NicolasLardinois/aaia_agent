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


def test_scan_records_with_source_proactive():
    # Der Scan ist der proaktive Recorder → der angelegte Posten trägt source="proactive".
    pos = [NS(ticker="AAPL", direction="long")]

    def judge_fn(ticker, direction):
        return NS(conflict=True, conflict_resolution=NS(verdict="EXIT", reasoning="r"))

    store = _Store()
    scan_portfolio_conflicts(pos, judge_fn, store)
    assert len(store.saved) == 1 and store.saved[0].source == "proactive"


def test_scan_orchestrator_has_no_conflict_store():
    # Regression (Review PR #28): der proaktive Scan-Orchestrator darf KEINEN conflict_store
    # tragen. Sonst nähme run() den Konflikt schon als source="on_demand" auf und der spätere
    # proaktive record würde via Dedupe (ticker, direction) verworfen → "proactive" erreicht
    # die DB nie. Diese Naht (_build_scan_orchestrator) war zuvor ungetestet.
    from unittest.mock import MagicMock
    from background_runner import _build_scan_orchestrator
    orch = _build_scan_orchestrator(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    assert orch.conflict_store is None
