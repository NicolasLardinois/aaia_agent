# API-Brücke (Cockpit-Flow) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine eingehende Web-API-Schicht (FastAPI HTTP + WebSocket) bauen, die den bestehenden Cockpit-/Top-Down-Lauf für ein künftiges Frontend per `GET`/`POST`/WebSocket erreichbar macht — ohne Fachlogik zu duplizieren.

**Architecture:** Hexagonaler **eingehender Adapter** unter `adapters/api/`. Die API ruft den bestehenden `TopDownOrchestrator` auf (rechnet nichts selbst). Der WebSocket-Stream ist der **erste echte Zuhörer** des `EventBus` (über eine neue `subscribe_all`-Methode des `InMemoryEventBus`). Eine eigene, pure Serialisierungs-Funktion erzeugt den Frontend-Vertrag (statt des verlustbehafteten `judge`-Caches). Pro Cockpit-Domäne wird ein echter `UNAVAILABLE`-Status mitgeliefert (neues `status`-Feld auf den Chief-Results, nutzt das bestehende `SignalStatus`-Enum).

**Tech Stack:** Python 3.10+, FastAPI, uvicorn, httpx (nur für `TestClient` in Tests), pytest. asyncio.

## Global Constraints

- **Sprache:** Code-Kommentare und Commit-Messages auf **Deutsch** (Projektstil). Commit-Präfixe: `feat(...)`, `test(...)`, `chore(...)`.
- **Hexagonal:** Agenten/`core/` importieren **nie** aus `adapters/`. Der API-Adapter darf den konkreten `InMemoryEventBus` kennen (er wird im Composition Root `app/server.py` verdrahtet).
- **TDD verpflichtend (AGENTS.md §4):** Erst der fehlschlagende Test, dann minimaler Code bis grün. Keine Implementierung ohne vorher geschriebenen, roten Test.
- **Async-Tests** werden wie im Projekt üblich geschrieben: `asyncio.run(coro())` in normalen `def test_…()`-Funktionen, **kein** `pytest.mark.asyncio`. Fakes/`MagicMock()` statt echter Provider — **kein** echter Netz-Call im Test.
- **`UNAVAILABLE` ≠ 0 ≠ NEUTRAL** (AGENTS.md §3 / Frontend-Spec §5.4): eine ausgefallene Domäne wird als `status: "unavailable"` markiert, nie als neutrales Signal verfälscht, und aus `sources_active` ausgenommen.
- **Magische Zahlen vermeiden:** Schwellen/Annahmen im Kommentar begründen.
- **Tests spiegeln die Paketstruktur:** API-Tests unter `tests/adapters/api/`.
- Test-Lauf gezielt: `python -m pytest tests/adapters/api -q`; gesamt: `python -m pytest -q`.

---

## File Structure

| Datei | Verantwortung |
|---|---|
| `core/domain/models.py` (modify) | `status: SignalStatus`-Feld an die 5 Chief-Results |
| `agents/market_cockpit/macro_chief_agent.py` (modify) | `default()` → `status=UNAVAILABLE` |
| `agents/market_cockpit/commodity_chief_agent_makro.py` (modify) | `default()` → `status=UNAVAILABLE` |
| `agents/market_cockpit/sentiment_chief_agent.py` (modify) | `default()` → `status=UNAVAILABLE` |
| `agents/market_cockpit/yield_curve_chief_agent.py` (modify) | `default()` → `status=UNAVAILABLE` |
| `agents/market_cockpit/sector_chief_agent.py` (modify) | `default()` → `status=UNAVAILABLE` |
| `adapters/event_bus/redis_bus.py` (modify) | `subscribe_all(handler)` am `InMemoryEventBus` |
| `adapters/api/__init__.py` (create) | Paket-Init |
| `adapters/api/cockpit_serializer.py` (create) | pure `cockpit_to_dict(result) -> dict` |
| `adapters/api/event_serializer.py` (create) | pure `event_to_dict(event, run_id) -> dict` |
| `adapters/api/ws_broadcaster.py` (create) | `WebSocketBroadcaster` (Verbindungsverwaltung + `broadcast`) |
| `adapters/api/run_manager.py` (create) | `RunManager` (Lauf als Hintergrund-Task, letztes Ergebnis, run_id) |
| `adapters/api/routes_cockpit.py` (create) | `build_router(run_manager)` — GET/POST/WS |
| `adapters/api/app_factory.py` (create) | `create_app(run_manager) -> FastAPI` |
| `app/server.py` (create) | Composition Root + `uvicorn.run` |
| `requirements.txt` (modify) | `+ fastapi`, `+ uvicorn[standard]`, `+ httpx` |
| `tests/adapters/api/__init__.py` (create) | Test-Paket-Init |

---

## Task 1: `status`-Feld auf den Chief-Results (UNAVAILABLE-Kontrakt)

**Files:**
- Modify: `core/domain/models.py` (Klassen `MacroChiefResult`, `CommodityChiefResult`, `SentimentChiefResult`, `YieldCurveChiefResult`, `SectorChiefResult`)
- Modify: `agents/market_cockpit/macro_chief_agent.py:120` (`default()`), `commodity_chief_agent_makro.py:92`, `sentiment_chief_agent.py:60`, `yield_curve_chief_agent.py:74`, `sector_chief_agent.py:50`
- Test: `tests/test_chief_default_status.py`

