# Daten-Caching-Schicht (v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine Caching-/Persistenz-Schicht als Decorator **hinter** den bestehenden Ports einführen, sodass jeder Analyselauf jede (Quelle, Serie) nur einmal zieht (Point-in-Time + Dedup), Rohdaten datiert persistiert (Offline-Resilienz + Backtest) — ohne Agenten-Änderung. v1 hängt **ECB-SDW** (Skalar) und **Yahoo-Kurshistorie** (Payload/DataFrame) um.

**Architektur:** Hexagonal. Der Decorator implementiert denselben Port wie der echte Adapter (`EcbDataProvider`, `MarketDataProvider`) und schaltet eine Cache-aside-Logik davor: In-Lauf-Memo (`RunContext`) → datierter `SnapshotStore` (frisch?) → Live-Fetch + write-through. Backtest = identischer Code mit historischem `as_of`. Skalare landen im vorhandenen `DatedHistoryPort` (Wiederverwendung), Payloads in einer JSON-Blob-Datei.

**Tech Stack:** Python 3, pytest, pandas (nur im Codec/Yahoo-Zweig). Keine neuen externen Libs.

## Global Constraints

- **TDD verpflichtend** (AGENTS.md §4): erst der fehlschlagende Test, dann Code. Kein Implementierungs-Code ohne vorher roten Test.
- **Deutsche** Code-Kommentare + Docstrings, moderne Type-Hints (`float | None`, `dict[str, float]`).
- **Kein Agent/Chief/Orchestrator wird geändert.** Nur neue Dateien + Composition-Root-Verdrahtung (`app/server.py`, `app/main.py`) + `config/settings.py`.
- **Defensive Aggregation** (AGENTS.md §2): der Decorator wirft **nie** eine neue Exception nach oben; Store-Schreibfehler werden geloggt und verschluckt (best effort).
- **Kein `git add -A`** — Pfade pro Commit explizit stagen.
- **PR-First:** Branch ist `feat/daten-caching-schicht` (bereits angelegt). Kein Merge ohne User-OK.
- Test-Runner: `python -m pytest -q`.

---

### Task 1: `RunContext` — Lauf-Identität + In-Lauf-Memo

**Files:**
- Create: `core/domain/run_context.py`
- Test: `tests/core/domain/test_run_context.py`

**Interfaces:**
- Produces: `RunContext(as_of: date)` mit Attributen `as_of: date`, `memo: dict[tuple[str, str], Any]` (leer initialisiert).

- [ ] **Step 1: Failing test schreiben**

`tests/core/domain/test_run_context.py`:
```python
from datetime import date

from core.domain.run_context import RunContext


def test_memo_startet_leer_und_ist_pro_instanz_isoliert():
    a = RunContext(as_of=date(2026, 7, 1))
    assert a.as_of == date(2026, 7, 1)
    assert a.memo == {}

    a.memo[("ecb", "cpi")] = 2.5
    b = RunContext(as_of=date(2026, 7, 1))
    # Kein geteilter Default-Zustand zwischen zwei Läufen.
    assert b.memo == {}
    assert a.memo[("ecb", "cpi")] == 2.5
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/core/domain/test_run_context.py -v`
Expected: FAIL (`ModuleNotFoundError: core.domain.run_context`).

- [ ] **Step 3: Minimal implementieren**

`core/domain/run_context.py`:
```python
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class RunContext:
    """Identität EINES Analyselaufs: ein eingefrorenes ``as_of``-Datum + ein In-Lauf-Memo.

    Garantiert, dass jede (namespace, key)-Kombination pro Lauf nur EINMAL live
    gezogen wird → Point-in-Time (alle Agenten sehen denselben Stand) + Dedup.
    Rein, keine I/O. Wird pro Lauf frisch im Composition-Root erzeugt; alle
    Caching-Decorator eines Laufs teilen sich DIESELBE Instanz.
    Backtest: ``as_of`` = historisches Datum → der Store liefert den damaligen Wert.
    """

    as_of: date
    memo: dict[tuple[str, str], Any] = field(default_factory=dict)
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/core/domain/test_run_context.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/domain/run_context.py tests/core/domain/test_run_context.py
git commit -m "feat(cache): RunContext (Lauf-Identität + In-Lauf-Memo)"
```

---

### Task 2: `SnapshotStore`-Port

**Files:**
- Create: `core/ports/snapshot_store.py`
- Test: `tests/core/ports/test_snapshot_store.py`

**Interfaces:**
- Produces: abstrakte Klasse `SnapshotStore(ABC)` mit
  - `put(self, namespace: str, key: str, obs_date: date, value: Any) -> None`
  - `get(self, namespace: str, key: str, as_of: date) -> Optional[tuple[date, Any]]` — `(obs_date, value)` des frischesten Eintrags mit `obs_date <= as_of`, sonst `None`.

- [ ] **Step 1: Failing test schreiben**

