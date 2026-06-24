# Eurozone-Makro Slice 2 (EU-Geldmenge ECB SDW) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** EU-Geldmenge (M2/M3 via ECB SDW) anbinden und das EU-Geldmengensignal scharfschalten, indem der `money_supply_agent` das nominale BIP (reales BIP + CPI) berechnet.

**Architektur:** Hexagonal. `EcbSdwProvider` liefert echte M2/M3-Jahreswachstumsraten (ECB SDW BSI); der `money_supply_agent` rechnet `eu_nom_gdp = ecb_gdp + ecb_cpi` (analog USA). **Keine Verdrahtungsänderung** — der Eurostat-Decorator delegiert `get_m2_growth`/`get_m3_growth` bereits an die Basis, und `get_gdp_growth`/`get_cpi` sind seit Slice 1 echt.

**Tech-Stack:** Python, `requests`, pytest, asyncio.

Spec: `docs/superpowers/specs/2026-06-23-eu-geldmenge-ecb-sdw-design.md`.

## Global Constraints

- Sprache: Code-Kommentare + Commit-Messages auf **Deutsch**. Trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **TDD verpflichtend**; Tests **offline-sicher** (`tests/conftest.py` blockt echtes `requests`; Netz per `patch("adapters.data.ecb_sdw.requests.get", …)` mocken).
- **Moderne Type-Hints** `float | None` für neuen Code.
- **Verifizierte ECB-SDW-Series (2026-06-23):** M3 = `BSI/M.U2.Y.V.M30.X.I.U2.2300.Z01.A`, M2 = `…M20…` — nur `M30`/`M20` unterscheidet sich; Jahreswachstum kommt direkt in %.
- **Sanity-Cap** Geldmengenwachstum `-50.0 … 50.0` %; Rundung **1 Nachkommastelle**; `logging.warning` bei Fehler/Strukturbruch/implausibel.
- **Nominaler-BIP-Proxy:** `eu_nom_gdp = ecb_gdp + ecb_cpi` (lineare Fisher-Näherung) — **identisch** zur bestehenden USA-Logik (`money_supply_agent.py:59`). **M3 bevorzugt** (`eu_m = m3 ?? m2`).
- **Verhaltens-erhaltend:** `_fetch_yield`/`_fetch_country_yield` nutzen künftig den geteilten Parse-Helfer — die bestehenden Yield-/Sovereign-Tests müssen grün bleiben.
- **Keine Verdrahtungsänderung** (`app/main.py`/`app/server.py` unverändert). **CH-Pfad unverändert**. `_signal`-Schwellen unverändert.
- Git: isolierter Worktree (eigener Index); nur explizite Pfade stagen; nach jedem Commit `git show --stat` prüfen (nur eigene Dateien).

---

## Dateienübersicht

**Geändert:**
- `adapters/data/ecb_sdw.py` — `import logging`+Logger; `_parse_sdmx_last_observation` (rein); `_BSI_BASE`; `_fetch_bsi_growth`; echte `get_m2_growth`/`get_m3_growth`; `_fetch_yield`/`_fetch_country_yield` nutzen den Helfer.
- `agents/market_cockpit/macro/money_supply_agent.py` — EU-Pfad: `ecb_gdp`/`ecb_cpi` holen + `eu_nom_gdp` rechnen.
- `tests/agents/market_cockpit/macro/test_money_supply_agent.py` — `_make_agent` um `eu_gdp`/`eu_cpi` erweitern + neue Tests.
- `docs/open_todos.md` — „EU-Geldmenge (Slice 2)"-Folge-Task abhaken.

**Neu:**
- `tests/adapters/test_ecb_sdw_money.py` — Tests für Parse-Helfer + M2/M3.

**Nicht geändert:** `app/main.py`/`app/server.py`, Eurostat-Decorator, CH-Pfad, `_signal`.

---

### Task 1: ECB-SDW M2/M3 + geteilter SDMX-Parse-Helfer

**Files:**
- Modify: `adapters/data/ecb_sdw.py`
- Test: `tests/adapters/test_ecb_sdw_money.py`

**Interfaces:**
- Produces:
  - `_parse_sdmx_last_observation(data: dict) -> float | None` (Modul-Funktion) — letzter Beobachtungswert aus ECB-SDMX-JSON; `None` bei fehlender Struktur/leer/nicht-numerisch.
  - `EcbSdwProvider.get_m3_growth() -> float | None`, `get_m2_growth() -> float | None` (echt).

- [ ] **Step 1: Failing Tests schreiben** — `tests/adapters/test_ecb_sdw_money.py`

