# Zugriffsschutz (Auth + Lauf-Lock) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die deployte Cockpit-Scheibe mit einem gemeinsamen Zugangs-Token (Passwort) und einem Lauf-Lock absichern — Backend prüft das Token auf allen Endpunkten, das Frontend zeigt einen Login-Screen.

**Architecture:** Backend: eine `auth.py` (pure `token_valid` + FastAPI-Dependency `require_token`), in GET/POST eingehängt, WS prüft den Token per Query-Parameter; `RunManager` bekommt einen Lauf-Lock (`409` bei aktivem Lauf, im `finally` freigegeben). Frontend: `useAuth` (Token in localStorage) + `LoginGate`-Komponente; das Token wird an alle Aufrufe gehängt (Header bzw. `?token=`), bei `401` erscheint der Login-Screen.

**Tech Stack:** FastAPI/Starlette, Python `secrets`; React/TypeScript, Vitest/RTL.

## Global Constraints

- **Sprache:** Code-Kommentare/UI-Texte auf **Deutsch**; Commit-Präfixe `feat(...)`/`fix(...)`/`test(...)`/`docs(...)`.
- **TDD verpflichtend:** erst der fehlschlagende Test, dann minimaler Code bis grün.
- **Token aus `AAIA_ACCESS_TOKEN`** (Env). **Leeres Token ⇒ Auth deaktiviert** (nur lokal; Warn-Log beim App-Bau). Niemals im Repo.
- **HTTP:** Token via `Authorization: Bearer <token>`; fehlt/falsch ⇒ **`401`**. **WS:** Token via Query-Param `?token=…`; falsch ⇒ `close(1008)` ohne `accept`.
- **Konstanter Zeitvergleich** mit `secrets.compare_digest`.
- **Lauf-Lock:** `RunManager.start_run() -> str | None` (`None` = es läuft bereits); Route ⇒ **`409`**. Lock im **`finally`** von `_execute` freigeben.
- **Frontend-Token** in `localStorage` unter Schlüssel `aaia_token`. `getCockpit`/`startRun` werfen bei `401` `UnauthorizedError`; `startRun` bei `409` `RunInProgressError`. WS-URL bekommt `?token=` (URL-enkodiert).
- **YAGNI:** kein Rate-Limit, keine Accounts, eine Instanz.
- **Keine echten Netz-Calls in Tests** (Fakes). Backend-Test-Default: ohne gesetztes `AAIA_ACCESS_TOKEN` ist Auth aus → bestehende Routen-Tests bleiben grün; Auth-Tests setzen den Env-Wert per `monkeypatch`.

---

## File Structure

| Datei | Verantwortung |
|---|---|
| `adapters/api/auth.py` (create) | `token_valid`, `require_token`, Bearer-Parsing |
| `adapters/api/routes_cockpit.py` (modify) | `Depends(require_token)` an GET/POST; WS-Token-Check; `409` bei Lock |
| `adapters/api/run_manager.py` (modify) | Lauf-Lock (`_running`, `start_run -> str|None`, `finally`) |
| `adapters/api/app_factory.py` (modify) | Warn-Log, wenn `AAIA_ACCESS_TOKEN` leer |
| `frontend/src/api/client.ts` (modify) | Token-Header, `UnauthorizedError`, `RunInProgressError` |
| `frontend/src/api/cockpitSocket.ts` (modify) | `?token=` an WS-URL |
| `frontend/src/auth/useAuth.ts` (create) | Token-State (localStorage) |
| `frontend/src/auth/LoginGate.tsx` (create) | Passwort-Screen |
| `frontend/src/hooks/useCockpit.ts` (modify) | Token + `onUnauthorized`; `401`/`409`-Handling |
| `frontend/src/pages/CockpitPage.tsx` (modify) | `onLogout`-Link |
| `frontend/src/App.tsx` (modify) | Login-Gate-Verdrahtung |
| `render.yaml` (modify) | `AAIA_ACCESS_TOKEN` (sync:false) |
| `docs/deploy-render.md` (modify) | Env-Tabelle + „Zugang für den Dozenten" |
| `docs/open_todos.md` (modify) | Logbuch |

---

## Task 1: Backend-Auth-Kern (`auth.py`)

**Files:**
- Create: `adapters/api/auth.py`
- Test: `tests/adapters/api/test_auth.py`

**Interfaces:**
- Produces: `token_valid(provided: str | None) -> bool` (leeres erwartetes Token ⇒ `True`); `require_token(authorization: str | None = Header(None)) -> None` (FastAPI-Dependency, `401` bei ungültig); intern `_expected_token() -> str`.

- [ ] **Step 1: Failing-Test**