`tests/core/ports/test_snapshot_store.py`:
```python
from datetime import date

import pytest

from core.ports.snapshot_store import SnapshotStore


def test_snapshot_store_ist_abstrakt():
    with pytest.raises(TypeError):
        SnapshotStore()  # abstrakte Methoden nicht implementiert


def test_minimal_subclass_erfuellt_den_vertrag():
    class Dummy(SnapshotStore):
        def __init__(self):
            self.store: dict[tuple[str, str], tuple[date, object]] = {}

        def put(self, namespace, key, obs_date, value):
            self.store[(namespace, key)] = (obs_date, value)

        def get(self, namespace, key, as_of):
            hit = self.store.get((namespace, key))
            if hit and hit[0] <= as_of:
                return hit
            return None

    d = Dummy()
    d.put("ecb", "cpi", date(2026, 6, 1), 2.5)
    assert d.get("ecb", "cpi", date(2026, 7, 1)) == (date(2026, 6, 1), 2.5)
    assert d.get("ecb", "cpi", date(2026, 5, 1)) is None
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/core/ports/test_snapshot_store.py -v`
Expected: FAIL (`ModuleNotFoundError: core.ports.snapshot_store`).

- [ ] **Step 3: Minimal implementieren**

`core/ports/snapshot_store.py`:
```python
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Optional


class SnapshotStore(ABC):
    """Datierter Key-Value-Store hinter den Caching-Decorators.

    ``value`` ist JSON-serialisierbar: entweder ein Skalar (float) ODER ein
    codierter Payload (z. B. ein per ``dataframe_codec`` serialisierter DataFrame).
    Die Datums-Semantik ist bewusst identisch zu ``DatedHistoryPort``: ``get``
    liefert den frischesten Wert mit ``obs_date <= as_of`` (Point-in-Time-fähig).
    """

    @abstractmethod
    def put(self, namespace: str, key: str, obs_date: date, value: Any) -> None:
        """Idempotent pro (namespace, key, obs_date): gleicher Tag überschreibt."""
        ...

    @abstractmethod
    def get(self, namespace: str, key: str, as_of: date) -> Optional[tuple[date, Any]]:
        """(obs_date, value) des frischesten Eintrags mit obs_date <= as_of; None wenn leer."""
        ...
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/core/ports/test_snapshot_store.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/ports/snapshot_store.py tests/core/ports/test_snapshot_store.py
git commit -m "feat(cache): SnapshotStore-Port (datierter Key-Value-Store)"
```

---

### Task 3: `CompositeSnapshotStore` — Skalare→DatedHistory, Payloads→JSON-Blob

**Files:**
- Create: `adapters/persistence/composite_snapshot_store.py`
- Test: `tests/adapters/persistence/test_composite_snapshot_store.py`

**Interfaces:**
- Consumes: `SnapshotStore` (Task 2), `DatedHistoryPort` (`core/ports/dated_history.py`), `InMemoryDatedHistory` (`adapters/persistence/in_memory_dated_history.py`, für Tests).
- Produces: `CompositeSnapshotStore(scalar_history: DatedHistoryPort, blob_path: str)` — implementiert `SnapshotStore`. Routet floats in `scalar_history` (Serie `f"{namespace}:{key}"`), alles andere in eine JSON-Blob-Datei.

- [ ] **Step 1: Failing test schreiben**

`tests/adapters/persistence/test_composite_snapshot_store.py`:
```python
from datetime import date

from adapters.persistence.composite_snapshot_store import CompositeSnapshotStore
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory


def _store(tmp_path):
    return CompositeSnapshotStore(InMemoryDatedHistory(), str(tmp_path / "blobs.json"))


def test_skalar_geht_in_datedhistory_und_kommt_datiert_zurueck(tmp_path):
    s = _store(tmp_path)
    s.put("ecb", "cpi", date(2026, 6, 1), 2.5)
    assert s.get("ecb", "cpi", date(2026, 7, 1)) == (date(2026, 6, 1), 2.5)


def test_get_liefert_frischesten_wert_kleiner_gleich_as_of(tmp_path):
    s = _store(tmp_path)
    s.put("ecb", "cpi", date(2026, 5, 1), 2.0)
    s.put("ecb", "cpi", date(2026, 6, 1), 2.5)
    # as_of zwischen beiden → älterer Wert
    assert s.get("ecb", "cpi", date(2026, 5, 15)) == (date(2026, 5, 1), 2.0)
    # as_of vor allem → None
    assert s.get("ecb", "cpi", date(2026, 4, 1)) is None


def test_payload_geht_in_blob_und_ueberlebt_neue_instanz(tmp_path):
    path = str(tmp_path / "blobs.json")
    s1 = CompositeSnapshotStore(InMemoryDatedHistory(), path)
    s1.put("yahoo.price_history", "AAPL:1y", date(2026, 6, 1), '{"schema": "x"}')
    # Neue Instanz liest die persistierte Blob-Datei.
    s2 = CompositeSnapshotStore(InMemoryDatedHistory(), path)
    assert s2.get("yahoo.price_history", "AAPL:1y", date(2026, 7, 1)) == (
        date(2026, 6, 1), '{"schema": "x"}')


def test_bool_gilt_nicht_als_skalar_sondern_als_payload(tmp_path):
    # bool ist Subklasse von int — darf NICHT in die float-Zeitreihe.
    s = _store(tmp_path)
    s.put("ns", "flag", date(2026, 6, 1), True)
    assert s.get("ns", "flag", date(2026, 7, 1)) == (date(2026, 6, 1), True)


def test_leerer_store_liefert_none(tmp_path):
    s = _store(tmp_path)
    assert s.get("ecb", "cpi", date(2026, 7, 1)) is None
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/persistence/test_composite_snapshot_store.py -v`
Expected: FAIL (`ModuleNotFoundError: adapters.persistence.composite_snapshot_store`).