```python
"""TDD-Tests fuer ECB-SDW M2/M3 (_fetch_bsi_growth) und _parse_sdmx_last_observation."""
from unittest.mock import patch, MagicMock

from adapters.data.ecb_sdw import EcbSdwProvider, _parse_sdmx_last_observation


def _bsi_payload(value):
    """Spiegelt die ECB-SDMX-JSON-Struktur (eine Reihe, eine Beobachtung)."""
    return {"dataSets": [{"series": {"0:0:0:0:0:0:0:0:0:0": {"observations": {"0": [value]}}}}]}


def _resp(payload):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    return r


_GET = "adapters.data.ecb_sdw.requests.get"


# ── _parse_sdmx_last_observation (rein) ────────────────────────────────────
def test_parse_gueltige_beobachtung():
    assert _parse_sdmx_last_observation(_bsi_payload(2.74)) == 2.74


def test_parse_fehlende_struktur_none():
    assert _parse_sdmx_last_observation({}) is None
    assert _parse_sdmx_last_observation({"dataSets": [{"series": {}}]}) is None


def test_parse_nicht_numerisch_none():
    assert _parse_sdmx_last_observation(_bsi_payload("abc")) is None


# ── M3/M2 (gemocktes requests.get) ─────────────────────────────────────────
def test_get_m3_growth_liefert_wert_und_pinnt_m30():
    with patch(_GET, return_value=_resp(_bsi_payload(2.7356))) as m:
        assert EcbSdwProvider().get_m3_growth() == 2.7
    assert "M30" in m.call_args.args[0]


def test_get_m2_growth_liefert_wert_und_pinnt_m20():
    with patch(_GET, return_value=_resp(_bsi_payload(2.8671))) as m:
        assert EcbSdwProvider().get_m2_growth() == 2.9
    assert "M20" in m.call_args.args[0]


def test_get_m3_growth_implausibel_none():
    with patch(_GET, return_value=_resp(_bsi_payload(999.0))):
        assert EcbSdwProvider().get_m3_growth() is None


def test_get_m3_growth_netzfehler_none():
    with patch(_GET, side_effect=ConnectionError("boom")):
        assert EcbSdwProvider().get_m3_growth() is None
```

- [ ] **Step 2: Test läuft (rot)**

Run: `python -m pytest tests/adapters/test_ecb_sdw_money.py -q`
Expected: FAIL — `ImportError: cannot import name '_parse_sdmx_last_observation'`.

- [ ] **Step 3: Helfer + Logger + `_BSI_BASE` ergänzen** — `adapters/data/ecb_sdw.py`

Import-Block oben (nach `import requests`) ergänzen:
```python
import csv
import logging
import requests
from typing import Optional
```
Direkt nach den Imports (vor `_BASE`) den Logger anlegen:
```python
_log = logging.getLogger(__name__)
```
Nach dem `_IRS_BASE`-Block die BSI-URL + den reinen Helfer als **Modul-Funktion** ergänzen (außerhalb der Klasse, z. B. nach `EUROZONE_COUNTRIES`):
```python
_BSI_BASE = (
    "https://data-api.ecb.europa.eu/service/data/BSI/"
    "M.U2.Y.V.{item}.X.I.U2.2300.Z01.A"
    "?format=jsondata&lastNObservations=1"
)


def _parse_sdmx_last_observation(data: dict) -> float | None:
    """Rein: letzter Beobachtungswert aus ECB-SDMX-JSON
    (data["dataSets"][0]["series"][<key>]["observations"][<key>][0]).
    None bei fehlender Struktur, leerer Reihe oder nicht-numerischem Wert."""
    try:
        series = data["dataSets"][0]["series"]
        first_key = next(iter(series))
        observations = series[first_key]["observations"]
        last_key = next(reversed(observations))
        return float(observations[last_key][0])
    except (KeyError, IndexError, TypeError, ValueError, StopIteration):
        return None
```

- [ ] **Step 4: M2/M3-Methoden + `_fetch_bsi_growth` implementieren, Stubs ersetzen** — in `EcbSdwProvider`

Die Stub-Zeilen ersetzen:
```python
    def get_m3_growth(self) -> Optional[float]:             return None
```
→
```python
    def get_m3_growth(self) -> float | None:
        return self._fetch_bsi_growth("M30")
```
und
```python
    def get_m2_growth(self) -> Optional[float]:             return None
```
→
```python
    def get_m2_growth(self) -> float | None:
        return self._fetch_bsi_growth("M20")
```