`tests/adapters/api/test_auth.py`:
```python
from adapters.api.auth import token_valid


def test_empty_expected_token_disables_auth(monkeypatch):
    monkeypatch.delenv("AAIA_ACCESS_TOKEN", raising=False)
    assert token_valid(None) is True
    assert token_valid("irgendwas") is True


def test_set_token_requires_exact_match(monkeypatch):
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    assert token_valid("geheim") is True
    assert token_valid("falsch") is False
    assert token_valid(None) is False
    assert token_valid("") is False
```

- [ ] **Step 2: Rot**

Run: `python -m pytest tests/adapters/api/test_auth.py -q`
Expected: FAIL (`ModuleNotFoundError: adapters.api.auth`).

- [ ] **Step 3: Implementieren**

`adapters/api/auth.py`:
```python
"""Gemeinsames Zugangs-Token (Shared Secret) fuer die API.

Leeres AAIA_ACCESS_TOKEN -> Auth deaktiviert (nur lokale Entwicklung).
Konstanter Zeitvergleich gegen Timing-Angriffe.
"""
import os
import secrets

from fastapi import Header, HTTPException, status


def _expected_token() -> str:
    return os.environ.get("AAIA_ACCESS_TOKEN", "")


def token_valid(provided: str | None) -> bool:
    expected = _expected_token()
    if not expected:
        return True  # kein Token gesetzt -> Auth aus (nur lokal sinnvoll)
    if not provided:
        return False
    return secrets.compare_digest(provided, expected)


def _bearer(authorization: str | None) -> str | None:
    # "Bearer <token>" -> "<token>"
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:]
    return None


def require_token(authorization: str | None = Header(default=None)) -> None:
    """FastAPI-Dependency: prueft den Bearer-Token, sonst 401."""
    if not token_valid(_bearer(authorization)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiges oder fehlendes Token",
        )
```

- [ ] **Step 4: Grün**

Run: `python -m pytest tests/adapters/api/test_auth.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/api/auth.py tests/adapters/api/test_auth.py
git commit -m "feat(api): Auth-Kern (token_valid + require_token, Shared Secret)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Auth in Routen + WebSocket einhängen

**Files:**
- Modify: `adapters/api/routes_cockpit.py`, `adapters/api/app_factory.py`
- Test: `tests/adapters/api/test_routes_auth.py`

**Interfaces:**
- Consumes: `require_token`, `token_valid` (Task 1).
- Produces: GET/POST verlangen `Depends(require_token)`; WS prüft `websocket.query_params.get("token")` via `token_valid` vor `accept()`.

- [ ] **Step 1: Failing-Test**

`tests/adapters/api/test_routes_auth.py`:
```python
import pytest
from fastapi.testclient import TestClient
from core.domain.models import CockpitResult
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager
from adapters.api.app_factory import create_app


class _FakeOrch:
    def __init__(self, bus):
        self.bus = bus
    async def run(self):
        return CockpitResult(
            macro=MacroChiefAgent.default(), commodities=CommodityChiefAgentMakro.default(),
            sentiment=SentimentChiefAgent.default(), yield_curve=YieldCurveChiefAgent.default(),
            sectors=SectorChiefAgent.default(),
        )


def _client():
    rm = RunManager(lambda bus: _FakeOrch(bus), WebSocketBroadcaster())
    return TestClient(create_app(rm))


def test_get_requires_token_when_set(monkeypatch):
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    client = _client()
    assert client.get("/api/cockpit").status_code == 401
    assert client.get("/api/cockpit", headers={"Authorization": "Bearer falsch"}).status_code == 401
    # korrektes Token -> kein 401 (204, da noch kein Lauf)
    assert client.get("/api/cockpit", headers={"Authorization": "Bearer geheim"}).status_code == 204


def test_post_requires_token_when_set(monkeypatch):
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    client = _client()
    assert client.post("/api/cockpit/run").status_code == 401
    assert client.post("/api/cockpit/run", headers={"Authorization": "Bearer geheim"}).status_code == 202


def test_ws_rejects_without_token(monkeypatch):
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    client = _client()
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/cockpit"):
            pass  # ohne ?token -> Verbindung wird abgewiesen


def test_ws_accepts_with_token(monkeypatch):
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    client = _client()
    with client.websocket_connect("/ws/cockpit?token=geheim") as ws:
        assert ws is not None  # akzeptiert
