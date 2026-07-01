from datetime import date

import pandas as pd
from pandas.testing import assert_frame_equal

from adapters.data.caching_data_provider import CachingMarketProvider
from adapters.persistence.composite_snapshot_store import CompositeSnapshotStore
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory
from core.domain.run_context import RunContext
from core.ports.data_provider import MarketDataProvider


def _frame():
    idx = pd.DatetimeIndex(["2026-06-01", "2026-06-02"], name="Date")
    return pd.DataFrame({"Close": [100.5, 101.0]}, index=idx)


class _FakeMarket(MarketDataProvider):
    def __init__(self):
        self.calls = 0

    def get_current_price(self, ticker): return 123.0
    def get_price_history(self, ticker, period="1y"):
        self.calls += 1
        return _frame()
    def get_info(self, ticker): return {"name": ticker}


def _wrap(inner, tmp_path):
    run = RunContext(as_of=date(2026, 7, 1))
    store = CompositeSnapshotStore(InMemoryDatedHistory(), str(tmp_path / "blobs.json"))
    return CachingMarketProvider(inner, run, store), store


def test_ist_ein_market_provider(tmp_path):
    prov, _ = _wrap(_FakeMarket(), tmp_path)
    assert isinstance(prov, MarketDataProvider)


def test_price_history_dedup_und_round_trip(tmp_path):
    inner = _FakeMarket()
    prov, _ = _wrap(inner, tmp_path)
    first = prov.get_price_history("AAPL", "1y")
    second = prov.get_price_history("AAPL", "1y")  # Memo-Hit
    assert inner.calls == 1
    assert_frame_equal(first, _frame(), check_like=True)
    assert_frame_equal(second, _frame(), check_like=True)


def test_store_treffer_decodiert_zurueck_zu_dataframe(tmp_path):
    inner = _FakeMarket()
    prov, store = _wrap(inner, tmp_path)
    prov.get_price_history("AAPL", "1y")               # schreibt codierten Payload
    # Neuer Lauf, neue Provider-Instanz, gleicher Store → Store-Hit, kein Live-Call.
    run2 = RunContext(as_of=date(2026, 7, 1))
    prov2 = CachingMarketProvider(_FakeMarket(), run2, store)
    restored = prov2.get_price_history("AAPL", "1y")
    assert isinstance(restored, pd.DataFrame)
    # WICHTIG: `restored` ging durch den Codec (encode→Store→decode). Der Codec
    # normalisiert die Datetime-Auflösung verlustfrei von us→ns (empirisch geprüft:
    # Werte UND Index-Werte bleiben identisch, nur die Auflösungseinheit ändert sich —
    # dieselbe brief-abgesegnete Nuance wie in Task 4). Deshalb `check_index_type=False`;
    # den Codec NICHT verlustbehaftet verbiegen.
    assert_frame_equal(restored, _frame(), check_like=True, check_index_type=False)


def test_delegation_current_price_und_info(tmp_path):
    prov, _ = _wrap(_FakeMarket(), tmp_path)
    assert prov.get_current_price("AAPL") == 123.0
    assert prov.get_info("AAPL") == {"name": "AAPL"}
