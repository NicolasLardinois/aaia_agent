# Zins-Richtung USA + EU + CH — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den `interest_rate_agent` so verdrahten, dass die Zinsrichtung (rising/falling/stable) für USA, EU und CH aus echten, datierten Leitzins-Historien nativer Quellen berechnet wird statt fix `"stable"` zu sein.

**Architecture:** Drei Provider liefern aktuellen Leitzins + datierte Historie aus key-freien nativen Quellen (FRED FEDFUNDS, ECB Data Portal FM-Dataset, SNB `data.snb.ch`). Der Agent baut daraus eine `InMemoryDatedHistory` und ruft die bestehende `_direction`-Logik.

**Tech Stack:** Python, `fredapi`, `requests`, Python-`csv`, pytest (unittest.mock).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-17-zins-richtung-usa-eu-ch-design.md`.
- History-Vertragsformat: `list[dict]`, Elemente `{"date": "YYYY-MM-DD", "rate": <float>}`, chronologisch ältester zuerst; bei Fehler/leer `[]`.
- Neue History-Port-Methoden sind **nicht-abstrakt mit Default `return []`** (bestehende Implementierer/Fakes dürfen NICHT brechen).
- Jede Quelle defensiv: `try/except` → aktueller Wert `None`, Historie `[]`.
- Verifizierte Identifier: FRED `FEDFUNDS`; ECB `FM.B.U2.EUR.4F.KR.MRR_FR.LEV` (Hauptrefinanzierungssatz, `format=csvdata`); SNB `data.snb.ch/api/cube/snboffzisa/data/csv/en`, Reihe `D0=="LZ"`.
- Branch `feat/zins-richtung`. Test-Runner: `python -m pytest ... -q`. Baseline vor diesem Plan: gesamte Suite grün (0 failed).

---

## Task 1: USA-Leitzins-Historie (FRED FEDFUNDS) + Port-Default

**Files:**
- Modify: `core/ports/data_provider.py` (Methode an `MacroDataProvider` anhängen)
- Modify: `adapters/data/fred_api.py` (Methode in `FredDataProvider`, nach `get_real_rate_history`)
- Test: `tests/adapters/test_fred_policy_rate.py` (Create)

**Interfaces:**
- Produces: `MacroDataProvider.get_policy_rate_history(self, years: int = 2) -> list[dict]` (Default `[]`); `FredDataProvider.get_policy_rate_history` (FEDFUNDS).

- [ ] **Step 1: Failing Test** — `tests/adapters/test_fred_policy_rate.py`:

```python
from unittest.mock import MagicMock

import pandas as pd

from adapters.data.fred_api import FredDataProvider


def _make_provider():
    p = FredDataProvider.__new__(FredDataProvider)
    p.fred = MagicMock()
    return p


def test_policy_rate_history_maps_and_drops_nan():
    p = _make_provider()
    idx = pd.date_range("2024-01-01", periods=3, freq="MS")
    p.fred.get_series.return_value = pd.Series([4.5, float("nan"), 4.75], index=idx)
    out = p.get_policy_rate_history(2)
    assert out == [
        {"date": "2024-01-01", "rate": 4.5},
        {"date": "2024-03-01", "rate": 4.75},
    ]


def test_policy_rate_history_uses_fedfunds():
    p = _make_provider()
    p.fred.get_series.return_value = pd.Series(
        [4.5], index=pd.date_range("2024-01-01", periods=1, freq="MS")
    )
    p.get_policy_rate_history(2)
    assert p.fred.get_series.call_args.args[0] == "FEDFUNDS"


def test_policy_rate_history_empty_on_failure():
    p = _make_provider()
    p.fred.get_series.side_effect = Exception("API down")
    assert p.get_policy_rate_history(2) == []
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/adapters/test_fred_policy_rate.py -q`. Erwartung: FAIL (Port-Default `[]` erfüllt Mapping/FEDFUNDS-Tests nicht).

- [ ] **Step 3: Port-Default** — in `core/ports/data_provider.py` in `class MacroDataProvider` (NICHT `@abstractmethod`) anhängen:

```python
    def get_policy_rate_history(self, years: int = 2) -> list[dict]:
        """Datierte Leitzins-Historie [{"date","rate"}, ...]. Default: leer."""
        return []
