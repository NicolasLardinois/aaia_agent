# CNN Fear & Greed — Daten-Adapter & Verdrahtung — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den CNN-Fear-&-Greed-Index als echte Live-Datenquelle anbinden, durch die Composition Roots injizieren und den redundant gewordenen Sentiment-Stub entfernen.

**Architecture:** Event-Driven + Hexagonal. Der `FearGreedAgent` (bereits fertig) hängt am Port `SentimentDataProvider`; der neue Adapter wird über `SentimentChiefAgent` → `TopDownOrchestrator` → `app/main.py`/`app/server.py` injiziert. I/O lebt nur im Adapter; Parsing ist eine reine, separat getestete Funktion.

**Tech Stack:** Python, `requests`, pytest, asyncio.

Spec: `docs/superpowers/specs/2026-06-23-cnn-fear-greed-design.md`.

## Global Constraints

- Sprache: Code-Kommentare und Commit-Messages auf **Deutsch** (bestehender Stil).
- **TDD verpflichtend:** erst der fehlschlagende Test, dann Implementierung.
- Tests müssen **offline-sicher** sein — `tests/conftest.py` blockt echtes `requests`/`yfinance`. Netz wird per `unittest.mock.patch` auf das Modul gemockt (Muster: `tests/adapters/test_ecb_yield_spreads.py`).
- Einheit Fear & Greed: **0–100** (nicht 0–1). Sanity-Cap: außerhalb `[0, 100]` → `None`.
- Defensive Aggregation: jede Fehlerquelle → `None` → Agent liefert `SignalStatus.UNAVAILABLE`, nie ein Crash.
- Git: Feature-Branch `feat/cnn-fear-greed`, kein direkter Merge nach `master`. Stagen nur explizite Pfade (kein `git add -A`). Commit-Trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## Dateienübersicht

**Neu:**
- `adapters/data/cnn_fear_greed.py` — Adapter `CnnFearGreedProvider` + reine `_parse`-Funktion.
- `tests/adapters/test_cnn_fear_greed.py` — Tests für `_parse` und den Adapter.

**Geändert:**
- `agents/market_cockpit/sentiment_chief_agent.py` — optionaler `sentiment`-Parameter, an `FearGreedAgent` durchgereicht.
- `orchestrators/top_down_orchestrator.py` — optionaler `sentiment`-Parameter, an `SentimentChiefAgent` durchgereicht.
- `app/main.py` — `CnnFearGreedProvider()` in `run_dashboard` injizieren.
- `app/server.py` — `CnnFearGreedProvider()` in `make_orchestrator` injizieren.
- `tests/test_integration_wiring.py` — Stub-Test entfernen, Verdrahtungs-Tests ergänzen.
- `docs/open_todos.md` — Logbuch-Einträge abhaken.

**Gelöscht:**
- `adapters/data/sentiment_stub.py` — `SentimentStubProvider` (redundant; `provider=None` verhält sich identisch).

---

### Task 1: Adapter `CnnFearGreedProvider` + reine `_parse`-Funktion

**Files:**
- Create: `adapters/data/cnn_fear_greed.py`
- Test: `tests/adapters/test_cnn_fear_greed.py`

**Interfaces:**
- Produces:
  - `_parse(data: dict) -> float | None` — extrahiert den Score 0–100 aus dem CNN-JSON; `None` bei fehlender Struktur, nicht-numerisch oder außerhalb `[0, 100]`.
  - `class CnnFearGreedProvider(SentimentDataProvider)` mit `get_fear_greed(self) -> float | None`.

- [ ] **Step 1: Failing Tests schreiben** — `tests/adapters/test_cnn_fear_greed.py`

