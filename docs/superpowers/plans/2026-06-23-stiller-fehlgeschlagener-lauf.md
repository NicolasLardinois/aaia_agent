# Stiller fehlgeschlagener Lauf — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `phase = "running"` („läuft …") endet im Cockpit immer deterministisch — entweder mit Ergebnis (`"ready"`) oder mit klarer Fehlermeldung (`"error"`), nie als stilles Hängen.

**Architecture:** Backend (`RunManager._execute`) fängt eine Orchestrator-Exception, loggt sie serverseitig und broadcastet — analog zum bestehenden `CockpitResultReady` — eine terminale Inline-WS-Nachricht `CockpitRunFailed` mit generischem Text. Frontend routet `CockpitRunFailed` in einen Fehlerzustand und behandelt zusätzlich den unaufgeforderten Verbindungsabbruch; absichtliches Schließen hängt vorher die WS-Handler ab (`closeSocket`), damit der normale Abschluss / Re-Run keinen Fehlalarm auslöst.

**Tech Stack:** Python 3.12 / asyncio / pytest (Backend); React 19 / TypeScript 6 / Vitest 4 / @testing-library/react (Frontend).

## Global Constraints

- Kommentare und Commit-Messages auf **Deutsch** (Projekt-Stil).
- **TDD verpflichtend:** erst der fehlschlagende Test, dann Implementierung.
- **Kein** neues Domain-Event, **keine** `core/domain`-Änderung (Ansatz A, Inline-WS-Nachricht).
- **Sicherheit:** die an den Client gesendete Fehlermeldung ist **generisch** (`"Analyse fehlgeschlagen"`) — niemals `str(exc)`/Stacktrace nach außen (Repo öffentlich). Details nur ins Server-Log.
- Terminal-Nachrichtenname exakt: **`CockpitRunFailed`** (symmetrisch zu `CockpitResultReady`).
- Backend-Tests: `python -m pytest tests/adapters/api -q`. Frontend-Tests: `npm test` (= `vitest run`) im Ordner `frontend/`.
- Branch ist bereits angelegt: `fix/cockpit-run-failed` (Worktree `.claude/worktrees/run-failed`).

---

### Task 1: Backend — terminales `CockpitRunFailed` bei Orchestrator-Fehler

**Files:**
- Modify: `adapters/api/run_manager.py`
- Test: `tests/adapters/api/test_run_manager.py`

**Interfaces:**
- Consumes: `RunManager(orchestrator_factory, broadcaster)`, `RunManager._execute(orchestrator, run_id)` (bestehend), `_RecordingBroadcaster` (bestehend in der Testdatei).
- Produces: terminale Broadcast-Nachricht `{"type": "CockpitRunFailed", "source": "run_manager", "payload": {"message": "Analyse fehlgeschlagen"}, "run_id": <run_id>}` im Fehlerpfad; neuer privater Helfer `RunManager._drain_progress()`.

- [ ] **Step 1: Failing-Tests schreiben**

In `tests/adapters/api/test_run_manager.py` oben bei den Imports ergänzen (falls noch nicht vorhanden, ist `asyncio` bereits importiert) und am Dateiende anhängen:

```python
class _FailingOrch:
    """Orchestrator, der mit einer Exception abbricht (Fehlerpfad)."""
    def __init__(self, bus=None):
        self.bus = bus
    async def run(self):
        raise RuntimeError("interner-detail-LEAK-xyz")  # darf NICHT nach aussen gelangen


def test_execute_broadcasts_failure_terminal_on_error():
    broadcaster = _RecordingBroadcaster()
    rm = RunManager(lambda bus: _FailingOrch(bus), broadcaster)
    rm._running = True  # simuliert: start_run() hat den Lock gesetzt

    asyncio.run(rm._execute(_FailingOrch(), run_id="run-err"))

    types = [m["type"] for m in broadcaster.messages]
    assert "CockpitResultReady" not in types          # kein Erfolgs-Terminal
    terminal = broadcaster.messages[-1]
    assert terminal["type"] == "CockpitRunFailed"
    assert terminal["source"] == "run_manager"
    assert terminal["run_id"] == "run-err"
    assert rm._running is False                        # Lock auch im Fehlerfall frei
    assert rm.latest is None                           # kein Ergebnis gespeichert


def test_failure_message_is_generic_and_does_not_leak():
    broadcaster = _RecordingBroadcaster()
    rm = RunManager(lambda bus: _FailingOrch(bus), broadcaster)

    asyncio.run(rm._execute(_FailingOrch(), run_id="run-err"))

    message = broadcaster.messages[-1]["payload"]["message"]
    assert message == "Analyse fehlgeschlagen"
    assert "LEAK" not in message                        # kein Exception-Text nach aussen


def test_failure_path_drains_progress_before_terminal():
    broadcaster = _RecordingBroadcaster()
    rm = RunManager(lambda bus: _FailingOrch(bus), broadcaster)

    async def scenario():
        async def progress():
            await broadcaster.broadcast({"type": "MacroChiefReady", "source": "m",
                                         "payload": {}, "run_id": "run-err"})
        rm._broadcast_tasks.add(asyncio.create_task(progress()))
        await rm._execute(_FailingOrch(), run_id="run-err")

    asyncio.run(scenario())
    types = [m["type"] for m in broadcaster.messages]
    assert types[-1] == "CockpitRunFailed"
    assert "MacroChiefReady" in types[:-1]              # Fortschritt kam VOR dem Terminal
```

- [ ] **Step 2: Tests laufen lassen — müssen fehlschlagen**

Run: `python -m pytest tests/adapters/api/test_run_manager.py -q`
Expected: FAIL (im Fehlerpfad wird aktuell keine `CockpitRunFailed`-Nachricht gesendet; `broadcaster.messages` ist leer → IndexError/AssertionError).

- [ ] **Step 3: Implementierung in `adapters/api/run_manager.py`**

Logging-Import oben ergänzen (nach den bestehenden Imports):

```python
import logging

_logger = logging.getLogger(__name__)
```

`_execute` ersetzen durch die Variante mit `except`-Zweig + extrahiertem Drain-Helfer:

```python
    async def _execute(self, orchestrator, run_id: str) -> None:
        try:
            result = await orchestrator.run()
            self._latest = result
            # Fortschritts-Broadcasts (fire-and-forget aus dem Bus-Handler) zuerst
            # abschliessen, damit das terminale Event garantiert ZULETZT ankommt
            # (Vertrag: erst Fortschritt, dann fertig).
            await self._drain_progress()
            await self.broadcaster.broadcast({
                "type": "CockpitResultReady",
                "source": "run_manager",
                "payload": cockpit_to_dict(result),
                "run_id": run_id,
            })
        except Exception:
            # Details NUR ins Server-Log (Beobachtbarkeit) — niemals an den Client
            # (Repo oeffentlich, Client nicht vertrauenswuerdig).
            _logger.exception("Cockpit-Lauf %s fehlgeschlagen", run_id)
            await self._drain_progress()
            await self.broadcaster.broadcast({
                "type": "CockpitRunFailed",
                "source": "run_manager",
                "payload": {"message": "Analyse fehlgeschlagen"},
                "run_id": run_id,
            })
        finally:
            self._running = False  # Lock immer freigeben (auch nach Fehler)

    async def _drain_progress(self) -> None:
        # Offene Fortschritts-Broadcast-Tasks abwarten, damit sie VOR dem
        # terminalen Event beim Client ankommen.
        if self._broadcast_tasks:
            await asyncio.gather(*self._broadcast_tasks, return_exceptions=True)
```

- [ ] **Step 4: Tests laufen lassen — müssen grün sein**

Run: `python -m pytest tests/adapters/api/test_run_manager.py -q`
Expected: PASS (alle Tests, inkl. der bestehenden Erfolgs-/Sequenz-Tests).

- [ ] **Step 5: Commit**

```bash
git add adapters/api/run_manager.py tests/adapters/api/test_run_manager.py
git commit -m "feat(api): terminales CockpitRunFailed bei Orchestrator-Fehler (Lauf haengt nicht mehr)"
```