```

- [ ] **Step 4: FRED-Implementierung** — in `adapters/data/fred_api.py` in `class FredDataProvider` direkt nach `get_real_rate_history`:

```python
    def get_policy_rate_history(self, years: int = 2) -> list[dict]:
        """FEDFUNDS der letzten `years` Jahre.
        Rueckgabe: [{"date":"YYYY-MM-DD","rate":float}, ...] (aeltester zuerst). Fehler/leer → []."""
        try:
            start = f"{datetime.utcnow().year - years}-01-01"
            series = self.fred.get_series("FEDFUNDS", observation_start=start).dropna()
            return [
                {"date": ts.strftime("%Y-%m-%d"), "rate": round(float(v), 3)}
                for ts, v in series.items()
            ]
        except Exception:
            return []
```

- [ ] **Step 5: Run → PASS** — `python -m pytest tests/adapters/test_fred_policy_rate.py -q`. Erwartung: 3 passed.

- [ ] **Step 6: Commit** — `git add core/ports/data_provider.py adapters/data/fred_api.py tests/adapters/test_fred_policy_rate.py && git commit -m "feat(fred): get_policy_rate_history (FEDFUNDS) + MacroDataProvider-Default"`

---

## Task 2: EU-Leitzins + Historie (ECB Data Portal, csvdata) + Port-Default

**Files:**
- Modify: `core/ports/data_provider.py` (Methode an `EcbDataProvider` anhängen)
- Modify: `adapters/data/ecb_sdw.py` (`get_interest_rate` ersetzen + `get_interest_rate_history` + Helfer)
- Test: `tests/adapters/test_ecb_interest_rate.py` (Create)

**Interfaces:**
- Consumes: `requests` (bereits in `ecb_sdw.py` genutzt).
- Produces: `EcbDataProvider.get_interest_rate_history(self, years: int = 2) -> list[dict]` (Default `[]`); `EcbSdwProvider.get_interest_rate()` (echt), `EcbSdwProvider.get_interest_rate_history()`.

ECB csvdata-Format (verifiziert): CSV mit Spalten u. a. `TIME_PERIOD` (z. B. `2026-06-17`) und `OBS_VALUE` (z. B. `2.4`). Endpoint: `https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.MRR_FR.LEV?format=csvdata` (+ `&lastNObservations=1` bzw. `&startPeriod=YYYY-MM-DD`).

- [ ] **Step 1: Failing Test** — `tests/adapters/test_ecb_interest_rate.py`:

```python
from unittest.mock import MagicMock, patch

from adapters.data.ecb_sdw import EcbSdwProvider

_CSV = (
    "KEY,FREQ,TIME_PERIOD,OBS_VALUE\r\n"
    "FM...,B,2026-04-01,2.15\r\n"
    "FM...,B,2026-06-17,2.4\r\n"
)


def _resp(text, status=200):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def test_get_interest_rate_returns_latest():
    p = EcbSdwProvider()
    with patch("adapters.data.ecb_sdw.requests.get", return_value=_resp(_CSV)):
        assert p.get_interest_rate() == 2.4


def test_get_interest_rate_history_maps_rows():
    p = EcbSdwProvider()
    with patch("adapters.data.ecb_sdw.requests.get", return_value=_resp(_CSV)):
        assert p.get_interest_rate_history(2) == [
            {"date": "2026-04-01", "rate": 2.15},
            {"date": "2026-06-17", "rate": 2.4},
        ]


def test_get_interest_rate_none_on_failure():
    p = EcbSdwProvider()
    with patch("adapters.data.ecb_sdw.requests.get", side_effect=Exception("net")):
        assert p.get_interest_rate() is None
        assert p.get_interest_rate_history(2) == []
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/adapters/test_ecb_interest_rate.py -q`. Erwartung: FAIL (`get_interest_rate` ist Stub `None`; `get_interest_rate_history` existiert noch nicht bzw. Default `[]`).

- [ ] **Step 3: Port-Default** — in `core/ports/data_provider.py` in `class EcbDataProvider` (NICHT `@abstractmethod`) anhängen:

```python
    def get_interest_rate_history(self, years: int = 2) -> list[dict]:
        """Datierte EZB-Leitzins-Historie [{"date","rate"}, ...]. Default: leer."""
        return []
