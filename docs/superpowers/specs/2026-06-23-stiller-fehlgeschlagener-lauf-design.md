# Design: Stiller fehlgeschlagener Lauf — terminales Fehler-Signal + Verbindungsabbruch

> Status: Design freigegeben (2026-06-23). Folgeaufgabe aus dem Review zu PR #32.
> Quelle des laufenden Status/PR-Protokolls: `docs/open_todos.md` (nicht hier).

## Problem

Im Cockpit-Flow öffnet das Frontend einen WebSocket, startet per `POST /api/cockpit/run`
einen Lauf und zeigt `phase = "running"` („läuft …") an, bis eine **terminale**
Nachricht eintrifft. Erfolg → der `RunManager` broadcastet `CockpitResultReady`
(als Inline-Dict, **kein** Domain-Event) → das Frontend wechselt auf `"ready"`.

Es gibt zwei Wege, auf denen der Client **dauerhaft in „läuft …" hängen** bleibt:

1. **Server-seitiger Fehler:** Wirft `orchestrator.run()` in `RunManager._execute`,
   greift nur das `finally` (Lock-Freigabe) — es wird **keine** terminale Nachricht
   gesendet. Der WebSocket bleibt offen (der `ws_cockpit`-Loop hält die Verbindung
   unabhängig), der Client bekommt weder Nachricht noch Close → `phase` bleibt ewig
   `"running"`.
2. **Verbindungsabbruch mitten im Lauf:** Reißt der WebSocket während des Laufs
   (Server-Neustart, Netzabbruch), feuert im Frontend `onclose` — wird aber **nicht
   behandelt** (`useCockpit` übergibt keinen `onClose`-Handler) → `phase` bleibt
   `"running"`.

**Ziel:** `phase = "running"` endet **immer** deterministisch — entweder in `"ready"`
(Ergebnis) oder `"error"` (klare Meldung). Nie ein stilles Hängen.

## Lösung (gewählter Ansatz: A — Inline-WS-Nachricht)

Spiegelt exakt den bestehenden Erfolgspfad: das Terminal-Signal ist eine kleine
Inline-WS-Nachricht, **kein** neues Domain-Event (das wäre inkonsistent zu
`CockpitResultReady` und überzogen).

### 1) Backend — `adapters/api/run_manager.py`

`_execute` bekommt einen `except Exception`-Zweig (nicht `BaseException` — `CancelledError`
soll weiter propagieren). Der Drain-Schritt wird als `_drain_progress()` extrahiert
(gegen Duplizierung), da Erfolgs- und Fehlerpfad ihn beide brauchen.

```python
async def _execute(self, orchestrator, run_id: str) -> None:
    try:
        result = await orchestrator.run()
        self._latest = result
        await self._drain_progress()
        await self.broadcaster.broadcast({
            "type": "CockpitResultReady", "source": "run_manager",
            "payload": cockpit_to_dict(result), "run_id": run_id,
        })
    except Exception:
        _logger.exception("Cockpit-Lauf %s fehlgeschlagen", run_id)  # Details NUR ins Log
        await self._drain_progress()
        await self.broadcaster.broadcast({
            "type": "CockpitRunFailed", "source": "run_manager",
            "payload": {"message": "Analyse fehlgeschlagen"}, "run_id": run_id,
        })
    finally:
        self._running = False  # Lock immer freigeben
```

- **Drain-Reihenfolge:** wie im Erfolgsfall werden offene Fortschritts-Broadcasts
  zuerst abgewartet, damit bereits emittierte Fortschritts-Events **vor** dem Terminal
  ankommen.
- **Sicherheit:** die Client-Nachricht ist **generisch** (`"Analyse fehlgeschlagen"`).
  Niemals `str(exc)`/Stacktrace nach außen (Repo öffentlich, Client nicht
  vertrauenswürdig). Die vollständigen Details landen über `logger.exception`
  im Server-Log (Beobachtbarkeit).
- **Name:** `CockpitRunFailed` — symmetrisch zu `CockpitResultReady`.

### 2) Frontend — terminales Fehler-Event (`src/api/cockpitSocket.ts`)

- `SocketHandlers` bekommt `onFailed?: (e: CockpitEvent) => void`.
- In `onmessage` nach `onEvent`: `type === "CockpitResultReady"` → `onResult`,
  sonst `type === "CockpitRunFailed"` → `onFailed`.

### 3) Frontend — Fehlerzustand + Verbindungsabbruch (`src/hooks/useCockpit.ts`)

- `onFailed` → `setError(payload.message ?? "Analyse fehlgeschlagen")`,
  `phase = "error"`, Socket schließen.
- `onEvent`-Filter blendet **beide** Terminal-Typen aus der Fortschrittsliste aus
  (`CockpitResultReady` und `CockpitRunFailed`).
- **Verbindungsabbruch-Guard:** Kernproblem — `onclose` feuert auch beim **normalen**
  Abschluss (wir schließen den WS nach `onResult`/`onFailed`) und beim Re-Run. Lösung:
  ein Helfer `closeSocket(ws)` setzt `ws.onclose = ws.onerror = null` **vor** `ws.close()`.
  Er wird bei **jedem absichtlichen** Schließen verwendet: Re-Run, Unmount, nach
  `onResult`, `onFailed`, `onError`. Dadurch feuert der `onClose`-Handler **nur** bei
  einem **unaufgeforderten** Abbruch → `setError("Verbindung zum Server unterbrochen")`,
  `phase = "error"`. Kein Überschreiben des fertigen Zustands, kein Fehlalarm beim Re-Run.

### 4) Fehlermeldungen (klar getrennt)

| Auslöser | Meldung |
|---|---|
| `CockpitRunFailed` (Server hat gerechnet, gescheitert) | „Analyse fehlgeschlagen" |
| unaufgeforderter `onclose` (Kabel reißt im Lauf) | „Verbindung zum Server unterbrochen" |
| `onerror` (WebSocket-Fehler, bestehend) | „WebSocket-Fehler" |

## Tests (TDD — erst rot)

**Backend (`tests/adapters/api/test_run_manager*.py`):**
- Werfender Orchestrator → Broadcaster erhält terminal `CockpitRunFailed`
  (und **kein** `CockpitResultReady`); `_running` danach `False` (Lock frei).
- Die Fehler-Nachricht ist generisch — `payload.message` enthält **nicht** den
  Exception-Text (Sicherheits-Check gegen Leak).
- Fortschritts-Broadcasts werden auch im Fehlerpfad gedrained (Terminal kommt zuletzt).

**Frontend (`frontend/src/**/*.test.ts(x)`):**
- `cockpitSocket`: `CockpitRunFailed`-Nachricht → `onFailed`; `CockpitResultReady`
  → `onResult` (bestehend, bleibt grün).
- `useCockpit`:
  - (a) `CockpitRunFailed` → `phase = "error"` + Meldung gesetzt.
  - (b) unaufgeforderter `onClose` während `"running"` → `phase = "error"` +
    „Verbindung zum Server unterbrochen".
  - (c) **Guard:** `onResult` → dann Close → `phase` bleibt `"ready"` (kein Fehlalarm).
  - (d) Re-Run schließt den alten Socket ohne Fehlalarm (alter `onclose` feuert nicht).

## Nicht-Ziele (YAGNI)

- Kein neues Domain-Event, keine `core/domain`-Änderung.
- Kein Retry/Backoff, keine automatische Wiederverbindung — nur klares Ende + Fehleranzeige.
- Kein Frontend-Timeout (kollidiert mit legitim langen Free-Tier-Läufen/Cold-Starts).
