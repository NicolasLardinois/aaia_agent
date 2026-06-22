# Frontend — Cockpit-Regime-Übersicht (erste Scheibe) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Cockpit-Regime-Übersicht als erste lauffähige React-Frontend-Scheibe bauen — live an die bestehende API-Brücke (PR #24) gebunden — und damit zugleich das Frontend-Fundament (Gerüst, API-/WS-Client, Basis-Komponenten, Render-Deploy) legen.

**Architecture:** Neues `frontend/`-Paket im Monorepo (React + TypeScript, Vite-Build → statische Dateien). Reine Anzeige-Logik als pure, zuerst getestete Funktionen; Daten über einen schlanken typisierten API-Client + WebSocket-Client (beide per Dependency-Injection gegen Fakes testbar); ein `useCockpit`-Hook orchestriert Laden/Lauf/Live-Events; die Seite setzt sich aus Basis- und Bildschirm-Komponenten zusammen. Deploy als separate Render Static Site neben dem bestehenden Web Service.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS v3, Vitest + React Testing Library (jsdom). Node ≥ 18.

## Global Constraints

- **Sprache:** UI-Texte und Code-Kommentare auf **Deutsch**; Commit-Präfixe `feat(...)`, `test(...)`, `chore(...)`, `docs(...)`.
- **TDD verpflichtend (AGENTS.md §4):** erst der fehlschlagende Test, dann minimaler Code bis grün. Pure Anzeige-Logik wird **zuerst** getestet.
- **Monorepo:** der gesamte Frontend-Code liegt unter `frontend/`. Python-Backend unberührt, außer der CORS-Konfig in Task 7.
- **UNAVAILABLE ≠ 0 ≠ NEUTRAL (Spec §4/§5.4):** Eine ausgefallene Domäne (`status === "unavailable"` **oder** `signal === null`) wird als „nicht verfügbar" dargestellt, **nie** als grünes/neutrales Signal, und zählt nicht in „aktiv".
- **Backend-Vertrag (Spec §6, unverändert konsumiert):** `GET /api/cockpit` → `200` `{ regime, regime_confidence, macro_status, domains:[{key,signal,status}], sources_active, sources_total }` **oder** `204`; `POST /api/cockpit/run` → `202 { run_id }`; `WS /ws/cockpit` → Nachrichten `{ type, source, payload, timestamp, run_id }`, terminal `type==="CockpitResultReady"` mit `payload` = Übersicht-Vertrag. `signal` ist `null` bei `status==="unavailable"`.
- **Reihenfolge beim Start:** **erst WebSocket öffnen (onopen), dann `POST …/run`** — sonst gehen frühe Events verloren.
- **Kein Auto-Start**, keine Charting-Bibliothek, keine Server-State-Bibliothek (YAGNI für einen Bildschirm).
- **Backend-Adresse** nur über `VITE_API_BASE_URL` (kein hartcodierter Link); Fallback `http://127.0.0.1:8000` für lokale Entwicklung.
- Test gezielt: `cd frontend && npx vitest run <pfad>`; gesamt: `cd frontend && npm test`.

---

## File Structure

| Datei | Verantwortung |
|---|---|
| `frontend/package.json`, `vite.config.ts`, `tsconfig*.json`, `tailwind.config.js`, `postcss.config.js`, `index.html` | Gerüst/Toolchain |
| `frontend/src/test/setup.ts` | Vitest-Setup (`@testing-library/jest-dom`) |
| `frontend/src/lib/format.ts` (+ `.test.ts`) | `formatConfidence` |
| `frontend/src/lib/contract.ts` | TS-Typen des Backend-Vertrags |
| `frontend/src/lib/display.ts` (+ `.test.ts`) | `signalToVisual`, `isUnavailable`, `sourcesLabel` |
| `frontend/src/components/SignalBadge.tsx` (+ `.test.tsx`) | Signal-Wort + Farbe / UNAVAILABLE |
| `frontend/src/components/ConfidenceBar.tsx` (+ `.test.tsx`) | Konfidenzbalken mit %-Label |
| `frontend/src/components/UnavailableField.tsx` (+ `.test.tsx`) | gestreift-graues „nicht verfügbar" |
| `frontend/src/api/client.ts` (+ `.test.ts`) | `getCockpit`, `startRun` |
| `frontend/src/api/cockpitSocket.ts` (+ `.test.ts`) | `openCockpitSocket` |
| `frontend/src/hooks/useCockpit.ts` (+ `.test.tsx`) | Zustands-Orchestrierung |
| `frontend/src/components/RegimeBanner.tsx`, `DomainTile.tsx`, `DataHealthIndicator.tsx`, `RunControl.tsx` | Bildschirm-Bausteine |
| `frontend/src/pages/CockpitPage.tsx` (+ `.test.tsx`) | Zusammensetzung + Zustände |
| `frontend/src/App.tsx`, `src/main.tsx`, `src/index.css`, `src/vite-env.d.ts` | App-Einbindung, Styles, Env-Typ |
| `frontend/.env.example`, `frontend/README.md` | Konfig/Doku |
| `adapters/api/app_factory.py` (modify) | CORS-Origins aus Env |
| `docs/open_todos.md` (modify) | Logbuch |

---

## Task 1: Gerüst + Toolchain, bewiesen durch den ersten Pure-Function-Test

**Files:**
- Create: `frontend/` (Vite-React-TS-Gerüst), `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/src/index.css`, `frontend/vite.config.ts` (überschrieben), `frontend/src/test/setup.ts`, `frontend/src/lib/format.ts`
- Test: `frontend/src/lib/format.test.ts`

**Interfaces:**
- Produces: `formatConfidence(value: number): string` — rundet auf ganze Prozent, clamped auf [0,1], Format `"71 %"` (mit schmalem Leerzeichen als normales Space).

- [ ] **Step 1: Node prüfen + Gerüst erzeugen**

Aus dem Worktree-Wurzelverzeichnis ausführen:
```bash
node --version    # erwartet v18 oder höher; sonst BLOCKED melden
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss@^3.4 postcss autoprefixer vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
npx tailwindcss init -p
```