```

- [ ] **Step 4: ECB-Implementierung** — in `adapters/data/ecb_sdw.py`: oben `import csv` ergänzen; die Konstante und Methoden hinzufügen; den Stub `get_interest_rate` (in der Stub-Sektion) entfernen/ersetzen.

```python
import csv  # oben bei den Imports

# Konstante (bei den anderen _BASE/_IRS_BASE-Konstanten):
_KEYRATE_BASE = (
    "https://data-api.ecb.europa.eu/service/data/FM/"
    "B.U2.EUR.4F.KR.MRR_FR.LEV?format=csvdata"
)

# In der Klasse EcbSdwProvider (get_interest_rate aus der Stub-Sektion ENTFERNEN
# und stattdessen diese beiden Methoden + Helfer ergaenzen):

    def get_interest_rate(self) -> Optional[float]:
        rows = self._fetch_keyrate_rows(self._KEYRATE_URL("&lastNObservations=1"))
        return rows[-1][1] if rows else None

    def get_interest_rate_history(self, years: int = 2) -> list[dict]:
        from datetime import date
        start = f"{date.today().year - years}-01-01"
        rows = self._fetch_keyrate_rows(self._KEYRATE_URL(f"&startPeriod={start}"))
        return [{"date": d, "rate": r} for d, r in rows]

    @staticmethod
    def _KEYRATE_URL(suffix: str) -> str:
        return _KEYRATE_BASE + suffix

    def _fetch_keyrate_rows(self, url: str) -> list:
        """Liefert [(date_str, rate_float), ...] (aeltester zuerst) aus ECB-csvdata. Fehler → []."""
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            reader = csv.DictReader(resp.text.splitlines())
            out = []
            for row in reader:
                d = row.get("TIME_PERIOD")
                v = row.get("OBS_VALUE")
                if d and v not in (None, ""):
                    out.append((d, round(float(v), 3)))
            out.sort(key=lambda x: x[0])
            return out
        except Exception:
            return []
```

> Hinweis: Im Diff den alten `def get_interest_rate(self) -> Optional[float]: return None` aus der „Stubs"-Sektion entfernen (wird durch die echte Methode ersetzt). Die anderen Stubs bleiben.

- [ ] **Step 5: Run → PASS** — `python -m pytest tests/adapters/test_ecb_interest_rate.py -q`. Erwartung: 3 passed.

- [ ] **Step 6: Commit** — `git add core/ports/data_provider.py adapters/data/ecb_sdw.py tests/adapters/test_ecb_interest_rate.py && git commit -m "feat(ecb): echter Leitzins (MRR_FR) + Historie via ECB csvdata + Port-Default"`

---

## Task 3: CH-Leitzins + Historie (SNB data.snb.ch, Reihe LZ) + Port-Default

**Files:**
- Modify: `core/ports/data_provider.py` (Methode an `SnbDataProvider` anhängen)
- Modify: `adapters/data/fred_snb.py` (`get_interest_rate` ersetzen + `get_interest_rate_history` + Helfer; `import requests`, `import csv`)
- Test: `tests/adapters/test_snb_interest_rate.py` (Create)

**Interfaces:**
- Produces: `SnbDataProvider.get_interest_rate_history(self, years: int = 2) -> list[dict]` (Default `[]`); `FredSnbProvider.get_interest_rate()` (echt, SNB-LZ), `FredSnbProvider.get_interest_rate_history()`.

SNB-CSV (verifiziert): Endpoint `https://data.snb.ch/api/cube/snboffzisa/data/csv/en`; semikolon-getrennt, alle Felder in `"..."`; Header `"Date";"D0";"Value"`; Datum `YYYY-MM`; Leitzins-Reihe `D0=="LZ"`; Zeile z. B. `"2026-04";"LZ";"2.15"`.

