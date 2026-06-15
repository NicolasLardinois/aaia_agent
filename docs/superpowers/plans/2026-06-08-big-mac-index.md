# Big Mac Index (Adjustiert) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den adjustierten Big Mac Index von The Economist implementieren — Daten fetchen, modellieren und in Top-Down-Kontext + MacroChiefResult integrieren.

**Architecture:** Neuer `BigMacAgent` in der Makro-Schicht des Market Cockpit. Agent fetcht halbjährlich aktualisierte CSV von Economist GitHub, berechnet BULLISH/BEARISH-Signal pro Land, integriert sich in `MacroChiefResult` wie der `BuffettIndicatorAgent`. Top-Down-Kontext zeigt das adjustierte Signal für das analysierte Land.

**Tech Stack:** Python 3.11+, requests (bereits in requirements.txt), pytest, csv (stdlib)

---

## Was der adjustierte Big Mac Index ist

**Raw Big Mac Index:** Vergleicht den Preis eines Big Mac (in USD) im In- und Ausland mit dem Marktwechselkurs. Differenz = implizierte Über-/Unterbewertung der Währung.

**Adjusted (adjustiert):** Korrigiert für das lokale Einkommensniveau (GDP per capita). Da in ärmeren Ländern Arbeit billiger ist, sind Big Macs dort strukturell günstiger — das ist keine Währungsunterbewertung. Die Regressionsgeraden-Bereinigung entfernt diesen Einkommenseffekt.

**Datenquelle:** The Economist publiziert die Daten öffentlich (MIT-Lizenz) auf GitHub. Die Datei `big-mac-adjusted-index.csv` wird halbjährlich (Januar/Juli) aktualisiert und enthält alle Länder mit McDonald's-Präsenz.

**Schlüsselfeld:** `dollar_adj` — % Über- (positiv) oder Unterbewertung (negativ) der Landeswährung relativ zum USD, adjustiert für Einkommensniveau.

---

## Neue Dateien

| Datei | Zweck |
|---|---|
| `agents/market_cockpit/macro/big_mac_agent.py` | Agent: fetcht Daten, berechnet Signale |
| `tests/agents/market_cockpit/macro/test_big_mac_agent.py` | Tests |

## Geänderte Dateien

| Datei | Änderung |
|---|---|
| `core/domain/models.py` | `BigMacCountryPoint`, `BigMacSnapshot`, `MacroChiefResult.big_mac` |
| `core/domain/events.py` | `BigMacDataReady` Event |
| `core/ports/data_provider.py` | `get_big_mac_data()` in `MacroDataProvider` |
| `adapters/data/fred_api.py` | `get_big_mac_data()` implementieren |
| `agents/market_cockpit/macro_chief_agent.py` | BigMacAgent parallel einbinden |
| `core/domain/top_down_context.py` | Big-Mac-Hinweis für analysiertes Land |

---

## Task 1: Datenmodelle + Event

**Files:**
- Modify: `core/domain/models.py` (nach `BuffettIndicatorSnapshot` ca. Zeile 142)
- Modify: `core/domain/events.py`

### Kontext
Folgt dem Muster von `BuffettCountryPoint` / `BuffettIndicatorSnapshot`.

- [ ] **Step 1: Modelle in `core/domain/models.py` einfügen**

Direkt nach der `BuffettIndicatorSnapshot`-Klasse (nach Zeile 142) einfügen:

```python
@dataclass
class BigMacCountryPoint:
    adj_pct: Optional[float]   # % über/unter USD-PPP (adjustiert für Einkommensniveau)
    signal: Signal             # BULLISH (<-15%), BEARISH (>+15%), NEUTRAL sonst
    date: Optional[str]        # Letztes Update (YYYY-MM-DD)
    name: Optional[str] = None # Landesname


@dataclass
class BigMacSnapshot:
    countries: dict[str, BigMacCountryPoint]  # ISO alpha-3 → Daten
    date: Optional[str]                        # Datum des letzten Economist-Updates

    @staticmethod
    def empty() -> "BigMacSnapshot":
        return BigMacSnapshot(countries={}, date=None)
```

Und `MacroChiefResult` (ca. Zeile 146) um `big_mac` ergänzen:

```python
@dataclass
class MacroChiefResult:
    regime: MarketRegime
    regime_confidence: float
    inflation: InflationSnapshot
    money_supply: MoneySupplySnapshot
    interest_rate: InterestRateSnapshot
    gdp: GDPSnapshot
    labor_income: LaborIncomeSnapshot
    credit: CreditSnapshot
    buffett_indicator: BuffettIndicatorSnapshot
    big_mac: BigMacSnapshot                   # NEU
```

- [ ] **Step 2: Event in `core/domain/events.py` einfügen**

```python
class BigMacDataReady(AgentEvent): pass
```

(Neben/nach `BuffettIndicatorReady`)

- [ ] **Step 3: Import-Test**

```
python -c "from core.domain.models import BigMacSnapshot, BigMacCountryPoint; from core.domain.events import BigMacDataReady; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add core/domain/models.py core/domain/events.py
git commit -m "feat: add BigMacCountryPoint, BigMacSnapshot models and BigMacDataReady event"
```

---

## Task 2: Port-Interface + Adapter-Implementierung

**Files:**
- Modify: `core/ports/data_provider.py`
- Modify: `adapters/data/fred_api.py`

### Kontext
`MacroDataProvider` bekommt eine neue abstrakte Methode. `FredDataProvider` implementiert diese — obwohl die Daten nicht von FRED kommen, folgt das dem etablierten Muster (Buffett-Weltbank-Daten laufen auch über `FredDataProvider`).

- [ ] **Step 1: Methode zum Port hinzufügen**

In `core/ports/data_provider.py`, in der `MacroDataProvider`-Klasse:

```python
@abstractmethod
def get_big_mac_data(self) -> dict:
    """Fetcht den adjustierten Big Mac Index von The Economist GitHub.
    
    Returns dict: iso_a3 → {"adj_pct": float|None, "date": str, "name": str}
    Leerer dict bei Fehler.
    """
```

- [ ] **Step 2: Implementierung in `adapters/data/fred_api.py`**

Import `requests` am Anfang der Datei sicherstellen (ist bereits in requirements.txt).

```python
_BIG_MAC_URL = (
    "https://raw.githubusercontent.com/TheEconomist/big-mac-data/"
    "master/output-data/big-mac-adjusted-index.csv"
)

def get_big_mac_data(self) -> dict:
    """Fetcht den adjustierten Big Mac Index von The Economist GitHub (MIT-Lizenz)."""
    import io
    import csv
    try:
        response = requests.get(_BIG_MAC_URL, timeout=15)
        response.raise_for_status()
        reader = csv.DictReader(io.StringIO(response.text))
        rows = [r for r in reader if r.get("dollar_adj")]  # nur Zeilen mit adj-Wert
        if not rows:
            return {}
        latest_date = max(r["date"] for r in rows)
        result = {}
        for row in (r for r in rows if r["date"] == latest_date):
            iso = row.get("iso_a3", "").strip()
            if not iso:
                continue
            try:
                adj_pct = round(float(row["dollar_adj"]) * 100, 1)  # in %
            except (ValueError, TypeError):
                adj_pct = None
            result[iso] = {
                "adj_pct": adj_pct,
                "date": latest_date,
                "name": row.get("name", "").strip(),
            }
        return result
    except Exception:
        return {}
```

- [ ] **Step 3: Schreibe Tests für den Adapter**

```python
# tests/adapters/test_big_mac_adapter.py
from unittest.mock import MagicMock, patch
from adapters.data.fred_api import FredDataProvider

def _provider():
    p = FredDataProvider.__new__(FredDataProvider)
    p.fred = MagicMock()
    return p

BIG_MAC_CSV = """date,iso_a3,name,dollar_adj
2024-07-01,CHE,Switzerland,0.28
2024-07-01,USA,United States,0.00
2024-07-01,BRA,Brazil,-0.32
2024-07-01,GBR,Britain,0.12
"""

def test_get_big_mac_data_parses_csv_correctly():
    provider = _provider()
    mock_resp = MagicMock()
    mock_resp.text = BIG_MAC_CSV
    mock_resp.raise_for_status = MagicMock()
    with patch("adapters.data.fred_api.requests.get", return_value=mock_resp):
        result = provider.get_big_mac_data()
    assert "CHE" in result
    assert result["CHE"]["adj_pct"] == 28.0    # 0.28 * 100
    assert result["BRA"]["adj_pct"] == -32.0   # -0.32 * 100
    assert result["CHE"]["date"] == "2024-07-01"
    assert result["CHE"]["name"] == "Switzerland"

def test_get_big_mac_data_returns_empty_dict_on_error():
    provider = _provider()
    with patch("adapters.data.fred_api.requests.get", side_effect=Exception("network error")):
        result = provider.get_big_mac_data()
    assert result == {}

def test_get_big_mac_data_uses_latest_date_only():
    provider = _provider()
    csv_two_dates = """date,iso_a3,name,dollar_adj
2024-01-01,CHE,Switzerland,0.20
2024-07-01,CHE,Switzerland,0.28
"""
    mock_resp = MagicMock()
    mock_resp.text = csv_two_dates
    mock_resp.raise_for_status = MagicMock()
    with patch("adapters.data.fred_api.requests.get", return_value=mock_resp):
        result = provider.get_big_mac_data()
    assert result["CHE"]["adj_pct"] == 28.0   # nur neuestes Datum
```