```

- [ ] **Step 2: Rot**

Run: `python -m pytest tests/adapters/api/test_routes_auth.py -q`
Expected: FAIL (GET/POST geben aktuell `204`/`202` statt `401`; WS akzeptiert ohne Token).

- [ ] **Step 3: Implementieren — Routen**

`adapters/api/routes_cockpit.py` (gesamten Inhalt ersetzen):
```python
"""HTTP- und WebSocket-Routen fuer den Cockpit-Flow (mit Token-Schutz).

Alle Endpunkte erfordern ein gueltiges Token (AAIA_ACCESS_TOKEN; leer -> Auth aus).
HTTP: Authorization: Bearer <token>. WS: ?token=<token> (Browser koennen bei WS
keine Header setzen). POST liefert 409, wenn bereits ein Lauf laeuft.
"""
from fastapi import APIRouter, Depends, Response, WebSocket, WebSocketDisconnect, status

from adapters.api.auth import require_token, token_valid
from adapters.api.cockpit_serializer import cockpit_to_dict
from adapters.api.run_manager import RunManager


def build_router(run_manager: RunManager) -> APIRouter:
    router = APIRouter()

    @router.get("/api/cockpit")
    def get_cockpit(_: None = Depends(require_token)):
        if run_manager.latest is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        return cockpit_to_dict(run_manager.latest)

    @router.post("/api/cockpit/run", status_code=status.HTTP_202_ACCEPTED)
    async def post_run(_: None = Depends(require_token)):
        run_id = run_manager.start_run()
        if run_id is None:
            return Response(status_code=status.HTTP_409_CONFLICT)  # laeuft bereits
        return {"run_id": run_id}

    @router.websocket("/ws/cockpit")
    async def ws_cockpit(websocket: WebSocket):
        # WS-Auth: Token als Query-Param; vor accept() pruefen.
        if not token_valid(websocket.query_params.get("token")):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        await websocket.accept()
        run_manager.broadcaster.connect(websocket)
        try:
            while True:
                await websocket.receive_text()  # haelt die Verbindung; erkennt Disconnect
        except WebSocketDisconnect:
            pass
        finally:
            run_manager.broadcaster.disconnect(websocket)

    return router
```
Hinweis: Der `409`-Zweig setzt Task 3 voraus (`start_run` kann `None` liefern). Bis Task 3 implementiert ist, gibt `start_run` immer einen `run_id` zurück (nie `None`), der `if`-Zweig ist dann nur totes-aber-korrektes Vorhalten — die Auth-Tests dieses Tasks prüfen `409` nicht.

- [ ] **Step 4: Implementieren — Warn-Log (app_factory)**

In `adapters/api/app_factory.py` oben ergänzen und in `create_app` warnen, wenn kein Token gesetzt ist:
```python
import logging
...
_logger = logging.getLogger(__name__)
...
def create_app(run_manager: RunManager) -> FastAPI:
    if not os.environ.get("AAIA_ACCESS_TOKEN"):
        _logger.warning("AAIA_ACCESS_TOKEN ist leer -> API ist UNGESCHUETZT (nur fuer lokale Entwicklung).")
    app = FastAPI(title="AAIA API", version="0.1.0")
    ...  # Rest unveraendert
```
(`os` ist in `app_factory.py` bereits importiert.)

- [ ] **Step 5: Grün + Regression**

Run: `python -m pytest tests/adapters/api/test_routes_auth.py tests/adapters/api/test_routes_cockpit.py -q`
Expected: PASS (neue Auth-Tests grün; bestehende Routen-Tests bleiben grün, da ohne gesetztes `AAIA_ACCESS_TOKEN` Auth aus ist).

- [ ] **Step 6: Commit**

```bash
git add adapters/api/routes_cockpit.py adapters/api/app_factory.py tests/adapters/api/test_routes_auth.py
git commit -m "feat(api): Token-Schutz fuer GET/POST/WS + Warn-Log bei offenem Token

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Lauf-Lock im `RunManager`

**Files:**
- Modify: `adapters/api/run_manager.py`
- Test: `tests/adapters/api/test_run_lock.py`

**Interfaces:**
- Consumes: bestehender `RunManager`.
- Produces: `start_run() -> str | None` (`None`, wenn bereits ein Lauf aktiv); `self._running: bool`; `_execute` gibt den Lock im `finally` frei.

- [ ] **Step 1: Failing-Test**

`tests/adapters/api/test_run_lock.py`:
```python
import asyncio
import pytest
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager


class _RaisingOrch:
    def __init__(self, bus=None):
        self.bus = bus
    async def run(self):
        raise RuntimeError("Lauf fehlgeschlagen")


def test_start_run_returns_none_when_already_running():
    rm = RunManager(lambda bus: _RaisingOrch(bus), WebSocketBroadcaster())
    rm._running = True  # simuliere aktiven Lauf
    assert rm.start_run() is None


def test_lock_is_released_in_finally_even_on_error():
    rm = RunManager(lambda bus: _RaisingOrch(bus), WebSocketBroadcaster())

    async def scenario():
        rm._running = True
        with pytest.raises(RuntimeError):
            await rm._execute(_RaisingOrch(), "run-x")

    asyncio.run(scenario())
    assert rm._running is False
```

