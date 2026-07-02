from datetime import date

from adapters.data.caching_data_provider import CachingEcbProvider, _CachingBase
from adapters.persistence.composite_snapshot_store import CompositeSnapshotStore
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory
from core.domain.run_context import RunContext
from core.ports.data_provider import EcbDataProvider
from core.ports.snapshot_store import SnapshotStore


class _FakeEcb(EcbDataProvider):
    """Zählt Live-Calls und kann Fehler simulieren."""

    def __init__(self, cpi=2.5, raise_on_cpi=False):
        self.calls = 0
        self._cpi = cpi
        self._raise = raise_on_cpi

    def get_cpi(self):
        self.calls += 1
        if self._raise:
            raise RuntimeError("Quelle down")
        return self._cpi

    # restliche Abstract-Methoden: neutrale Stubs
    def get_interest_rate(self): return None
    def get_m3_growth(self): return None
    def get_balance_sheet_growth(self): return None
    def get_core_cpi(self): return None
    def get_ppi(self): return None
    def get_gdp_growth(self): return None
    def get_unemployment(self): return None
    def get_pmi(self): return None
    def get_m2_growth(self): return None
    def get_sovereign_yields(self): return {"DE_10y": 2.4}
    def get_yield_spreads(self): return {"10y2y": 0.5, "10y3m": 0.8}
    def get_unemployment_history(self, months=14): return [6.1, 6.2, 6.3]


def _wrap(inner, as_of=date(2026, 7, 1), store=None):
    run = RunContext(as_of=as_of)
    store = store or CompositeSnapshotStore(InMemoryDatedHistory(), "/tmp/aaia_test_blobs.json")
    return CachingEcbProvider(inner, run, store), run, store


def test_ist_ein_ecb_provider():
    prov, _, _ = _wrap(_FakeEcb())
    assert isinstance(prov, EcbDataProvider)


def test_memo_dedup_nur_ein_live_call_pro_lauf():
    inner = _FakeEcb()
    prov, _, _ = _wrap(inner)
    assert prov.get_cpi() == 2.5
    assert prov.get_cpi() == 2.5
    assert inner.calls == 1  # zweiter Zugriff = Memo-Hit


def test_live_miss_schreibt_write_through_in_store():
    inner = _FakeEcb(cpi=3.1)
    prov, _, store = _wrap(inner)
    prov.get_cpi()
    assert store.get("ecb", "cpi", date(2026, 7, 1)) == (date(2026, 7, 1), 3.1)


def test_frischer_store_treffer_vermeidet_live_call():
    store = CompositeSnapshotStore(InMemoryDatedHistory(), "/tmp/aaia_test_blobs2.json")
    store.put("ecb", "cpi", date(2026, 7, 1), 9.9)  # heute geschrieben → frisch
    inner = _FakeEcb(cpi=1.1)
    prov, _, _ = _wrap(inner, store=store)
    assert prov.get_cpi() == 9.9
    assert inner.calls == 0


def test_exception_faellt_auf_letzten_bekannten_store_wert_zurueck():
    store = CompositeSnapshotStore(InMemoryDatedHistory(), "/tmp/aaia_test_blobs3.json")
    store.put("ecb", "cpi", date(2026, 1, 1), 2.0)  # alt/stale, aber bekannt
    inner = _FakeEcb(raise_on_cpi=True)
    # TTL-Default 1 Tag → Jan-Wert ist stale → Live-Versuch → Exception → Fallback auf Jan-Wert.
    prov, _, _ = _wrap(inner, as_of=date(2026, 7, 1), store=store)
    assert prov.get_cpi() == 2.0


def test_exception_ohne_store_liefert_none():
    inner = _FakeEcb(raise_on_cpi=True)
    prov, _, _ = _wrap(inner)
    assert prov.get_cpi() is None


def test_dict_rueckgaben_werden_unveraendert_durchgereicht():
    prov, _, _ = _wrap(_FakeEcb())
    assert prov.get_yield_spreads() == {"10y2y": 0.5, "10y3m": 0.8}
    assert prov.get_sovereign_yields() == {"DE_10y": 2.4}


def test_unemployment_history_wird_an_inner_delegiert():
    # Regressionsschutz: die konkrete ABC-Default-Methode (gibt [] zurück) darf
    # NICHT geerbt werden — sonst verliert das Umwickeln des echten Adapters die
    # EU-Arbeitslosen-Historie (Sahm-Regel im gdp_agent bräche auf None).
    prov, _, _ = _wrap(_FakeEcb())
    assert prov.get_unemployment_history() == [6.1, 6.2, 6.3]


class _ThrowingGetStore(SnapshotStore):
    """SnapshotStore, dessen get() wirft — simuliert einen IO-/netzgestützten Store."""

    def __init__(self):
        self.puts = []

    def get(self, namespace, key, as_of):
        raise RuntimeError("Store-Read kaputt")

    def put(self, namespace, key, obs_date, value):
        self.puts.append((namespace, key, obs_date, value))


def test_store_read_exception_faellt_auf_live_zurueck():
    # store.get() wirft → wie Store-Miss behandeln → Live-Fetch liefert den Wert, kein Wurf.
    inner = _FakeEcb(cpi=4.2)
    run = RunContext(as_of=date(2026, 7, 1))
    prov = CachingEcbProvider(inner, run, _ThrowingGetStore())
    assert prov.get_cpi() == 4.2
    assert inner.calls == 1


def test_decode_exception_bei_frischem_treffer_faellt_auf_live_zurueck(tmp_path):
    # Frischer Store-Treffer vorhanden, aber decode wirft → wie Miss → Live-Fetch.
    store = CompositeSnapshotStore(InMemoryDatedHistory(), str(tmp_path / "b.json"))
    store.put("ns", "k", date(2026, 7, 1), "roh")  # heute → frisch
    run = RunContext(as_of=date(2026, 7, 1))
    base = _CachingBase(object(), run, store)

    def _boom(_):
        raise ValueError("decode kaputt")

    calls = []

    def _fetch():
        calls.append(1)
        return "live"

    result = base._cached("ns", "k", _fetch, decode=_boom)
    assert result == "live"
    assert calls == [1]


def test_decode_exception_ohne_live_liefert_none_statt_wurf(tmp_path):
    # Stale Store-Wert, decode wirft, Live-Miss → None statt Exception (Invariant).
    store = CompositeSnapshotStore(InMemoryDatedHistory(), str(tmp_path / "b.json"))
    store.put("ns", "k", date(2026, 1, 1), "roh")  # alt/stale
    run = RunContext(as_of=date(2026, 7, 1))
    base = _CachingBase(object(), run, store)

    def _boom(_):
        raise ValueError("decode kaputt")

    result = base._cached("ns", "k", lambda: None, decode=_boom)
    assert result is None