- [ ] **Step 1: Failing Test** — `tests/adapters/test_snb_interest_rate.py`:

```python
from unittest.mock import MagicMock, patch

from adapters.data.fred_snb import FredSnbProvider

_CSV = (
    '"CubeId";"snboffzisa"\r\n'
    '"PublishingDate";"2026-05-21 09:00"\r\n'
    "\r\n"
    '"Date";"D0";"Value"\r\n'
    '"2026-02";"UG0";"1.0"\r\n'
    '"2026-02";"LZ";"1.75"\r\n'
    '"2026-04";"LZ";"2.15"\r\n'
)


def _provider():
    p = FredSnbProvider.__new__(FredSnbProvider)
    return p


def _resp(text):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def test_get_interest_rate_latest_lz():
    p = _provider()
    with patch("adapters.data.fred_snb.requests.get", return_value=_resp(_CSV)):
        assert p.get_interest_rate() == 2.15


def test_get_interest_rate_history_only_lz_iso_dates():
    p = _provider()
    with patch("adapters.data.fred_snb.requests.get", return_value=_resp(_CSV)):
        assert p.get_interest_rate_history(2) == [
            {"date": "2026-02-01", "rate": 1.75},
            {"date": "2026-04-01", "rate": 2.15},
        ]


def test_get_interest_rate_none_on_failure():
    p = _provider()
    with patch("adapters.data.fred_snb.requests.get", side_effect=Exception("net")):
        assert p.get_interest_rate() is None
        assert p.get_interest_rate_history(2) == []
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/adapters/test_snb_interest_rate.py -q`. Erwartung: FAIL (`get_interest_rate` Stub `None`; History-Methode Default `[]`).

- [ ] **Step 3: Port-Default** — in `core/ports/data_provider.py` in `class SnbDataProvider` (NICHT `@abstractmethod`) anhängen:

```python
    def get_interest_rate_history(self, years: int = 2) -> list[dict]:
        """Datierte SNB-Leitzins-Historie [{"date","rate"}, ...]. Default: leer."""
        return []
```

- [ ] **Step 4: SNB-Implementierung** — in `adapters/data/fred_snb.py`: `import csv` und `import requests` oben ergänzen; Konstante + Methoden hinzufügen; den Stub `get_interest_rate` entfernen/ersetzen.

```python
import csv       # oben bei den Imports
import requests  # oben bei den Imports

_SNB_OFFZIS_URL = "https://data.snb.ch/api/cube/snboffzisa/data/csv/en"

# In der Klasse FredSnbProvider (get_interest_rate aus der Stub-Sektion ENTFERNEN,
# diese Methoden + Helfer ergaenzen):

    def get_interest_rate(self) -> Optional[float]:
        rows = self._fetch_snb_policy_rate()
        return rows[-1][1] if rows else None

    def get_interest_rate_history(self, years: int = 2) -> list[dict]:
        from datetime import date
        cutoff = date.today().year - years
        rows = self._fetch_snb_policy_rate()
        return [
            {"date": d, "rate": r} for d, r in rows
            if int(d[:4]) >= cutoff
        ]

    def _fetch_snb_policy_rate(self) -> list:
        """Liefert [(iso_date, rate), ...] (aeltester zuerst) der SNB-Reihe LZ aus snboffzisa. Fehler → []."""
        try:
            resp = requests.get(_SNB_OFFZIS_URL, timeout=10)
            resp.raise_for_status()
            lines = resp.text.splitlines()
            # Datenbereich beginnt bei der Header-Zeile mit Date;D0;Value
            start = next(
                i for i, ln in enumerate(lines)
                if ln.replace('"', "").startswith("Date;D0;Value")
            )
            reader = csv.DictReader(lines[start:], delimiter=";", quotechar='"')
            out = []
            for row in reader:
                if row.get("D0") == "LZ":
                    val = row.get("Value")
                    ym = row.get("Date")
                    if val not in (None, "") and ym:
                        out.append((f"{ym}-01", round(float(val), 3)))
            out.sort(key=lambda x: x[0])
            return out
        except Exception:
            return []
```