- [ ] **Step 3: Minimal implementieren**

`adapters/persistence/composite_snapshot_store.py`:
```python
import json
import logging
import os
from datetime import date
from typing import Any, Optional

from core.ports.dated_history import DatedHistoryPort
from core.ports.snapshot_store import SnapshotStore

_log = logging.getLogger(__name__)


def _is_scalar(value: Any) -> bool:
    # bool ist Subklasse von int, soll aber NICHT als float-Zeitreihe gelten.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class CompositeSnapshotStore(SnapshotStore):
    """SnapshotStore, der nach Wert-Typ routet (Review-Entscheid 2026-07-01):

    - **float → DatedHistoryPort** (Wiederverwendung; Serie ``f"{namespace}:{key}"``).
      Kein zweiter Zeitreihen-Store; der Backtest-Fall fällt geschenkt ab.
    - **Payload (str/dict/…) → JSON-Blob-Datei** (datiert), da DatedHistoryPort nur floats hält.
    """

    def __init__(self, scalar_history: DatedHistoryPort, blob_path: str) -> None:
        self._scalars = scalar_history
        self._blob_path = blob_path
        self._blobs: dict[str, dict[str, Any]] = self._load_blobs()

    @staticmethod
    def _series(namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    def _load_blobs(self) -> dict[str, dict[str, Any]]:
        if not os.path.exists(self._blob_path):
            return {}
        try:
            with open(self._blob_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return raw if isinstance(raw, dict) else {}
        except Exception:
            return {}

    def _save_blobs(self) -> None:
        directory = os.path.dirname(self._blob_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self._blob_path, "w", encoding="utf-8") as f:
            json.dump(self._blobs, f)

    def put(self, namespace: str, key: str, obs_date: date, value: Any) -> None:
        series = self._series(namespace, key)
        if _is_scalar(value):
            self._scalars.append(series, obs_date, float(value))
        else:
            self._blobs.setdefault(series, {})[obs_date.isoformat()] = value
            try:
                self._save_blobs()
            except Exception as exc:  # Best effort: Persistenz-Fehler killt den Lauf nicht.
                _log.warning("CompositeSnapshotStore: Blob-Save fehlgeschlagen (%s)", exc)

    def get(self, namespace: str, key: str, as_of: date) -> Optional[tuple[date, Any]]:
        series = self._series(namespace, key)
        # 1. Skalar-Zweig (DatedHistoryPort) — frischester mit d <= as_of.
        scalar_hit: Optional[tuple[date, Any]] = None
        for d, v in self._scalars.values(series):
            if d <= as_of:
                scalar_hit = (d, v)
            else:
                break
        if scalar_hit is not None:
            return scalar_hit
        # 2. Blob-Zweig — analog.
        blob_hit: Optional[tuple[date, Any]] = None
        for iso, v in sorted(self._blobs.get(series, {}).items()):
            d = date.fromisoformat(iso)
            if d <= as_of:
                blob_hit = (d, v)
            else:
                break
        return blob_hit
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/adapters/persistence/test_composite_snapshot_store.py -v`
Expected: PASS (5 Tests).

- [ ] **Step 5: Commit**

```bash
git add adapters/persistence/composite_snapshot_store.py tests/adapters/persistence/test_composite_snapshot_store.py
git commit -m "feat(cache): CompositeSnapshotStore (Skalare→DatedHistory, Payloads→JSON-Blob)"
```

---

### Task 4: `dataframe_codec` — DataFrame ⇄ JSON-String

**Files:**
- Create: `core/utils/dataframe_codec.py`
- Test: `tests/core/utils/test_dataframe_codec.py`

**Interfaces:**
- Produces: `encode_frame(df: pd.DataFrame) -> str`, `decode_frame(payload: str) -> pd.DataFrame`. Round-Trip erhält Werte, Spalten-dtypes und (Datetime-)Index.

- [ ] **Step 1: Failing test schreiben**

`tests/core/utils/test_dataframe_codec.py`:
```python
import pandas as pd
from pandas.testing import assert_frame_equal

from core.utils.dataframe_codec import decode_frame, encode_frame


def test_round_trip_mit_datetime_index_erhaelt_werte_und_index():
    idx = pd.DatetimeIndex(["2026-06-01", "2026-06-02"], name="Date")
    df = pd.DataFrame({"Close": [100.5, 101.0], "Volume": [10, 20]}, index=idx)

    restored = decode_frame(encode_frame(df))

    assert_frame_equal(df, restored, check_like=True)


def test_leerer_frame_round_trip():
    df = pd.DataFrame({"Close": []})
    restored = decode_frame(encode_frame(df))
    assert list(restored.columns) == ["Close"]
    assert len(restored) == 0
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/core/utils/test_dataframe_codec.py -v`
Expected: FAIL (`ModuleNotFoundError: core.utils.dataframe_codec`).