- [ ] **Step 2: Konfig-Dateien setzen**

`frontend/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
```

`frontend/src/index.css` (gesamten Inhalt ersetzen):
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

`frontend/vite.config.ts` (gesamten Inhalt ersetzen):
```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
```

`frontend/src/test/setup.ts`:
```ts
import "@testing-library/jest-dom";
```

In `frontend/package.json` unter `"scripts"` ergänzen:
```json
    "test": "vitest run",
    "test:watch": "vitest"
```

- [ ] **Step 3: Failing-Test schreiben**

`frontend/src/lib/format.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { formatConfidence } from "./format";

describe("formatConfidence", () => {
  it("rundet auf ganze Prozent mit Leerzeichen", () => {
    expect(formatConfidence(0.71)).toBe("71 %");
  });
  it("behandelt 0 und 1", () => {
    expect(formatConfidence(0)).toBe("0 %");
    expect(formatConfidence(1)).toBe("100 %");
  });
  it("clamped Werte außerhalb [0,1]", () => {
    expect(formatConfidence(-0.2)).toBe("0 %");
    expect(formatConfidence(1.5)).toBe("100 %");
  });
});
```

- [ ] **Step 4: Test laufen lassen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/format.test.ts`
Expected: FAIL (`Failed to resolve import "./format"` bzw. `formatConfidence is not a function`).

- [ ] **Step 5: Implementieren**

`frontend/src/lib/format.ts`:
```ts
// Konfidenz (0..1) als ganze Prozent fuer die Anzeige; defensiv geclamped.
export function formatConfidence(value: number): string {
  const clamped = Math.max(0, Math.min(1, value));
  return `${Math.round(clamped * 100)} %`;
}
```

- [ ] **Step 6: Test laufen lassen — muss grün sein, Build prüfen**

Run: `cd frontend && npx vitest run src/lib/format.test.ts`
Expected: PASS (3 Tests).
Run: `cd frontend && npm run build`
Expected: Build erfolgreich, erzeugt `frontend/dist/`.

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "feat(frontend): Vite/React/TS/Tailwind/Vitest-Geruest + formatConfidence

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Vertrag-Typen + restliche Pure-Anzeige-Logik

**Files:**
- Create: `frontend/src/lib/contract.ts`, `frontend/src/lib/display.ts`
- Test: `frontend/src/lib/display.test.ts`

**Interfaces:**
- Produces (`contract.ts`): `Signal = "bullish"|"bearish"|"neutral"`; `Status = "available"|"unavailable"`; `DomainKey = "commodities"|"sentiment"|"yield_curve"|"sectors"`; `interface Domain { key: DomainKey; signal: Signal | null; status: Status }`; `interface CockpitOverview { regime: string; regime_confidence: number; macro_status: Status; domains: Domain[]; sources_active: number; sources_total: number }`.
- Produces (`display.ts`): `interface Visual { label: string; colorClass: string }`; `signalToVisual(signal: Signal | null): Visual`; `isUnavailable(domain: Domain): boolean`; `sourcesLabel(active: number, total: number): string`.

- [ ] **Step 1: Typen schreiben (kein Test nötig — reine Typen)**

`frontend/src/lib/contract.ts`:
```ts
// TS-Spiegel des Backend-Vertrags (Spec §6). signal ist null bei UNAVAILABLE.
export type Signal = "bullish" | "bearish" | "neutral";
export type Status = "available" | "unavailable";
export type DomainKey = "commodities" | "sentiment" | "yield_curve" | "sectors";

export interface Domain {
  key: DomainKey;
  signal: Signal | null;
  status: Status;
}

export interface CockpitOverview {
  regime: string;
  regime_confidence: number;
  macro_status: Status;
  domains: Domain[];
  sources_active: number;
  sources_total: number;
}
```

- [ ] **Step 2: Failing-Test schreiben**

`frontend/src/lib/display.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { signalToVisual, isUnavailable, sourcesLabel } from "./display";
import type { Domain } from "./contract";

describe("signalToVisual", () => {
  it("mappt Signale auf Wort + Farbe", () => {
    expect(signalToVisual("bullish")).toEqual({ label: "BULLISH", colorClass: "text-green-600" });
    expect(signalToVisual("bearish")).toEqual({ label: "BEARISH", colorClass: "text-red-600" });
    expect(signalToVisual("neutral")).toEqual({ label: "NEUTRAL", colorClass: "text-slate-500" });
  });
  it("zeigt null als 'nicht verfuegbar' (kein neutrales Signal)", () => {
    expect(signalToVisual(null)).toEqual({ label: "nicht verfügbar", colorClass: "text-slate-400" });
  });
});

describe("isUnavailable", () => {
  const base: Domain = { key: "sentiment", signal: "bearish", status: "available" };
  it("false bei verfuegbarer Domaene", () => {
    expect(isUnavailable(base)).toBe(false);
  });
  it("true bei status unavailable", () => {
    expect(isUnavailable({ ...base, status: "unavailable", signal: null })).toBe(true);
  });
  it("true wenn signal null ist (auch ohne status-Flag)", () => {
    expect(isUnavailable({ ...base, signal: null })).toBe(true);
  });
});

describe("sourcesLabel", () => {
  it("formatiert x/y Quellen aktiv", () => {
    expect(sourcesLabel(4, 5)).toBe("4/5 Quellen aktiv");
    expect(sourcesLabel(0, 5)).toBe("0/5 Quellen aktiv");
  });
});
```

- [ ] **Step 3: Test laufen lassen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/display.test.ts`
Expected: FAIL (`Failed to resolve import "./display"`).

- [ ] **Step 4: Implementieren**