- [ ] **Step 2: Rot**

Run: `python -m pytest tests/adapters/api/test_run_lock.py -q`
Expected: FAIL (`AttributeError`/`assert` — `_running` existiert nicht / `start_run` ignoriert es; `_execute` setzt nichts zurück).

- [ ] **Step 3: Implementieren**

In `adapters/api/run_manager.py`:
- `__init__` ergänzen: `self._running = False`
- `start_run` und `_execute` ersetzen durch:
```python
    def start_run(self) -> str | None:
        if self._running:
            return None  # es laeuft bereits ein Lauf -> Route antwortet 409
        self._running = True
        run_id = uuid4().hex
        bus = InMemoryEventBus()
        bus.subscribe_all(lambda ev: self._schedule(event_to_dict(ev, run_id)))
        orchestrator = self._make_orchestrator(bus)
        task = asyncio.create_task(self._execute(orchestrator, run_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return run_id

    async def _execute(self, orchestrator, run_id: str) -> None:
        try:
            result = await orchestrator.run()
            self._latest = result
            # Fortschritts-Broadcasts zuerst abschliessen, dann terminales Event.
            if self._broadcast_tasks:
                await asyncio.gather(*self._broadcast_tasks, return_exceptions=True)
            await self.broadcaster.broadcast({
                "type": "CockpitResultReady",
                "source": "run_manager",
                "payload": cockpit_to_dict(result),
                "run_id": run_id,
            })
        finally:
            self._running = False  # Lock immer freigeben (auch nach Fehler)
```
Den Rückgabetyp-Hinweis im Modul-Docstring ggf. anpassen.

- [ ] **Step 4: Grün + Regression**

Run: `python -m pytest tests/adapters/api/test_run_lock.py tests/adapters/api/test_run_manager.py -q`
Expected: PASS (Lock-Tests grün; bestehende RunManager-Tests bleiben grün — `start_run` liefert weiter einen `run_id`, wenn nicht gesperrt).

- [ ] **Step 5: Commit**

```bash
git add adapters/api/run_manager.py tests/adapters/api/test_run_lock.py
git commit -m "feat(api): Lauf-Lock im RunManager (409 bei aktivem Lauf, finally-Freigabe)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Frontend — Token im API-/WS-Client

**Files:**
- Modify: `frontend/src/api/client.ts`, `frontend/src/api/cockpitSocket.ts`
- Test: `frontend/src/api/client.test.ts`, `frontend/src/api/cockpitSocket.test.ts` (ergänzen)

**Interfaces:**
- Produces: `class UnauthorizedError extends Error`, `class RunInProgressError extends Error`; `getCockpit(base, fetchFn?, token?)` (401 → `UnauthorizedError`); `startRun(base, fetchFn?, token?)` (401 → `UnauthorizedError`, 409 → `RunInProgressError`); `openCockpitSocket(base, handlers, factory?, token?)` hängt `?token=` an.

- [ ] **Step 1: Failing-Tests (ergänzen)**

In `frontend/src/api/client.test.ts` ergänzen (Importe `UnauthorizedError`, `RunInProgressError` aus `./client`):
```ts
  it("haengt den Authorization-Header an, wenn ein Token gegeben ist", async () => {
    let seenHeaders: Record<string, string> | undefined;
    const fetchFn = (async (_url: string, init?: { headers?: Record<string, string> }) => {
      seenHeaders = init?.headers;
      return { status: 204, ok: false, json: async () => undefined };
    }) as unknown as typeof fetch;
    await getCockpit("http://x", fetchFn, "geheim");
    expect(seenHeaders).toMatchObject({ Authorization: "Bearer geheim" });
  });

  it("wirft UnauthorizedError bei 401", async () => {
    const fetchFn = (async () => ({ status: 401, ok: false, json: async () => undefined })) as unknown as typeof fetch;
    await expect(getCockpit("http://x", fetchFn, "x")).rejects.toBeInstanceOf(UnauthorizedError);
  });

  it("startRun wirft RunInProgressError bei 409", async () => {
    const fetchFn = (async () => ({ status: 409, ok: false, json: async () => undefined })) as unknown as typeof fetch;
    await expect(startRun("http://x", fetchFn, "x")).rejects.toBeInstanceOf(RunInProgressError);
  });