- [ ] **Step 3: Minimal implementieren**

`core/utils/dataframe_codec.py`:
```python
from io import StringIO

import pandas as pd


def encode_frame(df: pd.DataFrame) -> str:
    """DataFrame → JSON-String.

    ``orient="table"`` schreibt ein JSON-Schema mit Spalten, dtypes und Index mit —
    dadurch überlebt der Round-Trip den (Datetime-)Index und die Spalten-Typen,
    anders als bei den werteorientierten Orients.
    """
    return df.to_json(orient="table")


def decode_frame(payload: str) -> pd.DataFrame:
    """Umkehrung von :func:`encode_frame`. ``StringIO``, weil ``read_json`` einen
    rohen String künftig nicht mehr direkt akzeptiert."""
    return pd.read_json(StringIO(payload), orient="table")
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/core/utils/test_dataframe_codec.py -v`
Expected: PASS. (Falls `assert_frame_equal` an einer dtype-Nuance scheitert — z. B. int→int64 —, ist das ein echtes Codec-Signal: dann im Test `check_dtype` gezielt prüfen bzw. den erwarteten dtype im Test fixieren, NICHT den Codec verbiegen.)

- [ ] **Step 5: Commit**

```bash
git add core/utils/dataframe_codec.py tests/core/utils/test_dataframe_codec.py
git commit -m "feat(cache): dataframe_codec (DataFrame ⇄ JSON, Round-Trip-fest)"
```

---

### Task 5: `_CachingBase` + `CachingEcbProvider` + `wrap_providers`

**Files:**
- Create: `adapters/data/caching_data_provider.py`
- Test: `tests/adapters/data/test_caching_ecb_provider.py`

**Interfaces:**
- Consumes: `RunContext` (Task 1), `SnapshotStore` (Task 2), `EcbDataProvider` (`core/ports/data_provider.py`), `config.settings.SNAPSHOT_TTL_DAYS` (Task 7 — bis dahin fällt der Test auf einen `getattr`-Default zurück, s. u.).
- Produces:
  - `_CachingBase(inner, run: RunContext, store: SnapshotStore)` mit `_cached(namespace, key, fetch, encode=_identity, decode=_identity)` und `_is_fresh(obs_date) -> bool`.
  - `CachingEcbProvider(_CachingBase, EcbDataProvider)` — cached die 10 skalaren Makro-Methoden, delegiert dict/list-Rückgaben + `get_aaa_10y_yield` unverändert.
  - `wrap_providers(ecb, market, run, store) -> tuple[EcbDataProvider, MarketDataProvider]` (die Market-Hälfte kommt in Task 6 dazu).

**Wichtig (TTL-Default):** `_is_fresh` liest `settings.SNAPSHOT_TTL_DAYS`. Diese Konstante wird erst in Task 7 angelegt. Damit Task 5 eigenständig grün ist, liest `_is_fresh` defensiv via `getattr(settings, "SNAPSHOT_TTL_DAYS", 1)`.

- [ ] **Step 1: Failing test schreiben**

`tests/adapters/data/test_caching_ecb_provider.py`:
```python
from datetime import date

from adapters.data.caching_data_provider import CachingEcbProvider
from adapters.persistence.composite_snapshot_store import CompositeSnapshotStore
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory
from core.domain.run_context import RunContext
from core.ports.data_provider import EcbDataProvider


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
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/data/test_caching_ecb_provider.py -v`
Expected: FAIL (`ModuleNotFoundError: adapters.data.caching_data_provider`).

- [ ] **Step 3: Minimal implementieren**