---

### Task 2: Frontend — `cockpitSocket` routet `CockpitRunFailed` → `onFailed`

**Files:**
- Modify: `frontend/src/api/cockpitSocket.ts`
- Test: `frontend/src/api/cockpitSocket.test.ts`

**Interfaces:**
- Consumes: `openCockpitSocket(base, handlers, factory?, token?)`, `CockpitEvent`, `WebSocketLike` (bestehend).
- Produces: neues optionales Handler-Feld `onFailed?: (e: CockpitEvent) => void` in `SocketHandlers`; `onmessage` ruft `onFailed`, wenn `msg.type === "CockpitRunFailed"`.

- [ ] **Step 1: Failing-Test schreiben**

In `frontend/src/api/cockpitSocket.test.ts` im `describe`-Block ergänzen:

```typescript
  it("ruft onFailed beim terminalen CockpitRunFailed (nicht onResult)", () => {
    const ws = fakeWs();
    const onFailed = vi.fn();
    const onResult = vi.fn();
    openCockpitSocket("https://api.example.com", { onFailed, onResult }, () => ws);

    ws.onmessage!({ data: JSON.stringify({ type: "CockpitRunFailed", source: "run_manager", payload: { message: "Analyse fehlgeschlagen" }, run_id: "r" }) });

    expect(onFailed).toHaveBeenCalledOnce();
    expect(onFailed).toHaveBeenCalledWith(expect.objectContaining({ type: "CockpitRunFailed" }));
    expect(onResult).not.toHaveBeenCalled();
  });
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run (im Ordner `frontend/`): `npm test -- cockpitSocket`
Expected: FAIL (`onFailed` wird nicht aufgerufen — Routing fehlt).

- [ ] **Step 3: Implementierung in `frontend/src/api/cockpitSocket.ts`**

`SocketHandlers` um `onFailed` erweitern:

```typescript
export interface SocketHandlers {
  onOpen?: () => void;
  onEvent?: (e: CockpitEvent) => void;
  onResult?: (overview: CockpitOverview, e: CockpitEvent) => void;
  onFailed?: (e: CockpitEvent) => void;
  onError?: () => void;
  onClose?: () => void;
}
```

`onmessage` um das Routing ergänzen (nach dem bestehenden `CockpitResultReady`-Zweig):

```typescript
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data) as CockpitEvent;
    handlers.onEvent?.(msg);
    if (msg.type === "CockpitResultReady") {
      handlers.onResult?.(msg.payload as unknown as CockpitOverview, msg);
    } else if (msg.type === "CockpitRunFailed") {
      handlers.onFailed?.(msg);
    }
  };
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run (im Ordner `frontend/`): `npm test -- cockpitSocket`
Expected: PASS (neuer Test + die vier bestehenden Tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/cockpitSocket.ts frontend/src/api/cockpitSocket.test.ts
git commit -m "feat(frontend): cockpitSocket routet CockpitRunFailed -> onFailed"
```

---

### Task 3: Frontend — `useCockpit` Fehlerzustand + Verbindungsabbruch-Guard

**Files:**
- Modify: `frontend/src/hooks/useCockpit.ts`
- Test: `frontend/src/hooks/useCockpit.test.tsx`

**Interfaces:**
- Consumes: `useCockpit(deps)`, `Phase`, `openCockpitSocket`, `WebSocketLike`, `CockpitEvent`, `startRun`, `UnauthorizedError`, `RunInProgressError` (bestehend); neues `SocketHandlers.onFailed` aus Task 2.
- Produces: Modul-Helfer `closeSocket(ws: WebSocketLike | null)`; `useCockpit` setzt `phase = "error"` mit Meldung bei `CockpitRunFailed` und bei unaufgefordertem `onClose`.

- [ ] **Step 1: Failing-Tests schreiben**

In `frontend/src/hooks/useCockpit.test.tsx` im `describe`-Block ergänzen:

```tsx
  it("CockpitRunFailed -> phase error + Meldung aus dem Payload", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 202, body: { run_id: "r1" } },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });
    act(() => { ws.onopen!(); });
    act(() => { ws.onmessage!({ data: JSON.stringify({ type: "CockpitRunFailed", source: "run_manager", payload: { message: "Analyse fehlgeschlagen" }, run_id: "r1" }) }); });
    await waitFor(() => expect(result.current.phase).toBe("error"));
    expect(result.current.error).toBe("Analyse fehlgeschlagen");
  });

  it("unaufgeforderter onClose waehrend des Laufs -> phase error", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 202, body: { run_id: "r1" } },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });
    act(() => { ws.onopen!(); });
    act(() => { ws.onclose!(); });  // Kabel reisst, ohne Terminal
    await waitFor(() => expect(result.current.phase).toBe("error"));
    expect(result.current.error).toBe("Verbindung zum Server unterbrochen");
  });

  it("Guard: nach onResult ist onClose abgehaengt -> phase bleibt ready", async () => {
    const ws = makeFakeWs();
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 202, body: { run_id: "r1" } },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });
    act(() => { ws.onopen!(); });
    act(() => { ws.onmessage!({ data: JSON.stringify({ type: "CockpitResultReady", source: "run_manager", payload: overview, timestamp: "t", run_id: "r1" }) }); });
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(ws.onclose).toBeNull();          // Handler abgehaengt -> kein Fehlalarm moeglich
    expect(ws.close).toHaveBeenCalled();
  });

  it("Re-Run schliesst den alten Socket ohne Fehlalarm", async () => {
    const ws1 = makeFakeWs();
    const ws2 = makeFakeWs();
    const queue = [ws1, ws2];
    const factory = () => queue.shift()!;
    const fetchFn = fakeFetch({
      "GET http://x/api/cockpit": { status: 204 },
      "POST http://x/api/cockpit/run": { status: 202, body: { run_id: "r1" } },
    });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: factory }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    act(() => { result.current.startAnalysis(); });  // oeffnet ws1
    act(() => { result.current.startAnalysis(); });  // Re-Run: schliesst ws1, oeffnet ws2
    expect(ws1.onclose).toBeNull();          // alter Handler abgehaengt
    expect(ws1.close).toHaveBeenCalled();
    expect(result.current.phase).toBe("running");
    expect(result.current.error).toBeNull();
  });