- [ ] **Step 4: Tests ausführen und Fehler bestätigen**

```
pytest tests/adapters/test_big_mac_adapter.py -v
```
Expected: FAIL (Methode noch nicht implementiert)

- [ ] **Step 5: Implementierung einfügen, Tests wiederholen**

```
pytest tests/adapters/test_big_mac_adapter.py -v
```
Expected: alle PASS

- [ ] **Step 6: Commit**

```bash
git add core/ports/data_provider.py adapters/data/fred_api.py tests/adapters/test_big_mac_adapter.py
git commit -m "feat: add get_big_mac_data port + FredDataProvider implementation (Economist GitHub CSV)"
```

---

## Task 3: `BigMacAgent`

**Files:**
- Create: `agents/market_cockpit/macro/big_mac_agent.py`
- Create: `tests/agents/market_cockpit/macro/test_big_mac_agent.py`

### Kontext
Folgt dem Muster von `BuffettIndicatorAgent`: nimmt `macro: MacroDataProvider` und `bus: EventBus`, fetcht Daten via Provider, berechnet pro Land ein Signal, publiziert Event.

Signal-Logik: `adj_pct < -15` → BULLISH (Währung günstig → kann steigen), `adj_pct > +15` → BEARISH (Währung teuer), sonst NEUTRAL.

- [ ] **Step 1: Schreibe failing tests**

```python
# tests/agents/market_cockpit/macro/test_big_mac_agent.py
import asyncio
from unittest.mock import MagicMock
from agents.market_cockpit.macro.big_mac_agent import BigMacAgent, _signal
from core.domain.models import Signal, BigMacSnapshot

def test_signal_undervalued():
    assert _signal(-20.0) == Signal.BULLISH   # stark unterbewertet

def test_signal_overvalued():
    assert _signal(20.0) == Signal.BEARISH    # stark überbewertet

def test_signal_neutral():
    assert _signal(5.0) == Signal.NEUTRAL

def test_signal_none():
    assert _signal(None) == Signal.NEUTRAL

def test_run_creates_snapshot_with_countries():
    provider = MagicMock()
    provider.get_big_mac_data.return_value = {
        "CHE": {"adj_pct": 28.0, "date": "2024-07-01", "name": "Switzerland"},
        "BRA": {"adj_pct": -32.0, "date": "2024-07-01", "name": "Brazil"},
        "USA": {"adj_pct": 0.0, "date": "2024-07-01", "name": "United States"},
    }
    bus = MagicMock()
    agent = BigMacAgent(provider, bus)
    result = asyncio.run(agent.run())
    assert isinstance(result, BigMacSnapshot)
    assert "CHE" in result.countries
    assert result.countries["CHE"].signal == Signal.BEARISH   # 28% überbewertet
    assert result.countries["BRA"].signal == Signal.BULLISH   # 32% unterbewertet
    assert result.countries["USA"].signal == Signal.NEUTRAL   # 0% → Referenz
    assert result.date == "2024-07-01"

def test_run_returns_empty_snapshot_on_provider_failure():
    provider = MagicMock()
    provider.get_big_mac_data.side_effect = Exception("network error")
    bus = MagicMock()
    agent = BigMacAgent(provider, bus)
    result = asyncio.run(agent.run())
    assert result == BigMacSnapshot.empty()
```

- [ ] **Step 2: Tests ausführen und Fehler bestätigen**

