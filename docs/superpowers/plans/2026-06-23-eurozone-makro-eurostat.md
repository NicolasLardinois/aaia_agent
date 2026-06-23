# Eurozone-Makro Slice 1 (Eurostat-Realwirtschaft) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** EU-Realwirtschaft (HICP, Kern-HICP, PPI, reales BIP-Wachstum, Arbeitslosenquote) als echte Eurostat-Datenquelle anbinden — als Decorator über `EcbDataProvider` — sodass EU-Inflation und EU-BIP reale Signale liefern.

**Architektur:** Hexagonal. Neuer Adapter `adapters/data/eurostat.py`: `EurostatEcbProvider(EcbDataProvider)` implementiert die 5 Realwirtschafts-Methoden via Eurostat (HTTP, JSON-stat) und delegiert alle übrigen Methoden an einen darunterliegenden `EcbDataProvider` (real `EcbSdwProvider`). I/O im Adapter; JSON-stat-Extraktion ist eine reine, separat getestete Funktion.

**Tech-Stack:** Python, `requests`, pytest.

Spec: `docs/superpowers/specs/2026-06-23-eurozone-makro-eurostat-design.md`.

## Global Constraints

- Sprache: Code-Kommentare + Commit-Messages auf **Deutsch**. Commit-Trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **TDD verpflichtend:** erst der fehlschlagende Test, dann Implementierung.
- Tests **offline-sicher**: `tests/conftest.py` blockt echtes `requests`; Netz wird per `patch("adapters.data.eurostat.requests.get", …)` gemockt.
- **Moderne Type-Hints** `float | None` (kein `Optional[...]`).
- **Jüngste befüllte Beobachtung** = Wert beim **größten Integer-Key** im JSON-stat-`value`-Objekt (die jüngste Periode ist oft unveröffentlicht und fehlt im `value`). Nicht den höchsten Zeit-Index blind nehmen.
- **`lastTimePeriod=6`** in jeder Abfrage (stellt sicher, dass eine befüllte Periode im Fenster liegt).
- **Sanity-Caps:** Raten (CPI/Core/PPI/BIP) `-50.0 … 50.0`; Arbeitslosenquote `0.0 … 100.0`. Außerhalb → `None`. Rundung auf **1 Nachkommastelle**.
- **`logging.warning`** bei Netz-/HTTP-Fehler, Strukturbruch (`value` leer/unparsebar) und implausiblem Wert (Beobachtbarkeit, wie CNN-Adapter PR #34).
- **Verifizierte Eurostat-Codes (2026-06-23)** — exakt so verdrahten:
  - `get_cpi`: `prc_hicp_manr`, `{coicop=CP00, unit=RCH_A, geo=EA20}`
  - `get_core_cpi`: `prc_hicp_manr`, `{coicop=TOT_X_NRG_FOOD, unit=RCH_A, geo=EA20}`
  - `get_ppi`: `sts_inppd_m`, `{indic_bt=PRC_PRR_DOM, nace_r2=B-E36, s_adj=NSA, unit=PCH_SM, geo=EA20}`
  - `get_gdp_growth`: `namq_10_gdp`, `{na_item=B1GQ, unit=CLV_PCH_SM, s_adj=SCA, geo=EA20}`
  - `get_unemployment`: `une_rt_m`, `{sex=T, age=TOTAL, unit=PC_ACT, s_adj=SA, geo=EA21}` ← **EA21**, nicht EA20.
- Git: Feature-Branch `feat/eurozone-makro-eurostat`, kein Merge nach `master`. Nur explizite Pfade stagen (kein `git add -A`).

---

## Dateienübersicht

**Neu:**
- `adapters/data/eurostat.py` — `_parse_jsonstat_latest`, `_fetch_latest`, `EurostatEcbProvider`.
- `tests/adapters/test_eurostat.py` — Tests für Parse, die 5 Methoden, Delegation.

**Geändert:**
- `app/main.py` — `ecb=EurostatEcbProvider(EcbSdwProvider())` in `run_dashboard`.
- `app/server.py` — dito in `make_orchestrator`.
- `docs/open_todos.md` — Einträge abhaken + PMI/Geldmenge-Folge-Tasks.

**Nicht geändert:** Agenten-Logik (inflation/gdp/money_supply), Port-Datei, `EcbSdwProvider`.

---

### Task 1: Reine Extraktionsfunktion `_parse_jsonstat_latest`

**Files:**
- Create: `adapters/data/eurostat.py` (zunächst nur die Funktion)
- Test: `tests/adapters/test_eurostat.py`

**Interfaces:**
- Produces: `_parse_jsonstat_latest(data: dict) -> float | None` — jüngster befüllter Wert (größter Integer-Key in `data["value"]`); `None` bei fehlendem/leerem/unparsebarem `value`.

- [ ] **Step 1: Failing Tests schreiben** — `tests/adapters/test_eurostat.py`

```python
"""TDD-Tests fuer den Eurostat-Adapter (EurostatEcbProvider) und _parse_jsonstat_latest."""
from unittest.mock import patch, MagicMock

from adapters.data.eurostat import _parse_jsonstat_latest


# ── _parse_jsonstat_latest (rein, kein Netz) ───────────────────────────────
def test_parse_nimmt_groessten_integer_key():
    # value-Keys sind Positions-Indizes; die juengste BEFUELLTE Beobachtung
    # hat den groessten Key. "5" (juengste Periode) fehlt absichtlich (unveroeffentlicht).
    data = {"value": {"0": -2.1, "1": -2.2, "4": 4.9}}
    assert _parse_jsonstat_latest(data) == 4.9


def test_parse_einzelne_beobachtung():
    assert _parse_jsonstat_latest({"value": {"0": 2.0}}) == 2.0


def test_parse_leeres_value_none():
    assert _parse_jsonstat_latest({"value": {}}) is None


def test_parse_fehlendes_value_none():
    assert _parse_jsonstat_latest({}) is None
    assert _parse_jsonstat_latest({"value": None}) is None


def test_parse_nicht_numerisch_none():
    assert _parse_jsonstat_latest({"value": {"0": "abc"}}) is None
```

- [ ] **Step 2: Test läuft (rot)**

Run: `python -m pytest tests/adapters/test_eurostat.py -q`
Expected: FAIL — `ImportError: cannot import name '_parse_jsonstat_latest'`.

- [ ] **Step 3: Funktion implementieren** — `adapters/data/eurostat.py`

```python
"""Eurostat-Adapter fuer die EU-Realwirtschaft (HICP, Kern-HICP, PPI, reales BIP,
Arbeitslosenquote) als Decorator ueber EcbDataProvider.

Datenquelle: Eurostat Dissemination API (JSON-stat 2.0), frei, kein API-Key.
Besonderheiten (gegen echte Antworten verifiziert 2026-06-23):
- Mit dem passenden unit-Code liefert Eurostat die Jahresrate DIREKT (kein YoY-Rechnen).
- Die juengste Zeitperiode ist oft noch unveroeffentlicht und fehlt dann im value-Objekt
  (steht in positions-with-no-data) → wir nehmen die juengste BEFUELLTE Beobachtung
  (groesster Integer-Key in value).
- Datasets nutzen unterschiedliche Euroraum-Codes: HICP/PPI/BIP=EA20, Arbeitslosigkeit=EA21.
"""
import logging

import requests

from core.ports.data_provider import EcbDataProvider

_log = logging.getLogger(__name__)

_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"


def _parse_jsonstat_latest(data: dict) -> float | None:
    """Rein: juengster befuellter Wert aus dem JSON-stat-value-Objekt.

    value bildet Positions-Index (als String) auf Beobachtung ab; bei single-value-
    Dimensionen entspricht die Position dem Zeit-Index (aelteste=0 … juengste=N).
    Die juengste befuellte Beobachtung ist daher der groesste Integer-Key.
    None bei fehlendem/leerem value oder nicht-numerischem Wert.
    """
    value = data.get("value")
    if not isinstance(value, dict) or not value:
        return None
    try:
        latest_key = max(value, key=int)
        return float(value[latest_key])
    except (ValueError, TypeError):
        return None
```

- [ ] **Step 4: Test läuft (grün)**

Run: `python -m pytest tests/adapters/test_eurostat.py -q`
Expected: PASS (5 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add adapters/data/eurostat.py tests/adapters/test_eurostat.py
git commit -m "feat(macro): _parse_jsonstat_latest — juengste befuellte Eurostat-Beobachtung

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Adapter `EurostatEcbProvider` (Fetch-Helfer, 5 Methoden, Delegation)

**Files:**
- Modify: `adapters/data/eurostat.py`
- Test: `tests/adapters/test_eurostat.py`

**Interfaces:**
- Consumes: `_parse_jsonstat_latest` (Task 1); Port `EcbDataProvider`.
- Produces:
  - `_fetch_latest(dataset: str, params: dict, lo: float, hi: float) -> float | None` — Eurostat-Abfrage (`lastTimePeriod=6`), Parse, Sanity-Cap `[lo, hi]`, Rundung 1 Stelle; Fehler/Strukturbruch/implausibel → `logging.warning` → `None`.
  - `class EurostatEcbProvider(EcbDataProvider)` mit `__init__(self, base: EcbDataProvider)`; echte `get_cpi/get_core_cpi/get_ppi/get_gdp_growth/get_unemployment`; alle übrigen Methoden delegieren an `self._base`.

- [ ] **Step 1: Failing Tests schreiben** — an `tests/adapters/test_eurostat.py` anhängen

```python
# ── Fetch-Response-Helfer ──────────────────────────────────────────────────
def _resp(payload):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    return r


_GET = "adapters.data.eurostat.requests.get"


# ── Die 5 echten Methoden (gemocktes requests.get) ─────────────────────────
def test_get_cpi_liefert_jahresrate_und_richtige_codes():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"0": 2.0}})) as m:
        prov = EurostatEcbProvider(MagicMock())
        assert prov.get_cpi() == 2.0
    url = m.call_args.args[0]
    params = m.call_args.kwargs["params"]
    assert "prc_hicp_manr" in url
    assert params["coicop"] == "CP00" and params["unit"] == "RCH_A" and params["geo"] == "EA20"
    assert params["lastTimePeriod"] == 6


def test_get_core_cpi_codes():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"0": 2.3}})) as m:
        assert EurostatEcbProvider(MagicMock()).get_core_cpi() == 2.3
    params = m.call_args.kwargs["params"]
    assert params["coicop"] == "TOT_X_NRG_FOOD" and params["geo"] == "EA20"


def test_get_ppi_codes():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"3": 1.9, "4": 4.9}})) as m:
        assert EurostatEcbProvider(MagicMock()).get_ppi() == 4.9   # groesster Key
    url = m.call_args.args[0]
    params = m.call_args.kwargs["params"]
    assert "sts_inppd_m" in url
    assert params["indic_bt"] == "PRC_PRR_DOM" and params["nace_r2"] == "B-E36"
    assert params["s_adj"] == "NSA" and params["unit"] == "PCH_SM" and params["geo"] == "EA20"


def test_get_gdp_growth_codes():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"0": 0.3}})) as m:
        assert EurostatEcbProvider(MagicMock()).get_gdp_growth() == 0.3
    url = m.call_args.args[0]
    params = m.call_args.kwargs["params"]
    assert "namq_10_gdp" in url
    assert params["na_item"] == "B1GQ" and params["unit"] == "CLV_PCH_SM"
    assert params["s_adj"] == "SCA" and params["geo"] == "EA20"


def test_get_unemployment_codes_nutzt_ea21():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"4": 6.3}})) as m:
        assert EurostatEcbProvider(MagicMock()).get_unemployment() == 6.3
    url = m.call_args.args[0]
    params = m.call_args.kwargs["params"]
    assert "une_rt_m" in url
    assert params["sex"] == "T" and params["age"] == "TOTAL"
    assert params["unit"] == "PC_ACT" and params["s_adj"] == "SA"
    assert params["geo"] == "EA21"   # Stolperstein: NICHT EA20


def test_rundet_auf_eine_stelle():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"0": 2.34}})):
        assert EurostatEcbProvider(MagicMock()).get_cpi() == 2.3


def test_implausibler_wert_none():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"0": 999.0}})):
        assert EurostatEcbProvider(MagicMock()).get_cpi() is None


def test_netzfehler_none():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, side_effect=ConnectionError("boom")):
        assert EurostatEcbProvider(MagicMock()).get_gdp_growth() is None


# ── Decorator-Delegation: nicht-Eurostat-Methoden gehen an base ────────────
def test_delegiert_nicht_eurostat_methoden_an_base():
    from adapters.data.eurostat import EurostatEcbProvider
    base = MagicMock()
    base.get_yield_spreads.return_value = {"10y2y": 0.5, "10y3m": 0.4}
    base.get_pmi.return_value = None
    prov = EurostatEcbProvider(base)

    assert prov.get_yield_spreads() == {"10y2y": 0.5, "10y3m": 0.4}
    base.get_yield_spreads.assert_called_once()
    assert prov.get_pmi() is None
    base.get_pmi.assert_called_once()
    prov.get_interest_rate()
    base.get_interest_rate.assert_called_once()
    prov.get_m3_growth()
    base.get_m3_growth.assert_called_once()
    prov.get_sovereign_yields()
    base.get_sovereign_yields.assert_called_once()
```

- [ ] **Step 2: Test läuft (rot)**

Run: `python -m pytest tests/adapters/test_eurostat.py -q`
Expected: FAIL — `ImportError: cannot import name 'EurostatEcbProvider'`.

- [ ] **Step 3: Implementierung ergänzen** — in `adapters/data/eurostat.py` ans Datei-Ende anhängen

```python
def _fetch_latest(dataset: str, params: dict, lo: float, hi: float) -> float | None:
    """Eurostat-Abfrage → juengste befuellte Beobachtung, Sanity-Cap [lo, hi], Rundung 1 Stelle.
    Jeder Fehler/Strukturbruch/implausibler Wert → logging.warning → None (Beobachtbarkeit)."""
    full = {"format": "JSON", "lang": "EN", "lastTimePeriod": 6, **params}
    try:
        resp = requests.get(f"{_BASE}/{dataset}", params=full, timeout=10)
        resp.raise_for_status()
        raw = _parse_jsonstat_latest(resp.json())
    except Exception as exc:
        _log.warning("Eurostat %s nicht abrufbar (%s) — UNAVAILABLE", dataset, exc)
        return None
    if raw is None:
        _log.warning("Eurostat %s: keine befuellte Beobachtung (Strukturbruch?) — UNAVAILABLE", dataset)
        return None
    if not (lo <= raw <= hi):
        _log.warning("Eurostat %s: implausibler Wert %s ausserhalb [%s, %s] — UNAVAILABLE",
                     dataset, raw, lo, hi)
        return None
    return round(raw, 1)


class EurostatEcbProvider(EcbDataProvider):
    """EcbDataProvider-Decorator: EU-Realwirtschaft via Eurostat, Rest an base delegiert."""

    def __init__(self, base: EcbDataProvider):
        self._base = base

    # ── Echt via Eurostat (verifizierte Codes, 2026-06-23) ──────────────────
    def get_cpi(self) -> float | None:
        return _fetch_latest("prc_hicp_manr",
                             {"coicop": "CP00", "unit": "RCH_A", "geo": "EA20"}, -50.0, 50.0)

    def get_core_cpi(self) -> float | None:
        return _fetch_latest("prc_hicp_manr",
                             {"coicop": "TOT_X_NRG_FOOD", "unit": "RCH_A", "geo": "EA20"}, -50.0, 50.0)

    def get_ppi(self) -> float | None:
        return _fetch_latest("sts_inppd_m",
                             {"indic_bt": "PRC_PRR_DOM", "nace_r2": "B-E36", "s_adj": "NSA",
                              "unit": "PCH_SM", "geo": "EA20"}, -50.0, 50.0)

    def get_gdp_growth(self) -> float | None:
        return _fetch_latest("namq_10_gdp",
                             {"na_item": "B1GQ", "unit": "CLV_PCH_SM", "s_adj": "SCA",
                              "geo": "EA20"}, -50.0, 50.0)

    def get_unemployment(self) -> float | None:
        # Stolperstein: une_rt_m nutzt geo=EA21 (EA20 existiert dort nicht).
        return _fetch_latest("une_rt_m",
                             {"sex": "T", "age": "TOTAL", "unit": "PC_ACT", "s_adj": "SA",
                              "geo": "EA21"}, 0.0, 100.0)

    # ── Delegation an base (Renditen/Zinsen/Geldmenge/PMI) ──────────────────
    def get_interest_rate(self) -> float | None:
        return self._base.get_interest_rate()

    def get_interest_rate_history(self, years: int = 2) -> list[dict]:
        return self._base.get_interest_rate_history(years)

    def get_m3_growth(self) -> float | None:
        return self._base.get_m3_growth()

    def get_m2_growth(self) -> float | None:
        return self._base.get_m2_growth()

    def get_balance_sheet_growth(self) -> float | None:
        return self._base.get_balance_sheet_growth()

    def get_pmi(self) -> float | None:
        return self._base.get_pmi()

    def get_sovereign_yields(self) -> dict[str, float | None]:
        return self._base.get_sovereign_yields()

    def get_yield_spreads(self) -> dict[str, float | None]:
        return self._base.get_yield_spreads()
```

- [ ] **Step 4: Test läuft (grün)**

Run: `python -m pytest tests/adapters/test_eurostat.py -q`
Expected: PASS (alle Tests grün — Parse aus Task 1 + die neuen).

- [ ] **Step 5: Volle Suite (keine Regression)**

Run: `python -m pytest -q`
Expected: PASS (Gesamtsuite grün; offline-sicher). Pass-Zahl für die PR-Beschreibung notieren.

- [ ] **Step 6: Commit**

```bash
git add adapters/data/eurostat.py tests/adapters/test_eurostat.py
git commit -m "feat(macro): EurostatEcbProvider — EU-Realwirtschaft via Eurostat (Decorator)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Composition Roots verdrahten + Logbuch

**Files:**
- Modify: `app/main.py`
- Modify: `app/server.py`
- Modify: `docs/open_todos.md`

**Interfaces:**
- Consumes: `EurostatEcbProvider` (Task 2); bestehender `EcbSdwProvider`.

- [ ] **Step 1: `app/main.py` verdrahten**

Import nach `from adapters.data.ecb_sdw import EcbSdwProvider` (Zeile 23) ergänzen:
```python
from adapters.data.eurostat import EurostatEcbProvider
```

In `run_dashboard` die `ecb`-Zeile im `TopDownOrchestrator(...)`-Aufruf ersetzen:
```python
        ecb=EcbSdwProvider(),
```
→
```python
        ecb=EurostatEcbProvider(EcbSdwProvider()),
```

- [ ] **Step 2: `app/server.py` verdrahten**

Import nach `from adapters.data.ecb_sdw import EcbSdwProvider` (Zeile 11) ergänzen:
```python
from adapters.data.eurostat import EurostatEcbProvider
```

In `make_orchestrator` die `ecb`-Zeile ersetzen:
```python
        ecb=EcbSdwProvider(),
```
→
```python
        ecb=EurostatEcbProvider(EcbSdwProvider()),
```

- [ ] **Step 3: Verifikation — komplette Suite grün**

Run: `python -m pytest -q`
Expected: PASS (gesamte Suite grün; keine echten Netz-Calls). Pass-Zahl notieren.

- [ ] **Step 4: Logbuch `docs/open_todos.md` pflegen**

Die EU-Makro-Stubs sind im Logbuch im Block „Aus Plan D1/D2" bzw. den ECB-Einträgen verzeichnet. Zuerst die Stellen finden, dann gezielt editieren:

Run: `grep -n "ecb_snb_stub\|get_cpi\|get_gdp_growth\|Eurostat\|EZB\|ECB SDW\|get_ppi\|get_unemployment" docs/open_todos.md`

Einen abgehakten Sammeleintrag im passenden Block ergänzen (Stil wie bei Fear & Greed, deutsch):
```
- [x] **EU-Realwirtschaft (Eurostat) angebunden** — `adapters/data/eurostat.py` (`EurostatEcbProvider`, Decorator), injiziert via `ecb=EurostatEcbProvider(EcbSdwProvider())` in `app/main.py` + `app/server.py`. **Lösung:** HICP/Kern-HICP/PPI/reales BIP/Arbeitslosenquote via Eurostat (Jahresrate direkt; jüngste befüllte Beobachtung; geo EA20 bzw. EA21 für Arbeitslosigkeit); Sanity-Caps + WARNING-Logs; Fehler → `None` → `UNAVAILABLE`. Schaltet EU-Inflation komplett + EU-BIP (über Trend) scharf.
```
Und die offenen Folge-Tasks festhalten (falls nicht vorhanden):
```
- [ ] **Folge-Task — EU-PMI** (gdp_agent): S&P-Global-PMI ist proprietär (keine freie API) → bleibt `UNAVAILABLE`; einen Fremdindex mit PMI-Schwellen zu nutzen wäre fachlich falsch. EU-BIP-Signal läuft solange über „BIP über Trend". Quelle/Lizenz klären.
- [ ] **Folge-Task — EU-Geldmenge (Slice 2, ECB SDW)**: `get_m2_growth`/`get_m3_growth` in `ecb_sdw.py` anbinden + im `money_supply_agent` nominales BIP = reales BIP (`ecb.get_gdp_growth`) + CPI (`ecb.get_cpi`) berechnen (Zeile 68), damit das EU-Geldmengensignal scharfschaltet (analog USA, Zeile 59).
```

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/server.py docs/open_todos.md
git commit -m "feat(macro): EU-Realwirtschaft (Eurostat) in Composition Roots verdrahten + Logbuch

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (gegen die Spec)

**1. Spec-Abdeckung:**
- Adapter `eurostat.py` mit `_parse_jsonstat_latest` + `_fetch_latest` + Decorator → Task 1 + 2. ✓
- 5 echte Methoden mit verifizierten Codes (geo EA20/EA21, PPI PRC_PRR_DOM, latest-populated, lastTimePeriod=6) → Task 2 + Global Constraints. ✓
- Sanity-Caps (Raten -50..50, Arbeitslosigkeit 0..100), Rundung, WARNING-Logs → Task 2. ✓
- Delegation der Nicht-Eurostat-Methoden an base → Task 2 (Code + Test). ✓
- Verdrahtung in app/main.py + app/server.py → Task 3. ✓
- Tests (Parse-Grenzfälle, je Methode Codes, Sanity-Cap, Netzfehler, Delegation) → Task 1 + 2. ✓
- Logbuch + PMI/Geldmenge-Folge-Tasks → Task 3. ✓
- Keine Agenten-Logik-Änderung → kein Task fasst Agenten an. ✓
- README unverändert → kein Task ändert README. ✓

**2. Placeholder-Scan:** keine TBD/„handle edge cases"; jeder Code-Schritt zeigt vollständigen Code. ✓

**3. Typ-Konsistenz:** `_parse_jsonstat_latest(data: dict) -> float | None`, `_fetch_latest(dataset, params, lo, hi) -> float | None`, alle Methoden `-> float | None` (bzw. `dict`/`list` bei Delegation analog Port). `EurostatEcbProvider(base: EcbDataProvider)` konsistent zwischen Task 2 (Definition) und Task 3 (Nutzung `EurostatEcbProvider(EcbSdwProvider())`). ✓
