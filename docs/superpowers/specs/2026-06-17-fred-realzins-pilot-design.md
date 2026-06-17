# Daten-Integration Pilot: FRED-Realzins-Historie — Design

**Datum:** 2026-06-17
**Status:** Genehmigt (Design)
**Branch:** `feat/daten-integration`

## Kontext & Ziel

Plan E hat die Stub-Agenten + Ports gebaut; die Agenten liefern `SignalStatus.UNAVAILABLE`, bis echte Datenquellen angebunden sind (siehe `docs/open_todos.md`). Dieser Pilot bindet **eine** Quelle vollständig an, um das Muster **„Adapter → Port → Agent wird live"** end-to-end zu beweisen — mit der geringsten Reibung.

Gewählte Quelle: **FRED-Realzins-Historie** (`DFII10`, 10-jähriger US-TIPS-Realzins). Macht die **Gold-Realzins-Korrelation** im `precious_metal_price`-Agenten live. `DFII10` ist fachlich der richtige Input: Gold ist USD-denominiert, der dominante Treiber ist der US-Realzins.

## Scope

**Im Pilot:**
- `MacroDataProvider.get_real_rate_history(years=5)` im bestehenden `FredDataProvider` implementieren (überschreibt den nicht-abstrakten Port-Default `return []`).
- Verdrahtung, sodass der Macro-Provider beim `precious_metal_price`-Agenten ankommt.
- Tests (Unit + Verdrahtung).

**Bewusst außerhalb (Folge-Schritte, eigenes Muster):**
- EU/CH-Realzins (andere Quelle: EZB-SDW/SNB; für die USD-Gold-Korrelation fachlich nicht nötig).
- interest_rate-Richtung (anderer Mechanismus: `DatedHistory`-Port mit `FEDFUNDS`, nicht Realzins-Historie).
- Alle weiteren Quellen (COT/CFTC, Fear&Greed/CNN, Supply/EIA-USDA-LME, Index-Daten).

## Ansatz

**Bestehenden `FredDataProvider` erweitern** (statt neuer Adapter-Klasse): Die FRED-Logik bleibt an einem Ort, nutzt den schon konfigurierten Key und die vorhandene `fredapi`-Library. `DFII10` ist im Modul bereits als `real_rate_10y` gemappt. Eine separate Adapter-Klasse wäre unnötige Duplizierung.

## Komponenten / Änderungen

### 1. `adapters/data/fred_api.py` — `get_real_rate_history`

Neue Methode in `FredDataProvider` (überschreibt den Port-Default):

```python
def get_real_rate_history(self, years: int = 5) -> list[dict]:
    """DFII10 (10J US-TIPS-Realzins) über `years` Jahre.
    Rückgabe: [{"date": "YYYY-MM-DD", "real_rate_10y": <float>}, ...] (ältester→neuester).
    Bei Fehler oder leerer Serie: []."""
```

- Quelle: `self.fred.get_series("DFII10", observation_start=<heute − years>)`.
- `.dropna()`; pro verbleibendem Punkt ein Dict `{"date": <ISO-Datum>, "real_rate_10y": float(wert)}`.
- Chronologisch aufsteigend (ältester zuerst).
- `try/except` → bei jedem Fehler `return []` (konsistent mit den anderen FRED-Methoden; der Agent bleibt dann `UNAVAILABLE`/Korrelation `None`).

### 2. Verdrahtung — Macro-Provider erreicht den Price-Agenten

Der `precious_metal_price`-Agent akzeptiert bereits `macro: MacroDataProvider | None = None` und ruft `macro.get_real_rate_history(5)`. Sicherzustellen:
- Der **Precious-Metals-Chief** nimmt einen Macro-Provider entgegen und reicht ihn als `macro=` an den `precious_metal_price`-Agenten weiter.
- `app/main.py` (Modus 2, Bottom-Up) gibt den bereits konstruierten `FredDataProvider` in die Kette → Precious-Metals-Chief.
- Rückwärtskompatibel: fehlt der Macro-Provider (`None`), bleibt das Verhalten wie bisher (`real_yield_correlation=None`).

Der exakte Verdrahtungspfad (Orchestrator → Chief → Agent) wird im Umsetzungsplan anhand des echten Codes festgelegt.

## Datenfluss

`app/main.py` (Modus 2) → Bottom-Up-Orchestrator → Precious-Metals-Chief → `precious_metal_price`-Agent → `macro.get_real_rate_history(5)` → FRED `DFII10` → `_real_yield_correlation` (Gold-Tagesrenditen `pct_change` vs. Realzins-Differenzen `diff`, datumsausgerichtet) → `real_yield_correlation`.

## Fehlerbehandlung

- FRED-Fehler/leer → `get_real_rate_history` gibt `[]` zurück.
- Agent-Guard (vorhanden): `if not rr_history or len(rr_history) < 30: return None` → Korrelation `None`, kein Crash, Snapshot bleibt nutzbar.
- Kein neuer Key, keine neue Abhängigkeit (alles via bestehender `fredapi` + konfiguriertem FRED-Key).

## Tests

- **Unit (`tests/adapters/test_fred_real_rate.py`):** `get_real_rate_history` gegen ein gemocktes `self.fred.get_series` (pandas Series mit DatetimeIndex inkl. NaN) → korrekte Listenform, Keys `date`/`real_rate_10y`, NaN gedroppt, chronologisch; FRED-Exception → `[]`.
- **Verdrahtung:** `precious_metal_price`-Agent mit einem Fake-Macro-Provider, der ≥30 Realzins-Punkte liefert → `real_yield_correlation` ist ein `float`, Snapshot-Status `AVAILABLE`; ohne Macro-Provider → `None`/wie bisher.
- Kein Live-API-Test in der Suite (konsistent mit den bestehenden Adaptern; Live-Prüfung optional manuell).

## Akzeptanzkriterien

1. `FredDataProvider.get_real_rate_history(5)` liefert die DFII10-Reihe im Vertragsformat; Fehler → `[]`.
2. Mit verdrahtetem FRED-Macro-Provider berechnet `precious_metal_price` eine echte `real_yield_correlation` (Status `AVAILABLE`).
3. Gesamte Testsuite bleibt grün (0 failed).
4. Das Muster ist dokumentiert, sodass die nächsten Adapter (COT, Fear&Greed, …) es 1:1 wiederholen.