Die Fetch-Methode in der Klasse ergänzen (z. B. nach `_fetch_yield`):
```python
    def _fetch_bsi_growth(self, item: str) -> float | None:
        """ECB-SDW BSI-Jahreswachstum (M30/M20) in %. Sanity-Cap -50..50, Rundung 1 Stelle;
        Fehler/Strukturbruch/implausibel → logging.warning → None (Beobachtbarkeit)."""
        try:
            response = requests.get(_BSI_BASE.format(item=item), timeout=10)
            response.raise_for_status()
            raw = _parse_sdmx_last_observation(response.json())
        except Exception as exc:
            _log.warning("ECB SDW BSI %s nicht abrufbar (%s) — UNAVAILABLE", item, exc)
            return None
        if raw is None:
            _log.warning("ECB SDW BSI %s: keine Beobachtung (Strukturbruch?) — UNAVAILABLE", item)
            return None
        if not (-50.0 <= raw <= 50.0):
            _log.warning("ECB SDW BSI %s: implausibler Wert %s — UNAVAILABLE", item, raw)
            return None
        return round(raw, 1)
```

- [ ] **Step 5: `_fetch_yield`/`_fetch_country_yield` auf den Helfer umstellen (verhaltens-erhaltend)**

`_fetch_yield` ersetzen:
```python
    def _fetch_yield(self, maturity: str) -> Optional[float]:
        url = _BASE.format(mat=maturity)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            series = data["dataSets"][0]["series"]
            first_key = next(iter(series))
            observations = series[first_key]["observations"]
            last_key = next(reversed(observations))
            return float(observations[last_key][0])
        except Exception:
            return None
```
→
```python
    def _fetch_yield(self, maturity: str) -> Optional[float]:
        try:
            response = requests.get(_BASE.format(mat=maturity), timeout=10)
            response.raise_for_status()
            return _parse_sdmx_last_observation(response.json())
        except Exception:
            return None
```

`_fetch_country_yield` ersetzen:
```python
    def _fetch_country_yield(self, country: str) -> Optional[float]:
        url = _IRS_BASE.format(country=country)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            series = data["dataSets"][0]["series"]
            first_key = next(iter(series))
            observations = series[first_key]["observations"]
            last_key = next(reversed(observations))
            return float(observations[last_key][0])
        except Exception:
            return None
```
→
```python
    def _fetch_country_yield(self, country: str) -> Optional[float]:
        try:
            response = requests.get(_IRS_BASE.format(country=country), timeout=10)
            response.raise_for_status()
            return _parse_sdmx_last_observation(response.json())
        except Exception:
            return None
```

- [ ] **Step 6: Tests + Regression grün**

Run: `python -m pytest tests/adapters/test_ecb_sdw_money.py tests/adapters/test_ecb_yield_spreads.py tests/adapters/test_ecb_interest_rate.py -q`
Expected: PASS (neue M2/M3-Tests + bestehende Yield-/Sovereign-Tests unverändert grün — Refactor verhaltens-erhaltend).

- [ ] **Step 7: Commit**

```bash
git add adapters/data/ecb_sdw.py tests/adapters/test_ecb_sdw_money.py
git commit -m "feat(macro): ECB-SDW M2/M3-Jahreswachstum + geteilter SDMX-Parse-Helfer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
Danach `git show --stat HEAD` prüfen: nur diese zwei Dateien.

---

### Task 2: money_supply_agent — EU nominales BIP + Logbuch

**Files:**
- Modify: `agents/market_cockpit/macro/money_supply_agent.py`
- Modify: `tests/agents/market_cockpit/macro/test_money_supply_agent.py`
- Modify: `docs/open_todos.md`

**Interfaces:**
- Consumes: `ecb.get_gdp_growth()`, `ecb.get_cpi()` (seit Slice 1 echt); `ecb.get_m2_growth`/`get_m3_growth` (Task 1); `excess_over_nominal_gdp` (`core/utils/real_nominal.py`).

- [ ] **Step 1: Failing Tests schreiben** — `tests/agents/market_cockpit/macro/test_money_supply_agent.py`

Zuerst die Factory `_make_agent` erweitern (sonst liefert der MagicMock für die neuen `ecb`-Aufrufe ungewollt ein Truthy-Objekt statt `None` und die None-Guard-Tests brechen):
```python
def _make_agent(*, eu_m3=None, eu_m2=None, ch_m3=None, ch_m2=None, ext=None):
    """Hilfs-Factory: erstellt MoneySupplyAgent mit gemockten Providern."""
    macro = MagicMock()
    macro.get_extended_state.return_value = ext or {}
    ecb = MagicMock()
    ecb.get_m2_growth.return_value = eu_m2
    ecb.get_m3_growth.return_value = eu_m3
    snb = MagicMock()
    snb.get_m2_growth.return_value = ch_m2
    snb.get_m3_growth.return_value = ch_m3
    bus = MagicMock()
    return MoneySupplyAgent(macro=macro, ecb=ecb, snb=snb, bus=bus)