`adapters/data/caching_data_provider.py`:
```python
import logging
from typing import Any, Callable

import config.settings as settings
from core.domain.run_context import RunContext
from core.ports.data_provider import EcbDataProvider
from core.ports.snapshot_store import SnapshotStore

_log = logging.getLogger(__name__)

_DEFAULT_TTL_DAYS = 1


def _identity(x: Any) -> Any:
    return x


class _CachingBase:
    """Cache-aside-Logik, geteilt von allen Port-Decorators.

    Ablauf je Aufruf: (1) In-Lauf-Memo → (2) frischer SnapshotStore-Treffer →
    (3) Live-Fetch + write-through. Bei Exception/None: letzter bekannter Store-Wert
    (Offline-Resilienz), sonst None/Default des inneren Adapters. Wirft NIE selbst.
    """

    def __init__(self, inner: Any, run: RunContext, store: SnapshotStore) -> None:
        self._inner = inner
        self._run = run
        self._store = store

    def _is_fresh(self, obs_date) -> bool:
        ttl = getattr(settings, "SNAPSHOT_TTL_DAYS", _DEFAULT_TTL_DAYS)
        return (self._run.as_of - obs_date).days < ttl

    def _cached(
        self,
        namespace: str,
        key: str,
        fetch: Callable[[], Any],
        encode: Callable[[Any], Any] = _identity,
        decode: Callable[[Any], Any] = _identity,
    ) -> Any:
        memo_key = (namespace, key)
        if memo_key in self._run.memo:                       # 1. In-Lauf-Memo
            return self._run.memo[memo_key]

        dated = self._store.get(namespace, key, self._run.as_of)
        if dated is not None and self._is_fresh(dated[0]):   # 2. frischer Store-Treffer
            value = decode(dated[1])
            self._run.memo[memo_key] = value
            return value

        try:                                                 # 3. Live
            value = fetch()
        except Exception as exc:
            _log.warning("Caching %s:%s Live-Fetch fehlgeschlagen (%s)", namespace, key, exc)
            value = None

        if value is None:                                    # Offline-Resilienz: letzter bekannter (auch stale)
            value = decode(dated[1]) if dated is not None else None
        else:
            try:
                self._store.put(namespace, key, self._run.as_of, encode(value))
            except Exception as exc:                         # Store-Write ist best effort
                _log.warning("Caching %s:%s Store-Write fehlgeschlagen (%s)", namespace, key, exc)

        self._run.memo[memo_key] = value
        return value


class CachingEcbProvider(_CachingBase, EcbDataProvider):
    """Caching-Decorator für EcbDataProvider. Die 10 skalaren Makro-Werte werden
    pro Lauf memoisiert + datiert persistiert; Struktur-Rückgaben (dict/list) und
    ``get_aaa_10y_yield`` werden in v1 unverändert durchgereicht (Caching davon = Folge-Task)."""

    _NS = "ecb"

    # ── gecachte Skalare ─────────────────────────────────────────────────────
    def get_interest_rate(self):        return self._cached(self._NS, "interest_rate", self._inner.get_interest_rate)
    def get_m3_growth(self):            return self._cached(self._NS, "m3_growth", self._inner.get_m3_growth)
    def get_m2_growth(self):            return self._cached(self._NS, "m2_growth", self._inner.get_m2_growth)
    def get_balance_sheet_growth(self): return self._cached(self._NS, "balance_sheet_growth", self._inner.get_balance_sheet_growth)
    def get_cpi(self):                  return self._cached(self._NS, "cpi", self._inner.get_cpi)
    def get_core_cpi(self):             return self._cached(self._NS, "core_cpi", self._inner.get_core_cpi)
    def get_ppi(self):                  return self._cached(self._NS, "ppi", self._inner.get_ppi)
    def get_gdp_growth(self):           return self._cached(self._NS, "gdp_growth", self._inner.get_gdp_growth)
    def get_unemployment(self):         return self._cached(self._NS, "unemployment", self._inner.get_unemployment)
    def get_pmi(self):                  return self._cached(self._NS, "pmi", self._inner.get_pmi)

    # ── v1 unverändert durchgereicht ─────────────────────────────────────────
    def get_sovereign_yields(self):     return self._inner.get_sovereign_yields()
    def get_yield_spreads(self):        return self._inner.get_yield_spreads()

    def get_interest_rate_history(self, years: int = 2):
        return self._inner.get_interest_rate_history(years)

    def get_aaa_10y_yield(self):
        # Nicht auf dem ABC, aber vom Realzins-Pfad genutzt (EurostatEcbProvider reicht es durch).
        return self._inner.get_aaa_10y_yield()


def wrap_providers(ecb, market, run: RunContext, store: SnapshotStore):
    """Umhüllt die echten Adapter mit ihren Caching-Decorators. In Task 6 wird die
    Market-Hälfte durch ``CachingMarketProvider`` ersetzt."""
    return CachingEcbProvider(ecb, run, store), market
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/adapters/data/test_caching_ecb_provider.py -v`
Expected: PASS (8 Tests).

- [ ] **Step 5: Commit**

```bash
git add adapters/data/caching_data_provider.py tests/adapters/data/test_caching_ecb_provider.py
git commit -m "feat(cache): CachingEcbProvider + Cache-aside-Basis (_CachingBase)"
```

---

### Task 6: `CachingMarketProvider` — Payload-Pfad (Yahoo-Kurshistorie)

**Files:**
- Modify: `adapters/data/caching_data_provider.py` (Klasse ergänzen, `wrap_providers` fertigstellen)
- Test: `tests/adapters/data/test_caching_market_provider.py`

**Interfaces:**
- Consumes: `MarketDataProvider` (`core/ports/data_provider.py`), `encode_frame`/`decode_frame` (Task 4).
- Produces: `CachingMarketProvider(_CachingBase, MarketDataProvider)` — cached `get_price_history(ticker, period)` via DataFrame-Codec (Namespace `"yahoo.price_history"`, Key `f"{ticker}:{period}"`); delegiert `get_current_price`, `get_info` und die Index-Default-Methoden unverändert.

- [ ] **Step 1: Failing test schreiben**