```

- [ ] **Step 2: Tests laufen lassen — müssen fehlschlagen**

Run (im Ordner `frontend/`): `npm test -- useCockpit`
Expected: FAIL (`onFailed`/`onClose` werden noch nicht behandelt; `ws.onclose` wird nicht abgehängt).

- [ ] **Step 3: Implementierung in `frontend/src/hooks/useCockpit.ts`**

Modul-Helfer oberhalb von `useCockpit` (nach den Imports / `DEFAULT_BASE`) einfügen:

```typescript
// Absichtliches Schliessen: WS-Handler abhaengen, BEVOR geschlossen wird, damit
// onclose/onerror nicht mehr feuern. Sonst wuerde der normale Abschluss (onResult
// schliesst den WS), ein Re-Run oder das Unmount faelschlich "Verbindung
// unterbrochen" melden. So feuert onClose nur bei einem UNAUFGEFORDERTEN Abbruch.
function closeSocket(ws: WebSocketLike | null): void {
  if (!ws) return;
  ws.onclose = null;
  ws.onerror = null;
  ws.close();
}
```

Unmount-Cleanup auf `closeSocket` umstellen:

```typescript
  // Offenen WebSocket beim Unmount schliessen (kein Leak / kein setState nach Unmount).
  useEffect(() => () => { closeSocket(wsRef.current); }, []);