```python
"""TDD-Tests fuer CnnFearGreedProvider und die reine _parse-Funktion."""
from unittest.mock import patch, MagicMock

from adapters.data.cnn_fear_greed import CnnFearGreedProvider, _parse


def _payload(score):
    """Spiegelt die verschachtelte CNN-Struktur: data['fear_and_greed']['score']."""
    return {"fear_and_greed": {"score": score, "rating": "neutral"}}


# ── _parse (rein, kein Netz) ───────────────────────────────────────────────
def test_parse_gueltiger_score():
    assert _parse(_payload(42.7)) == 42.7


def test_parse_rundet_auf_eine_stelle():
    assert _parse(_payload(42.66)) == 42.7


def test_parse_grenzen_0_und_100_gueltig():
    assert _parse(_payload(0)) == 0.0
    assert _parse(_payload(100)) == 100.0


def test_parse_ausserhalb_bereich_none():
    assert _parse(_payload(150)) is None
    assert _parse(_payload(-5)) is None


def test_parse_fehlender_key_none():
    assert _parse({}) is None
    assert _parse({"fear_and_greed": {}}) is None


def test_parse_nicht_numerisch_none():
    assert _parse(_payload("abc")) is None
    assert _parse(_payload(None)) is None


# ── Adapter (gemocktes requests.get) ───────────────────────────────────────
def _make_response(payload):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


def test_get_fear_greed_liefert_score():
    with patch("adapters.data.cnn_fear_greed.requests.get",
               return_value=_make_response(_payload(63.2))):
        assert CnnFearGreedProvider().get_fear_greed() == 63.2


def test_get_fear_greed_bei_netzfehler_none():
    with patch("adapters.data.cnn_fear_greed.requests.get",
               side_effect=ConnectionError("boom")):
        assert CnnFearGreedProvider().get_fear_greed() is None


def test_get_fear_greed_bei_http_error_none():
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("418 Teapot")
    with patch("adapters.data.cnn_fear_greed.requests.get", return_value=resp):
        assert CnnFearGreedProvider().get_fear_greed() is None
```

- [ ] **Step 2: Test läuft (rot)**

Run: `python -m pytest tests/adapters/test_cnn_fear_greed.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'adapters.data.cnn_fear_greed'`.

- [ ] **Step 3: Adapter implementieren** — `adapters/data/cnn_fear_greed.py`

```python
"""CNN Fear & Greed Index — echter Daten-Adapter.

Quelle: https://production.dataviz.cnn.io/index/fearandgreed/graphdata/
Liefert den aktuellen Index-Wert 0–100 (0 = Extreme Fear, 100 = Extreme Greed).

Datenrealitaet (bewusst behandelt):
- CNN blockt Anfragen ohne Browser-User-Agent (HTTP 418) → Header gesetzt.
- Der aktuelle Wert liegt verschachtelt unter data["fear_and_greed"]["score"].
- Inoffizieller Endpoint: bei jeder Stoerung → None → Agent liefert UNAVAILABLE.
"""
import requests
from typing import Optional

from core.ports.data_provider import SentimentDataProvider

_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _parse(data: dict) -> Optional[float]:
    """Rein: extrahiert den aktuellen Fear&Greed-Score (0–100) aus dem CNN-JSON.

    Rueckgabe: gerundeter Score, oder None falls die Struktur fehlt, der Wert
    nicht-numerisch ist oder ausserhalb des plausiblen Bereichs [0, 100] liegt
    (Sanity-Cap, AGENTS.md §3 — Einheit ist 0–100, nicht 0–1).
    """
    try:
        score = float(data["fear_and_greed"]["score"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (0.0 <= score <= 100.0):
        return None
    return round(score, 1)


class CnnFearGreedProvider(SentimentDataProvider):
    """SentimentDataProvider auf Basis des CNN-Fear-&-Greed-Endpoints."""

    def get_fear_greed(self) -> Optional[float]:
        try:
            resp = requests.get(_URL, headers=_HEADERS, timeout=10)
            resp.raise_for_status()
            return _parse(resp.json())
        except Exception:
            return None
```

- [ ] **Step 4: Test läuft (grün)**