`tests/adapters/data/test_caching_market_provider.py`:
```python
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
    assert_frame_equal(restored, _frame(), check_like=True)


def test_delegation_current_price_und_info(tmp_path):
    prov, _ = _wrap(_FakeMarket(), tmp_path)
    assert prov.get_current_price("AAPL") == 123.0
    assert prov.get_info("AAPL") == {"name": "AAPL"}
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/data/test_caching_market_provider.py -v`
Expected: FAIL (`ImportError: cannot import name 'CachingMarketProvider'`).

- [ ] **Step 3: Minimal implementieren**

In `adapters/data/caching_data_provider.py` die Importe ergänzen:
```python
from core.ports.data_provider import EcbDataProvider, MarketDataProvider
from core.utils.dataframe_codec import decode_frame, encode_frame
```

Klasse ergänzen (nach `CachingEcbProvider`):
```python
class CachingMarketProvider(_CachingBase, MarketDataProvider):
    """Caching-Decorator für MarketDataProvider. v1 cached ``get_price_history``
    (DataFrame → Payload-Codec); Preis-/Info- und Index-Methoden werden unverändert
    durchgereicht."""

    _NS = "yahoo.price_history"

    def get_price_history(self, ticker: str, period: str = "1y"):
        return self._cached(
            self._NS,
            f"{ticker}:{period}",
            lambda: self._inner.get_price_history(ticker, period),
            encode=encode_frame,
            decode=decode_frame,
        )

    # ── unverändert durchgereicht ────────────────────────────────────────────
    def get_current_price(self, ticker: str):
        return self._inner.get_current_price(ticker)

    def get_info(self, ticker: str) -> dict:
        return self._inner.get_info(ticker)

    def get_index_constituents(self, index_ticker: str) -> list[str]:
        return self._inner.get_index_constituents(index_ticker)

    def get_constituent_histories(self, index_ticker: str, period: str = "2y") -> dict:
        return self._inner.get_constituent_histories(index_ticker, period)

    def get_index_fundamentals(self, index_ticker: str) -> dict:
        return self._inner.get_index_fundamentals(index_ticker)

    def get_index_holdings(self, index_ticker: str) -> list:
        return self._inner.get_index_holdings(index_ticker)
```

`wrap_providers` fertigstellen (die Market-Hälfte einsetzen):
```python
def wrap_providers(ecb, market, run: RunContext, store: SnapshotStore):
    """Umhüllt die echten Adapter mit ihren Caching-Decorators."""
    return CachingEcbProvider(ecb, run, store), CachingMarketProvider(market, run, store)
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/adapters/data/test_caching_market_provider.py tests/adapters/data/test_caching_ecb_provider.py -v`
Expected: PASS (alle).

- [ ] **Step 5: Commit**

```bash
git add adapters/data/caching_data_provider.py tests/adapters/data/test_caching_market_provider.py
git commit -m "feat(cache): CachingMarketProvider (Yahoo-Kurshistorie über Payload-Codec)"
```

---

### Task 7: TTL-Config + Verdrahtung im Composition-Root

**Files:**
- Modify: `config/settings.py` (TTL-Konstante ergänzen)
- Modify: `app/server.py:34-49` (`make_orchestrator`)
- Modify: `app/main.py:190-207` (`run_dashboard`)
- Test: `tests/adapters/data/test_wrap_providers.py`

**Interfaces:**
- Consumes: `wrap_providers` (Task 6), `CompositeSnapshotStore`, `JsonDatedHistory`, `RunContext`.
- Produces: `settings.SNAPSHOT_TTL_DAYS: int`. Verdrahtung: ECB + Market laufen in beiden Einstiegspunkten durch `wrap_providers`, mit einem **pro Lauf** frischen `RunContext(as_of=date.today())`. (`make_orchestrator` wird von `RunManager` pro Lauf aufgerufen → automatisch frisch; `run_dashboard` läuft je Aufruf einmal.)

- [ ] **Step 1: Failing test schreiben**

`tests/adapters/data/test_wrap_providers.py`:
```python
from datetime import date

from adapters.data.caching_data_provider import (
    CachingEcbProvider,
    CachingMarketProvider,
    wrap_providers,
)
from adapters.persistence.composite_snapshot_store import CompositeSnapshotStore
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory
from core.domain.run_context import RunContext


class _E:  # minimaler ECB-Doppelgänger (Duck-Typing reicht dem Decorator)
    def __getattr__(self, name):
        return lambda *a, **k: None


class _M:
    def __getattr__(self, name):
        return lambda *a, **k: None


def test_wrap_providers_liefert_beide_caching_decorators(tmp_path):
    run = RunContext(as_of=date(2026, 7, 1))
    store = CompositeSnapshotStore(InMemoryDatedHistory(), str(tmp_path / "b.json"))
    ecb, market = wrap_providers(_E(), _M(), run, store)
    assert isinstance(ecb, CachingEcbProvider)
    assert isinstance(market, CachingMarketProvider)


def test_settings_hat_ttl_konstante():
    import config.settings as settings
    assert isinstance(settings.SNAPSHOT_TTL_DAYS, int)
    assert settings.SNAPSHOT_TTL_DAYS >= 1
```