```
pytest tests/agents/market_cockpit/macro/test_big_mac_agent.py -v
```
Expected: alle FAIL (Datei existiert noch nicht)

- [ ] **Step 3: Agent implementieren**

```python
# agents/market_cockpit/macro/big_mac_agent.py
import asyncio
from core.domain.events import BigMacDataReady
from core.domain.models import BigMacCountryPoint, BigMacSnapshot, Signal
from core.ports.data_provider import MacroDataProvider
from core.ports.event_bus import EventBus

_BULLISH_THRESHOLD = -15.0   # % unter USD-PPP → Währung günstig
_BEARISH_THRESHOLD = +15.0   # % über USD-PPP → Währung teuer


def _signal(adj_pct: float | None) -> Signal:
    if adj_pct is None:
        return Signal.NEUTRAL
    if adj_pct < _BULLISH_THRESHOLD:
        return Signal.BULLISH
    if adj_pct > _BEARISH_THRESHOLD:
        return Signal.BEARISH
    return Signal.NEUTRAL


class BigMacAgent:
    def __init__(self, macro: MacroDataProvider, bus: EventBus):
        self.macro = macro
        self.bus   = bus

    async def run(self) -> BigMacSnapshot:
        try:
            raw = await asyncio.to_thread(self.macro.get_big_mac_data)
        except Exception:
            return BigMacSnapshot.empty()

        if not raw:
            return BigMacSnapshot.empty()

        countries: dict[str, BigMacCountryPoint] = {}
        date: str | None = None

        for iso, data in raw.items():
            adj_pct = data.get("adj_pct")
            entry_date = data.get("date")
            if date is None and entry_date:
                date = entry_date
            countries[iso] = BigMacCountryPoint(
                adj_pct=adj_pct,
                signal=_signal(adj_pct),
                date=entry_date,
                name=data.get("name"),
            )

        snapshot = BigMacSnapshot(countries=countries, date=date)
        self.bus.publish(BigMacDataReady(source="big_mac_agent", payload={
            "date": date, "country_count": len(countries),
        }))
        return snapshot

    @staticmethod
    def default() -> BigMacSnapshot:
        return BigMacSnapshot.empty()
```

- [ ] **Step 4: Tests ausführen**

```
pytest tests/agents/market_cockpit/macro/test_big_mac_agent.py -v
```
Expected: alle PASS

- [ ] **Step 5: Commit**

```bash
git add agents/market_cockpit/macro/big_mac_agent.py tests/agents/market_cockpit/macro/test_big_mac_agent.py
git commit -m "feat: add BigMacAgent with BULLISH/BEARISH signal per country"
```

---

## Task 4: `MacroChiefAgent` — BigMacAgent integrieren

**Files:**
- Modify: `agents/market_cockpit/macro_chief_agent.py`
- Modify: `core/domain/top_down_context.py`

### Kontext
`MacroChiefAgent.run()` muss `BigMacAgent` parallel zu den anderen Agents ausführen und das Ergebnis in `MacroChiefResult` eintragen. `top_down_context.py` erhält einen optionalen Hinweis wenn die Währung des analysierten Landes signifikant fehlbewertet ist.

**Hinweis:** `MacroChiefResult` hat in Schritt 1 das neue Feld `big_mac` erhalten — es muss jetzt befüllt werden. Wenn das Feld noch nicht im `default()` enthalten ist, muss es dort ebenfalls ergänzt werden.

- [ ] **Step 1: BigMacAgent in `macro_chief_agent.py` einbinden**

Import hinzufügen:
```python
from agents.market_cockpit.macro.big_mac_agent import BigMacAgent
```

In `__init__`:
```python
self.big_mac_agent = BigMacAgent(macro, bus)
```

In `run()` — `asyncio.gather` um einen Eintrag ergänzen:
```python
results = await asyncio.gather(
    self.inflation_agent.run(),
    self.money_supply_agent.run(),
    self.interest_rate_agent.run(),
    self.gdp_agent.run(),
    self.labor_income_agent.run(),
    self.credit_agent.run(),
    self.buffett_indicator_agent.run(),
    self.big_mac_agent.run(),              # NEU (Index 7)
    asyncio.to_thread(self._macro.get_economic_state),  # jetzt Index 8
    return_exceptions=True,
)
```

