# FRED-Realzins-Pilot — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `FredDataProvider.get_real_rate_history` mit echten DFII10-Daten implementieren und den Macro-Provider an den `precious_metal_price`-Agenten verdrahten, sodass die Gold-Realzins-Korrelation live wird.

**Architecture:** Bestehenden `FredDataProvider` (nutzt `fredapi`) um eine Methode erweitern, die den Port-Default `return []` überschreibt; eine Ein-Zeilen-Verdrahtung im Precious-Metals-Chief, der den Macro-Provider bereits erhält, ihn aber noch nicht an den Price-Agenten weiterreicht.

**Tech Stack:** Python, `fredapi`, pandas, pytest (unittest.mock).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-17-fred-realzins-pilot-design.md`.
- Vertragsformat `get_real_rate_history(years=5) -> list[dict]`: Elemente `{"date": "YYYY-MM-DD", "real_rate_10y": <float>}`, chronologisch ältester→neuester; bei Fehler/leer `[]`.
- Der `precious_metal_price`-Agent konsumiert `r["date"]` und `r["real_rate_10y"]` und braucht ≥30 Punkte (sonst Korrelation `None`).
- Nicht-brechend: fehlt der Macro-Provider (`None`), bleibt das Verhalten wie bisher (`real_yield_correlation=None`).
- Branch: `feat/daten-integration`. Test-Runner: `python -m pytest ... -q`.

---

## Task 1: `FredDataProvider.get_real_rate_history` (DFII10)

**Files:**
- Modify: `adapters/data/fred_api.py` (Methode in Klasse `FredDataProvider` ergänzen, nach `get_buffett_history`)
- Test: `tests/adapters/test_fred_real_rate.py` (Create)

**Interfaces:**
- Produces: `FredDataProvider.get_real_rate_history(self, years: int = 5) -> list[dict]` — Elemente `{"date": str (YYYY-MM-DD), "real_rate_10y": float}`, ältester zuerst; `[]` bei Fehler.

- [ ] **Step 1: Failing Test schreiben** — `tests/adapters/test_fred_real_rate.py`:

```python
from unittest.mock import MagicMock

import pandas as pd

from adapters.data.fred_api import FredDataProvider


def _make_provider():
    p = FredDataProvider.__new__(FredDataProvider)
    p.fred = MagicMock()
    return p


def test_maps_series_to_dicts_drops_nan_chronological():
    p = _make_provider()
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    p.fred.get_series.return_value = pd.Series([1.0, float("nan"), 1.2], index=idx)
    out = p.get_real_rate_history(5)
    assert out == [
        {"date": "2024-01-01", "real_rate_10y": 1.0},
        {"date": "2024-01-03", "real_rate_10y": 1.2},
    ]


def test_uses_dfii10_series():
    p = _make_provider()
    p.fred.get_series.return_value = pd.Series(
        [0.5], index=pd.date_range("2024-01-01", periods=1, freq="D")
    )
    p.get_real_rate_history(5)
    assert p.fred.get_series.call_args.args[0] == "DFII10"


def test_returns_empty_on_failure():
    p = _make_provider()
    p.fred.get_series.side_effect = Exception("API down")
    assert p.get_real_rate_history(5) == []
```

- [ ] **Step 2: Test laufen lassen → erwartet FAIL** — `python -m pytest tests/adapters/test_fred_real_rate.py -q`. Erwartung: FAIL (Methode liefert aktuell den Port-Default `[]` → `test_maps_series_to_dicts_drops_nan_chronological` und `test_uses_dfii10_series` schlagen fehl).

- [ ] **Step 3: Implementierung** — in `adapters/data/fred_api.py` in der Klasse `FredDataProvider` direkt nach `get_buffett_history` einfügen:

```python
    def get_real_rate_history(self, years: int = 5) -> list[dict]:
        """DFII10 (10J US-TIPS-Realzins) der letzten `years` Jahre.
        Rueckgabe: [{"date": "YYYY-MM-DD", "real_rate_10y": float}, ...] (aeltester zuerst).
        Bei Fehler/leerer Serie: []."""
        try:
            start = f"{datetime.utcnow().year - years}-01-01"
            series = self.fred.get_series("DFII10", observation_start=start).dropna()
            return [
                {"date": ts.strftime("%Y-%m-%d"), "real_rate_10y": round(float(v), 3)}
                for ts, v in series.items()
            ]
        except Exception:
            return []