**Interfaces:**
- Produces: jedes Chief-Result hat `status: SignalStatus` (Default `SignalStatus.AVAILABLE`); jede `Chief.default()` liefert `status=SignalStatus.UNAVAILABLE`. `SignalStatus` ist bereits in `core/domain/models.py` definiert (`AVAILABLE="available"`, `UNAVAILABLE="unavailable"`).

- [ ] **Step 1: Failing-Test schreiben**

`tests/test_chief_default_status.py`:
```python
from core.domain.models import SignalStatus
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent


def test_each_chief_default_is_unavailable():
    assert MacroChiefAgent.default().status is SignalStatus.UNAVAILABLE
    assert CommodityChiefAgentMakro.default().status is SignalStatus.UNAVAILABLE
    assert SentimentChiefAgent.default().status is SignalStatus.UNAVAILABLE
    assert YieldCurveChiefAgent.default().status is SignalStatus.UNAVAILABLE
    assert SectorChiefAgent.default().status is SignalStatus.UNAVAILABLE


def test_sector_result_defaults_to_available_when_built_normally():
    # Ein normal konstruiertes Result ist verfügbar (Default-Feldwert).
    from core.domain.models import SectorChiefResult, SectorPerformanceSnapshot, SectorRotationSnapshot, Signal
    perf = SectorPerformanceSnapshot(usa={}, eurozone={}, leading_usa="", lagging_usa="", leading_eu="", lagging_eu="")
    rot = SectorRotationSnapshot(recommended=[], avoid=[], alignment="neutral", signal=Signal.NEUTRAL)
    result = SectorChiefResult(performance=perf, rotation=rot)
    assert result.status is SignalStatus.AVAILABLE
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/test_chief_default_status.py -q`
Expected: FAIL (`AttributeError: 'MacroChiefResult' object has no attribute 'status'` bzw. `TypeError` beim Konstruieren).

- [ ] **Step 3: `status`-Feld an die 5 Dataclasses anhängen**

In `core/domain/models.py` jeweils als **letztes** Feld der Klasse hinzufügen (alle fünf sind `@dataclass`; `SignalStatus` ist im selben Modul definiert):

`MacroChiefResult` (nach `buffett_indicator`):
```python
    status: SignalStatus = SignalStatus.AVAILABLE
```
`CommodityChiefResult` (nach `signal: Signal = Signal.NEUTRAL`):
```python
    status: SignalStatus = SignalStatus.AVAILABLE
```
`SentimentChiefResult` (nach `signal: Signal = Signal.NEUTRAL`):
```python
    status: SignalStatus = SignalStatus.AVAILABLE
```
`YieldCurveChiefResult` (nach `signal: Signal = Signal.NEUTRAL`):
```python
    status: SignalStatus = SignalStatus.AVAILABLE
```
`SectorChiefResult` (nach `rotation`):
```python
    status: SignalStatus = SignalStatus.AVAILABLE
```

- [ ] **Step 4: In jeder `default()` `status=UNAVAILABLE` setzen**

Jeweils `status=SignalStatus.UNAVAILABLE` als zusätzliches Keyword-Argument in den Konstruktor-Aufruf der `default()`-Methode aufnehmen. Falls `SignalStatus` in der Datei noch nicht importiert ist, zum Import aus `core.domain.models` hinzufügen.

`macro_chief_agent.py` — Import ergänzen (`from core.domain.models import ... , SignalStatus`), dann im `return MacroChiefResult(...)` der `default()` ergänzen:
```python
            buffett_indicator=BuffettIndicatorAgent.default(),
            status=SignalStatus.UNAVAILABLE,
        )
```
`commodity_chief_agent_makro.py` — `SignalStatus` ist bereits importiert; in `default()`:
```python
            agricultural=AgriculturalAgent.default(),
            signal=Signal.NEUTRAL,
            status=SignalStatus.UNAVAILABLE,
        )
```
`sentiment_chief_agent.py` — Import um `SignalStatus` ergänzen; in `default()`:
```python
            put_call=PutCallAgent.default(),
            signal=Signal.NEUTRAL,
            status=SignalStatus.UNAVAILABLE,
        )
```
`yield_curve_chief_agent.py` — Import um `SignalStatus` ergänzen; in `default()`:
```python
            sovereign_spreads=SovereignSpreadAgent.default(),
            signal=Signal.NEUTRAL,
            status=SignalStatus.UNAVAILABLE,
        )
```
`sector_chief_agent.py` — Import um `SignalStatus` ergänzen; in `default()`:
```python
            rotation=_DEFAULT_ROTATION,
            status=SignalStatus.UNAVAILABLE,
        )
```

- [ ] **Step 5: Tests laufen lassen — müssen grün sein, plus Regression**

Run: `python -m pytest tests/test_chief_default_status.py -q`
Expected: PASS.
Run: `python -m pytest -q`
Expected: PASS (keine Regression — das neue Feld hat einen Default, bestehende Konstruktionen bleiben gültig).

- [ ] **Step 6: Commit**

