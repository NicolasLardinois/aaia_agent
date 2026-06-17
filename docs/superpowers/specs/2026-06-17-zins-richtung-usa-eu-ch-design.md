# Zins-Richtung (USA + EU + CH) live — Design

**Datum:** 2026-06-17
**Status:** Genehmigt (Design)
**Branch:** `feat/zins-richtung`

## Kontext & Ziel

Der `interest_rate_agent` ruft `_direction(..., history=None, ...)` (Zeilen 96–98) → die Zinsrichtung ist immer `"stable"`, das Signal immer NEUTRAL. Zusätzlich sind die **EU- und CH-Leitzinsen selbst Stubs** (`EcbSdwProvider.get_interest_rate()` → `None`, `FredSnbProvider.get_interest_rate()` → `None`).

Ziel: „steigt/fällt/stabil" je Region (USA, EU, CH) **echt** berechnen — aktueller Leitzins + datierte Leitzins-Historie aus **nativen, key-freien Quellen**, verdrahtet über `InMemoryDatedHistory` → `_direction`.

## Verifizierte Quellen (live geprüft, ohne API-Key)

| Region | Quelle | Identifier | geprüft |
|---|---|---|---|
| USA | FRED | `FEDFUNDS` | vorhanden (Key gesetzt) |
| EU | ECB Data Portal (dieselbe API wie die Yields) | `FM.B.U2.EUR.4F.KR.MRR_FR.LEV` (Hauptrefinanzierungssatz) | ✅ 2,40 % (17.06.2026) |
| CH | `data.snb.ch` Cube `snboffzisa` | Reihe `H` (SNB-Leitzins) | ✅ 2,15 % (04/2026) |

Keine neuen kostenpflichtigen/angemeldeten APIs; `requests` (für ECB/SNB) und `fredapi` (USA) sind bereits Abhängigkeiten.

## Scope

**Im Plan:**
- USA-Leitzins-Historie (FEDFUNDS) als Provider-Methode.
- EU: `get_interest_rate()` (Stub ersetzen) **und** `get_interest_rate_history()` via ECB FM-Dataset.
- CH: `get_interest_rate()` (Stub ersetzen) **und** `get_interest_rate_history()` via `data.snb.ch`.
- Neue History-Port-Methoden **nicht-abstrakt mit Default `[]`** (bestehende Implementierer/Fakes brechen nicht — Lektion aus Plan E).
- Verdrahtung im `interest_rate_agent`: pro Region echte Richtung via `InMemoryDatedHistory` + `_direction`.
- Tests (gemockt) je Quelle + Verdrahtung + Richtung.

**Außerhalb:** EU/CH-Realzins-Verfeinerung (eigener CPI), andere Datenquellen (COT, Fear&Greed, …).

## Komponenten / Änderungen

### 1. `adapters/data/fred_api.py` — USA-Leitzins-Historie
```python
def get_policy_rate_history(self, years: int = 2) -> list[dict]:
    """FEDFUNDS der letzten `years` Jahre.
    Rueckgabe: [{"date":"YYYY-MM-DD","rate":float}, ...] (aeltester zuerst). Fehler/leer → []."""
```
Muster wie `get_real_rate_history` (FRED `get_series("FEDFUNDS", observation_start=...)`, `.dropna()`, `try/except → []`).

### 2. `core/ports/data_provider.py` — neue History-Methoden (nicht-abstrakt, Default `[]`)
- `MacroDataProvider.get_policy_rate_history(self, years: int = 2) -> list[dict]: return []`
- `EcbDataProvider.get_interest_rate_history(self, years: int = 2) -> list[dict]: return []`
- `SnbDataProvider.get_interest_rate_history(self, years: int = 2) -> list[dict]: return []`

### 3. `adapters/data/ecb_sdw.py` — EU-Leitzins (nativ)
- `get_interest_rate()`: letzten Wert von `FM.B.U2.EUR.4F.KR.MRR_FR.LEV` (`lastNObservations=1`), Parser wie `_fetch_yield`.
- `get_interest_rate_history(years=2)`: dieselbe Serie über `years` (`startPeriod=<heute−years>`), alle Beobachtungen → `[{"date","rate"}]` (ältester zuerst). Defensiv `try/except → None`/`[]`.