`_safe`-Zuweisungen anpassen:
```python
big_mac           = _safe(results[7], BigMacAgent.default())
state             = _safe(results[8], {})
```

`MacroChiefResult(...)` um `big_mac=big_mac` ergänzen.

Und `default()` ebenfalls:
```python
@staticmethod
def default() -> MacroChiefResult:
    ...
    big_mac=BigMacSnapshot.empty(),
    ...
```

- [ ] **Step 2: Import-Test und Smoke-Test**

```
python -c "
from unittest.mock import MagicMock
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
a = MacroChiefAgent.__new__(MacroChiefAgent)
print('Import OK')
"
```
Expected: `Import OK`

- [ ] **Step 3: Big-Mac-Hinweis in `top_down_context.py`**

Neue Hilfsfunktion vor `derive_top_down_context` einfügen:

```python
def _big_mac_note(big_mac, market: str) -> str | None:
    """Gibt einen Hinweis zurück wenn die Währung des analysierten Landes signifikant fehl bewertet ist."""
    if big_mac is None or not hasattr(big_mac, "countries"):
        return None
    # ISO-2 → ISO-3 Mapping für die wichtigsten Märkte
    _MARKET_TO_ISO3 = {
        "USA": "USA", "CH": "CHE", "DE": "DEU", "FR": "FRA",
        "IT": "ITA", "ES": "ESP", "GB": "GBR", "JP": "JPN",
        "CN": "CHN", "BR": "BRA", "IN": "IND", "AU": "AUS",
        "CA": "CAN", "KR": "KOR", "MX": "MEX", "RU": "RUS",
        "AT": "AUT", "NL": "NLD", "BE": "BEL", "PT": "PRT",
        "FI": "FIN", "IE": "IRL", "SE": "SWE", "NO": "NOR",
        "DK": "DNK", "PL": "POL", "CZ": "CZE", "HU": "HUN",
    }
    iso3 = _MARKET_TO_ISO3.get(market.upper())
    if not iso3:
        return None
    country = big_mac.countries.get(iso3)
    if not country or country.adj_pct is None:
        return None
    if abs(country.adj_pct) < 15.0:
        return None
    direction = "überbewertet" if country.adj_pct > 0 else "unterbewertet"
    return (
        f"Big Mac Index: {country.name or iso3}-Währung laut adj. Index "
        f"{abs(country.adj_pct):.0f}% {direction} (Stand: {country.date or 'n/a'})"
    )
```

Und in `derive_top_down_context` einbinden — nur für `equity`, `etf`, `index` (Währungsbewertung ist für Rohstoffe irrelevant):

```python
if asset_class in ("equity", "etf", "index"):
    big_mac_snap = getattr(cockpit.macro, "big_mac", None)
    bm_note = _big_mac_note(big_mac_snap, market)
    if bm_note:
        notes.append(bm_note)
```

- [ ] **Step 4: Schreibe Test für Big-Mac-Hinweis**

```python
# tests/core/test_top_down_context.py (ergänzen)
from agents.market_cockpit.macro.big_mac_agent import _signal
from core.domain.models import BigMacSnapshot, BigMacCountryPoint, Signal

def test_big_mac_note_appears_for_significant_misalignment():
    from core.domain.top_down_context import derive_top_down_context
    from unittest.mock import MagicMock
    cockpit = _make_cockpit(inverted=False, spread=None)
    # CHE überbewertet
    cockpit.macro.big_mac = BigMacSnapshot(
        countries={"CHE": BigMacCountryPoint(adj_pct=28.0, signal=Signal.BEARISH, date="2024-07-01", name="Switzerland")},
        date="2024-07-01",
    )
    result = derive_top_down_context(cockpit, sector="Financials", market="CH", asset_class="equity")
    assert "Big Mac" in result
    assert "28" in result

def test_big_mac_note_absent_for_small_misalignment():
    from core.domain.top_down_context import derive_top_down_context
    from unittest.mock import MagicMock
    cockpit = _make_cockpit(inverted=False, spread=None)
    cockpit.macro.big_mac = BigMacSnapshot(
        countries={"CHE": BigMacCountryPoint(adj_pct=5.0, signal=Signal.NEUTRAL, date="2024-07-01", name="Switzerland")},
        date="2024-07-01",
    )
    result = derive_top_down_context(cockpit, sector="Financials", market="CH", asset_class="equity")
    assert "Big Mac" not in result

def test_big_mac_note_absent_for_commodities():
    from core.domain.top_down_context import derive_top_down_context
    cockpit = _make_cockpit(inverted=False, spread=None)
    cockpit.macro.big_mac = BigMacSnapshot(
        countries={"CHE": BigMacCountryPoint(adj_pct=28.0, signal=Signal.BEARISH, date="2024-07-01", name="Switzerland")},
        date="2024-07-01",
    )
    result = derive_top_down_context(cockpit, sector="Energy", market="CH", asset_class="commodity")
    assert "Big Mac" not in result
```