> Hinweis: `_E`/`_M` sind bewusst KEINE ABC-Subklassen — der Decorator delegiert per Duck-Typing, und dieser Test prüft nur die Verdrahtung (`isinstance` der Decorators + TTL-Konstante), nicht das Port-Interface (das deckt Task 5/6 ab).

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/data/test_wrap_providers.py -v`
Expected: FAIL (`AttributeError: module 'config.settings' has no attribute 'SNAPSHOT_TTL_DAYS'`).

- [ ] **Step 3: Implementieren**

In `config/settings.py` nach den API-Keys ergänzen:
```python
# Daten-Caching-Schicht: wie viele Tage ein persistierter Rohdaten-Snapshot ohne
# Live-Nachziehen wiederverwendet wird (Dedup ZWISCHEN Läufen). Default 1 =
# Wiederverwendung nur am selben Kalendertag. Innerhalb EINES Laufs garantiert
# ohnehin das In-Lauf-Memo Konsistenz (unabhängig von diesem Wert).
SNAPSHOT_TTL_DAYS = int(os.getenv("SNAPSHOT_TTL_DAYS", "1"))
```

In `app/server.py` — Importe ergänzen (bei den übrigen Adapter-Importen):
```python
from datetime import date

from adapters.persistence.composite_snapshot_store import CompositeSnapshotStore
from adapters.data.caching_data_provider import wrap_providers
from core.domain.run_context import RunContext
```
Pfad-Konstante bei den anderen `_..._PATH`-Konstanten ergänzen:
```python
# Rohdaten-Snapshot: Skalare in eine eigene DatedHistory-Datei (getrennt von der
# Yield-Spread-Backtest-Historie), Payloads in eine Blob-Datei.
_SNAPSHOT_SCALARS_PATH = os.path.join(os.path.dirname(__file__), "..", ".cache", "snapshot_scalars.json")
_SNAPSHOT_BLOBS_PATH   = os.path.join(os.path.dirname(__file__), "..", ".cache", "snapshot_blobs.json")
```
In `make_orchestrator` die `ecb=`/`market=`-Zeilen ersetzen:
```python
    require_keys()
    run_ctx = RunContext(as_of=date.today())
    snapshot_store = CompositeSnapshotStore(
        JsonDatedHistory(_SNAPSHOT_SCALARS_PATH), _SNAPSHOT_BLOBS_PATH,
    )
    ecb_cached, market_cached = wrap_providers(
        EurostatEcbProvider(EcbSdwProvider()), YahooFinanceProvider(), run_ctx, snapshot_store,
    )
    return TopDownOrchestrator(
        macro=FredDataProvider(FRED_API_KEY),
        ecb=ecb_cached,
        snb=FredSnbProvider(FRED_API_KEY),
        market=market_cached,
        bus=bus,
        sentiment=CnnFearGreedProvider(),
        history=JsonDatedHistory(_HISTORY_PATH),
        world_bank=WorldBankMarketCapProvider(),
        metal_spot=FmpMetalSpotProvider(),
    )
```
Analog in `app/main.py` `run_dashboard` — Importe ergänzen:
```python
from datetime import date  # falls noch nicht importiert

from adapters.persistence.composite_snapshot_store import CompositeSnapshotStore
from adapters.data.caching_data_provider import wrap_providers
from core.domain.run_context import RunContext
```
und im `run_dashboard`-Body vor dem `TopDownOrchestrator(...)`:
```python
    snapshot_scalars_path = os.path.join(os.path.dirname(__file__), "..", ".cache", "snapshot_scalars.json")
    snapshot_blobs_path   = os.path.join(os.path.dirname(__file__), "..", ".cache", "snapshot_blobs.json")
    run_ctx = RunContext(as_of=date.today())
    snapshot_store = CompositeSnapshotStore(JsonDatedHistory(snapshot_scalars_path), snapshot_blobs_path)
    ecb_cached, market_cached = wrap_providers(
        EurostatEcbProvider(EcbSdwProvider()), YahooFinanceProvider(), run_ctx, snapshot_store,
    )
```
und in der `TopDownOrchestrator(...)`-Konstruktion `ecb=EurostatEcbProvider(EcbSdwProvider())` → `ecb=ecb_cached` und `market=YahooFinanceProvider()` → `market=market_cached` ersetzen.

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/adapters/data/test_wrap_providers.py -v`
Expected: PASS.

Zusätzlich Import-Smoke (Verdrahtung bricht nicht beim Import, bleibt keyfrei):
Run: `python -c "import app.server; print('ok')"`
Expected: Ausgabe `ok` (kein `require_keys`-Fehler, da `make_orchestrator` nicht aufgerufen wird).

- [ ] **Step 5: Commit**

```bash
git add config/settings.py app/server.py app/main.py tests/adapters/data/test_wrap_providers.py
git commit -m "feat(cache): Verdrahtung ECB+Yahoo über wrap_providers + SNAPSHOT_TTL_DAYS"
```

---

### Task 8: Voller Testlauf + Logbuch

**Files:**
- Modify: `docs/open_todos.md`

- [ ] **Step 1: Gesamte Test-Suite grün?**