> Hinweis: Im Diff den alten `def get_interest_rate(self) -> Optional[float]: return None` aus der „Stubs"-Sektion entfernen. Klassenname `FredSnbProvider` bleibt (Datenquelle jetzt gemischt FRED+SNB — kurzer Kommentar an der Klasse).

- [ ] **Step 5: Run → PASS** — `python -m pytest tests/adapters/test_snb_interest_rate.py -q`. Erwartung: 3 passed.

- [ ] **Step 6: Commit** — `git add core/ports/data_provider.py adapters/data/fred_snb.py tests/adapters/test_snb_interest_rate.py && git commit -m "feat(snb): echter SNB-Leitzins (LZ) + Historie via data.snb.ch + Port-Default"`

---

## Task 4: Agent-Verdrahtung (InMemoryDatedHistory + _direction)

**Files:**
- Modify: `agents/market_cockpit/macro/interest_rate_agent.py` (Import + `run()`)
- Test: `tests/agents/market_cockpit/macro/test_interest_rate_direction.py` (Create)

**Interfaces:**
- Consumes: `get_policy_rate_history` (Task 1), `EcbDataProvider.get_interest_rate_history` (Task 2), `SnbDataProvider.get_interest_rate_history` (Task 3); `InMemoryDatedHistory(data: dict[str, list[tuple[date, float]]])`; `_direction(current, history, series, months_back=3, today=None)`.

- [ ] **Step 1: Failing Test** — `tests/agents/market_cockpit/macro/test_interest_rate_direction.py`:

```python
import asyncio
from unittest.mock import MagicMock

from agents.market_cockpit.macro.interest_rate_agent import InterestRateAgent
from core.domain.models import Signal


def _macro():
    m = MagicMock()
    m.get_economic_state.return_value = {"fed_rate": 5.0, "inflation": 3.0}
    # Vor ~3 Monaten 4.0 → heute 5.0 ⇒ steigend
    m.get_policy_rate_history.return_value = [
        {"date": "2025-01-01", "rate": 4.0},
        {"date": "2026-05-01", "rate": 5.0},
    ]
    return m


def _ecb():
    e = MagicMock()
    e.get_interest_rate.return_value = 2.4
    e.get_balance_sheet_growth.return_value = None
    e.get_interest_rate_history.return_value = [
        {"date": "2025-01-01", "rate": 2.0},
        {"date": "2026-05-01", "rate": 2.4},
    ]
    return e


def _snb():
    s = MagicMock()
    s.get_interest_rate.return_value = 1.0
    s.get_balance_sheet_growth.return_value = None
    s.get_interest_rate_history.return_value = [
        {"date": "2025-01-01", "rate": 2.0},
        {"date": "2026-05-01", "rate": 1.0},
    ]
    return s


def test_directions_aus_historie():
    agent = InterestRateAgent(_macro(), _ecb(), _snb(), MagicMock())
    snap = asyncio.run(agent.run())
    assert snap.usa.rate_direction == "rising"
    assert snap.eurozone.rate_direction == "rising"
    assert snap.switzerland.rate_direction == "falling"


def test_ohne_historie_bleibt_stable():
    macro = _macro(); macro.get_policy_rate_history.return_value = []
    ecb = _ecb(); ecb.get_interest_rate_history.return_value = []
    snb = _snb(); snb.get_interest_rate_history.return_value = []
    agent = InterestRateAgent(macro, ecb, snb, MagicMock())
    snap = asyncio.run(agent.run())
    assert snap.usa.rate_direction == "stable"
    assert snap.eurozone.rate_direction == "stable"
    assert snap.switzerland.rate_direction == "stable"
```