```

> Hinweis: `datetime` ist oben in der Datei bereits importiert (`from datetime import datetime`). Muster konsistent mit `get_buffett_history` (gleiches `observation_start`-Schema, gleiches `try/except → []`).

- [ ] **Step 4: Test laufen → erwartet PASS** — `python -m pytest tests/adapters/test_fred_real_rate.py -q`. Erwartung: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add adapters/data/fred_api.py tests/adapters/test_fred_real_rate.py
git commit -m "feat(fred): get_real_rate_history (DFII10) statt Port-Default"
```

---

## Task 2: Macro-Provider an den Price-Agenten verdrahten

**Files:**
- Modify: `agents/stock_deep_dive/precious_metals_chief_agent.py:20`
- Test: `tests/agents/stock_deep_dive/precious_metals/test_precious_metals_chief_wiring.py` (Create)

**Interfaces:**
- Consumes: `FredDataProvider.get_real_rate_history` (Task 1); `PreciousMetalPriceAgent.__init__(self, provider, bus, macro=None)` (vorhanden; speichert `self.macro = macro`).
- Produces: `PreciousMetalsChiefAgent` reicht seinen `macro`-Provider an `pm_price_agent` weiter (`pm_price_agent.macro is macro`).

- [ ] **Step 1: Failing Test schreiben** — `tests/agents/stock_deep_dive/precious_metals/test_precious_metals_chief_wiring.py`:

```python
from unittest.mock import MagicMock

from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent


def test_chief_reicht_macro_an_price_agent_weiter():
    macro = MagicMock()
    market = MagicMock()
    bus = MagicMock()
    chief = PreciousMetalsChiefAgent(macro, market, bus)
    # Der Price-Agent muss denselben Macro-Provider erhalten (fuer get_real_rate_history)
    assert chief.pm_price_agent.macro is macro
```

- [ ] **Step 2: Test laufen lassen → erwartet FAIL** — `python -m pytest tests/agents/stock_deep_dive/precious_metals/test_precious_metals_chief_wiring.py -q`. Erwartung: FAIL — aktuell wird `PreciousMetalPriceAgent(market, bus)` ohne `macro` konstruiert → `pm_price_agent.macro is None`.

- [ ] **Step 3: Implementierung** — in `agents/stock_deep_dive/precious_metals_chief_agent.py` Zeile 20 ändern:

```python
        self.pm_price_agent     = PreciousMetalPriceAgent(market, bus, macro=macro)
```

(vorher: `self.pm_price_agent     = PreciousMetalPriceAgent(market, bus)`)

- [ ] **Step 4: Test laufen → erwartet PASS** — `python -m pytest tests/agents/stock_deep_dive/precious_metals/test_precious_metals_chief_wiring.py -q`. Erwartung: 1 passed.

- [ ] **Step 5: Gesamt-Regression** — `python -m pytest -q`. Erwartung: 0 failed (Baseline 619 + 4 neue Tests = 623). Bei Fehlern: superpowers:systematic-debugging.

- [ ] **Step 6: Commit**

```bash
git add agents/stock_deep_dive/precious_metals_chief_agent.py tests/agents/stock_deep_dive/precious_metals/test_precious_metals_chief_wiring.py
git commit -m "feat(precious_metals): Macro-Provider an Price-Agent verdrahten (Realzins-Korrelation live)"
```

---

## Abdeckung (Spec → Task)

| Spec-Element | Task |
|---|---|
| `get_real_rate_history(years=5)` (DFII10, Vertragsformat, Fehler→[]) | Task 1 |
| Verdrahtung Macro-Provider → `precious_metal_price`-Agent | Task 2 |
| Unit-Test (Mapping/NaN/DFII10/Fehler) | Task 1 |
| Verdrahtungs-Test (`pm_price_agent.macro is macro`) | Task 2 |
| Nicht-brechend (macro=None → wie bisher) | per Default-Parameter (Task 2 Test deckt den gesetzten Fall) |
| Gesamtsuite grün | Task 2, Step 5 |

## Manuelle Live-Verifikation (optional, nach Merge)

Nicht Teil der Testsuite (kein Live-API-Call in Tests). Optional einmalig prüfen:
```bash
python -c "from adapters.data.fred_api import FredDataProvider; import os; p=FredDataProvider(os.getenv('FRED_API_KEY')); h=p.get_real_rate_history(5); print(len(h), h[:1], h[-1:])"
```
Erwartung: einige hundert Einträge, jüngster mit aktuellem DFII10-Wert.