```bash
git add core/domain/models.py agents/market_cockpit/macro_chief_agent.py agents/market_cockpit/commodity_chief_agent_makro.py agents/market_cockpit/sentiment_chief_agent.py agents/market_cockpit/yield_curve_chief_agent.py agents/market_cockpit/sector_chief_agent.py tests/test_chief_default_status.py
git commit -m "feat(domain): status (SignalStatus) auf den Cockpit-Chief-Results

Macht UNAVAILABLE pro Domaene erstklassig: Default AVAILABLE auf jedem
Chief-Result, default() liefert UNAVAILABLE. Der Orchestrator-Fallback
(Chief.default() bei Ausfall) signalisiert damit automatisch 'ausgefallen'.
Grundlage fuer den ehrlichen 'x/5 Quellen aktiv'-Zaehler der API.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `cockpit_to_dict` — pure Serialisierung (Frontend-Vertrag)

**Files:**
- Create: `adapters/api/__init__.py` (leer)
- Create: `adapters/api/cockpit_serializer.py`
- Create: `tests/adapters/api/__init__.py` (leer)
- Test: `tests/adapters/api/test_cockpit_serializer.py`

**Interfaces:**
- Consumes: `CockpitResult` (Task 1, inkl. `status` auf den Chiefs); `SignalStatus`.
- Produces: `cockpit_to_dict(result: CockpitResult) -> dict` mit Schlüsseln `regime` (str), `regime_confidence` (float), `macro_status` (str), `domains` (Liste von `{key, signal, status}`), `sources_active` (int), `sources_total` (int).

- [ ] **Step 1: Failing-Test schreiben**

`tests/adapters/api/test_cockpit_serializer.py`:
```python
from core.domain.models import (
    CockpitResult, SignalStatus, Signal, MarketRegime,
    SentimentChiefResult, VIXSnapshot, FearGreedSnapshot, PutCallSnapshot,
    YieldCurveChiefResult, YieldSpreadSnapshot, YieldSpreadDataPoint, SovereignSpreadSnapshot,
    SectorChiefResult, SectorPerformanceSnapshot, SectorRotationSnapshot,
    CommodityChiefResult, EnergySnapshot, IndustrialMetalsSnapshot,
    PreciousMetalsMacroSnapshot, AgriculturalSnapshot,
)
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from adapters.api.cockpit_serializer import cockpit_to_dict


def _available_cockpit() -> CockpitResult:
    """Voll verfuegbares Cockpit mit eindeutigen Signalen pro Domaene."""
    macro = MacroChiefAgent.default()
    macro.regime = MarketRegime.EXPANSION
    macro.regime_confidence = 0.71
    macro.status = SignalStatus.AVAILABLE

    commodities = CommodityChiefResult(
        energy=EnergySnapshot(None, None, None, Signal.NEUTRAL),
        industrial_metals=IndustrialMetalsSnapshot(None, None, None, None, Signal.NEUTRAL),
        precious_metals=PreciousMetalsMacroSnapshot(None, None, None, None, None, None, Signal.NEUTRAL),
        agricultural=AgriculturalSnapshot(None, None, None, None, None, None, None, Signal.NEUTRAL),
        signal=Signal.NEUTRAL, status=SignalStatus.AVAILABLE,
    )
    sentiment = SentimentChiefResult(
        vix=VIXSnapshot(None, None, Signal.NEUTRAL),
        fear_greed=FearGreedSnapshot(None, "Neutral", Signal.NEUTRAL),
        put_call=PutCallSnapshot(None, Signal.NEUTRAL),
        signal=Signal.BEARISH, status=SignalStatus.AVAILABLE,
    )
    spread = YieldSpreadDataPoint(0.4, 1.1, 0.7, False, Signal.BULLISH)
    yield_curve = YieldCurveChiefResult(
        yield_spreads=YieldSpreadSnapshot(usa=spread, eurozone=spread, switzerland=spread),
        sovereign_spreads=SovereignSpreadSnapshot(None, None, None, Signal.NEUTRAL),
        signal=Signal.BULLISH, status=SignalStatus.AVAILABLE,
    )
    sectors = SectorChiefResult(
        performance=SectorPerformanceSnapshot(usa={}, eurozone={}, leading_usa="Tech", lagging_usa="Energy", leading_eu="", lagging_eu=""),
        rotation=SectorRotationSnapshot(recommended=[], avoid=[], alignment="neutral", signal=Signal.NEUTRAL),
        status=SignalStatus.AVAILABLE,
    )
    return CockpitResult(macro=macro, commodities=commodities, sentiment=sentiment, yield_curve=yield_curve, sectors=sectors)


def test_serializes_regime_and_domains_when_all_available():
    d = cockpit_to_dict(_available_cockpit())
    assert d["regime"] == "Aufschwung"          # MarketRegime.EXPANSION.value
    assert d["regime_confidence"] == 0.71
    assert d["macro_status"] == "available"
    keys = [e["key"] for e in d["domains"]]
    assert keys == ["commodities", "sentiment", "yield_curve", "sectors"]
    by_key = {e["key"]: e for e in d["domains"]}
    assert by_key["sentiment"]["signal"] == "bearish"
    assert by_key["yield_curve"]["signal"] == "bullish"
    assert by_key["sectors"]["signal"] == "neutral"   # aus rotation.signal
    assert d["sources_total"] == 5
    assert d["sources_active"] == 5