> Hinweis: Der Test ist robust gegenüber „heute", solange der jüngste Historien-Punkt (2026-05-01) ≤ heute und der Referenzpunkt (heute − 3 Monate) ≥ 2025-01-01 liegt — beides gilt im Projektzeitraum (2026). Sollte das Datum driften, den jüngsten Punkt auf den Vormonat setzen.

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/agents/market_cockpit/macro/test_interest_rate_direction.py -q`. Erwartung: FAIL (aktuell `history=None` → alle `"stable"`).

- [ ] **Step 3: Implementierung** — in `agents/market_cockpit/macro/interest_rate_agent.py`:

(a) Import ergänzen (zu den vorhandenen Imports):
```python
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory
```

(b) In `run()` die drei Historien holen — den bestehenden `asyncio.gather`-Block um drei Aufrufe erweitern (oder einen zweiten `gather`); konkret nach dem bestehenden `_safe(...)`-Block ergänzen:
```python
        usa_hist, eu_hist, ch_hist = await asyncio.gather(
            asyncio.to_thread(self.macro.get_policy_rate_history, 2),
            asyncio.to_thread(self.ecb.get_interest_rate_history, 2),
            asyncio.to_thread(self.snb.get_interest_rate_history, 2),
            return_exceptions=True,
        )
        def _safe_hist(h): return [] if isinstance(h, Exception) or not h else h

        def _to_pairs(hist):
            pairs = []
            for r in hist:
                try:
                    pairs.append((date.fromisoformat(r["date"]), float(r["rate"])))
                except Exception:
                    continue
            return pairs

        history = InMemoryDatedHistory({
            "fed_rate": _to_pairs(_safe_hist(usa_hist)),
            "ecb_rate": _to_pairs(_safe_hist(eu_hist)),
            "snb_rate": _to_pairs(_safe_hist(ch_hist)),
        })
        _today = date.today()
```

(c) Die drei `_direction`-Aufrufe (aktuell `history=None`) ersetzen durch:
```python
        usa_dir = _direction(fed_rate, history=history, series="fed_rate", today=_today)
        eu_dir  = _direction(ecb_rate, history=history, series="ecb_rate", today=_today)
        ch_dir  = _direction(snb_rate, history=history, series="snb_rate", today=_today)
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/agents/market_cockpit/macro/test_interest_rate_direction.py -q`. Erwartung: 2 passed.

- [ ] **Step 5: Gesamt-Regression** — `python -m pytest -q`. Erwartung: 0 failed (neue Tests dazu; bestehende interest_rate-/Provider-Tests weiterhin grün — die neuen Port-Methoden sind nicht-abstrakt, brechen keine Fakes). Bei Fehlern: superpowers:systematic-debugging.

- [ ] **Step 6: Commit** — `git add agents/market_cockpit/macro/interest_rate_agent.py tests/agents/market_cockpit/macro/test_interest_rate_direction.py && git commit -m "feat(interest_rate): echte Richtung USA/EU/CH via DatedHistory (P3.7)"`

---

## Abdeckung (Spec → Task)

| Spec-Element | Task |
|---|---|
| USA-Leitzins-Historie (FEDFUNDS) | Task 1 |
| EU `get_interest_rate` (echt) + Historie (ECB FM csvdata) | Task 2 |
| CH `get_interest_rate` (echt) + Historie (SNB `data.snb.ch` LZ) | Task 3 |
| Port-History-Methoden nicht-abstrakt (Default `[]`) | Task 1/2/3 |
| Agent-Verdrahtung (InMemoryDatedHistory → `_direction`) | Task 4 |
| Defensive Fehlerbehandlung je Quelle | Task 1–3 |
| Tests (Quelle gemockt) + Richtung | Task 1–4 |
| Gesamtsuite grün | Task 4, Step 5 |

## Manuelle Live-Verifikation (optional, nach Merge)

```bash
python -c "from adapters.data.ecb_sdw import EcbSdwProvider as E; e=E(); print('ECB', e.get_interest_rate(), len(e.get_interest_rate_history(2)))"
python -c "from adapters.data.fred_snb import FredSnbProvider as S; s=S.__new__(S); print('SNB', s.get_interest_rate(), len(s.get_interest_rate_history(2)))"
```
Erwartung: ECB ~2.4 mit Historie; SNB ~2.15 mit Historie.