`frontend/src/lib/display.ts`:
```ts
import type { Signal, Domain } from "./contract";

export interface Visual {
  label: string;
  colorClass: string;
}

// Signal -> Wort + Tailwind-Farbklasse. null (UNAVAILABLE) ist ein eigener
// Zustand, NIE als neutrales Signal dargestellt (Spec §5.4).
export function signalToVisual(signal: Signal | null): Visual {
  switch (signal) {
    case "bullish":
      return { label: "BULLISH", colorClass: "text-green-600" };
    case "bearish":
      return { label: "BEARISH", colorClass: "text-red-600" };
    case "neutral":
      return { label: "NEUTRAL", colorClass: "text-slate-500" };
    default:
      return { label: "nicht verfügbar", colorClass: "text-slate-400" };
  }
}

// Domaene gilt als ausgefallen, wenn der Status es sagt ODER kein Signal da ist.
export function isUnavailable(domain: Domain): boolean {
  return domain.status === "unavailable" || domain.signal === null;
}

export function sourcesLabel(active: number, total: number): string {
  return `${active}/${total} Quellen aktiv`;
}
```

- [ ] **Step 5: Test laufen lassen — muss grün sein**

Run: `cd frontend && npx vitest run src/lib/display.test.ts`
Expected: PASS (alle Tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib
git commit -m "feat(frontend): Vertrag-Typen + pure Anzeige-Logik (signalToVisual/isUnavailable/sourcesLabel)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Basis-Komponenten (SignalBadge, ConfidenceBar, UnavailableField)

**Files:**
- Create: `frontend/src/components/SignalBadge.tsx`, `ConfidenceBar.tsx`, `UnavailableField.tsx`
- Test: `frontend/src/components/SignalBadge.test.tsx`, `ConfidenceBar.test.tsx`, `UnavailableField.test.tsx`

**Interfaces:**
- Consumes: `signalToVisual` (Task 2), `formatConfidence` (Task 1).
- Produces: `SignalBadge({ signal }: { signal: Signal | null })`; `ConfidenceBar({ value }: { value: number })`; `UnavailableField({ reason }: { reason?: string })`.

- [ ] **Step 1: Failing-Tests schreiben**

`frontend/src/components/SignalBadge.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SignalBadge } from "./SignalBadge";

describe("SignalBadge", () => {
  it("zeigt das Signal-Wort", () => {
    render(<SignalBadge signal="bullish" />);
    expect(screen.getByText("BULLISH")).toBeInTheDocument();
  });
  it("zeigt bei null 'nicht verfuegbar'", () => {
    render(<SignalBadge signal={null} />);
    expect(screen.getByText("nicht verfügbar")).toBeInTheDocument();
  });
});
```

`frontend/src/components/ConfidenceBar.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBar } from "./ConfidenceBar";

describe("ConfidenceBar", () => {
  it("zeigt das Prozent-Label", () => {
    render(<ConfidenceBar value={0.71} />);
    expect(screen.getByText("71 %")).toBeInTheDocument();
  });
  it("setzt die Balkenbreite per aria-Wert", () => {
    render(<ConfidenceBar value={0.71} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "71");
  });
});
```

`frontend/src/components/UnavailableField.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { UnavailableField } from "./UnavailableField";

describe("UnavailableField", () => {
  it("zeigt 'nicht verfuegbar' und den Grund als Titel", () => {
    render(<UnavailableField reason="Stub-Quelle" />);
    const el = screen.getByText("nicht verfügbar");
    expect(el).toBeInTheDocument();
    expect(screen.getByTitle("Stub-Quelle")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Tests laufen lassen — müssen fehlschlagen**

Run: `cd frontend && npx vitest run src/components/SignalBadge.test.tsx src/components/ConfidenceBar.test.tsx src/components/UnavailableField.test.tsx`
Expected: FAIL (Module nicht gefunden).

- [ ] **Step 3: Implementieren**

`frontend/src/components/SignalBadge.tsx`:
```tsx
import type { Signal } from "../lib/contract";
import { signalToVisual } from "../lib/display";

export function SignalBadge({ signal }: { signal: Signal | null }) {
  const { label, colorClass } = signalToVisual(signal);
  return <span className={`font-semibold ${colorClass}`}>{label}</span>;
}
```

`frontend/src/components/ConfidenceBar.tsx`:
```tsx
import { formatConfidence } from "../lib/format";

export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="flex items-center gap-2">
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 w-32 rounded bg-slate-200"
      >
        <div className="h-2 rounded bg-slate-600" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm tabular-nums">{formatConfidence(value)}</span>
    </div>
  );
}
```

`frontend/src/components/UnavailableField.tsx`:
```tsx
// Gestreift-graues Feld fuer UNAVAILABLE — eigener Zustand, nie neutral/0 (Spec §5.4).
export function UnavailableField({ reason }: { reason?: string }) {
  return (
    <span
      title={reason ?? "Datenquelle nicht verfügbar"}
      className="inline-block rounded px-2 py-0.5 text-sm text-slate-500
                 bg-[repeating-linear-gradient(45deg,#e2e8f0,#e2e8f0_4px,#f1f5f9_4px,#f1f5f9_8px)]"
    >
      nicht verfügbar
    </span>
  );
}
```

- [ ] **Step 4: Tests laufen lassen — müssen grün sein**

Run: `cd frontend && npx vitest run src/components/SignalBadge.test.tsx src/components/ConfidenceBar.test.tsx src/components/UnavailableField.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components
git commit -m "feat(frontend): Basis-Komponenten SignalBadge/ConfidenceBar/UnavailableField

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: API-Client + WebSocket-Client (gegen Fakes testbar)

**Files:**
- Create: `frontend/src/api/client.ts`, `frontend/src/api/cockpitSocket.ts`, `frontend/src/vite-env.d.ts` (Env-Typ ergänzen)
- Test: `frontend/src/api/client.test.ts`, `frontend/src/api/cockpitSocket.test.ts`

**Interfaces:**
- Consumes: `CockpitOverview` (Task 2).
- Produces (`client.ts`): `getCockpit(base: string, fetchFn?: typeof fetch): Promise<CockpitOverview | null>` (`204` → `null`); `startRun(base: string, fetchFn?: typeof fetch): Promise<string>` (gibt `run_id`).
- Produces (`cockpitSocket.ts`): `interface CockpitEvent { type: string; source: string; payload: Record<string, unknown>; timestamp: string; run_id: string }`; `interface WebSocketLike { onopen: (() => void) | null; onmessage: ((ev: { data: string }) => void) | null; onerror: (() => void) | null; onclose: (() => void) | null; close(): void }`; `type WebSocketFactory = (url: string) => WebSocketLike`; `interface SocketHandlers { onOpen?: () => void; onEvent?: (e: CockpitEvent) => void; onResult?: (o: CockpitOverview, e: CockpitEvent) => void; onError?: () => void; onClose?: () => void }`; `openCockpitSocket(base: string, handlers: SocketHandlers, factory?: WebSocketFactory): WebSocketLike`.

- [ ] **Step 1: Failing-Tests schreiben**

`frontend/src/api/client.test.ts`:
```ts
import { describe, it, expect, vi } from "vitest";
import { getCockpit, startRun } from "./client";

const overview = {
  regime: "Aufschwung", regime_confidence: 0.71, macro_status: "available",
  domains: [], sources_active: 5, sources_total: 5,
};

function fakeFetch(status: number, body?: unknown): typeof fetch {
  return vi.fn(async () => ({
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  })) as unknown as typeof fetch;
}

describe("getCockpit", () => {
  it("gibt die Uebersicht bei 200", async () => {
    const res = await getCockpit("http://x", fakeFetch(200, overview));
    expect(res).toEqual(overview);
  });
  it("gibt null bei 204", async () => {
    const res = await getCockpit("http://x", fakeFetch(204));
    expect(res).toBeNull();
  });
  it("wirft bei Fehlerstatus", async () => {
    await expect(getCockpit("http://x", fakeFetch(500))).rejects.toThrow();
  });
});

describe("startRun", () => {
  it("gibt die run_id bei 202", async () => {
    const id = await startRun("http://x", fakeFetch(202, { run_id: "abc" }));
    expect(id).toBe("abc");
  });
});
```

`frontend/src/api/cockpitSocket.test.ts`:
```ts
import { describe, it, expect, vi } from "vitest";
import { openCockpitSocket, type WebSocketLike } from "./cockpitSocket";

function fakeWs(): WebSocketLike {
  return { onopen: null, onmessage: null, onerror: null, onclose: null, close: vi.fn() };
}

describe("openCockpitSocket", () => {
  it("leitet die ws-URL aus der http-Basis ab", () => {
    let seen = "";
    const ws = fakeWs();
    openCockpitSocket("http://127.0.0.1:8000", {}, (url) => { seen = url; return ws; });
    expect(seen).toBe("ws://127.0.0.1:8000/ws/cockpit");
  });

  it("ruft onOpen, onEvent und (beim Terminal) onResult", () => {
    const ws = fakeWs();
    const onOpen = vi.fn();
    const onEvent = vi.fn();
    const onResult = vi.fn();
    openCockpitSocket("https://api.example.com", { onOpen, onEvent, onResult }, () => ws);

    ws.onopen!();
    ws.onmessage!({ data: JSON.stringify({ type: "MacroChiefReady", source: "m", payload: {}, timestamp: "t", run_id: "r" }) });
    const ovPayload = { regime: "X", regime_confidence: 0.5, macro_status: "available", domains: [], sources_active: 5, sources_total: 5 };
    ws.onmessage!({ data: JSON.stringify({ type: "CockpitResultReady", source: "run_manager", payload: ovPayload, timestamp: "t", run_id: "r" }) });

    expect(onOpen).toHaveBeenCalledOnce();
    expect(onEvent).toHaveBeenCalledTimes(2);
    expect(onResult).toHaveBeenCalledOnce();
    expect(onResult).toHaveBeenCalledWith(ovPayload, expect.objectContaining({ type: "CockpitResultReady" }));
  });
});
```

- [ ] **Step 2: Tests laufen lassen — müssen fehlschlagen**

Run: `cd frontend && npx vitest run src/api/client.test.ts src/api/cockpitSocket.test.ts`
Expected: FAIL (Module nicht gefunden).

- [ ] **Step 3: Implementieren**

`frontend/src/vite-env.d.ts` (gesamten Inhalt setzen):
```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

`frontend/src/api/client.ts`:
```ts
import type { CockpitOverview } from "../lib/contract";

// GET liest das letzte Ergebnis; 204 == noch kein Lauf -> null.
export async function getCockpit(
  base: string,
  fetchFn: typeof fetch = fetch,
): Promise<CockpitOverview | null> {
  const res = await fetchFn(`${base}/api/cockpit`);
  if (res.status === 204) return null;
  if (!res.ok) throw new Error(`GET /api/cockpit fehlgeschlagen: ${res.status}`);
  return (await res.json()) as CockpitOverview;
}

// POST startet einen Lauf im Hintergrund; Antwort 202 { run_id }.
export async function startRun(
  base: string,
  fetchFn: typeof fetch = fetch,
): Promise<string> {
  const res = await fetchFn(`${base}/api/cockpit/run`, { method: "POST" });
  if (!res.ok) throw new Error(`POST /api/cockpit/run fehlgeschlagen: ${res.status}`);
  const data = (await res.json()) as { run_id: string };
  return data.run_id;
}
```

`frontend/src/api/cockpitSocket.ts`:
```ts
import type { CockpitOverview } from "../lib/contract";

export interface CockpitEvent {
  type: string;
  source: string;
  payload: Record<string, unknown>;
  timestamp: string;
  run_id: string;
}

// Minimal-Interface eines WebSockets -> per Factory injizierbar (jsdom hat keinen WebSocket).
export interface WebSocketLike {
  onopen: (() => void) | null;
  onmessage: ((ev: { data: string }) => void) | null;
  onerror: (() => void) | null;
  onclose: (() => void) | null;
  close(): void;
}

export type WebSocketFactory = (url: string) => WebSocketLike;

export interface SocketHandlers {
  onOpen?: () => void;
  onEvent?: (e: CockpitEvent) => void;
  onResult?: (overview: CockpitOverview, e: CockpitEvent) => void;
  onError?: () => void;
  onClose?: () => void;
}

function wsUrl(base: string): string {
  return base.replace(/^http/, "ws") + "/ws/cockpit";
}

export function openCockpitSocket(
  base: string,
  handlers: SocketHandlers,
  factory: WebSocketFactory = (url) => new WebSocket(url) as unknown as WebSocketLike,
): WebSocketLike {
  const ws = factory(wsUrl(base));
  ws.onopen = () => handlers.onOpen?.();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data) as CockpitEvent;
    handlers.onEvent?.(msg);
    if (msg.type === "CockpitResultReady") {
      handlers.onResult?.(msg.payload as unknown as CockpitOverview, msg);
    }
  };
  ws.onerror = () => handlers.onError?.();
  ws.onclose = () => handlers.onClose?.();
  return ws;
}
```

- [ ] **Step 4: Tests laufen lassen — müssen grün sein**

Run: `cd frontend && npx vitest run src/api/client.test.ts src/api/cockpitSocket.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api frontend/src/vite-env.d.ts
git commit -m "feat(frontend): API-Client (getCockpit/startRun) + WebSocket-Client (openCockpitSocket)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: `useCockpit`-Hook (Laden, Start = WS→POST, Live-Events, Terminal, Fehler)