def test_unavailable_domain_is_excluded_from_active_and_marked():
    # Alle-Default-Cockpit => alle Chiefs UNAVAILABLE => 0/5 aktiv.
    result = CockpitResult(
        macro=MacroChiefAgent.default(),
        commodities=CommodityChiefAgentMakro.default(),
        sentiment=SentimentChiefAgent.default(),
        yield_curve=YieldCurveChiefAgent.default(),
        sectors=SectorChiefAgent.default(),
    )
    d = cockpit_to_dict(result)
    assert d["macro_status"] == "unavailable"
    assert all(e["status"] == "unavailable" for e in d["domains"])
    assert d["sources_active"] == 0
    assert d["sources_total"] == 5
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/api/test_cockpit_serializer.py -q`
Expected: FAIL (`ModuleNotFoundError: adapters.api.cockpit_serializer`).

- [ ] **Step 3: Serializer implementieren**

`adapters/api/__init__.py`: leere Datei.
`tests/adapters/api/__init__.py`: leere Datei.
`adapters/api/cockpit_serializer.py`:
```python
"""Pure Serialisierung eines CockpitResult in den Frontend-Vertrag (Regime-Uebersicht).

Kein I/O. UNAVAILABLE ist ein eigener Zustand (status), nicht NEUTRAL/0 — eine
ausgefallene Domaene zaehlt NICHT in sources_active (AGENTS.md §3 / Frontend §5.4).
Macro wird durch das Regime-Banner repraesentiert (kein eigenes Signal-Feld im
Modell); die vier Sub-Domaenen tragen ihr eigenes overall-signal.
"""
from core.domain.models import CockpitResult, SignalStatus


def cockpit_to_dict(result: CockpitResult) -> dict:
    domains = [
        {"key": "commodities", "signal": result.commodities.signal.value,        "status": result.commodities.status.value},
        {"key": "sentiment",   "signal": result.sentiment.signal.value,          "status": result.sentiment.status.value},
        {"key": "yield_curve", "signal": result.yield_curve.signal.value,        "status": result.yield_curve.status.value},
        {"key": "sectors",     "signal": result.sectors.rotation.signal.value,   "status": result.sectors.status.value},
    ]
    macro_available = result.macro.status is SignalStatus.AVAILABLE
    sources_active = (1 if macro_available else 0) + sum(
        1 for d in domains if d["status"] == SignalStatus.AVAILABLE.value
    )
    return {
        "regime": result.macro.regime.value,
        "regime_confidence": result.macro.regime_confidence,
        "macro_status": result.macro.status.value,
        "domains": domains,
        "sources_active": sources_active,
        "sources_total": 1 + len(domains),  # Macro + 4 Sub-Domaenen
    }
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/adapters/api/test_cockpit_serializer.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/api/__init__.py adapters/api/cockpit_serializer.py tests/adapters/api/__init__.py tests/adapters/api/test_cockpit_serializer.py
git commit -m "feat(api): cockpit_to_dict — pure Serialisierung des Regime-Uebersicht-Vertrags

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `event_to_dict` — pure Event-Serialisierung (WebSocket)

**Files:**
- Create: `adapters/api/event_serializer.py`
- Test: `tests/adapters/api/test_event_serializer.py`

**Interfaces:**
- Consumes: `AgentEvent` (`core/domain/events.py`: `source: str`, `payload: dict`, `timestamp: datetime`).
- Produces: `event_to_dict(event: AgentEvent, run_id: str) -> dict` mit `type` (Klassenname), `source`, `payload`, `timestamp` (ISO-String), `run_id`.

- [ ] **Step 1: Failing-Test schreiben**

`tests/adapters/api/test_event_serializer.py`:
```python
from datetime import datetime
from core.domain.events import MacroChiefReady
from adapters.api.event_serializer import event_to_dict


def test_event_to_dict_maps_all_fields():
    ts = datetime(2026, 6, 22, 10, 15, 3)
    event = MacroChiefReady(source="macro_chief", payload={"regime": "Aufschwung"}, timestamp=ts)
    d = event_to_dict(event, run_id="abc123")
    assert d["type"] == "MacroChiefReady"
    assert d["source"] == "macro_chief"
    assert d["payload"] == {"regime": "Aufschwung"}
    assert d["timestamp"] == "2026-06-22T10:15:03"
    assert d["run_id"] == "abc123"
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/api/test_event_serializer.py -q`
Expected: FAIL (`ModuleNotFoundError: adapters.api.event_serializer`).

- [ ] **Step 3: Implementieren**

`adapters/api/event_serializer.py`:
```python
"""Pure Serialisierung eines AgentEvent fuer den WebSocket-Stream.

run_id wird mitgegeben, damit das Frontend Events einem Lauf zuordnen kann
(v1 hat keinen Lock — ueberlappende Laeufe waeren sonst ununterscheidbar).
"""
from core.domain.events import AgentEvent


def event_to_dict(event: AgentEvent, run_id: str) -> dict:
    return {
        "type": type(event).__name__,
        "source": event.source,
        "payload": event.payload,
        "timestamp": event.timestamp.isoformat(),
        "run_id": run_id,
    }
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/adapters/api/test_event_serializer.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/api/event_serializer.py tests/adapters/api/test_event_serializer.py
git commit -m "feat(api): event_to_dict — pure Event-Serialisierung mit run_id

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `subscribe_all` am `InMemoryEventBus`

**Files:**
- Modify: `adapters/event_bus/redis_bus.py` (`InMemoryEventBus`)
- Test: `tests/adapters/test_event_bus_subscribe_all.py`

**Interfaces:**
- Produces: `InMemoryEventBus.subscribe_all(handler: Callable[[AgentEvent], None]) -> None`. Der Handler wird bei **jedem** `publish` (zusätzlich zu typgenauen Subscribern) aufgerufen. Exceptions im Handler werden — wie beim bestehenden `publish` — geloggt und übersprungen.

- [ ] **Step 1: Failing-Test schreiben**

`tests/adapters/test_event_bus_subscribe_all.py`:
```python
from adapters.event_bus.redis_bus import InMemoryEventBus
from core.domain.events import MacroChiefReady, SentimentChiefReady