```
In `frontend/src/api/cockpitSocket.test.ts` ergänzen:
```ts
  it("haengt den Token als Query-Parameter an die ws-URL", () => {
    let seen = "";
    const ws = { onopen: null, onmessage: null, onerror: null, onclose: null, close: () => {} } as unknown as import("./cockpitSocket").WebSocketLike;
    openCockpitSocket("http://127.0.0.1:8000", {}, (url) => { seen = url; return ws; }, "geheim");
    expect(seen).toBe("ws://127.0.0.1:8000/ws/cockpit?token=geheim");
  });
```

- [ ] **Step 2: Rot**

Run: `cd frontend && npx vitest run src/api/client.test.ts src/api/cockpitSocket.test.ts`
Expected: FAIL (Klassen/Token-Param fehlen).

- [ ] **Step 3: Implementieren — client.ts**

`frontend/src/api/client.ts` (gesamten Inhalt ersetzen):
```ts
import type { CockpitOverview } from "../lib/contract";

// Fehlerklassen, damit der Hook 401/409 von generischen Fehlern trennen kann.
export class UnauthorizedError extends Error {}
export class RunInProgressError extends Error {}

function authHeaders(token?: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// GET liest das letzte Ergebnis; 204 == noch kein Lauf -> null; 401 -> UnauthorizedError.
export async function getCockpit(
  base: string,
  fetchFn: typeof fetch = fetch,
  token?: string | null,
): Promise<CockpitOverview | null> {
  const res = await fetchFn(`${base}/api/cockpit`, { headers: authHeaders(token) });
  if (res.status === 401) throw new UnauthorizedError();
  if (res.status === 204) return null;
  if (!res.ok) throw new Error(`GET /api/cockpit fehlgeschlagen: ${res.status}`);
  return (await res.json()) as CockpitOverview;
}

// POST startet einen Lauf; 202 { run_id }; 401 -> UnauthorizedError; 409 -> RunInProgressError.
export async function startRun(
  base: string,
  fetchFn: typeof fetch = fetch,
  token?: string | null,
): Promise<string> {
  const res = await fetchFn(`${base}/api/cockpit/run`, { method: "POST", headers: authHeaders(token) });
  if (res.status === 401) throw new UnauthorizedError();
  if (res.status === 409) throw new RunInProgressError();
  if (!res.ok) throw new Error(`POST /api/cockpit/run fehlgeschlagen: ${res.status}`);
  const data = (await res.json()) as { run_id: string };
  return data.run_id;
}
```

- [ ] **Step 4: Implementieren — cockpitSocket.ts**

In `frontend/src/api/cockpitSocket.ts` `wsUrl` und `openCockpitSocket` anpassen:
```ts
function wsUrl(base: string, token?: string | null): string {
  const url = base.replace(/^http/, "ws") + "/ws/cockpit";
  return token ? `${url}?token=${encodeURIComponent(token)}` : url;
}

export function openCockpitSocket(
  base: string,
  handlers: SocketHandlers,
  factory: WebSocketFactory = (url) => new WebSocket(url) as unknown as WebSocketLike,
  token?: string | null,
): WebSocketLike {
  const ws = factory(wsUrl(base, token));
  // ... Rest unveraendert (onopen/onmessage/onerror/onclose)
```

- [ ] **Step 5: Grün**

Run: `cd frontend && npx vitest run src/api/client.test.ts src/api/cockpitSocket.test.ts`
Expected: PASS (alte + neue Tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/cockpitSocket.ts frontend/src/api/client.test.ts frontend/src/api/cockpitSocket.test.ts
git commit -m "feat(frontend): Token an API-/WS-Client (Header bzw. ?token=, 401/409-Fehlerklassen)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Frontend — `useAuth` + `LoginGate`

**Files:**
- Create: `frontend/src/auth/useAuth.ts`, `frontend/src/auth/LoginGate.tsx`
- Test: `frontend/src/auth/useAuth.test.tsx`, `frontend/src/auth/LoginGate.test.tsx`

**Interfaces:**
- Produces: `useAuth() -> { token: string | null, login(t: string): void, logout(): void }` (localStorage-Schlüssel `aaia_token`); `LoginGate({ error?: boolean, onSubmit: (token: string) => void })`.

- [ ] **Step 1: Failing-Tests**

`frontend/src/auth/useAuth.test.tsx`:
```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAuth } from "./useAuth";

describe("useAuth", () => {
  beforeEach(() => localStorage.clear());

  it("startet ohne Token", () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.token).toBeNull();
  });

  it("login speichert das Token (auch in localStorage), logout entfernt es", () => {
    const { result } = renderHook(() => useAuth());
    act(() => result.current.login("geheim"));
    expect(result.current.token).toBe("geheim");
    expect(localStorage.getItem("aaia_token")).toBe("geheim");
    act(() => result.current.logout());
    expect(result.current.token).toBeNull();
    expect(localStorage.getItem("aaia_token")).toBeNull();
  });
});
```

`frontend/src/auth/LoginGate.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LoginGate } from "./LoginGate";