### 4. `adapters/data/fred_snb.py` — CH-Leitzins (nativ, data.snb.ch)
- `get_interest_rate()`: jüngster Wert der SNB-Reihe `H` aus `data.snb.ch/api/cube/snboffzisa/data/csv/en` (CSV; semikolon-getrennt, Header überspringen, Spalte mit `D0='H'`).
- `get_interest_rate_history(years=2)`: alle `H`-Werte der letzten `years` → `[{"date","rate"}]` (Datum aus dem Monats-Feld, z. B. `YYYY-MM` → `YYYY-MM-01`). Defensiv `try/except → None`/`[]`.
- Neuer `requests`-basierter Fetch (Klasse bleibt `FredSnbProvider`; Datenquelle ist jetzt gemischt FRED+SNB — Kommentar ergänzen).

### 5. `agents/market_cockpit/macro/interest_rate_agent.py` — Verdrahtung
- In `run()` zusätzlich die drei Historien holen (`asyncio.to_thread`, in den bestehenden `gather` integrieren oder separat), je defensiv.
- Eine `InMemoryDatedHistory` mit allen drei Reihen bauen:
  `{"fed_rate": [(date, rate),…], "ecb_rate": […], "snb_rate": […]}` (Konvertierung aus `[{"date","rate"}]`).
- `_direction(fed_rate, history=hist, series="fed_rate", today=date.today())` usw. (statt `history=None`).
- Fehlt eine Historie (leer) → Serie leer → `value_on_or_before` → `None` → `"stable"` (kein Crash, kein toter Code).

## Datenfluss

`interest_rate_agent.run()` → (FRED FEDFUNDS-Hist | ECB MRR_FR-Hist | SNB `H`-Hist) → `InMemoryDatedHistory` → `_direction(rate, hist, series, today)` → `rate_direction` je Region → `_signal(rate, direction, real_rate)`.

## Fehlerbehandlung

Jede Quelle defensiv (`try/except` → `None`/`[]`). Fehlt Wert oder Historie → Region bleibt `"stable"`/NEUTRAL. Kein prozess-globaler Zustand (kein `_RATE_HISTORY`).

## Tests

- **FRED** (`tests/adapters/`): `get_policy_rate_history` gegen gemocktes `fred.get_series` (Series mit NaN) → Listenform/NaN-Drop/chronologisch; Fehler→`[]`.
- **ECB** (`tests/adapters/`): `get_interest_rate` + `get_interest_rate_history` gegen gemocktes `requests.get` (ECB-jsondata-Struktur wie bei den Yields) → korrekter Wert/Liste; Fehler→`None`/`[]`.
- **SNB** (`tests/adapters/`): `get_interest_rate` + `get_interest_rate_history` gegen gemocktes `requests.get` (SNB-CSV mit `D0`-Spalte `H`) → korrekter Wert/Liste; Fehler→`None`/`[]`.
- **Verdrahtung** (`tests/agents/market_cockpit/macro/`): `interest_rate_agent` mit Fake-Providern, die je eine Reihe liefern, bei der „vor 3 Monaten" < heute (steigend) → `rate_direction == "rising"` je Region; ohne Historie → `"stable"`. `today` wird über die `_direction`-Schnittstelle deterministisch gehalten (Agent nutzt `date.today()`; Test injiziert Reihen relativ zu einem festen Bezug bzw. testet `_direction` direkt).

## Akzeptanzkriterien

1. Die drei Provider liefern aktuellen Leitzins + datierte Historie im Vertragsformat; Fehler → `None`/`[]`.
2. `interest_rate_agent` berechnet je Region eine echte `rate_direction` (rising/falling/stable) statt fix `"stable"`; bei vorhandener Historie + passendem Verlauf ein nicht-NEUTRALes Signal.
3. Neue Port-History-Methoden sind nicht-abstrakt (bestehende Implementierer/Fakes unverändert lauffähig).
4. Gesamte Testsuite bleibt grün (0 failed).
5. Muster dokumentiert (native ECB-/SNB-Quelle), wiederholbar für weitere ECB/SNB-Größen (CPI, M3 etc.).