Run: `python -m pytest -q`
Expected: alle Tests grün (keine Regression durch die neue Schicht). Bei Rot: Ursache beheben, bevor es weitergeht — die Caching-Schicht darf bestehendes Verhalten nicht verändern (sie ist verhaltens-erhaltend, nur mit Memo/Persistenz davor).

- [ ] **Step 2: `.cache`-Artefakte ignoriert?**

Run: `git status --porcelain`
Expected: keine `.cache/snapshot_*.json` auftauchend. Falls doch: prüfen, ob `.cache/` bereits in `.gitignore` steht (die bestehenden `.cache/*.json` werden schon ignoriert) — sonst NICHT committen, sondern separat mit dem User klären.

- [ ] **Step 3: Logbuch-Eintrag**

In `docs/open_todos.md` einen Eintrag ergänzen (Format wie bestehende Einträge), sinngemäß:
```markdown
- [x] **Daten-Caching-Schicht v1 (Data Mart hinter den Ports)** — Lösung: Caching-Decorator
  hinter den Ports (Lazy+Memoize): RunContext (Point-in-Time+Dedup) + SnapshotStore-Port +
  CompositeSnapshotStore (Skalare→DatedHistoryPort wiederverwendet, Payloads→JSON-Blob) +
  dataframe_codec + CachingEcbProvider/CachingMarketProvider, verdrahtet für ECB-SDW (Skalar)
  und Yahoo-Kurshistorie (Payload). Spec: docs/superpowers/specs/2026-07-01-daten-caching-schicht-design.md.
  Offene Folge-Aufgaben:
  - Weitere Quellen je 1 PR umhängen (FRED, Eurostat-Direktpfade, Finnhub, Fear&Greed, FMP, SNB).
  - ECB dict/list-Rückgaben (get_yield_spreads/get_sovereign_yields/interest_rate_history) cachen.
  - Supabase-SnapshotStore-Adapter (aktuell nur JSON-Datei).
  - Per-namespace-TTL statt globalem SNAPSHOT_TTL_DAYS.
  - Backtest-Einstiegspunkte (replay/calibrate) auf RunContext(as_of=historisch) umstellen.
  - tz-aware DatetimeIndex im dataframe_codec verifizieren (yfinance liefert tz-aware).
```

- [ ] **Step 4: Commit**

```bash
git add docs/open_todos.md
git commit -m "docs(todos): Daten-Caching-Schicht v1 + Folge-Aufgaben protokolliert"
```

- [ ] **Step 5: Branch pushen + PR öffnen**

```bash
git push -u origin feat/daten-caching-schicht
```
PR-Beschreibung (Deutsch): **was** (Caching-Schicht hinter den Ports, v1 mit ECB+Yahoo), **warum** (Point-in-Time-Konsistenz, Dedup/Kosten, Offline-Resilienz, Backtest — ohne Agenten-Änderung), **wie** (Decorator + RunContext + SnapshotStore, DatedHistoryPort wiederverwendet). Auf den zweiten Blick des Users warten — **kein** Selbst-Merge.

---

## Self-Review (gegen die Spec)

- **§2 In-Scope Punkt 1 (RunContext):** Task 1. ✓
- **§2 Punkt 2 (SnapshotStore-Port):** Task 2. ✓
- **§2 Punkt 3 (JSON-Store) + §3 CompositeSnapshotStore (DatedHistoryPort-Wiederverwendung):** Task 3. ✓
- **§2 Punkt 5 + §3 dataframe_codec:** Task 4. ✓
- **§2 Punkt 4 (Decorator, ECB + Yahoo):** Task 5 (ECB) + Task 6 (Yahoo/Payload). ✓
- **§2 Punkt 6 (Verdrahtung) + §4 TTL:** Task 7. ✓
- **§3 Datenfluss (Memo→Store→Live, write-through, Offline-Fallback):** Task 5 `_cached` + Tests. ✓
- **§5 Fehlerbehandlung (nie neue Exception, Store-Write best effort):** `_cached` + `CompositeSnapshotStore.put`. ✓
- **§6 Tests (alle 6 Fälle):** Memo-Hit/Store-Hit/Live-Miss/Exception→last-known/leer+Exception→None/Point-in-Time verteilt über Task 5; Codec-Round-Trip Task 4; Store-Semantik Task 3. ✓
- **§7 Rollout (v1 = Gerüst + ECB + Yahoo; Rest Folge-PRs):** Tasks 1–7, Folge-Aufgaben in Task 8 Logbuch. ✓
- **§8 Entscheidungen (Yahoo in v1, DatedHistoryPort wiederverwenden):** Task 6 bzw. Task 3. ✓
- **Platzhalter-Scan:** keine TBD/TODO-Platzhalter; jeder Code-Step zeigt vollständigen Code. ✓
- **Typ-Konsistenz:** `SnapshotStore.get` liefert überall `Optional[tuple[date, Any]]`; `_cached(namespace, key, fetch, encode, decode)` einheitlich; `wrap_providers(ecb, market, run, store)` in Task 5 (Teil) → Task 6 (fertig) konsistent. ✓