describe("LoginGate", () => {
  it("ruft onSubmit mit dem eingegebenen Passwort", () => {
    const onSubmit = vi.fn();
    render(<LoginGate onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText("Passwort"), { target: { value: "geheim" } });
    fireEvent.click(screen.getByRole("button", { name: /Anmelden/i }));
    expect(onSubmit).toHaveBeenCalledWith("geheim");
  });

  it("zeigt bei error die Meldung 'Falsches Passwort'", () => {
    render(<LoginGate error onSubmit={() => {}} />);
    expect(screen.getByText(/Falsches Passwort/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Rot**

Run: `cd frontend && npx vitest run src/auth/useAuth.test.tsx src/auth/LoginGate.test.tsx`
Expected: FAIL (Module fehlen).

- [ ] **Step 3: Implementieren**

`frontend/src/auth/useAuth.ts`:
```ts
import { useCallback, useState } from "react";

const KEY = "aaia_token";

// Token-Status fuer den Zugang; persistiert im localStorage (man bleibt angemeldet).
export function useAuth() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(KEY));

  const login = useCallback((t: string) => {
    localStorage.setItem(KEY, t);
    setToken(t);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(KEY);
    setToken(null);
  }, []);

  return { token, login, logout };
}
```

`frontend/src/auth/LoginGate.tsx`:
```tsx
import { useState } from "react";

// Einfacher Passwort-Screen: der Dozent gibt das geteilte Passwort ein.
export function LoginGate({ error, onSubmit }: { error?: boolean; onSubmit: (token: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <main className="mx-auto max-w-sm space-y-3 p-6">
      <h1 className="text-xl font-bold">AAIA — Cockpit</h1>
      <p className="text-slate-500">Bitte Passwort eingeben.</p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value) onSubmit(value);
        }}
        className="space-y-2"
      >
        <input
          type="password"
          aria-label="Passwort"
          placeholder="Passwort"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-full rounded border border-slate-300 px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">Falsches Passwort</p>}
        <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white">
          Anmelden
        </button>
      </form>
    </main>
  );
}
```

- [ ] **Step 4: Grün**

Run: `cd frontend && npx vitest run src/auth/useAuth.test.tsx src/auth/LoginGate.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/auth
git commit -m "feat(frontend): useAuth (localStorage) + LoginGate-Passwortscreen

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Frontend — `useCockpit`-Token + Login-Verdrahtung

**Files:**
- Modify: `frontend/src/hooks/useCockpit.ts`, `frontend/src/pages/CockpitPage.tsx`, `frontend/src/App.tsx`
- Test: `frontend/src/hooks/useCockpit.test.tsx` (ergänzen)

**Interfaces:**
- Consumes: `getCockpit`/`startRun`/`UnauthorizedError`/`RunInProgressError` (Task 4), `openCockpitSocket` mit Token (Task 4), `useAuth`/`LoginGate` (Task 5).
- Produces: `UseCockpitDeps` um `token?: string | null` und `onUnauthorized?: () => void` erweitert; `CockpitPage({ deps?, onLogout? })`; `App` zeigt `LoginGate`, wenn kein Token.

- [ ] **Step 1: Failing-Test (ergänzen)**

In `frontend/src/hooks/useCockpit.test.tsx` ergänzen:
```tsx
  it("ruft onUnauthorized bei 401 statt einen generischen Fehler zu setzen", async () => {
    const fetchFn = (async () => ({ status: 401, ok: false, json: async () => undefined })) as unknown as typeof fetch;
    const onUnauthorized = vi.fn();
    const { result } = renderHook(() =>
      useCockpit({ base: "http://x", fetchFn, wsFactory: makeFakeWs, onUnauthorized }),
    );
    await waitFor(() => expect(onUnauthorized).toHaveBeenCalledOnce());
    expect(result.current.phase).not.toBe("error");
  });
```

- [ ] **Step 2: Rot**

Run: `cd frontend && npx vitest run src/hooks/useCockpit.test.tsx`
Expected: FAIL (`onUnauthorized` unbekannt; 401 landet im generischen Fehlerpfad → phase "error").

- [ ] **Step 3: Implementieren — useCockpit.ts**

In `frontend/src/hooks/useCockpit.ts`:
- Importe ergänzen: `import { getCockpit, startRun, UnauthorizedError, RunInProgressError } from "../api/client";`
- `UseCockpitDeps` erweitern:
```ts
export interface UseCockpitDeps {
  base?: string;
  fetchFn?: typeof fetch;
  wsFactory?: WebSocketFactory;
  token?: string | null;
  onUnauthorized?: () => void;
}
```
- im Hook `const token = deps.token; const onUnauthorized = deps.onUnauthorized;`
- Mount-Effekt-`catch` ersetzen:
```ts
    getCockpit(base, fetchFn, token)
      .then((data) => { if (!cancelled) { setOverview(data); setPhase("ready"); } })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof UnauthorizedError) { onUnauthorized?.(); return; }
        setError("Backend nicht erreichbar"); setPhase("error");
      });
```
  (Deps-Array des Mount-Effekts: `[base, fetchFn, token]`.)
- `openCockpitSocket(...)`-Aufruf um den Token erweitern (als 4. Argument) und die `onOpen`/Fehlerpfade anpassen:
```ts
    wsRef.current = openCockpitSocket(
      base,
      {
        onOpen: () => {
          startRun(base, fetchFn, token).catch((e) => {
            if (e instanceof RunInProgressError) return;       // laeuft schon -> WS liefert das Ergebnis
            if (e instanceof UnauthorizedError) { onUnauthorized?.(); return; }
            setError("Start fehlgeschlagen"); setPhase("error");
          });
        },
        onEvent: (e) => { if (e.type !== "CockpitResultReady") setEvents((prev) => [...prev, e]); },
        onResult: (ov) => { setOverview(ov); setPhase("ready"); wsRef.current?.close(); },
        onError: () => { setError("WebSocket-Fehler"); setPhase("error"); },
      },
      wsFactory,
      token,
    );
```
  (`startAnalysis`-`useCallback`-Deps: `[base, fetchFn, wsFactory, token]`.)

- [ ] **Step 4: Implementieren — CockpitPage.tsx (Logout-Link)**

`frontend/src/pages/CockpitPage.tsx`: Signatur und Header anpassen:
```tsx
export function CockpitPage({ deps, onLogout }: { deps?: UseCockpitDeps; onLogout?: () => void }) {
  const { overview, phase, error, startAnalysis } = useCockpit(deps);

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-bold">AAIA — Cockpit</h1>
        <div className="flex items-center gap-4">
          {overview && <DataHealthIndicator active={overview.sources_active} total={overview.sources_total} />}
          <RunControl phase={phase} onStart={startAnalysis} />
          {onLogout && (
            <button type="button" onClick={onLogout} className="text-sm text-slate-500 underline">
              Abmelden
            </button>
          )}
        </div>
      </header>
      {/* Rest unveraendert */}
```

- [ ] **Step 5: Implementieren — App.tsx (Login-Gate)**

`frontend/src/App.tsx` (gesamten Inhalt ersetzen):
```tsx
import { useState } from "react";
import { CockpitPage } from "./pages/CockpitPage";
import { useAuth } from "./auth/useAuth";
import { LoginGate } from "./auth/LoginGate";

export default function App() {
  const { token, login, logout } = useAuth();
  const [authError, setAuthError] = useState(false);

  if (!token) {
    return <LoginGate error={authError} onSubmit={(t) => { setAuthError(false); login(t); }} />;
  }
  return (
    <CockpitPage
      deps={{ token, onUnauthorized: () => { setAuthError(true); logout(); } }}
      onLogout={logout}
    />
  );
}
```

- [ ] **Step 6: Grün + Build + ganze Suite**

Run: `cd frontend && npx vitest run src/hooks/useCockpit.test.tsx`
Expected: PASS.
Run: `cd frontend && npm run build`
Expected: Build erfolgreich (tsc sauber).
Run: `cd frontend && npm test`
Expected: gesamte Frontend-Suite grün.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/hooks/useCockpit.ts frontend/src/pages/CockpitPage.tsx frontend/src/App.tsx frontend/src/hooks/useCockpit.test.tsx
git commit -m "feat(frontend): Login-Gate verdrahtet (Token in useCockpit, 401 -> Passwortscreen, Abmelden)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Deploy-Config + Doku + Logbuch

**Files:**
- Modify: `render.yaml`, `docs/deploy-render.md`, `docs/open_todos.md`
- Test: `tests/adapters/api/test_app_factory_cors.py` (unverändert lauffähig — Sanity)

**Interfaces:** keine (Config/Doku).

- [ ] **Step 1: `render.yaml` — `AAIA_ACCESS_TOKEN`**

In `render.yaml` beim Backend-Dienst `aaia-api` unter `envVars` ergänzen (nach `FMP_API_KEY`):
```yaml
      - key: AAIA_ACCESS_TOKEN
        sync: false                # Zugangs-Passwort (Pflicht fuer oeffentliche Instanz; leer = ungeschuetzt)
```

- [ ] **Step 2: `render.yaml` gültig?**

Run: `python -c "import yaml; d=yaml.safe_load(open('render.yaml')); api=[s for s in d['services'] if s['name']=='aaia-api'][0]; print([e['key'] for e in api['envVars']])"`
Expected: Liste enthält `AAIA_ACCESS_TOKEN`.

- [ ] **Step 3: Deploy-Doku ergänzen**

In `docs/deploy-render.md`:
- Env-Tabelle: Zeile ergänzen
  `| \`AAIA_ACCESS_TOKEN\` | Backend | **ja (öffentlich)** | Zugangs-Passwort; leer = API ungeschützt (nur lokal) |`
- Neuer Abschnitt am Ende:
```markdown
## Zugang für den Dozenten
1. Backend (`aaia-api`) → Environment → `AAIA_ACCESS_TOKEN` = ein selbst gewähltes Passwort → Save.
2. Dem Dozenten **URL + Passwort** geben.
3. Er öffnet `https://aaia-frontend.onrender.com`, gibt das Passwort im Login-Screen ein — fertig. (Das Passwort bleibt lokal im Browser gespeichert; „Abmelden" setzt es zurück.)

> Ist `AAIA_ACCESS_TOKEN` leer, ist die API **ungeschützt** — nur für lokale Entwicklung.
```

- [ ] **Step 4: Logbuch ergänzen**

In `docs/open_todos.md`, im Abschnitt „Frontend / API-Brücke", einen Unterabschnitt „Zugriffsschutz (Branch `feat/access-protection`)" ergänzen (additiv):
- **Umgesetzt:** Shared-Token (`AAIA_ACCESS_TOKEN`) schützt GET/POST/WS (Header bzw. `?token=`, constant-time; leer = Auth aus + Warn-Log); Lauf-Lock (`409`, `finally`-Freigabe); Frontend-Login-Gate (`useAuth`/`LoginGate`, localStorage, `401` → Passwortscreen, „Abmelden"); `render.yaml` + Deploy-Doku „Zugang für den Dozenten". Spec/Plan: `docs/superpowers/specs|plans/2026-06-22-access-protection*`.
- **Offene Folge-Aufgaben:** WS-Token als „erste Nachricht" statt Query-Param (Log-Hygiene); echte Accounts/Rate-Limit erst bei Bedarf; Backend-Folgeaufgabe #7 damit (für die Demo) **erledigt**.

- [ ] **Step 5: Sanity + Commit**

Run: `python -m pytest tests/adapters/api -q`
Expected: PASS (gesamtes API-Test-Paket grün).
```bash
git add render.yaml docs/deploy-render.md docs/open_todos.md
git commit -m "docs(deploy): AAIA_ACCESS_TOKEN in render.yaml + Dozenten-Zugang dokumentiert

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (gegen die Spec)

**Spec-Abdeckung:**
- §2 Backend-Token (env, Header, WS-Query, constant-time, leer=aus+Warn, `auth.py`/`require_token`) → Tasks 1+2 ✓
- §3 Lauf-Lock (`start_run -> str|None`, `_running`, `finally`, Route `409`) → Task 3 (+ `409`-Route in Task 2) ✓
- §4 Frontend-Login (useAuth/localStorage, LoginGate, 401→Login, Token an GET/POST/WS, Logout, `UnauthorizedError`/`RunInProgressError`) → Tasks 4+5+6 ✓
- §5 Deploy (`AAIA_ACCESS_TOKEN` in render.yaml, Doku „Zugang für den Dozenten") → Task 7 ✓
- §6 Tests (Backend 401/202/WS/409/Lock-Release; Frontend Login/401/Token) → Tasks 1–6 ✓
- §7 Abgrenzung/Folge-Aufgaben → Task 7 (Logbuch) ✓

**Platzhalter-Scan:** kein „TBD"/„später"; vollständiger Code je Schritt. ✓ (Der `409`-Zweig in Task 2 ist als korrekt-aber-erst-mit-Task-3-aktiv markiert.)

**Typ-Konsistenz:** `token_valid`/`require_token`; `start_run() -> str | None`; `UnauthorizedError`/`RunInProgressError`; `getCockpit(base, fetchFn?, token?)`/`startRun(base, fetchFn?, token?)`; `openCockpitSocket(base, handlers, factory?, token?)`; `UseCockpitDeps.{token,onUnauthorized}`; `CockpitPage({deps?, onLogout?})`; `useAuth() -> {token, login, logout}`; localStorage-Schlüssel `aaia_token` — über alle Tasks identisch. ✓