Run: `python -m pytest tests/adapters/test_cnn_fear_greed.py -q`
Expected: PASS (alle 9 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add adapters/data/cnn_fear_greed.py tests/adapters/test_cnn_fear_greed.py
git commit -m "feat(sentiment): CNN Fear & Greed Adapter (echte Datenquelle)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Verdrahtung durchreichen + Sentiment-Stub entfernen

**Files:**
- Modify: `agents/market_cockpit/sentiment_chief_agent.py`
- Modify: `orchestrators/top_down_orchestrator.py`
- Modify: `tests/test_integration_wiring.py`
- Delete: `adapters/data/sentiment_stub.py`

**Interfaces:**
- Consumes: `CnnFearGreedProvider` (Task 1); Port `SentimentDataProvider`.
- Produces:
  - `SentimentChiefAgent(market, bus, sentiment: SentimentDataProvider | None = None)` — reicht `sentiment` als `provider` an `FearGreedAgent` durch.
  - `TopDownOrchestrator(macro, ecb, snb, market, bus, sentiment: SentimentDataProvider | None = None)` — reicht `sentiment` an `SentimentChiefAgent` durch.

- [ ] **Step 1: Failing Tests schreiben** — `tests/test_integration_wiring.py` anpassen

(a) Import-Zeile für den Stub entfernen:

```python
from adapters.data.sentiment_stub import SentimentStubProvider
```
→ **löschen**.

(b) Import aus `core.domain.models` um `Signal` erweitern:

```python
from core.domain.models import SignalStatus
```
→ ersetzen durch:
```python
from core.domain.models import Signal, SignalStatus
```

(c) Den Stub-Test komplett entfernen:

```python
def test_sentiment_stub_provider_returns_none():
    """SentimentStubProvider: Stub liefert None → FearGreedAgent UNAVAILABLE."""
    stub = SentimentStubProvider()
    assert stub.get_fear_greed() is None
```
→ **löschen**.

(d) Zwei neue Verdrahtungs-Tests am Dateiende ergänzen:

```python
def test_sentiment_chief_uses_injected_fear_greed_provider():
    """SentimentChiefAgent reicht den injizierten Provider an den FearGreedAgent
    durch → Extreme-Fear-Wert 10 ergibt BULLISH (contrarian) und AVAILABLE."""
    class _FakeSentiment:
        def get_fear_greed(self):
            return 10.0
    market = MagicMock()
    market.get_current_price.return_value = None
    bus = MagicMock()
    chief = SentimentChiefAgent(market, bus, sentiment=_FakeSentiment())
    result = asyncio.run(chief.run())
    assert result.fear_greed.value == 10.0
    assert result.fear_greed.signal == Signal.BULLISH
    assert result.fear_greed.status == SignalStatus.AVAILABLE


def test_top_down_orchestrator_threads_sentiment_provider():
    """TopDownOrchestrator reicht den sentiment-Provider bis zum FearGreedAgent durch."""
    from orchestrators.top_down_orchestrator import TopDownOrchestrator
    fake = MagicMock()
    orch = TopDownOrchestrator(
        macro=MagicMock(), ecb=MagicMock(), snb=MagicMock(),
        market=MagicMock(), bus=MagicMock(), sentiment=fake,
    )
    assert orch.sentiment_chief.fear_greed_agent.provider is fake
```

- [ ] **Step 2: Test läuft (rot)**

Run: `python -m pytest tests/test_integration_wiring.py -q`
Expected: FAIL — `SentimentChiefAgent()`/`TopDownOrchestrator()` akzeptieren das `sentiment`-Argument noch nicht (`TypeError: unexpected keyword argument 'sentiment'`).

- [ ] **Step 3: `SentimentChiefAgent` erweitern** — `agents/market_cockpit/sentiment_chief_agent.py`

Import-Zeile ersetzen:
```python
from core.ports.data_provider import MarketDataProvider
```
→
```python
from core.ports.data_provider import MarketDataProvider, SentimentDataProvider
```

Konstruktor ersetzen:
```python
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        self.vix_agent        = VIXAgent(market, bus)
        self.fear_greed_agent = FearGreedAgent(bus)
        self.put_call_agent   = PutCallAgent(market, bus)
```
→
```python
    def __init__(self, market: MarketDataProvider, bus: EventBus,
                 sentiment: SentimentDataProvider | None = None):
        self.bus = bus
        self.vix_agent        = VIXAgent(market, bus)
        self.fear_greed_agent = FearGreedAgent(bus, provider=sentiment)
        self.put_call_agent   = PutCallAgent(market, bus)
```

- [ ] **Step 4: `TopDownOrchestrator` erweitern** — `orchestrators/top_down_orchestrator.py`

Import-Zeile ersetzen:
```python
from core.ports.data_provider import EcbDataProvider, MacroDataProvider, MarketDataProvider, SnbDataProvider
```
→
```python
from core.ports.data_provider import EcbDataProvider, MacroDataProvider, MarketDataProvider, SnbDataProvider, SentimentDataProvider
```

Konstruktor-Signatur und Sentiment-Chief-Zeile ersetzen:
```python
    def __init__(
        self,
        macro: MacroDataProvider,
        ecb: EcbDataProvider,
        snb: SnbDataProvider,
        market: MarketDataProvider,
        bus: EventBus,
    ):
        self.macro_chief       = MacroChiefAgent(macro, ecb, snb, bus)
        self.commodity_chief   = CommodityChiefAgentMakro(market, bus)
        self.sentiment_chief   = SentimentChiefAgent(market, bus)
```
→
```python
    def __init__(
        self,
        macro: MacroDataProvider,
        ecb: EcbDataProvider,
        snb: SnbDataProvider,
        market: MarketDataProvider,
        bus: EventBus,
        sentiment: SentimentDataProvider | None = None,
    ):
        self.macro_chief       = MacroChiefAgent(macro, ecb, snb, bus)
        self.commodity_chief   = CommodityChiefAgentMakro(market, bus)
        self.sentiment_chief   = SentimentChiefAgent(market, bus, sentiment)
```

- [ ] **Step 5: Stub-Datei löschen**

```bash
git rm adapters/data/sentiment_stub.py
```

- [ ] **Step 6: Tests laufen (grün)**

Run: `python -m pytest tests/test_integration_wiring.py -q`
Expected: PASS (Stub-Test weg, zwei neue grün, bestehende „ohne Provider → None" weiter grün).

- [ ] **Step 7: Commit**

```bash
git add agents/market_cockpit/sentiment_chief_agent.py orchestrators/top_down_orchestrator.py tests/test_integration_wiring.py adapters/data/sentiment_stub.py
git commit -m "feat(sentiment): sentiment-Provider durch Chief + Orchestrator durchreichen; Stub entfernen

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Composition Roots verdrahten + Logbuch

**Files:**
- Modify: `app/main.py`
- Modify: `app/server.py`
- Modify: `docs/open_todos.md`

**Interfaces:**
- Consumes: `CnnFearGreedProvider` (Task 1); `TopDownOrchestrator(..., sentiment=…)` (Task 2).

- [ ] **Step 1: `app/main.py` verdrahten**

Import nach den übrigen `adapters.data`-Imports ergänzen (nach Zeile 24, `from adapters.data.fred_snb import FredSnbProvider`):
```python
from adapters.data.cnn_fear_greed import CnnFearGreedProvider
```

In `run_dashboard` den `TopDownOrchestrator(...)`-Aufruf um `sentiment` ergänzen:
```python
    orch  = TopDownOrchestrator(
        macro=fred,
        ecb=EcbSdwProvider(),
        snb=FredSnbProvider(FRED_API_KEY),
        market=YahooFinanceProvider(),
        bus=bus,
    )
```
→
```python
    orch  = TopDownOrchestrator(
        macro=fred,
        ecb=EcbSdwProvider(),
        snb=FredSnbProvider(FRED_API_KEY),
        market=YahooFinanceProvider(),
        bus=bus,
        sentiment=CnnFearGreedProvider(),
    )
```

- [ ] **Step 2: `app/server.py` verdrahten**

Import ergänzen (nach Zeile 12, `from adapters.data.fred_snb import FredSnbProvider`):
```python
from adapters.data.cnn_fear_greed import CnnFearGreedProvider
```

In `make_orchestrator` den Aufruf ergänzen:
```python
    return TopDownOrchestrator(
        macro=FredDataProvider(FRED_API_KEY),
        ecb=EcbSdwProvider(),
        snb=FredSnbProvider(FRED_API_KEY),
        market=YahooFinanceProvider(),
        bus=bus,
    )
```
→
```python
    return TopDownOrchestrator(
        macro=FredDataProvider(FRED_API_KEY),
        ecb=EcbSdwProvider(),
        snb=FredSnbProvider(FRED_API_KEY),
        market=YahooFinanceProvider(),
        bus=bus,
        sentiment=CnnFearGreedProvider(),
    )
```

- [ ] **Step 3: Verifikation — komplette Suite offline-sicher grün**

Run: `python -m pytest -q`
Expected: PASS (gesamte Suite grün; keine echten Netz-Calls). Notiere die Zahl der grünen Tests für die PR-Beschreibung.

- [ ] **Step 4: Logbuch `docs/open_todos.md` pflegen**

Im Abschnitt „## 2. STUB-APIS" den Sentiment-Stub-Bezug und im Fear-&-Greed-Eintrag (Zeile ~431) abhaken bzw. mit Lösungsvermerk versehen. Zuerst die betroffenen Stellen lesen, dann gezielt editieren:

Run zum Auffinden: `python -m pytest --collect-only -q > /dev/null; grep -n "Fear&Greed\|sentiment_stub\|SentimentStubProvider\|cnn_fear_greed" docs/open_todos.md`

Eintrag(e) abhaken mit Vermerk in der Form:
```
- [x] **Fear & Greed live angebunden** — `adapters/data/cnn_fear_greed.py` (`CnnFearGreedProvider`), injiziert in `app/main.py` + `app/server.py` via `TopDownOrchestrator(sentiment=…)`. **Lösung:** echter CNN-Adapter (0–100, Sanity-Cap, Browser-UA, verschachteltes JSON `fear_and_greed.score`); reine `_parse`-Funktion getestet; Fehler → `None` → `UNAVAILABLE`. Redundanter `sentiment_stub.py` entfernt (PR-Branch `feat/cnn-fear-greed`).
```

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/server.py docs/open_todos.md
git commit -m "feat(sentiment): CNN Fear & Greed in Composition Roots verdrahten + Logbuch

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (gegen die Spec)

**1. Spec-Abdeckung:**
- Adapter `cnn_fear_greed.py` mit getrenntem `_parse`, User-Agent, verschachteltem JSON, Sanity-Cap → Task 1. ✓
- Verdrahtung durch Chief + Orchestrator, Default `None` → Task 2. ✓
- Injektion in `app/main.py` + `app/server.py` → Task 3. ✓
- Stub-Entfernung inkl. Test → Task 2. ✓
- Tests (`_parse`-Grenzfälle, requests-Mock, Verdrahtung mit Fake) → Task 1 + Task 2. ✓
- Logbuch-Pflege, README unverändert → Task 3. ✓
- Signal-/Label-Logik unverändert → kein Task berührt sie. ✓

**2. Placeholder-Scan:** keine TBD/TODO/„handle edge cases"; jeder Code-Schritt zeigt vollständigen Code. ✓

**3. Typ-Konsistenz:** `_parse(data: dict) -> float | None`, `get_fear_greed() -> float | None`, `sentiment: SentimentDataProvider | None = None` in Chief und Orchestrator identisch; `FearGreedAgent(bus, provider=sentiment)` entspricht der bestehenden Signatur `FearGreedAgent(bus, provider=None)`. ✓