```
→ ersetzen durch:
```python
def _make_agent(*, eu_m3=None, eu_m2=None, eu_gdp=None, eu_cpi=None,
                ch_m3=None, ch_m2=None, ext=None):
    """Hilfs-Factory: erstellt MoneySupplyAgent mit gemockten Providern.

    eu_gdp/eu_cpi muessen explizit gesetzt werden, sonst liefert der MagicMock
    fuer ecb.get_gdp_growth/get_cpi ein Truthy-Objekt statt None.
    """
    macro = MagicMock()
    macro.get_extended_state.return_value = ext or {}
    ecb = MagicMock()
    ecb.get_m2_growth.return_value = eu_m2
    ecb.get_m3_growth.return_value = eu_m3
    ecb.get_gdp_growth.return_value = eu_gdp
    ecb.get_cpi.return_value = eu_cpi
    snb = MagicMock()
    snb.get_m2_growth.return_value = ch_m2
    snb.get_m3_growth.return_value = ch_m3
    bus = MagicMock()
    return MoneySupplyAgent(macro=macro, ecb=ecb, snb=snb, bus=bus)
```

Drei neue Tests am Dateiende ergänzen:
```python
def test_eu_signal_schaltet_scharf_mit_echten_inputs():
    """M3=2.7, reales BIP=0.3, CPI=2.0 → nom BIP=2.3 → excess=0.4 → BULLISH."""
    agent = _make_agent(eu_m3=2.7, eu_gdp=0.3, eu_cpi=2.0)
    result = asyncio.run(agent.run())
    assert result.eurozone.signal == Signal.BULLISH


def test_eu_faellt_auf_m2_zurueck_wenn_m3_fehlt():
    """M3 fehlt, M2=2.9 + BIP/CPI → eu_m nutzt M2 → excess 0.6 → BULLISH."""
    agent = _make_agent(eu_m2=2.9, eu_gdp=0.3, eu_cpi=2.0)
    result = asyncio.run(agent.run())
    assert result.eurozone.m2_growth == 2.9
    assert result.eurozone.signal == Signal.BULLISH


def test_eu_neutral_wenn_cpi_fehlt():
    """M3 + BIP vorhanden, CPI fehlt → eu_nom_gdp None → NEUTRAL (kein Crash)."""
    agent = _make_agent(eu_m3=2.7, eu_gdp=0.3, eu_cpi=None)
    result = asyncio.run(agent.run())
    assert result.eurozone.signal == Signal.NEUTRAL