**Files:**
- Create: `frontend/src/hooks/useCockpit.ts`
- Test: `frontend/src/hooks/useCockpit.test.tsx`

**Interfaces:**
- Consumes: `getCockpit`, `startRun` (Task 4), `openCockpitSocket`, `CockpitEvent`, `WebSocketFactory`, `WebSocketLike` (Task 4), `CockpitOverview` (Task 2).
- Produces: `type Phase = "loading" | "ready" | "running" | "error"`; `interface UseCockpitDeps { base?: string; fetchFn?: typeof fetch; wsFactory?: WebSocketFactory }`; `interface UseCockpit { overview: CockpitOverview | null; phase: Phase; events: CockpitEvent[]; error: string | null; startAnalysis: () => void }`; `useCockpit(deps?: UseCockpitDeps): UseCockpit`. Beim Mount lädt der Hook via `getCockpit`. `startAnalysis` öffnet zuerst den WebSocket und startet `startRun` **erst in `onOpen`**.

- [ ] **Step 1: Failing-Test schreiben**

`frontend/src/hooks/useCockpit.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useCockpit } from "./useCockpit";
import type { WebSocketLike } from "../api/cockpitSocket";

const overview = {
  regime: "Aufschwung", regime_confidence: 0.71, macro_status: "available",
  domains: [], sources_active: 5, sources_total: 5,
};

function fakeFetch(map: Record<string, { status: number; body?: unknown }>): typeof fetch {
  return (async (url: string, init?: { method?: string }) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    const entry = map[key] ?? { status: 404 };
    return { status: entry.status, ok: entry.status >= 200 && entry.status < 300, json: async () => entry.body };
  }) as unknown as typeof fetch;
}

function makeFakeWs(): WebSocketLike {
  return { onopen: null, onmessage: null, onerror: null, onclose: null, close: vi.fn() };
}

describe("useCockpit", () => {
  it("laedt beim Mount die Uebersicht (200)", async () => {
    const fetchFn = fakeFetch({ "GET http://x/api/cockpit": { status: 200, body: overview } });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: makeFakeWs }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(result.current.overview).toEqual(overview);
  });

  it("zeigt Leerzustand bei 204 (overview null, phase ready)", async () => {
    const fetchFn = fakeFetch({ "GET http://x/api/cockpit": { status: 204 } });
    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: makeFakeWs }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(result.current.overview).toBeNull();
  });

  it("startet POST erst nach WS-onopen und fuellt beim Terminal die Uebersicht", async () => {
    const ws = makeFakeWs();
    const postSpy = vi.fn(async () => ({ status: 202, ok: true, json: async () => ({ run_id: "r1" }) }));
    const fetchFn = ((url: string, init?: { method?: string }) => {
      if ((init?.method ?? "GET") === "POST") return postSpy();
      return Promise.resolve({ status: 204, ok: false, json: async () => undefined });
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useCockpit({ base: "http://x", fetchFn, wsFactory: () => ws }));
    await waitFor(() => expect(result.current.phase).toBe("ready"));

    act(() => { result.current.startAnalysis(); });
    expect(result.current.phase).toBe("running");
    // POST darf noch NICHT gelaufen sein (WS noch nicht offen):
    expect(postSpy).not.toHaveBeenCalled();

    act(() => { ws.onopen!(); });
    await waitFor(() => expect(postSpy).toHaveBeenCalledOnce());

    act(() => {
      ws.onmessage!({ data: JSON.stringify({ type: "CockpitResultReady", source: "run_manager", payload: overview, timestamp: "t", run_id: "r1" }) });
    });
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    expect(result.current.overview).toEqual(overview);
  });
});
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/hooks/useCockpit.test.tsx`
Expected: FAIL (Modul nicht gefunden).

