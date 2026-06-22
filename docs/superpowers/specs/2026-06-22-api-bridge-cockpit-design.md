# API-Brücke (Cockpit-Flow) — Design

> **Status:** Spezifikation / Design-Entwurf · **Datum:** 2026-06-22
> **Scope:** Erstes Teilprojekt des Frontend-Vorhabens — eine **eingehende Web-API-Schicht** (HTTP + WebSocket), die das heute reine CLI-Backend für ein künftiges React-Frontend erreichbar macht. Bewusst auf **genau einen Analyse-Modus** begrenzt: den **Top-Down-/Cockpit-Flow**, als saubere Referenz-Implementierung. `bottomup`/`judge` folgen später nach demselben Muster.
> **Erdung:** Baut auf dem Frontend-Konzept `docs/superpowers/specs/2026-06-21-frontend-konzept.md` (React, Desktop-first, WebSocket-live) und dem bestehenden Code auf (`app/main.py`, `orchestrators/top_down_orchestrator.py`, `core/ports/event_bus.py`, `adapters/event_bus/redis_bus.py`).
> **Wichtig:** Reines Design-Dokument. Der **laufende Status** (Roadmap, PR-Protokoll, Reihenfolge, Folge-Aufgaben) gehört ausschließlich ins Logbuch `docs/open_todos.md` (AGENTS.md §5) — hier steht das *Warum* und *Wie* des Designs.

---

## 1. Problem & Ausgangslage

Das AAIA-Backend ist heute **CLI-only** (`app/main.py` mit den Modi `dashboard`, `bottomup`, `judge`). Es gibt **keine** HTTP-/WebSocket-Schicht; ein Frontend hätte aktuell nichts, womit es reden könnte. Das im Frontend-Konzept beschlossene React-Frontend braucht als Voraussetzung eine **Brücke**: eine API, die Analyse-Ergebnisse ausliefert und den Lauf-Fortschritt live streamt.

Zwei konkrete Befunde aus dem Code, die das Design prägen:

1. **Der `EventBus` hat schon ein `subscribe`, aber niemand nutzt es.** Der `InMemoryEventBus` (`adapters/event_bus/redis_bus.py`) verteilt Events synchron an Handler — bisher gibt es keinen einzigen Abonnenten (vgl. Logbuch §7, „EDA-Event-Bus ohne Zuhörer"). Der WebSocket-Fortschritts-Stream ist der **natürliche erste echte Zuhörer** und macht den Bus damit erstmals „verdient".
2. **Der vorhandene `ResultCache.save_cockpit` ist bewusst verlustbehaftet.** Er speichert nur eine flache Zusammenfassung (Regime, einige Spreads, VIX/Fear&Greed, führende Sektoren), die ausschließlich den `judge`-Modus füttert (`adapters/cache/result_cache.py:588`). Für ein Frontend reicht das nicht. → Die API braucht eine **eigene Serialisierungs-Schicht** vom echten `CockpitResult`-Objekt in einen Frontend-Vertrag; der alte Cache wird **nicht** recycelt.

---

## 2. Architektur-Einordnung (Hexagonal)

Die Web-API ist ein **eingehender Adapter** („driving/primary adapter") — sie ruft die bestehenden Orchestratoren auf und **rechnet selbst nichts**. Der WebSocket-Stream ist ein **Adapter auf den `EventBus`-Port**. Kein Eingriff in `core/`, keine Duplizierung von Fach-/Aggregationslogik.

```
Browser (React, später)
   │  HTTP GET/POST        ▲ WebSocket (Events)
   ▼                       │
┌─────────────────────────────────────────────┐
│ adapters/api/  (eingehender Adapter, FastAPI) │
│  • Routen (GET /api/cockpit, POST …/run)      │
│  • WebSocketBroadcaster (offene Verbindungen) │
│  • Bus→WS-Abonnent (EventBus-Port-Adapter)    │
│  • cockpit_serializer (pure Funktion)         │
└───────────────┬───────────────────────────────┘
                │ ruft auf (wie app/main.py)
                ▼
   TopDownOrchestrator.run()  ──publish──▶  EventBus (InMemoryEventBus)
                │                                   │ subscribe_all
                ▼                                   ▼
            CockpitResult                      Bus→WS-Abonnent
```

### Neue/erweiterte Dateien

| Datei | Inhalt |
|---|---|
| `adapters/api/__init__.py` | Paket-Init |
| `adapters/api/app_factory.py` | `create_app(...)` baut die FastAPI-App, nimmt Abhängigkeiten injiziert entgegen (testbar) |
| `adapters/api/routes_cockpit.py` | Die drei Cockpit-Schnittstellen |
| `adapters/api/cockpit_serializer.py` | **pure Funktion** `cockpit_to_dict(result) -> dict` |
| `adapters/api/ws_broadcaster.py` | `WebSocketBroadcaster` (Verbindungsverwaltung) + Bus→WS-Abonnent |
| `adapters/api/event_serializer.py` | **pure Funktion** `event_to_dict(event, run_id) -> dict` |
| `adapters/api/run_manager.py` | Startet Orchestrator-Läufe als Hintergrund-Task, vergibt `run_id`, hält letztes Ergebnis im Speicher |
| `app/server.py` | Einstiegspunkt (uvicorn), Composition Root — verdrahtet Adapter + Orchestrator, analog zu `app/main.py` |
| `adapters/event_bus/redis_bus.py` | **kleine Ergänzung** am `InMemoryEventBus`: `subscribe_all(handler)` |
| `requirements.txt` | `+ fastapi`, `+ uvicorn[standard]`, `+ httpx` (für Tests/`TestClient`) |

> **Begründung Ablage:** `adapters/api/` ist konsistent mit der Hexagonal-Regel (alle eingehenden/ausgehenden Adapter unter `adapters/`). `app/server.py` ist der Composition Root (verdrahtet konkrete Adapter), genau wie `app/main.py` für die CLI.

---

## 3. Die drei Schnittstellen (nur Cockpit)

| Methode | Pfad | Verhalten | Antwort |
|---|---|---|---|
| `GET` | `/api/cockpit` | Liest das **letzte** Cockpit-Ergebnis aus dem Speicher. Keine externen Calls. | `200` + JSON (`cockpit_to_dict`) · `204 No Content`, wenn noch nie ein Lauf lief |
| `POST` | `/api/cockpit/run` | Startet `TopDownOrchestrator.run()` als **Hintergrund-Task**, antwortet **sofort**. | `202 Accepted` + `{ "run_id": "<uuid>" }` |
| `WS` | `/ws/cockpit` | Live-Fortschritt: jedes `AgentEvent` als JSON, bis `CockpitResultReady`. | Stream von Event-JSON-Objekten |

**Read-vs-Run bewusst getrennt:** Ein Lauf kostet echte FRED-/Yahoo-Calls und dauert mehrere Sekunden — deshalb **nie automatisch bei GET**. `GET` liest den letzten Stand, `POST` stößt bewusst neu an. Das passt zur Datenrealität (Makro-/Tageszeit-Takt, nicht Sekundentakt).

**Lebensdauer des Ergebnisses (v1):** Der `RunManager` hält den letzten vollen `CockpitResult` **im Speicher**. Server-Neustart = leer (`GET` → `204`, bis ein neuer Lauf erfolgt). Für eine Dev-Brücke akzeptabel; echte Persistenz eines reichen API-Snapshots ist eine **spätere Folge-Aufgabe** (Logbuch).

---

## 4. WebSocket-Event-Vertrag

Jedes `AgentEvent` (Basisklasse in `core/domain/events.py`: `source`, `payload`, `timestamp`; Unterklassen wie `MacroChiefReady`, `CommodityChiefReady`, …) wird so gepusht:

```json
{
  "type": "MacroChiefReady",
  "source": "macro_chief",
  "payload": { "...": "..." },
  "timestamp": "2026-06-22T10:15:03.123Z",
  "run_id": "f1c2…"
}
```

- `type` = Klassenname des Events (`type(event).__name__`) → das Frontend kann gezielt auf `CockpitResultReady` (Lauf fertig) reagieren.
- `run_id` ist **mitgegeben**, damit das Frontend Events einem Lauf zuordnen kann. Das ist nötig, weil v1 **keinen Lock** hat (siehe §7) — zwei überlappende Läufe würden sonst ununterscheidbar interleaven.
- Das Frontend sieht so live „Makro fertig → Sentiment fertig → … → Cockpit fertig" und kann eine Wartezeit greifbar machen.

---

## 5. Die heikle Stelle: synchroner Bus ↔ asynchroner WebSocket

`bus.publish()` ist **synchron** und wird aus den Orchestrator-Coroutinen heraus auf **demselben** asyncio-Event-Loop wie die FastAPI-App aufgerufen (der Orchestrator wird vom API-Adapter `await`-et). Daraus folgt:

- Ein **Bus→WS-Abonnent** (registriert über `subscribe_all`) wird bei jedem `publish` synchron aufgerufen. Er serialisiert das Event (`event_to_dict`) und legt es per `put_nowait` in eine `asyncio.Queue`.
- Der **WebSocket-Handler** ist eine Coroutine, die diese Queue leert und über die offene Verbindung sendet.
- Weil alles auf demselben Loop läuft, reicht `put_nowait` — **kein** Thread-Safety-Problem (`call_soon_threadsafe` nur nötig, falls der Lauf je in einen Thread ausgelagert würde; v1 nicht).

**Ergänzung am Bus — `subscribe_all(handler)`:** Der `InMemoryEventBus` verteilt heute nur nach **exaktem** Event-Typ (`self._handlers[type(event)]`). Um **alle** Event-Typen generisch zu streamen, ohne jede der ~50 Event-Klassen einzeln zu abonnieren, bekommt der `InMemoryEventBus` eine kleine, additive Methode `subscribe_all(handler)`: eine Liste von Handlern, die bei **jedem** `publish` (zusätzlich zu den typgenauen) aufgerufen werden. Das ist minimal, ändert bestehendes Verhalten nicht und löst zugleich den Logbuch-Punkt §7 mit an (der Bus bekommt seinen ersten Zuhörer).

> Der `EventBus`-**Port** (`core/ports/event_bus.py`) bleibt unangetastet (`publish`/`subscribe`); `subscribe_all` ist eine konkrete Bequemlichkeit des In-Memory-Adapters. Der API-Adapter darf den konkreten Bus kennen, weil `app/server.py` (Composition Root) ihn verdrahtet.

---

## 6. Serialisierungs-Vertrag (erster Schnitt)

`cockpit_to_dict(result: CockpitResult) -> dict` als **pure Funktion** (keine I/O, leicht testbar). Felder genau für die **Regime-Übersicht** (Frontend-Spec §4.1):

```jsonc
{
  "regime": "AUFSCHWUNG",            // result.macro.regime.value
  "regime_confidence": 0.71,         // result.macro.regime_confidence
  "domains": [
    { "key": "macro",       "signal": "BULLISH", "confidence": 0.78, "available": true,  "headline": "Inflation ↓ (USA)" },
    { "key": "commodities", "signal": "NEUTRAL", "confidence": 0.55, "available": true,  "headline": "Öl +, Cu −" },
    { "key": "sentiment",   "signal": "BEARISH", "confidence": 0.64, "available": true,  "headline": "VIX hoch" },
    { "key": "yield_curve", "signal": "BULLISH", "confidence": 0.80, "available": true,  "headline": "10J/2J +0.40" },
    { "key": "sectors",     "signal": null,      "confidence": null, "available": false, "headline": null }  // UNAVAILABLE
  ],
  "sources_active": 4,
  "sources_total": 5
}
```

**Regeln (fachliche Korrektheit, AGENTS.md §3):**
- **`UNAVAILABLE` ≠ 0 ≠ NEUTRAL** (Frontend-Spec §5.4): Eine ausgefallene Domäne hat `available: false`, `signal: null` — **nicht** `NEUTRAL`. Sie zählt in `sources_active` **nicht** mit.
- `sources_active`/`sources_total` speisen den „x/y Quellen aktiv"-Zähler.
- **Nicht** in v1: die ~150-Länder-Buffett-Daten, Big-Mac, alle Sub-Signal-Details, Zinskurven-Punkte. Die kommen mit dem jeweiligen Widget in späteren Schnitten (YAGNI). v1 deckt **nur** die Landing-Übersicht ab.

> **Offene Detailfrage für den Plan:** Wie genau das pro-Domäne-`available`-Flag und der `headline`-Kurztext aus den vorhandenen Chief-Result-Objekten abgeleitet werden (welches Feld signalisiert „UNAVAILABLE"/Default), wird beim Schreiben des Plans gegen die konkreten `*ChiefResult`-Modelle in `core/domain/models.py` festgelegt. Falls die Modelle keinen klaren „ausgefallen"-Marker tragen, ist das eine Folge-Aufgabe (Backend-Vertrag, Logbuch).

---

## 7. Bewusst NICHT in v1 (YAGNI) & bekannte Grenzen

- **Kein Lock auf parallele Läufe** (bewusste Nutzer-Entscheidung 2026-06-22): Zwei `POST …/run` können gleichzeitig laufen; die `run_id` an jedem Event hält sie auseinander. Ein „nur ein Lauf gleichzeitig" (409 Conflict) ist problemlos später nachrüstbar → Folge-Aufgabe.
- **Keine Persistenz** des API-Snapshots (nur In-Memory; Neustart = leer).
- **Keine Authentifizierung / kein CORS-Härten** über das für lokale Entwicklung Nötige hinaus (Dev-CORS für `localhost`-Frontend).
- **Kein** `bottomup`/`judge`-Endpunkt, **kein** Redis-Bus, **keine** reichen Widget-Daten (Buffett/Big-Mac). Alles spätere Schnitte nach demselben Muster.

---

## 8. Tests (TDD verpflichtend, AGENTS.md §4)

Erst rot, dann grün. Externe Provider werden **gefaket** — kein echter Netz-Call im Test.

1. **`cockpit_to_dict` (pure):** Happy-Path (alle Domänen verfügbar) · eine Domäne `UNAVAILABLE` → `available:false`, `signal:null`, `sources_active` korrekt dekrementiert · Regime/Konfidenz korrekt durchgereicht.
2. **`event_to_dict` (pure):** `type`/`source`/`payload`/`timestamp`/`run_id` korrekt abgebildet.
3. **`subscribe_all` am `InMemoryEventBus`:** registrierter Handler wird bei **jedem** `publish` (beliebiger Event-Typ) aufgerufen; bestehende typgenaue Subscriber funktionieren unverändert weiter.
4. **Bus→WS-Abonnent:** Event publizieren → erwartetes JSON liegt in der Queue.
5. **Endpunkte via FastAPI-`TestClient`:**
   - `GET /api/cockpit` ohne vorherigen Lauf → `204`.
   - `POST /api/cockpit/run` → `202` + `run_id` (Orchestrator gefaket, liefert ein bekanntes `CockpitResult`).
   - nach Lauf: `GET /api/cockpit` → `200` + erwartetes JSON.
   - `WS /ws/cockpit` empfängt während eines (gefakten) Laufs die Event-JSONs inkl. abschließendem `CockpitResultReady`.

Tests spiegeln die Paketstruktur: `tests/adapters/api/…`.

---

## 9. Nächste Schritte

1. **Plan schreiben** (`docs/superpowers/plans/2026-06-22-api-bridge-cockpit.md`) — TDD-Schritte in Umsetzungsreihenfolge.
2. Umsetzung in einem Feature-Branch (`feat/api-bridge-cockpit`), PR-First (AGENTS.md §5).
3. Entscheidungen & Folge-Aufgaben (kein Lock, keine Persistenz, `available`-Marker-Frage) ins Logbuch `docs/open_todos.md` übernehmen.

---

*Querverweise: `docs/superpowers/specs/2026-06-21-frontend-konzept.md` (übergeordnetes Frontend-Konzept), `core/ports/event_bus.py` + `adapters/event_bus/redis_bus.py` (Bus), `orchestrators/top_down_orchestrator.py` (Cockpit-Lauf), `adapters/cache/result_cache.py:588` (verlustbehafteter Alt-Cache — bewusst nicht recycelt). Status/PR-Protokoll: `docs/open_todos.md`.*