def test_subscribe_all_receives_every_event_type():
    bus = InMemoryEventBus()
    received = []
    bus.subscribe_all(received.append)
    bus.publish(MacroChiefReady(source="m", payload={}))
    bus.publish(SentimentChiefReady(source="s", payload={}))
    assert [type(e).__name__ for e in received] == ["MacroChiefReady", "SentimentChiefReady"]


def test_typed_subscribe_still_works_alongside_subscribe_all():
    bus = InMemoryEventBus()
    typed, all_ = [], []
    bus.subscribe(MacroChiefReady, typed.append)
    bus.subscribe_all(all_.append)
    bus.publish(MacroChiefReady(source="m", payload={}))
    assert len(typed) == 1 and len(all_) == 1


def test_failing_all_handler_does_not_break_publish():
    bus = InMemoryEventBus()
    seen = []
    bus.subscribe_all(lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
    bus.subscribe_all(seen.append)  # zweiter Handler laeuft trotzdem
    bus.publish(MacroChiefReady(source="m", payload={}))
    assert len(seen) == 1
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/test_event_bus_subscribe_all.py -q`
Expected: FAIL (`AttributeError: 'InMemoryEventBus' object has no attribute 'subscribe_all'`).

- [ ] **Step 3: Implementieren**

In `adapters/event_bus/redis_bus.py`, `InMemoryEventBus.__init__` um eine Liste ergänzen und `publish` erweitern:
```python
    def __init__(self):
        self._handlers: dict[type, list[Callable]] = defaultdict(list)
        self._all_handlers: list[Callable] = []
        self._log: list[AgentEvent] = []

    def publish(self, event: AgentEvent) -> None:
        self._log.append(event)
        for handler in self._handlers.get(type(event), []):
            try:
                handler(event)
            except Exception:
                _logger.exception(
                    "Handler %s raised for %s — skipping",
                    handler, type(event).__name__,
                )
        for handler in self._all_handlers:
            try:
                handler(event)
            except Exception:
                _logger.exception(
                    "Wildcard-Handler %s raised for %s — skipping",
                    handler, type(event).__name__,
                )

    def subscribe_all(self, handler: Callable[[AgentEvent], None]) -> None:
        """Ruft handler bei JEDEM publish auf (erster echter Bus-Zuhoerer, vgl. open_todos §7)."""
        self._all_handlers.append(handler)
```

- [ ] **Step 4: Test laufen lassen — muss grün sein, plus Regression**

Run: `python -m pytest tests/adapters/test_event_bus_subscribe_all.py -q`
Expected: PASS.
Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/event_bus/redis_bus.py tests/adapters/test_event_bus_subscribe_all.py
git commit -m "feat(api): subscribe_all am InMemoryEventBus (erster echter Bus-Zuhoerer)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: `WebSocketBroadcaster`

**Files:**
- Create: `adapters/api/ws_broadcaster.py`
- Test: `tests/adapters/api/test_ws_broadcaster.py`

**Interfaces:**
- Produces: `WebSocketBroadcaster` mit `connections: list`, `connect(ws)`, `disconnect(ws)`, `async broadcast(message: dict) -> None`. `broadcast` ruft `await ws.send_json(message)` für jede Verbindung; wirft eine Verbindung dabei, wird sie entfernt (kein Abbruch der übrigen). Erwartet WS-Objekte mit async `send_json(dict)` (FastAPI-`WebSocket` erfüllt das; im Test ein Fake).

- [ ] **Step 1: Failing-Test schreiben**

`tests/adapters/api/test_ws_broadcaster.py`:
```python
import asyncio
from adapters.api.ws_broadcaster import WebSocketBroadcaster


class _FakeWS:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []
    async def send_json(self, message):
        if self.fail:
            raise RuntimeError("connection closed")
        self.sent.append(message)


def test_broadcast_reaches_all_connections():
    b = WebSocketBroadcaster()
    a, c = _FakeWS(), _FakeWS()
    b.connect(a); b.connect(c)
    asyncio.run(b.broadcast({"type": "X"}))
    assert a.sent == [{"type": "X"}]
    assert c.sent == [{"type": "X"}]


def test_broadcast_drops_dead_connection_and_keeps_others():
    b = WebSocketBroadcaster()
    dead, alive = _FakeWS(fail=True), _FakeWS()
    b.connect(dead); b.connect(alive)
    asyncio.run(b.broadcast({"type": "X"}))
    assert alive.sent == [{"type": "X"}]
    assert dead not in b.connections
    assert alive in b.connections
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/api/test_ws_broadcaster.py -q`
Expected: FAIL (`ModuleNotFoundError: adapters.api.ws_broadcaster`).

- [ ] **Step 3: Implementieren**

`adapters/api/ws_broadcaster.py`:
```python
"""Verwaltet offene WebSocket-Verbindungen und sendet Nachrichten an alle.

Framework-arm: erwartet nur Objekte mit async send_json(dict) — FastAPIs
WebSocket erfuellt das, im Test ein Fake. Eine Verbindung, die beim Senden
wirft, wird entfernt (eine tote Verbindung darf den Broadcast nicht abbrechen).
"""
import logging

_logger = logging.getLogger(__name__)


class WebSocketBroadcaster:
    def __init__(self):
        self.connections: list = []

    def connect(self, ws) -> None:
        self.connections.append(ws)

    def disconnect(self, ws) -> None:
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in list(self.connections):
            try:
                await ws.send_json(message)
            except Exception:
                _logger.warning("WS-Senden fehlgeschlagen — Verbindung entfernt", exc_info=True)
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/adapters/api/test_ws_broadcaster.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/api/ws_broadcaster.py tests/adapters/api/test_ws_broadcaster.py
git commit -m "feat(api): WebSocketBroadcaster — Verbindungsverwaltung + robustes broadcast

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: `RunManager` — Lauf als Hintergrund-Task, letztes Ergebnis

**Files:**
- Create: `adapters/api/run_manager.py`
- Test: `tests/adapters/api/test_run_manager.py`

**Interfaces:**
- Consumes: `WebSocketBroadcaster` (Task 5), `cockpit_to_dict` (Task 2), `event_to_dict` (Task 3), `InMemoryEventBus` (Task 4), `EventBus`-Port.
- Produces: `RunManager(orchestrator_factory: Callable[[EventBus], object], broadcaster: WebSocketBroadcaster)`. Methoden: `start_run() -> str` (run_id, startet Hintergrund-Task), `async _execute(orchestrator, run_id)` (führt `await orchestrator.run()` aus, speichert Ergebnis, broadcastet terminales `CockpitResultReady`), Property `latest` (letztes `CockpitResult` oder `None`), Attribut `broadcaster`. `orchestrator_factory` ist eine Funktion, die einen `bus` bekommt und ein Objekt mit `async run() -> CockpitResult` liefert.

- [ ] **Step 1: Failing-Test schreiben**

`tests/adapters/api/test_run_manager.py`:
```python
import asyncio
from core.domain.models import CockpitResult
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager


def _default_cockpit() -> CockpitResult:
    return CockpitResult(
        macro=MacroChiefAgent.default(),
        commodities=CommodityChiefAgentMakro.default(),
        sentiment=SentimentChiefAgent.default(),
        yield_curve=YieldCurveChiefAgent.default(),
        sectors=SectorChiefAgent.default(),
    )


class _FakeOrch:
    def __init__(self, bus):
        self.bus = bus
    async def run(self):
        return _default_cockpit()


class _RecordingBroadcaster(WebSocketBroadcaster):
    def __init__(self):
        super().__init__()
        self.messages = []
    async def broadcast(self, message):
        self.messages.append(message)


def test_latest_is_none_before_any_run():
    rm = RunManager(lambda bus: _FakeOrch(bus), WebSocketBroadcaster())
    assert rm.latest is None


def test_execute_stores_result_and_broadcasts_terminal_event():
    broadcaster = _RecordingBroadcaster()
    rm = RunManager(lambda bus: _FakeOrch(bus), broadcaster)

    async def scenario():
        await rm._execute(_FakeOrch(bus=None), run_id="run-1")

    asyncio.run(scenario())
    assert rm.latest is not None
    terminal = broadcaster.messages[-1]
    assert terminal["type"] == "CockpitResultReady"
    assert terminal["run_id"] == "run-1"
    assert terminal["payload"]["regime"] == "Abschwung"  # Macro-Default = SLOWDOWN
    assert terminal["payload"]["sources_active"] == 0     # alle Defaults => UNAVAILABLE


def test_start_run_returns_distinct_run_ids():
    rm = RunManager(lambda bus: _FakeOrch(bus), WebSocketBroadcaster())

    async def scenario():
        a = rm.start_run()
        b = rm.start_run()
        await asyncio.gather(*list(rm._tasks))
        return a, b

    a, b = asyncio.run(scenario())
    assert a != b
    assert rm.latest is not None
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/api/test_run_manager.py -q`
Expected: FAIL (`ModuleNotFoundError: adapters.api.run_manager`).

- [ ] **Step 3: Implementieren**

`adapters/api/run_manager.py`:
```python
"""Startet Cockpit-Laeufe als Hintergrund-Task und haelt das letzte Ergebnis.

POST /api/cockpit/run -> start_run() (sofort, run_id). Fortschritt der Agenten
fliesst ueber den Bus (subscribe_all) in den Broadcaster; nach Abschluss
broadcastet der RunManager ein terminales CockpitResultReady mit dem
serialisierten Ergebnis. Pro Lauf ein frischer InMemoryEventBus -> ueberlappende
Laeufe bleiben sauber getrennt (v1 hat bewusst keinen Lock).
"""
import asyncio
from typing import Callable
from uuid import uuid4

from adapters.api.cockpit_serializer import cockpit_to_dict
from adapters.api.event_serializer import event_to_dict
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.event_bus.redis_bus import InMemoryEventBus
from core.ports.event_bus import EventBus


class RunManager:
    def __init__(self, orchestrator_factory: Callable[[EventBus], object], broadcaster: WebSocketBroadcaster):
        self._make_orchestrator = orchestrator_factory
        self.broadcaster = broadcaster
        self._latest = None
        self._tasks: set[asyncio.Task] = set()

    @property
    def latest(self):
        return self._latest

    def start_run(self) -> str:
        run_id = uuid4().hex
        bus = InMemoryEventBus()
        bus.subscribe_all(lambda ev: self._schedule(event_to_dict(ev, run_id)))
        orchestrator = self._make_orchestrator(bus)
        task = asyncio.create_task(self._execute(orchestrator, run_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return run_id

    def _schedule(self, message: dict) -> None:
        # Sync-Bus-Handler -> async Broadcast: auf demselben Loop, daher create_task.
        asyncio.create_task(self.broadcaster.broadcast(message))

    async def _execute(self, orchestrator, run_id: str) -> None:
        result = await orchestrator.run()
        self._latest = result
        await self.broadcaster.broadcast({
            "type": "CockpitResultReady",
            "source": "run_manager",
            "payload": cockpit_to_dict(result),
            "run_id": run_id,
        })
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/adapters/api/test_run_manager.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/api/run_manager.py tests/adapters/api/test_run_manager.py
git commit -m "feat(api): RunManager — Hintergrund-Lauf, run_id, terminales CockpitResultReady

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: FastAPI-App + Routen + Server-Einstiegspunkt

**Files:**
- Modify: `requirements.txt` (`+ fastapi`, `+ uvicorn[standard]`, `+ httpx`)
- Create: `adapters/api/routes_cockpit.py`
- Create: `adapters/api/app_factory.py`
- Create: `app/server.py`
- Test: `tests/adapters/api/test_routes_cockpit.py`

**Interfaces:**
- Consumes: `RunManager` (Task 6), `cockpit_to_dict` (Task 2).
- Produces: `build_router(run_manager: RunManager) -> APIRouter` (`GET /api/cockpit`, `POST /api/cockpit/run`, `WS /ws/cockpit`); `create_app(run_manager: RunManager) -> FastAPI`. `app/server.py` baut die echten Provider + `make_orchestrator(bus)` + Broadcaster + RunManager + App und startet uvicorn.

- [ ] **Step 1: Dependencies ergänzen**

`requirements.txt` am Ende ergänzen:
```
fastapi
uvicorn[standard]
httpx
```
Installieren:
```bash
python -m pip install fastapi "uvicorn[standard]" httpx
```

- [ ] **Step 2: Failing-Test schreiben**

`tests/adapters/api/test_routes_cockpit.py`:
```python
from fastapi.testclient import TestClient
from core.domain.models import CockpitResult
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from core.domain.events import MacroChiefReady
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager
from adapters.api.app_factory import create_app


def _default_cockpit() -> CockpitResult:
    return CockpitResult(
        macro=MacroChiefAgent.default(),
        commodities=CommodityChiefAgentMakro.default(),
        sentiment=SentimentChiefAgent.default(),
        yield_curve=YieldCurveChiefAgent.default(),
        sectors=SectorChiefAgent.default(),
    )


class _FakeOrch:
    def __init__(self, bus):
        self.bus = bus
    async def run(self):
        self.bus.publish(MacroChiefReady(source="macro_chief", payload={}))
        return _default_cockpit()


def _make_client() -> TestClient:
    rm = RunManager(lambda bus: _FakeOrch(bus), WebSocketBroadcaster())
    return TestClient(create_app(rm))


def test_get_cockpit_is_204_before_any_run():
    client = _make_client()
    r = client.get("/api/cockpit")
    assert r.status_code == 204


def test_post_run_returns_202_and_run_id():
    client = _make_client()
    r = client.post("/api/cockpit/run")
    assert r.status_code == 202
    assert "run_id" in r.json()


def test_ws_streams_until_terminal_then_get_returns_result():
    client = _make_client()
    with client.websocket_connect("/ws/cockpit") as ws:
        r = client.post("/api/cockpit/run")
        assert r.status_code == 202
        terminal = None
        for _ in range(20):  # bis zum terminalen Event lesen
            msg = ws.receive_json()
            if msg["type"] == "CockpitResultReady":
                terminal = msg
                break
        assert terminal is not None
        assert terminal["payload"]["regime"] == "Abschwung"
    g = client.get("/api/cockpit")
    assert g.status_code == 200
    assert g.json()["sources_total"] == 5
```

- [ ] **Step 3: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/api/test_routes_cockpit.py -q`
Expected: FAIL (`ModuleNotFoundError: adapters.api.app_factory`).

- [ ] **Step 4: Routen implementieren**

`adapters/api/routes_cockpit.py`:
```python
"""HTTP- und WebSocket-Routen fuer den Cockpit-Flow.

GET liest das letzte Ergebnis (keine externen Calls). POST stoesst einen Lauf
als Hintergrund-Task an und antwortet sofort (202 + run_id) — async def, damit
asyncio.create_task im RunManager einen laufenden Event-Loop hat. WS registriert
die Verbindung beim Broadcaster und haelt sie offen, bis der Client trennt.
"""
from fastapi import APIRouter, Response, WebSocket, WebSocketDisconnect, status

from adapters.api.cockpit_serializer import cockpit_to_dict
from adapters.api.run_manager import RunManager


def build_router(run_manager: RunManager) -> APIRouter:
    router = APIRouter()

    @router.get("/api/cockpit")
    def get_cockpit():
        if run_manager.latest is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        return cockpit_to_dict(run_manager.latest)

    @router.post("/api/cockpit/run", status_code=status.HTTP_202_ACCEPTED)
    async def post_run():
        run_id = run_manager.start_run()
        return {"run_id": run_id}

    @router.websocket("/ws/cockpit")
    async def ws_cockpit(websocket: WebSocket):
        await websocket.accept()
        run_manager.broadcaster.connect(websocket)
        try:
            while True:
                await websocket.receive_text()  # haelt die Verbindung; erkennt Disconnect
        except WebSocketDisconnect:
            run_manager.broadcaster.disconnect(websocket)

    return router
```

`adapters/api/app_factory.py`:
```python
"""Baut die FastAPI-App. Dev-CORS fuer das lokale Frontend (Vite/CRA)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.api.routes_cockpit import build_router
from adapters.api.run_manager import RunManager


def create_app(run_manager: RunManager) -> FastAPI:
    app = FastAPI(title="AAIA API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(build_router(run_manager))
    return app
```

- [ ] **Step 5: Test laufen lassen — muss grün sein**

Run: `python -m pytest tests/adapters/api/test_routes_cockpit.py -q`
Expected: PASS.

- [ ] **Step 6: Composition Root `app/server.py` schreiben**

`app/server.py`:
```python
"""Einstiegspunkt der Web-API (uvicorn). Composition Root: verdrahtet die echten
Adapter mit dem TopDownOrchestrator — analog zu app/main.py fuer die CLI.

Start:  python -m app.server      (lauscht auf 127.0.0.1:8000)
"""
import uvicorn

from config.settings import FRED_API_KEY
from adapters.data.fred_api import FredDataProvider
from adapters.data.yahoo_finance import YahooFinanceProvider
from adapters.data.ecb_sdw import EcbSdwProvider
from adapters.data.fred_snb import FredSnbProvider
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager
from adapters.api.app_factory import create_app
from orchestrators.top_down_orchestrator import TopDownOrchestrator


def make_orchestrator(bus):
    return TopDownOrchestrator(
        macro=FredDataProvider(FRED_API_KEY),
        ecb=EcbSdwProvider(),
        snb=FredSnbProvider(FRED_API_KEY),
        market=YahooFinanceProvider(),
        bus=bus,
    )


broadcaster = WebSocketBroadcaster()
run_manager = RunManager(make_orchestrator, broadcaster)
app = create_app(run_manager)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

- [ ] **Step 7: Smoke-Check des Einstiegspunkts (Import, ohne Server-Start)**

Run: `python -c "import app.server; print('ok', type(app.server.app).__name__)"`
Expected: `ok FastAPI` (verifiziert, dass die Verdrahtung importierbar ist; startet keinen Server, macht keine Netz-Calls).

- [ ] **Step 8: Gesamtsuite + Commit**

Run: `python -m pytest -q`
Expected: PASS (gesamte Suite grün).
```bash
git add requirements.txt adapters/api/routes_cockpit.py adapters/api/app_factory.py app/server.py tests/adapters/api/test_routes_cockpit.py
git commit -m "feat(api): FastAPI-Routen (GET/POST/WS) + Server-Einstiegspunkt fuer Cockpit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Logbuch + Doku nachziehen

**Files:**
- Modify: `docs/open_todos.md`

**Interfaces:** keine (Doku).

- [ ] **Step 1: Logbuch-Einträge ergänzen**

In `docs/open_todos.md` ergänzen (kein Code):
- Unter §7 „EDA-Event-Bus ohne Zuhörer": Vermerk, dass mit `subscribe_all` + WebSocket-Stream **der erste echte Zuhörer** existiert (Teil-Erledigung; verbleibend: Redis-Bus / weitere Subscriber).
- Neuer Eintrag „Frontend / API-Brücke": v1 (Cockpit-Flow) umgesetzt; **offene Folge-Aufgaben** mit Lösungsansatz:
  - **Kein Lock auf parallele Läufe** — bei Bedarf `409 Conflict` bei laufendem Lauf (run_id/Lauf-Status im RunManager halten).
  - **Keine Persistenz des letzten Ergebnisses** — bei Server-Neustart leer; ggf. reichen API-Snapshot als JSON ablegen/laden.
  - **Pro-Domäne-Konfidenz & feineres UNAVAILABLE** — Chiefs (commodity) verwerfen heute eine berechnete Konfidenz (`weighted_signal`); für die Tiles „Conf %" und datenbasiertes UNAVAILABLE (statt nur „Chief gecrasht") später Konfidenz/Status pro Chief-Result mitführen.
  - **Folgeschnitte** `bottomup`/`judge`-Endpunkte nach demselben Muster.