- [ ] **Step 3: Implementieren**

`frontend/src/hooks/useCockpit.ts`:
```ts
import { useCallback, useEffect, useState } from "react";
import { getCockpit, startRun } from "../api/client";
import { openCockpitSocket, type CockpitEvent, type WebSocketFactory } from "../api/cockpitSocket";
import type { CockpitOverview } from "../lib/contract";

export type Phase = "loading" | "ready" | "running" | "error";

export interface UseCockpitDeps {
  base?: string;
  fetchFn?: typeof fetch;
  wsFactory?: WebSocketFactory;
}

export interface UseCockpit {
  overview: CockpitOverview | null;
  phase: Phase;
  events: CockpitEvent[];
  error: string | null;
  startAnalysis: () => void;
}

const DEFAULT_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export function useCockpit(deps: UseCockpitDeps = {}): UseCockpit {
  const base = deps.base ?? DEFAULT_BASE;
  const fetchFn = deps.fetchFn;
  const wsFactory = deps.wsFactory;

  const [overview, setOverview] = useState<CockpitOverview | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [events, setEvents] = useState<CockpitEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCockpit(base, fetchFn)
      .then((data) => { if (!cancelled) { setOverview(data); setPhase("ready"); } })
      .catch(() => { if (!cancelled) { setError("Backend nicht erreichbar"); setPhase("error"); } });
    return () => { cancelled = true; };
  }, [base, fetchFn]);

  const startAnalysis = useCallback(() => {
    setPhase("running");
    setEvents([]);
    setError(null);
    // Reihenfolge: erst WS oeffnen, POST erst in onOpen -> keine fruehen Events verloren.
    const ws = openCockpitSocket(
      base,
      {
        onOpen: () => {
          startRun(base, fetchFn).catch(() => { setError("Start fehlgeschlagen"); setPhase("error"); });
        },
        onEvent: (e) => setEvents((prev) => [...prev, e]),
        onResult: (ov) => { setOverview(ov); setPhase("ready"); ws.close(); },
        onError: () => { setError("WebSocket-Fehler"); setPhase("error"); },
      },
      wsFactory,
    );
  }, [base, fetchFn, wsFactory]);

  return { overview, phase, events, error, startAnalysis };
}
```