```

- [ ] **Step 2: Test läuft (rot)**

Run: `python -m pytest tests/agents/market_cockpit/macro/test_money_supply_agent.py -q`
Expected: FAIL — `test_eu_signal_schaltet_scharf_mit_echten_inputs` ergibt NEUTRAL statt BULLISH (Agent rechnet `eu_nom_gdp` noch nicht).

- [ ] **Step 3: Agent-Logik ergänzen** — `agents/market_cockpit/macro/money_supply_agent.py`

`asyncio.gather`-Block ersetzen:
```python
        ext, ecb_m2, ecb_m3, snb_m2, snb_m3 = await asyncio.gather(
            asyncio.to_thread(self.macro.get_extended_state),
            asyncio.to_thread(self.ecb.get_m2_growth),
            asyncio.to_thread(self.ecb.get_m3_growth),
            asyncio.to_thread(self.snb.get_m2_growth),
            asyncio.to_thread(self.snb.get_m3_growth),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v

        ext    = _safe(ext)    or {}
        ecb_m2 = _safe(ecb_m2)
        ecb_m3 = _safe(ecb_m3)
        snb_m2 = _safe(snb_m2)
        snb_m3 = _safe(snb_m3)
```
→
```python
        ext, ecb_m2, ecb_m3, ecb_gdp, ecb_cpi, snb_m2, snb_m3 = await asyncio.gather(
            asyncio.to_thread(self.macro.get_extended_state),
            asyncio.to_thread(self.ecb.get_m2_growth),
            asyncio.to_thread(self.ecb.get_m3_growth),
            asyncio.to_thread(self.ecb.get_gdp_growth),
            asyncio.to_thread(self.ecb.get_cpi),
            asyncio.to_thread(self.snb.get_m2_growth),
            asyncio.to_thread(self.snb.get_m3_growth),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v

        ext    = _safe(ext)    or {}
        ecb_m2  = _safe(ecb_m2)
        ecb_m3  = _safe(ecb_m3)
        ecb_gdp = _safe(ecb_gdp)
        ecb_cpi = _safe(ecb_cpi)
        snb_m2 = _safe(snb_m2)
        snb_m3 = _safe(snb_m3)
```

EU-Block ersetzen:
```python
        eu_m = ecb_m3 if ecb_m3 is not None else ecb_m2
        eu_nom_gdp = None  # TODO: EZB/Eurostat nominales BIP anbinden
        eu_excess = excess_over_nominal_gdp(eu_m, eu_nom_gdp) if (eu_m is not None and eu_nom_gdp is not None) else None
```
→
```python
        eu_m = ecb_m3 if ecb_m3 is not None else ecb_m2
        # Nominales BIP-Wachstum = reales BIP + CPI (Proxy, analog USA oben)
        eu_nom_gdp = (ecb_gdp + ecb_cpi) if (ecb_gdp is not None and ecb_cpi is not None) else None
        eu_excess = excess_over_nominal_gdp(eu_m, eu_nom_gdp) if (eu_m is not None and eu_nom_gdp is not None) else None
```

- [ ] **Step 4: Test grün**

Run: `python -m pytest tests/agents/market_cockpit/macro/test_money_supply_agent.py -q`
Expected: PASS (neue 3 Tests grün; bestehende None-Guard-Tests weiter grün dank `_make_agent`-Anpassung).

- [ ] **Step 5: Logbuch `docs/open_todos.md` pflegen**

Zuerst die Stelle finden:
Run: `grep -n "Folge-Task — EU-Geldmenge" docs/open_todos.md`
Den Eintrag von `- [ ]` auf `- [x]` setzen und einen deutschen Lösungsvermerk anhängen, Stil:
```
  - [x] **EU-Geldmenge (Slice 2, ECB SDW) angebunden** — `ecb_sdw.py` liefert M2/M3-Jahreswachstum (BSI, verifiziert); `money_supply_agent` rechnet `eu_nom_gdp = reales BIP + CPI` (analog USA) → EU-Geldmengensignal scharf. Sanity-Cap + WARNING-Logs; Fehler → `None` → NEUTRAL. (CH-nom-BIP bleibt offen = spätere CH-Slice.)
```

- [ ] **Step 6: Volle Suite (offline-sicher)**

Run: `python -m pytest -q`
Expected: PASS bis auf evtl. **vorbestehende** Flaky-Route-Tests (`tests/adapters/api/test_routes_cockpit.py`, nur im Gesamtlauf) — KEINE neuen Fehler durch diese Slice. Pass-Zahl für die PR-Beschreibung notieren.

- [ ] **Step 7: Commit**

```bash
git add agents/market_cockpit/macro/money_supply_agent.py tests/agents/market_cockpit/macro/test_money_supply_agent.py docs/open_todos.md
git commit -m "feat(macro): EU-Geldmengensignal scharf (nominales BIP = reales BIP + CPI) + Logbuch

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
Danach `git show --stat HEAD` prüfen: nur diese drei Dateien.

---

## Self-Review (gegen die Spec)

**1. Spec-Abdeckung:**
- ECB-SDW M2/M3 (verifizierte BSI-Codes M30/M20) + reine `_parse_sdmx_last_observation` → Task 1. ✓
- `_fetch_yield`/`_fetch_country_yield` nutzen den Helfer (DRY, verhaltens-erhaltend) → Task 1 Step 5. ✓
- Sanity-Cap -50..50, Rundung, WARNING-Logs → Task 1 Step 4. ✓
- Agent: `eu_nom_gdp = ecb_gdp + ecb_cpi`, M3 bevorzugt → Task 2 Step 3. ✓
- `_make_agent`-Anpassung (sonst MagicMock-Falle) → Task 2 Step 1. ✓
- Tests Adapter + Agent (scharfes Signal, M2-Fallback, NEUTRAL bei fehlendem CPI) → Task 1 + 2. ✓
- Keine Verdrahtung, CH unverändert, `_signal` unverändert → kein Task berührt sie. ✓
- Logbuch abgehakt, README unverändert → Task 2 Step 5. ✓

**2. Placeholder-Scan:** keine TBD/„handle edge cases"; jeder Code-Schritt zeigt vollständigen Code. ✓

**3. Typ-Konsistenz:** `_parse_sdmx_last_observation(data: dict) -> float | None`, `_fetch_bsi_growth(item: str) -> float | None`, `get_m2_growth/get_m3_growth -> float | None` durchgängig; `_make_agent(..., eu_gdp, eu_cpi, ...)` konsistent zwischen Definition (Task 2 Step 1) und Nutzung (neue Tests). ✓