- [ ] **Step 2: Commit**

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): API-Bruecke v1 + Folge-Aufgaben protokolliert

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (gegen das Spec)

**Spec-Abdeckung:**
- §2 GET/POST/WS → Task 7 (Routen) ✓
- §3 Read-vs-Run getrennt, 202+run_id → Task 6/7 ✓
- §4 WebSocket-Event-Vertrag inkl. run_id → Task 3 (event_to_dict) + Task 6 (run_id-Tagging) ✓
- §5 Sync-Bus↔Async-WS + `subscribe_all` → Task 4 (subscribe_all) + Task 6 (`_schedule`/create_task) + Task 5 (Broadcaster) ✓
- §6 Serialisierungs-Vertrag (regime, domains, UNAVAILABLE, x/y) → Task 2 ✓; der in §6 offene „available-Marker" → in **Task 1** sauber gelöst (status auf Chief-Results, statt geraten) ✓
- §8 TDD-Tests (serializer, event, subscribe_all, broadcaster/run, Endpunkte via TestClient) → Tasks 2–7 ✓
- §7/§9 YAGNI-Grenzen + Folge-Aufgaben → Task 8 (Logbuch) ✓

**Platzhalter-Scan:** keine „TBD"/„später" — jeder Code-Schritt zeigt vollständigen Code. ✓

**Typ-Konsistenz:** `cockpit_to_dict(result)->dict`, `event_to_dict(event, run_id)->dict`, `subscribe_all(handler)`, `WebSocketBroadcaster.{connect,disconnect,broadcast}`, `RunManager(orchestrator_factory, broadcaster).{start_run,latest,broadcaster,_execute}`, `build_router(run_manager)`, `create_app(run_manager)` — über alle Tasks identisch verwendet. ✓