- [ ] **Step 4: Test laufen lassen — muss grün sein**

Run: `cd frontend && npx vitest run src/hooks/useCockpit.test.tsx`
Expected: PASS (alle Tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks
git commit -m "feat(frontend): useCockpit-Hook (Laden, Start WS->POST, Live-Events, Terminal, Fehler)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Bildschirm-Komponenten + CockpitPage + App-Einbindung

**Files:**
- Create: `frontend/src/components/RegimeBanner.tsx`, `DomainTile.tsx`, `DataHealthIndicator.tsx`, `RunControl.tsx`, `frontend/src/pages/CockpitPage.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/main.tsx` (Tailwind-CSS-Import sicherstellen)
- Test: `frontend/src/pages/CockpitPage.test.tsx`

**Interfaces:**
- Consumes: `useCockpit` (Task 5), `SignalBadge`/`ConfidenceBar`/`UnavailableField` (Task 3), `formatConfidence` (Task 1), `signalToVisual`/`isUnavailable`/`sourcesLabel` (Task 2), `CockpitOverview`/`Domain` (Task 2).
- Produces: `RegimeBanner({ overview })`, `DomainTile({ domain })`, `DataHealthIndicator({ active, total })`, `RunControl({ phase, onStart })`, `CockpitPage({ deps? }: { deps?: UseCockpitDeps })`.

- [ ] **Step 1: Failing-Test schreiben**

`frontend/src/pages/CockpitPage.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { CockpitPage } from "./CockpitPage";
import type { WebSocketLike } from "../api/cockpitSocket";

function fakeFetch(status: number, body?: unknown): typeof fetch {
  return (async () => ({ status, ok: status >= 200 && status < 300, json: async () => body })) as unknown as typeof fetch;
}
const fakeWs = (): WebSocketLike => ({ onopen: null, onmessage: null, onerror: null, onclose: null, close: vi.fn() });

const overview = {
  regime: "Aufschwung", regime_confidence: 0.71, macro_status: "available",
  domains: [
    { key: "commodities", signal: "neutral", status: "available" },
    { key: "sentiment", signal: "bearish", status: "available" },
    { key: "yield_curve", signal: "bullish", status: "available" },
    { key: "sectors", signal: null, status: "unavailable" },
  ],
  sources_active: 4, sources_total: 5,
};

describe("CockpitPage", () => {
  it("zeigt Regime, vier Kacheln und den Health-Zaehler bei 200", async () => {
    render(<CockpitPage deps={{ base: "http://x", fetchFn: fakeFetch(200, overview), wsFactory: fakeWs }} />);
    await waitFor(() => expect(screen.getByText("Aufschwung")).toBeInTheDocument());
    expect(screen.getByText("71 %")).toBeInTheDocument();
    expect(screen.getByText("BEARISH")).toBeInTheDocument();
    expect(screen.getByText("4/5 Quellen aktiv")).toBeInTheDocument();
    // ausgefallene Sektoren-Domaene: kein Signal, sondern 'nicht verfuegbar'
    expect(screen.getByText("nicht verfügbar")).toBeInTheDocument();
  });

  it("zeigt den Leerzustand bei 204", async () => {
    render(<CockpitPage deps={{ base: "http://x", fetchFn: fakeFetch(204), wsFactory: fakeWs }} />);
    await waitFor(() => expect(screen.getByText(/Noch keine Analyse/i)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Analyse starten/i })).toBeInTheDocument();
  });

  it("zeigt einen Fehlerhinweis, wenn das Backend nicht erreichbar ist", async () => {
    render(<CockpitPage deps={{ base: "http://x", fetchFn: fakeFetch(500), wsFactory: fakeWs }} />);
    await waitFor(() => expect(screen.getByText(/nicht erreichbar/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/pages/CockpitPage.test.tsx`
Expected: FAIL (Module nicht gefunden).

- [ ] **Step 3: Bildschirm-Komponenten implementieren**

`frontend/src/components/RegimeBanner.tsx`:
```tsx
import type { CockpitOverview } from "../lib/contract";
import { ConfidenceBar } from "./ConfidenceBar";
import { UnavailableField } from "./UnavailableField";

export function RegimeBanner({ overview }: { overview: CockpitOverview }) {
  return (
    <section className="rounded-lg border border-slate-200 p-4">
      <h2 className="text-xs uppercase tracking-wide text-slate-500">Marktregime</h2>
      {overview.macro_status === "unavailable" ? (
        <UnavailableField reason="Makro-Daten nicht verfügbar" />
      ) : (
        <div className="mt-1 flex items-center gap-4">
          <span className="text-2xl font-bold">{overview.regime}</span>
          <ConfidenceBar value={overview.regime_confidence} />
        </div>
      )}
    </section>
  );
}
```

`frontend/src/components/DomainTile.tsx`:
```tsx
import type { Domain } from "../lib/contract";
import { isUnavailable } from "../lib/display";
import { SignalBadge } from "./SignalBadge";
import { UnavailableField } from "./UnavailableField";

const LABELS: Record<Domain["key"], string> = {
  commodities: "Rohstoffe",
  sentiment: "Sentiment",
  yield_curve: "Zinskurve",
  sectors: "Sektoren",
};

export function DomainTile({ domain }: { domain: Domain }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="text-xs uppercase tracking-wide text-slate-500">{LABELS[domain.key]}</div>
      <div className="mt-1">
        {isUnavailable(domain) ? <UnavailableField reason="Quelle ausgefallen" /> : <SignalBadge signal={domain.signal} />}
      </div>
    </div>
  );
}
```

`frontend/src/components/DataHealthIndicator.tsx`:
```tsx
import { sourcesLabel } from "../lib/display";

export function DataHealthIndicator({ active, total }: { active: number; total: number }) {
  const allUp = active === total;
  return (
    <span className={`text-sm ${allUp ? "text-slate-500" : "text-amber-600"}`}>
      {sourcesLabel(active, total)}
    </span>
  );
}
```

`frontend/src/components/RunControl.tsx`:
```tsx
import type { Phase } from "../hooks/useCockpit";

export function RunControl({ phase, onStart }: { phase: Phase; onStart: () => void }) {
  const running = phase === "running";
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={onStart}
        disabled={running}
        className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
      >
        Analyse starten
      </button>
      {running && <span className="text-sm text-slate-500">läuft …</span>}
    </div>
  );
}
```

- [ ] **Step 4: CockpitPage + App implementieren**

`frontend/src/pages/CockpitPage.tsx`:
```tsx
import { useCockpit, type UseCockpitDeps } from "../hooks/useCockpit";
import { RegimeBanner } from "../components/RegimeBanner";
import { DomainTile } from "../components/DomainTile";
import { DataHealthIndicator } from "../components/DataHealthIndicator";
import { RunControl } from "../components/RunControl";

export function CockpitPage({ deps }: { deps?: UseCockpitDeps }) {
  const { overview, phase, error, startAnalysis } = useCockpit(deps);

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-bold">AAIA — Cockpit</h1>
        <div className="flex items-center gap-4">
          {overview && <DataHealthIndicator active={overview.sources_active} total={overview.sources_total} />}
          <RunControl phase={phase} onStart={startAnalysis} />
        </div>
      </header>

      {phase === "loading" && <p className="text-slate-500">Lädt …</p>}
      {phase === "error" && <p className="text-red-600">{error ?? "Backend nicht erreichbar"}</p>}

      {phase !== "loading" && phase !== "error" && !overview && (
        <p className="text-slate-500">Noch keine Analyse — starte eine über „Analyse starten".</p>
      )}

      {overview && (
        <>
          <RegimeBanner overview={overview} />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {overview.domains.map((d) => (
              <DomainTile key={d.key} domain={d} />
            ))}
          </div>
        </>
      )}
    </main>
  );
}
```

`frontend/src/App.tsx` (gesamten Inhalt ersetzen):
```tsx
import { CockpitPage } from "./pages/CockpitPage";

export default function App() {
  return <CockpitPage />;
}
```

In `frontend/src/main.tsx` sicherstellen, dass `import "./index.css";` vorhanden ist (vom Gerüst i. d. R. schon gesetzt); falls nicht, ergänzen.

- [ ] **Step 5: Test laufen lassen — muss grün sein, Build prüfen**

Run: `cd frontend && npx vitest run src/pages/CockpitPage.test.tsx`
Expected: PASS (alle drei Tests).
Run: `cd frontend && npm run build`
Expected: Build erfolgreich.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): Bildschirm-Komponenten + CockpitPage + App-Einbindung

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Env-Konfig + Backend-CORS aus Env + Frontend-README