- [ ] **Step 5: Tests ausführen**

```
pytest tests/core/test_top_down_context.py -v
```
Expected: alle PASS (inkl. neue Big-Mac-Tests)

- [ ] **Step 6: Commit**

```bash
git add agents/market_cockpit/macro_chief_agent.py core/domain/top_down_context.py tests/core/test_top_down_context.py
git commit -m "feat: integrate BigMacAgent into MacroChiefAgent, add big mac note to top_down_context"
```

---

## Task 5: `MacroChiefResult.default()` updaten + Integrationsprüfung

**Files:**
- Verify: `agents/market_cockpit/macro_chief_agent.py` (default-Methode)

### Kontext
Überall wo `MacroChiefAgent.default()` aufgerufen wird, muss jetzt `big_mac=BigMacSnapshot.empty()` enthalten sein. Andernfalls crashen alle Downstream-Consumer die `cockpit.macro.big_mac` zugreifen.

- [ ] **Step 1: default()-Methode prüfen**

```
grep -n "def default" agents/market_cockpit/macro_chief_agent.py
```

Lese die Methode — sie muss alle Felder von `MacroChiefResult` befüllen. Wenn `big_mac` fehlt, ergänzen:

```python
@staticmethod
def default() -> MacroChiefResult:
    return MacroChiefResult(
        regime=MarketRegime.EXPANSION,
        regime_confidence=0.5,
        inflation=InflationAgent.default(),
        money_supply=MoneySupplyAgent.default(),
        interest_rate=InterestRateAgent.default(),
        gdp=GDPAgent.default(),
        labor_income=LaborIncomeAgent.default(),
        credit=CreditAgent.default(),
        buffett_indicator=BuffettIndicatorAgent.default(),
        big_mac=BigMacSnapshot.empty(),    # NEU
    )
```

- [ ] **Step 2: Alle Tests durchlaufen**

```
pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: alle bestehenden Tests PASS, keine neuen Fehler

- [ ] **Step 3: Manueller Smoke-Test — Import-Kette prüfen**

```
python -c "
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
d = MacroChiefAgent.default()
print('regime:', d.regime)
print('big_mac countries:', len(d.big_mac.countries))
print('OK')
"
```
Expected:
```
regime: Aufschwung
big_mac countries: 0
OK
```

- [ ] **Step 4: Commit**

```bash
git add agents/market_cockpit/macro_chief_agent.py
git commit -m "feat: MacroChiefAgent.default() includes BigMacSnapshot.empty()"
```

---

## Gesamtübersicht

| Task | Inhalt | Status |
|---|---|---|
| 1 | Datenmodelle + Event | - [ ] |
| 2 | Port + Adapter (Economist GitHub CSV) | - [ ] |
| 3 | BigMacAgent (Signal pro Land) | - [ ] |
| 4 | MacroChiefAgent Integration + top_down_context Hinweis | - [ ] |
| 5 | default() updaten + Integrationstest | - [ ] |

---

## Einschränkungen — sichtbar im Dashboard

Aus `frontend_notes.md` — müssen bei der Anzeige kommuniziert werden:

1. **Nicht-handelsfähige Güter** stark gewichtet → nicht 1:1 auf Wechselkurse übertragbar
2. **Nur für Länder mit McDonald's-Präsenz** verfügbar (~50 Länder)
3. **Halbjährlich aktualisiert** (Jan/Jul) — keine Echtzeit-Daten
4. **Lokale Steuern/Subventionen** verzerren den Preis (z.B. CH: hohe Mindestlöhne)

## Offene Frontend-Entscheidungen (aus `frontend_notes.md`)

- Tabelle vs. Balkendiagramm für Ländervergleich
- Highlight des analysierten Landes
- Datum der letzten Datenpublikation anzeigen