```

`startAnalysis` ersetzen:

```typescript
  const startAnalysis = useCallback(() => {
    setPhase("running");
    setEvents([]);
    setError(null);
    closeSocket(wsRef.current); // vorherigen Lauf abbrechen (Doppelklick/Re-Run) OHNE Fehlalarm
    // Reihenfolge: erst WS oeffnen, POST erst in onOpen -> keine fruehen Events verloren.
    wsRef.current = openCockpitSocket(
      base,
      {
        onOpen: () => {
          startRun(base, fetchFn, token).catch((e) => {
            if (e instanceof RunInProgressError) return;       // laeuft schon -> WS liefert das Ergebnis
            if (e instanceof UnauthorizedError) { onUnauthorizedRef.current?.(); return; }
            setError("Start fehlgeschlagen"); setPhase("error");
          });
        },
        // onEvent feuert fuer JEDE Nachricht; die terminalen Events (Ergebnis/Fehler)
        // gehoeren nicht in den Fortschritts-Stream.
        onEvent: (e) => {
          if (e.type !== "CockpitResultReady" && e.type !== "CockpitRunFailed") {
            setEvents((prev) => [...prev, e]);
          }
        },
        onResult: (ov) => { setOverview(ov); setPhase("ready"); closeSocket(wsRef.current); },
        onFailed: (e) => {
          const msg = typeof e.payload?.message === "string" ? e.payload.message : "Analyse fehlgeschlagen";
          setError(msg); setPhase("error"); closeSocket(wsRef.current);
        },
        onError: () => { setError("WebSocket-Fehler"); setPhase("error"); closeSocket(wsRef.current); },
        onClose: () => { setError("Verbindung zum Server unterbrochen"); setPhase("error"); },
      },
      wsFactory,
      token,
    );
  }, [base, fetchFn, wsFactory, token]);
```

- [ ] **Step 4: Tests laufen lassen — müssen grün sein**

Run (im Ordner `frontend/`): `npm test -- useCockpit`
Expected: PASS (neue Tests + alle bestehenden useCockpit-Tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useCockpit.ts frontend/src/hooks/useCockpit.test.tsx
git commit -m "feat(frontend): useCockpit beendet 'laeuft' immer (CockpitRunFailed + Verbindungsabbruch-Guard)"
```

---

### Task 4: Gesamtlauf — beide Test-Suites grün

**Files:** (keine Code-Änderung — reine Verifikation vor dem PR)

- [ ] **Step 1: Backend-Gesamtlauf**

Run (Repo-Wurzel): `python -m pytest -q`
Expected: PASS (keine Regression in den übrigen Paketen).

- [ ] **Step 2: Frontend-Gesamtlauf**

Run (im Ordner `frontend/`): `npm test`
Expected: PASS (alle Vitest-Dateien grün).

- [ ] **Step 3: (kein Commit nötig)**

Beide Suites grün → der Branch ist bereit für `finishing-a-development-branch` (Push + PR, Review durch den User, danach Logbuch-Vermerk).

---

## Self-Review

**1. Spec coverage:**
- Backend-Fehlerpfad + generische Meldung + Drain → Task 1. ✓
- `cockpitSocket` `onFailed`-Routing → Task 2. ✓
- `useCockpit` Fehlerzustand, `onEvent`-Filter beider Terminals, `closeSocket`-Guard, unaufgeforderter `onClose` → Task 3. ✓
- Drei getrennte Meldungen (Analyse fehlgeschlagen / Verbindung unterbrochen / WebSocket-Fehler) → Task 3. ✓
- Sicherheit (kein Leak) → Task 1 (`test_failure_message_is_generic_and_does_not_leak`). ✓
- Nicht-Ziele (kein Domain-Event/Timeout/Retry) → eingehalten. ✓

**2. Placeholder scan:** keine TBD/TODO; jeder Code-Schritt enthält vollständigen Code. ✓

**3. Type consistency:** `CockpitRunFailed` (Backend-Broadcast) ↔ Routing in `cockpitSocket` ↔ `onFailed` in `useCockpit` durchgängig identisch; Payload-Feld `message` (Backend `{"message": ...}`) ↔ Frontend `e.payload.message`. `closeSocket(ws: WebSocketLike | null)` in Task 3 definiert und dort konsistent verwendet. `onFailed?: (e: CockpitEvent) => void` in Task 2 definiert, in Task 3 konsumiert. ✓