**Files:**
- Create: `frontend/.env.example`, `frontend/README.md`
- Modify: `adapters/api/app_factory.py`
- Test: `tests/adapters/api/test_app_factory_cors.py`

**Interfaces:**
- Consumes: bestehendes `create_app(run_manager)` (PR #24).
- Produces: `create_app` liest zusätzliche erlaubte Origins aus der Umgebungsvariable `AAIA_CORS_ORIGINS` (kommagetrennt) und ergänzt sie zu den localhost-Dev-Origins. Hilfsfunktion `_allowed_origins(env: str | None) -> list[str]` (pur, testbar).

- [ ] **Step 1: Failing-Test schreiben (Backend, pytest)**

`tests/adapters/api/test_app_factory_cors.py`:
```python
from adapters.api.app_factory import _allowed_origins


def test_default_origins_are_localhost_dev():
    origins = _allowed_origins(None)
    assert "http://localhost:5173" in origins
    assert "http://localhost:3000" in origins


def test_env_origins_are_appended_and_trimmed():
    origins = _allowed_origins("https://dash.onrender.com, https://x.example.com")
    assert "https://dash.onrender.com" in origins
    assert "https://x.example.com" in origins
    # Dev-Origins bleiben erhalten
    assert "http://localhost:5173" in origins


def test_blank_env_is_ignored():
    assert _allowed_origins("") == _allowed_origins(None)
    assert _allowed_origins("  ,  ") == _allowed_origins(None)
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `python -m pytest tests/adapters/api/test_app_factory_cors.py -q`
Expected: FAIL (`ImportError: cannot import name '_allowed_origins'`).

- [ ] **Step 3: Implementieren (Backend)**

In `adapters/api/app_factory.py` die Origin-Logik herausziehen und aus der Env ergänzen. Die Datei wird zu:
```python
"""Baut die FastAPI-App. CORS-Origins: localhost-Dev + optional aus Env (Render-Frontend)."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.api.routes_cockpit import build_router
from adapters.api.run_manager import RunManager

_DEV_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]


def _allowed_origins(env: str | None) -> list[str]:
    """Dev-Origins + optionale, kommagetrennte Origins aus AAIA_CORS_ORIGINS (leere ignoriert)."""
    extra = [o.strip() for o in (env or "").split(",") if o.strip()]
    return _DEV_ORIGINS + extra


def create_app(run_manager: RunManager) -> FastAPI:
    app = FastAPI(title="AAIA API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(os.environ.get("AAIA_CORS_ORIGINS")),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(build_router(run_manager))
    return app
```

- [ ] **Step 4: Tests laufen lassen — müssen grün sein (kein Regress)**

Run: `python -m pytest tests/adapters/api/test_app_factory_cors.py tests/adapters/api/test_routes_cockpit.py -q`
Expected: PASS.

- [ ] **Step 5: Frontend-Konfig + README**

`frontend/.env.example`:
```
# Basis-URL des AAIA-Backends (ohne abschliessenden Slash).
# Lokal: das laufende FastAPI-Backend. Auf Render: die Web-Service-URL.
VITE_API_BASE_URL=http://127.0.0.1:8000
```

`frontend/README.md`:
```markdown
# AAIA Frontend — Cockpit-Übersicht (erste Scheibe)

React + TypeScript + Vite. Zeigt die Cockpit-Regime-Übersicht live über die AAIA-API-Brücke.

## Entwicklung
1. Backend starten (Repo-Wurzel): `python -m app.server` (lauscht auf `127.0.0.1:8000`).
2. `cp .env.example .env` und ggf. `VITE_API_BASE_URL` anpassen.
3. `npm install && npm run dev` — Dev-Server auf `http://localhost:5173`.

## Tests
`npm test` (Vitest). Pure Anzeige-Logik + Komponenten/Hook gegen Fakes.

## Build / Deploy (Render Static Site)
- Build-Command: `npm install && npm run build`
- Publish-Verzeichnis: `dist`
- Environment-Variable: `VITE_API_BASE_URL` = URL des Backend-Web-Service (`https://…`).
- Backend: die Frontend-URL in `AAIA_CORS_ORIGINS` (kommagetrennt) des Web-Service eintragen, damit HTTP **und** WebSocket erlaubt sind.
- Backend-Web-Service: **eine Instanz** (kein Autoscaling) — In-Memory-Zustand.
```

- [ ] **Step 6: Frontend-Suite + Commit**

Run: `cd frontend && npm test`
Expected: PASS (gesamte Frontend-Suite grün).
```bash
git add frontend/.env.example frontend/README.md adapters/api/app_factory.py tests/adapters/api/test_app_factory_cors.py
git commit -m "feat(api): CORS-Origins aus AAIA_CORS_ORIGINS + Frontend-Env/README fuer Render

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Logbuch nachziehen

**Files:**
- Modify: `docs/open_todos.md`

**Interfaces:** keine (Doku).

- [ ] **Step 1: Eintrag ergänzen**

In `docs/open_todos.md` unter dem Abschnitt „Frontend / API-Brücke" einen Unterabschnitt „Frontend-Scheibe 1 — Cockpit-Übersicht (Branch `feat/frontend-cockpit-overview`)" ergänzen:
- **Umgesetzt:** React/TS/Vite/Tailwind-Frontend unter `frontend/`; Cockpit-Regime-Übersicht (Regime-Banner + 4 Domänen-Kacheln + Daten-Health + Run-Button), live über `GET`/`POST`/`WS`; UNAVAILABLE-Vertrag (`signal=null`/Status) als gestreift-graues Feld; Basis-Komponenten (SignalBadge/ConfidenceBar/UnavailableField); pure Anzeige-Logik TDD-getestet; Render-Deploy als Static Site + `AAIA_CORS_ORIGINS` im Backend. Spec: `docs/superpowers/specs/2026-06-22-frontend-cockpit-overview-design.md`, Plan: `docs/superpowers/plans/2026-06-22-frontend-cockpit-overview.md`.
- **Offene Folge-Aufgaben (mit Lösungsansatz):**
  - **WS-Reconnect/Replay:** bricht die WS-Leitung ab, fällt das Frontend auf `GET` zurück, aber ein laufender Lauf wird nicht weiterverfolgt. *Ansatz:* Reconnect mit Backoff + `GET`-Poll als Fallback; serverseitiger Pro-Lauf-Replay-Puffer (Backend-Folgeaufgabe #3) macht es robust.
  - **Drill-downs als nächste Scheiben:** Zinskurve/Buffett/Big-Mac — brauchen erst erweiterte Backend-Felder (eigene Spec/Plan je Scheibe).
  - **Auth vor öffentlicher Render-Exposition:** verknüpft mit Backend-Folgeaufgabe #7 (Auth + Rate-Limiting + Lauf-Lock), bevor das Dashboard über localhost/privat hinaus erreichbar ist.
  - **Charting-Bibliothek** (ECharts/Lightweight-Charts) erst mit den Drill-downs einführen.

- [ ] **Step 2: Commit**

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): Frontend-Scheibe 1 (Cockpit-Uebersicht) + Folge-Aufgaben

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (gegen die Spec)

**Spec-Abdeckung:**
- §1 Scope (nur Übersicht, Fundament) → Tasks 1–7 ✓
- §2 Stack (React/TS/Vite/Tailwind/Vitest, Monorepo, schlank) → Task 1 ✓; kein React Query/Charting (nicht eingeführt) ✓
- §3 Datenfluss (GET beim Laden, WS→POST, kein Auto-Start, Fehlerzustände) → Task 5 (Hook) + Task 6 (Seite) ✓
- §4 UI (1 Banner + 4 Kacheln + Health + Run; Basis-Bausteine; UNAVAILABLE/`signal=null`) → Tasks 3 + 6 ✓
- §5 Pure Logik (signalToVisual/formatConfidence/sourcesLabel/isUnavailable, TDD) → Tasks 1 + 2 ✓
- §6 Backend-Vertrag (GET 200/204, POST 202, WS terminal) → Tasks 4 + 5 ✓
- §7 Deploy (Static Site, VITE_API_BASE_URL, CORS, 1 Instanz) → Task 7 ✓
- §8 Tests (pure zuerst, Komponenten-Smoke, gegen Fakes) → durchgängig ✓
- §9 Nicht-Ziele + Folge-Aufgaben → Task 8 ✓

**Platzhalter-Scan:** kein „TBD"/„später"; jeder Code-Schritt zeigt vollständigen Code. ✓

**Typ-Konsistenz:** `CockpitOverview`/`Domain`/`Signal`/`Status` (Task 2) identisch in client/socket/hook/components verwendet; `getCockpit(base, fetchFn?)`, `startRun(base, fetchFn?)`, `openCockpitSocket(base, handlers, factory?)`, `useCockpit(deps?)`, `Phase`, `signalToVisual`/`isUnavailable`/`sourcesLabel`/`formatConfidence` über alle Tasks gleich. ✓
