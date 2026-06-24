# Frontend Slice 4 — Konflikt-Inbox — Implementation Plan

**For agentic workers:** Execute the tasks in order. Each task is TDD-first: write the failing test (Rot), implement until green (Grün), then commit. Use **German** for code comments, UI strings, and commit messages (AGENTS.md §0). Run the full test suite before claiming any task done. Reports go to `.superpowers/sdd/...` (leading dot, git-ignored) — **never** to `docs/superpowers/sdd/`, and **never** commit scratch files (no `git add -A`/`git add -f`; stage explicit paths only).

---

## Goal

Baue die **Konflikt-Inbox** (Spec §7 Slice 4, Konzept §2.5, Wireframe §4.9) — die beratende Benachrichtigungs- und Audit-Ansicht für gekippte Thesen. Sie deckt die User-Stories **US28–US30** vollständig ab:

- **US28** — Inbox listet Konflikte, sobald ein AAIA-Urteil gegen eine **gehaltene Position** läuft (z. B. long gehalten, neues Urteil SELL/SHORT). Die **Anzahl offener Konflikte** speist den **Inbox-Badge in der Topbar** (heute hartkodiert `0` → jetzt echt).
- **US29** — pro Konflikt ein **beratendes Verdikt EXIT / HOLD / REVERSE** mit Begründung; der Default-Vorschlag ist hervorgehoben. Beratend — **keine** Trade-Ausführung.
- **US30** — Konflikte **offen → erledigt** abarbeiten mit Entscheidung **gefolgt / ignoriert / vertagt**, protokolliert. Tabs „Offen" / „Erledigt"; der Erledigt-Tab ist der **Audit-Trail**. Jede Karte verlinkt auf die **Portfolio**-Position und den **Deep-Dive** (Konzept §3 Querverlinkung).

Daten kommen über die **Tausch-Naht** (Spec §2) aus Demo-Fixtures; der Umstieg auf echt bleibt eine Zeile. Kein Backend → der Erledigt-Status lebt clientseitig im Komponenten-State (Reset bei Reload akzeptabel, als Folge-Aufgabe protokolliert).

## Architecture

- **Hexagonal/Naht wie Slice 1–3:** Vertrag (`contract/inbox.ts`) → Naht (`data/inbox.ts` mit `loadInbox(deps?)`) → Demo-Fixture (`data/demo/inbox.ts`, `isDemo:true`). UI-Komponenten sind dumm und konsumieren über `useView`.
- **Eine Quelle der Wahrheit für die Konflikt-Erkennung:** `detectConflict`/`conflictNote` aus `lib/conflict.ts` (Slice 3) wird **wiederverwendet** — keine Duplikat-Logik. Das Demo-Fixture leitet seine Konflikte aus denselben Demo-Positionen ab wie das Portfolio (Konsistenz, mind. XLE long + SELL).
- **Reine, getestete Anzeige-/Ableitungs-Logik** (`lib/inbox.ts`): `suggestVerdict(direction, heldVerdict, newVerdict)` → EXIT/HOLD/REVERSE mit fachlicher Begründung, und `openCount(conflicts)` → Zahl für den Badge. React-entkoppelt, Grenzfälle zuerst.
- **Status clientseitig:** Die `InboxPage` hält den Abarbeitungs-Status (`offen`/`erledigt` + protokollierte Entscheidung) in einem `useReducer` über den Fixture-Konflikten. Keine Persistenz.
- **Badge-Verdrahtung:** `AppRoutes` lädt die Inbox-Zahl einmalig (über die Naht) und reicht `inboxCount` an `<AppShell>` durch. Das stört die bestehende `useCockpit`-Live-Anbindung nicht (eigener, getrennter Datenpfad).

## Tech Stack

React 19 + TypeScript + Vite + Tailwind v3, react-router-dom v7, Vitest + React Testing Library + `@testing-library/user-event`. Test-Runner: `npm test` (= `vitest run`) im Verzeichnis `frontend/`. Kein echter Netz-Call im Test (Fixtures/Fakes).

## Global Constraints

- **TDD verpflichtend** (AGENTS.md §4): erst der fehlschlagende Test, dann Code. Grenzfälle für die pure Logik explizit (jede Richtung × jedes Verdikt; `openCount` bei 0/gemischt/alle erledigt).
- **Deutsch** in Kommentaren, UI-Strings, Commit-Messages.
- **UNAVAILABLE ≠ 0 ≠ NEUTRAL** — der Inbox-Badge zeigt die echte offene Zahl; „keine Konflikte" ist `0` (legitim), nicht UNAVAILABLE.
- **Keine magischen Zahlen ohne Begründung** — jede Verdikt-Schwelle/Regel im Kommentar fachlich erklärt.
- **Keine Trade-Ausführung** — Aktionen markieren nur erledigt + protokollieren (US30).
- Loader stabil an `useView` übergeben (Modul-Identität oder `useCallback`), sonst Refetch-Loop.
- `isDemo` steuert `DemoBadge` automatisch; nicht von Hand ein-/ausblenden.
- Reports nach `.superpowers/sdd/...`; keine Scratch-Datei committen.

---

## File Structure

| Datei | Art | Zweck |
|---|---|---|
| `frontend/src/contract/inbox.ts` | neu | Vertrag: `ConflictDTO`, `ConflictVerdict`, `ConflictDecision`, `ConflictStatus`, `InboxView extends DemoMeta` |
| `frontend/src/lib/inbox.ts` | neu | Pure Logik: `suggestVerdict(...)` (EXIT/HOLD/REVERSE + Begründung), `openCount(...)` |
| `frontend/src/lib/inbox.test.ts` | neu | TDD für `suggestVerdict`/`openCount` (Grenzfälle) |
| `frontend/src/data/inbox.ts` | neu | Tausch-Naht: `loadInbox(deps?)` (Demo heute, echte Zeile auskommentiert) |
| `frontend/src/data/demo/inbox.ts` | neu | Demo-Fixture: mehrere Konflikte (inkl. XLE long+SELL), `isDemo:true`, aus `detectConflict` abgeleitet |
| `frontend/src/data/inbox.test.ts` | neu | Naht-Test: `isDemo:true`, ≥1 Konflikt, XLE-Fall, alle als `offen` initialisiert |
| `frontend/src/components/inbox/ConflictCard.tsx` | neu | Eine Konflikt-Karte: Badge, Urteil-Kippe, Verdikt-Optionen (Default hervorgehoben), Begründung, Aktionen, Querlinks |
| `frontend/src/components/inbox/ConflictCard.test.tsx` | neu | Smoke: rendert Felder, Default-Verdikt hervorgehoben, Aktions-Callbacks, Links |
| `frontend/src/pages/InboxPage.tsx` | neu | Seite: Tabs Offen/Erledigt, `useReducer`-Status, Abarbeitung, DemoBadge |
| `frontend/src/pages/InboxPage.test.tsx` | neu | Smoke: Tabs, Abarbeiten verschiebt Karte Offen→Erledigt, Audit-Trail-Eintrag |
| `frontend/src/data/inboxCount.ts` | neu | Schlanker Lader für die Badge-Zahl (nutzt `loadInbox` + `openCount`) |
| `frontend/src/routes.tsx` | ändern | `/inbox` → `InboxPage`; `inboxCount` echt laden und an `AppShell` durchreichen |
| `frontend/src/routes.test.tsx` | ändern | `/inbox` rendert InboxPage; Badge zeigt offene Zahl |
| `docs/open_todos.md` | ändern | Logbuch: Slice 4 erledigt + Folge-Aufgaben (Persistenz, echter Inbox-Endpunkt, WebSocket-Push) |

---

# DISPATCH A — Naht + pure Logik (Vertrag, Demo-Fixture, `suggestVerdict`/`openCount`, `detectConflict`-Wiederverwendung)

---

## Task A1 — Vertrag `contract/inbox.ts`

**Files:** `frontend/src/contract/inbox.ts` (neu)

**Interfaces (vollständiger Code):**

```ts
// frontend/src/contract/inbox.ts
// Inbox-Vertrag (Spec §2): beschreibt die KUENFTIGE API-Form. Demo + Echt liefern denselben
// Vertrag, InboxView extends DemoMeta. Die Inbox ist BERATEND — Aktionen fuehren KEINE Trades
// aus, sie markieren erledigt + protokollieren die Entscheidung (US30, Konzept §2.5).
import type { DemoMeta, Underlying, Wrapper, LongVerdict, ShortVerdict } from "./common";
import type { Direction } from "./portfolio";

// Beratendes Verdikt pro Konflikt (US29): aussteigen / halten / Richtung drehen.
export type ConflictVerdict = "EXIT" | "HOLD" | "REVERSE";

// Abarbeitungs-Status (US30): offen -> erledigt. "erledigt" traegt immer eine Entscheidung.
export type ConflictStatus = "offen" | "erledigt";

// Protokollierte Entscheidung beim Erledigen (US30): dem Verdikt gefolgt / ignoriert / vertagt.
export type ConflictDecision = "gefolgt" | "ignoriert" | "vertagt";

export interface ConflictDTO {
  id: string;                   // stabile ID (Ticker+Richtung reicht in der Demo)
  ticker: string;
  name: string;
  underlying: Underlying;
  wrapper: Wrapper;
  direction: Direction;         // gehaltene Positionsrichtung (long/short)
  heldVerdict: LongVerdict | ShortVerdict;  // Urteil, das die These STUETZTE, als die Position eroeffnet wurde
  newLongVerdict: LongVerdict;  // aktuelles AAIA-Long-Urteil
  newShortVerdict: ShortVerdict;// aktuelles AAIA-Short-Urteil
  confidence: number;           // 0..1 — Konfidenz des kippenden Urteils
  conflictNote: string;         // Kurzbegruendung, WARUM dies ein Konflikt ist (aus lib/conflict)
  suggestedVerdict: ConflictVerdict; // beratender Default-Vorschlag (US29), hervorgehoben
  suggestedRationale: string;   // fachliche Begruendung des Vorschlags
  status: ConflictStatus;       // initial immer "offen"
}

export interface InboxView extends DemoMeta {
  conflicts: ConflictDTO[];
}
```

**TDD-Steps:**
1. Kein eigener Test (reiner Typ-Vertrag) — die Korrektheit wird durch die Tests in A2–A4 (die diesen Vertrag konsumieren) erzwungen. Lege die Datei an.
2. `npm test` muss weiter grün sein (TypeScript-Kompilation der bestehenden Suite bricht nicht).
3. Commit:
```
feat(inbox): Vertrag contract/inbox.ts (ConflictDTO + InboxView)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task A2 — Pure Logik `lib/inbox.ts` (`suggestVerdict` + `openCount`)

**Files:** `frontend/src/lib/inbox.ts` (neu), `frontend/src/lib/inbox.test.ts` (neu)

**Fachliche Begründung (im Code als Kommentar, US29):** Bei einem Konflikt läuft das neue Urteil gegen die gehaltene Position. Der beratende Default leitet sich aus der **Stärke und Richtung** des Gegensignals ab:
- **long-Position:**
  - neues **Short-Urteil SHORT** (aktives Gegen-Setup) → **REVERSE** (Richtung drehen): das System sieht nicht nur „raus", sondern ein tragfähiges Short.
  - neues **Long-Urteil SELL** ohne SHORT → **EXIT** (aussteigen): These trägt nicht mehr, aber kein bestätigtes Short-Setup.
  - sonst (kein echtes Gegensignal mehr) → **HOLD**: kein Handlungsdruck.
- **short-Position (spiegelbildlich):**
  - neues **Long-Urteil BUY** → **REVERSE** (vom Short auf Long drehen).
  - neues **Short-Urteil COVER** ohne BUY → **EXIT** (eindecken).
  - sonst → **HOLD**.

Das ist beratend; eine niedrige Konfidenz wird in der Begründung benannt, ändert aber den Default nicht (das überlässt das System dem Nutzer — keine magische Konfidenz-Schwelle hier).

**Interfaces (vollständiger Code):**

```ts
// frontend/src/lib/inbox.ts
import type { ConflictVerdict, ConflictDTO } from "../contract/inbox";
import type { Direction } from "../contract/portfolio";
import type { LongVerdict, ShortVerdict } from "../contract/common";

export interface VerdictSuggestion {
  verdict: ConflictVerdict;     // EXIT / HOLD / REVERSE (Default-Vorschlag, US29)
  rationale: string;            // fachliche Begruendung (Deutsch, ohne magische Zahl)
}

// Beratender Default-Vorschlag (US29). REVERSE nur, wenn das System ein AKTIVES Gegen-Setup
// sieht (long: neues SHORT; short: neues BUY) — sonst EXIT (raus) bzw. HOLD (kein Druck).
export function suggestVerdict(
  direction: Direction,
  _heldVerdict: LongVerdict | ShortVerdict,
  newLong: LongVerdict,
  newShort: ShortVerdict,
): VerdictSuggestion {
  if (direction === "long") {
    if (newShort === "SHORT") {
      return { verdict: "REVERSE", rationale: "Aktives Short-Setup gegen die Long-Position — Richtung drehen erwägen." };
    }
    if (newLong === "SELL") {
      return { verdict: "EXIT", rationale: "Long-These trägt nicht mehr (SELL), aber kein bestätigtes Short — Ausstieg erwägen." };
    }
    return { verdict: "HOLD", rationale: "Kein tragfähiges Gegensignal — vorerst halten." };
  }
  // short-Position (spiegelbildlich)
  if (newLong === "BUY") {
    return { verdict: "REVERSE", rationale: "Aktives Long-Setup gegen die Short-Position — Richtung drehen erwägen." };
  }
  if (newShort === "COVER") {
    return { verdict: "EXIT", rationale: "Short-These trägt nicht mehr (COVER), aber kein bestätigtes Long — Eindecken erwägen." };
  }
  return { verdict: "HOLD", rationale: "Kein tragfähiges Gegensignal — vorerst halten." };
}

// Anzahl OFFENER Konflikte fuer den Topbar-Badge (US28). Erledigte zaehlen NICHT mit.
export function openCount(conflicts: Pick<ConflictDTO, "status">[]): number {
  return conflicts.filter((c) => c.status === "offen").length;
}
```

**Test (vollständiger Code):**

```ts
// frontend/src/lib/inbox.test.ts
import { describe, it, expect } from "vitest";
import { suggestVerdict, openCount } from "./inbox";

describe("suggestVerdict (beratender Default, US29)", () => {
  it("long + neues SHORT => REVERSE (aktives Gegen-Setup)", () => {
    expect(suggestVerdict("long", "BUY", "HOLD", "SHORT").verdict).toBe("REVERSE");
  });
  it("long + SELL ohne SHORT => EXIT", () => {
    expect(suggestVerdict("long", "BUY", "SELL", "NONE").verdict).toBe("EXIT");
  });
  it("long ohne echtes Gegensignal => HOLD", () => {
    expect(suggestVerdict("long", "BUY", "HOLD", "NONE").verdict).toBe("HOLD");
  });
  it("short + neues BUY => REVERSE", () => {
    expect(suggestVerdict("short", "SHORT", "BUY", "HOLD").verdict).toBe("REVERSE");
  });
  it("short + COVER ohne BUY => EXIT", () => {
    expect(suggestVerdict("short", "SHORT", "NONE", "COVER").verdict).toBe("EXIT");
  });
  it("short ohne echtes Gegensignal => HOLD", () => {
    expect(suggestVerdict("short", "SHORT", "NONE", "HOLD").verdict).toBe("HOLD");
  });
  it("liefert immer eine nicht-leere Begruendung", () => {
    expect(suggestVerdict("long", "BUY", "SELL", "NONE").rationale.length).toBeGreaterThan(0);
  });
});

describe("openCount (Badge-Zahl, US28)", () => {
  it("zaehlt nur offene Konflikte", () => {
    expect(openCount([{ status: "offen" }, { status: "erledigt" }, { status: "offen" }])).toBe(2);
  });
  it("leere Liste => 0 (legitime Null, kein UNAVAILABLE)", () => {
    expect(openCount([])).toBe(0);
  });
  it("alle erledigt => 0", () => {
    expect(openCount([{ status: "erledigt" }, { status: "erledigt" }])).toBe(0);
  });
});
```

**TDD-Steps:**
1. Schreibe `inbox.test.ts` (Rot — Modul fehlt).
2. Implementiere `lib/inbox.ts` bis grün.
3. `npm test` — grün.
4. Commit:
```
feat(inbox): pure Logik suggestVerdict + openCount (US28/US29)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task A3 — Demo-Fixture `data/demo/inbox.ts` (aus `detectConflict` abgeleitet)

**Files:** `frontend/src/data/demo/inbox.ts` (neu)

**Vorgaben:**
- Definiere eine kleine Liste plausibler **Quell-Positionen** (Ticker, Name, underlying, wrapper, direction, heldVerdict, aktuelles `newLong`/`newShort`, confidence) — mind. **3 echte Konflikte**, davon einer **XLE long + SELL** (konsistent zum Portfolio-Demo), plus ggf. eine Nicht-Konflikt-Position, die durch `detectConflict` herausgefiltert wird (beweist die Wiederverwendung).
- Baue jeden `ConflictDTO` aus diesen Positionen, **ausschließlich** für die per `detectConflict(direction, judgment)` als Konflikt erkannten Fälle (keine Duplikat-Logik):
  - `conflictNote` aus `conflictNote(direction, judgment)`.
  - `suggestedVerdict`/`suggestedRationale` aus `suggestVerdict(direction, heldVerdict, newLong, newShort)`.
  - `status: "offen"` initial.
- `isDemo: true`.

**Konkrete Konflikt-Fälle (fachlich konsistent):**
- `XLE` — `equity_index`/`fund`, **long**, heldVerdict `BUY`, neu `longVerdict:"SELL"`, `shortVerdict:"NONE"`, conf 0.58 → `suggestVerdict` = **EXIT**.
- `GC=F` — `precious_metal`/`future`, **long**, heldVerdict `BUY`, neu `longVerdict:"HOLD"`, `shortVerdict:"SHORT"`, conf 0.55 → **REVERSE** (aktives Short-Setup).
- `TSLA` — `equity`/`single`, **short**, heldVerdict `SHORT`, neu `longVerdict:"BUY"`, `shortVerdict:"COVER"`, conf 0.62 → **REVERSE** (BUY hat Vorrang vor COVER).
- (Kontroll-Position, **kein** Konflikt → wird gefiltert): `MSFT` — **long**, neu `longVerdict:"BUY"` → `detectConflict` = false, erscheint NICHT in der Inbox.

**Helper-Hinweis:** Baue ein `PositionJudgmentDTO` aus `newLong`/`newShort`/`confidence`, um `detectConflict`/`conflictNote` aufzurufen — exakt dieselbe Funktion wie im Portfolio (eine Quelle der Wahrheit).

**TDD-Steps:**
1. Kein dedizierter Test in diesem Task (das Fixture wird in A4 über die Naht getestet). Implementiere das Fixture so, dass es A4 grün macht.
2. Commit erfolgt zusammen mit A4 (oder separat — Fixture allein ist commit-fähig):
```
feat(inbox): Demo-Fixture data/demo/inbox.ts (XLE/GC=F/TSLA, aus detectConflict)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task A4 — Tausch-Naht `data/inbox.ts` + Naht-Test

**Files:** `frontend/src/data/inbox.ts` (neu), `frontend/src/data/inbox.test.ts` (neu)

**Interfaces (vollständiger Code):**

```ts
// frontend/src/data/inbox.ts
// DIE TAUSCH-NAHT (Spec §2): genau EINE Lade-Funktion fuer die Inbox. Heute Demo-Fixture;
// beim Umstieg auf echt wird GENAU die auskommentierte Zeile getauscht (setzt isDemo:false).
import type { InboxView } from "../contract/inbox";
import { demoInbox } from "./demo/inbox";
import type { ApiDeps } from "./apiDeps";

export async function loadInbox(_deps?: ApiDeps): Promise<InboxView> {
  return demoInbox();
  // return fetchInbox(_deps); // <- einzige Zeile, die beim Umstieg getauscht wird
}
```

**Test (vollständiger Code):**

```ts
// frontend/src/data/inbox.test.ts
import { describe, it, expect } from "vitest";
import { loadInbox } from "./inbox";
import { detectConflict } from "../lib/conflict";
import type { PositionJudgmentDTO } from "../contract/portfolio";

// Rekonstruiert das Urteil aus dem DTO, um die Konflikt-Erkennung gegenzupruefen (eine Quelle der Wahrheit).
function judgmentOf(c: { newLongVerdict: PositionJudgmentDTO["longVerdict"]; newShortVerdict: PositionJudgmentDTO["shortVerdict"]; confidence: number }): PositionJudgmentDTO {
  return { longVerdict: c.newLongVerdict, shortVerdict: c.newShortVerdict, confidence: c.confidence };
}

describe("loadInbox (Tausch-Naht)", () => {
  it("liefert einen Demo-View (isDemo:true) mit mehreren Konflikten", async () => {
    const v = await loadInbox();
    expect(v.isDemo).toBe(true);
    expect(v.conflicts.length).toBeGreaterThanOrEqual(3);
  });
  it("enthaelt den XLE-Konflikt (long gehalten, Urteil SELL) mit Default EXIT", async () => {
    const v = await loadInbox();
    const xle = v.conflicts.find((c) => c.ticker === "XLE");
    expect(xle).toBeDefined();
    expect(xle?.direction).toBe("long");
    expect(xle?.suggestedVerdict).toBe("EXIT");
  });
  it("jeder gelistete Eintrag ist wirklich ein Konflikt (detectConflict-Wiederverwendung)", async () => {
    const v = await loadInbox();
    for (const c of v.conflicts) {
      expect(detectConflict(c.direction, judgmentOf(c))).toBe(true);
    }
  });
  it("alle Eintraege starten als offen (US30)", async () => {
    const v = await loadInbox();
    expect(v.conflicts.every((c) => c.status === "offen")).toBe(true);
  });
});
```

**TDD-Steps:**
1. Schreibe `data/inbox.test.ts` (Rot — Naht + Fixture fehlen, falls A3 noch nicht commit-fähig war).
2. Stelle sicher, dass `data/inbox.ts` (dieser Task) und `data/demo/inbox.ts` (A3) die Tests grün machen.
3. `npm test` — grün.
4. Commit:
```
feat(inbox): Tausch-Naht loadInbox + Naht-Test

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

# DISPATCH B — InboxPage + Karten + Tabs + Abarbeitung + Querverlinkung + Badge-Verdrahtung + Routing

> Dispatch B baut auf den committeten Artefakten aus Dispatch A auf (Vertrag, Naht, Fixture, pure Logik).

---

## Task B1 — `ConflictCard.tsx` (eine Karte)

**Files:** `frontend/src/components/inbox/ConflictCard.tsx` (neu), `frontend/src/components/inbox/ConflictCard.test.tsx` (neu)

**Exaktes Interface:**

```ts
import type { ConflictDTO, ConflictDecision } from "../../contract/inbox";

export interface ConflictCardProps {
  conflict: ConflictDTO;
  // US30: nur im Offen-Tab gesetzt. Erledigen markiert + protokolliert (KEINE Trade-Ausfuehrung).
  onResolve?: (id: string, decision: ConflictDecision) => void;
  // im Erledigt-Tab gesetzt: die protokollierte Entscheidung (Audit-Trail).
  loggedDecision?: ConflictDecision;
}
```

**Strukturelle Vorgaben (Wireframe §4.9):**
- Wiederverwenden: `<UnderlyingWrapperBadge underlying wrapper />`, `<ConfidenceBar value={conflict.confidence} />`.
- Kopfzeile: Ticker (als `<Link to={\`/deep-dive/${ticker}\`}>`), Name, Richtungs-Kürzel (L/S), und der Kipp-Text, z. B. „du bist LONG, neues Urteil: SELL (58 %)". Das relevante neue Urteil-Wort über `verdictToVisual` einfärben (Wiederverwendung `lib/judgment`).
- Verdikt-Reihe: drei Optionen **EXIT / HOLD / REVERSE**; die `conflict.suggestedVerdict`-Option **hervorgehoben** (z. B. Ring/Fett + `aria-pressed` oder ein „Vorschlag"-Label). `conflict.suggestedRationale` als Begründungstext sichtbar.
- Konflikt-Begründung: `conflict.conflictNote`.
- **Querlinks (Konzept §3):** „↗ Deep-Dive" → `/deep-dive/${ticker}`; „↗ Portfolio" → `/portfolio` (die Position lebt dort; ein Anchor/`#${ticker}` ist optional, nicht erforderlich).
- **Aktionen (nur wenn `onResolve` gesetzt, US30):** drei Buttons „Gefolgt" / „Ignoriert" / „Vertagt" → rufen `onResolve(conflict.id, decision)`. **Kein** Trade-Wording wie „Order senden" — die Buttons protokollieren nur. Beschrifte „Folgen → Notiz" als reine Protokoll-Aktion.
- **Erledigt-Modus (`loggedDecision` gesetzt):** keine Aktions-Buttons, stattdessen ein Audit-Label „Erledigt: <decision>".

**Kern-Test-Assertions:**

```ts
// ConflictCard.test.tsx — Kernfaelle
// 1. rendert Ticker + Kipp-Text + suggestedRationale
//    render(<MemoryRouter><ConflictCard conflict={xleConflict} onResolve={vi.fn()} /></MemoryRouter>)
//    expect(screen.getByText("XLE")).toBeInTheDocument()
//    expect(screen.getByText(/SELL/)).toBeInTheDocument()
// 2. Default-Verdikt (EXIT) ist hervorgehoben:
//    expect(screen.getByText("EXIT")).toHaveAttribute("aria-pressed", "true")  // oder Klassen-/Label-Check
// 3. Deep-Dive-Link zeigt auf /deep-dive/XLE:
//    expect(screen.getByRole("link", { name: /Deep-Dive/i })).toHaveAttribute("href", "/deep-dive/XLE")
// 4. Aktion protokolliert (KEINE Ausfuehrung): Klick "Gefolgt" ruft onResolve("xle...","gefolgt")
//    await userEvent.click(screen.getByRole("button", { name: /Gefolgt/i }))
//    expect(onResolve).toHaveBeenCalledWith(xleConflict.id, "gefolgt")
// 5. Erledigt-Modus zeigt das Audit-Label und KEINE Aktions-Buttons:
//    render(<MemoryRouter><ConflictCard conflict={xleConflict} loggedDecision="ignoriert" /></MemoryRouter>)
//    expect(screen.getByText(/Erledigt: ignoriert/i)).toBeInTheDocument()
//    expect(screen.queryByRole("button", { name: /Gefolgt/i })).toBeNull()
```

**TDD-Steps:**
1. Schreibe `ConflictCard.test.tsx` (Rot). Baue ein Test-Fixture-Konflikt-Objekt inline (oder importiere `demoInbox()` und nimm den XLE-Eintrag).
2. Implementiere `ConflictCard.tsx` bis grün.
3. `npm test` — grün.
4. Commit:
```
feat(inbox): ConflictCard mit Verdikt-Optionen + Querlinks + Protokoll-Aktionen

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task B2 — `InboxPage.tsx` (Tabs Offen/Erledigt + Status-Abarbeitung)

**Files:** `frontend/src/pages/InboxPage.tsx` (neu), `frontend/src/pages/InboxPage.test.tsx` (neu)

**Exaktes Interface:**

```ts
import type { InboxView } from "../contract/inbox";
import { loadInbox } from "../data/inbox";

export function InboxPage({ loader = loadInbox }: { loader?: () => Promise<InboxView> }): JSX.Element
```

**Strukturelle Vorgaben:**
- Lädt über `useView(loader)` (Loader-Prop = Modul-Identität als Default → kein Refetch-Loop).
- Kopf: `<h2>Konflikt-Inbox</h2>` + `<DemoBadge isDemo={data.isDemo} />`.
- **Status clientseitig** via `useReducer`: initialer State leitet sich aus `data.conflicts` ab (alle „offen", keine Entscheidung). Aktion `RESOLVE { id, decision }` setzt `status:"erledigt"` + speichert `decision`. **Wichtig:** Den Reducer-State aus den geladenen Daten initialisieren (z. B. `useEffect`/Lazy-Init, sobald `data` da ist) — Reset bei Reload ist akzeptabel.
- **Tabs „Offen (n)" / „Erledigt (m)":** lokaler `useState` für den aktiven Tab; `role="tab"`/`aria-selected` setzen. Offen-Zähler = `openCount(state.items)` (Wiederverwendung der puren Funktion).
- Offen-Tab: für jede offene Karte `<ConflictCard conflict onResolve={(id,d)=>dispatch({type:"RESOLVE",id,decision:d})} />`.
- Erledigt-Tab (**Audit-Trail**): für jede erledigte Karte `<ConflictCard conflict loggedDecision={...} />` ohne `onResolve`.
- Leerer Offen-Tab: freundlicher Hinweis „Keine offenen Konflikte." (legitime Null — kein UNAVAILABLE).
- Loading/Error-Pfade wie `PortfolioPage` (Lädt …/Fehler).

**Kern-Test-Assertions:**

```ts
// InboxPage.test.tsx
// Helfer: renderWithRouter(<InboxPage loader={() => Promise.resolve(demoInbox())} />)
// 1. Tabs sichtbar, Offen-Tab zeigt die Konflikt-Anzahl:
//    await screen.findByText("XLE")  // Offen-Tab default
//    expect(screen.getByRole("tab", { name: /Offen/i })).toBeInTheDocument()
// 2. Abarbeiten verschiebt Karte Offen->Erledigt + protokolliert:
//    await userEvent.click( <XLE-Karte> "Gefolgt" )
//    -> XLE nicht mehr im Offen-Tab; Offen-Zaehler -1
//    Wechsel auf Erledigt-Tab -> screen.getByText(/Erledigt: gefolgt/i) sichtbar (Audit-Trail)
// 3. Sind alle abgearbeitet -> Offen-Tab zeigt "Keine offenen Konflikte."
```

**TDD-Steps:**
1. Schreibe `InboxPage.test.tsx` (Rot).
2. Implementiere `InboxPage.tsx` bis grün.
3. `npm test` — grün.
4. Commit:
```
feat(inbox): InboxPage mit Offen/Erledigt-Tabs + clientseitiger Abarbeitung (US30)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task B3 — Badge-Verdrahtung + Routing (`inboxCount` echt, `/inbox` → InboxPage)

**Files:** `frontend/src/data/inboxCount.ts` (neu), `frontend/src/routes.tsx` (ändern), `frontend/src/routes.test.tsx` (ändern)

**Gewählter Weg (einfachste Lösung, stört `useCockpit` nicht):** `AppRoutes` lädt die offene Konflikt-Zahl **einmalig** über die Naht und reicht sie als `inboxCount` an `<AppShell>` durch — getrennter Datenpfad, kein Eingriff in `useCockpit`/Cockpit-Live.

**Neuer schlanker Lader (vollständiger Code):**

```ts
// frontend/src/data/inboxCount.ts
// Schlanker Lader fuer die Topbar-Badge-Zahl (US28): laedt die Inbox ueber die Naht und
// zaehlt die OFFENEN Konflikte (openCount). Getrennt vom Cockpit-Datenpfad -> stoert die
// useCockpit-Live-Anbindung nicht. Reset bei Reload akzeptabel (kein Backend, Demo).
import { loadInbox } from "./inbox";
import { openCount } from "../lib/inbox";
import type { ApiDeps } from "./apiDeps";

export async function loadInboxCount(deps?: ApiDeps): Promise<number> {
  const view = await loadInbox(deps);
  return openCount(view.conflicts);
}
```

**`routes.tsx`-Änderungen (strukturell):**
- Importiere `InboxPage` und `loadInboxCount`.
- In `AppRoutes`: einen lokalen `inboxCount`-State (`useState<number>(0)`) halten; in einem `useEffect` einmalig `loadInboxCount(deps && { token: deps.token })` aufrufen und den State setzen (Fehler still schlucken → bleibt 0, kein Crash). `deps` ist optional; im Test wird `AppRoutes` ohne `deps` gerendert.
- `<AppShell inboxCount={inboxCount} … />` statt hartkodiert `0`.
- Route `/inbox`: `element={<InboxPage />}` statt `PlaceholderPage`.

**Hinweis:** `AppRoutes` wird damit eine Komponente mit Hooks — das ist es bereits implizit (JSX-Funktion); füge `useState`/`useEffect`-Importe hinzu. Loader im `useEffect` ist modul-stabil → kein Loop.

**`routes.test.tsx`-Ergänzungen:**

```ts
// Ergaenzungen in routes.test.tsx
// A) /inbox rendert die InboxPage:
//    renderAt("/inbox")
//    await waitFor(() => expect(screen.getByRole("heading", { name: /Konflikt-Inbox/i })).toBeInTheDocument())
// B) Inbox-Badge zeigt die offene Zahl (>=3 Demo-Konflikte) in der Topbar:
//    renderAt("/cockpit")
//    await waitFor(() => expect(screen.getByText("3")).toBeInTheDocument())
//    // (Zahl an die Demo-Fixture-Konfliktanzahl anpassen; >=3 laut A3)
```

**TDD-Steps:**
1. Ergänze `routes.test.tsx` um A) und B) (Rot).
2. Lege `data/inboxCount.ts` an; verdrahte `routes.tsx` (InboxPage-Route + echter `inboxCount`).
3. `npm test` — grün (inkl. der bestehenden Routing-Tests).
4. Commit:
```
feat(inbox): /inbox-Route + echter Topbar-Badge (loadInboxCount/openCount, US28)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task B4 — Logbuch `docs/open_todos.md`

**Files:** `docs/open_todos.md` (ändern)

**Vorgaben (AGENTS.md §5):**
- Slice-4-Eintrag **abhaken** mit kurzem **Lösung:**-Hinweis (was/warum/wie): Konflikt-Inbox über die Tausch-Naht (`loadInbox`), `detectConflict` wiederverwendet, beratendes Verdikt via `suggestVerdict`, clientseitige Abarbeitung mit Audit-Trail, Topbar-Badge über `loadInboxCount`/`openCount` echt verdrahtet.
- **Folge-Aufgaben** mit Lösungsansatz ergänzen:
  - **Persistenz des Abarbeitungs-Status** (heute Reset bei Reload) → später LocalStorage oder echter Inbox-Endpunkt (Status serverseitig).
  - **Echter Inbox-Endpunkt** (`fetchInbox`) → die auskommentierte Naht-Zeile aktivieren; Backend leitet Konflikte aus Portfolio × Judgment ab.
  - **WebSocket-Push für die Inbox** (Konzept §6.4) → Badge live aktualisieren, statt einmaligem Laden.
- Diese Logbuch-Änderung läuft mit im Slice-4-PR (kein direkter Master-Commit für Code-begleitende Doku).

**TDD-Steps:** Kein Test (Doku). Commit:
```
docs(open_todos): Slice 4 (Konflikt-Inbox) erledigt + Folge-Aufgaben (Persistenz/Endpunkt/WS)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

# Self-Review (vor „fertig")

**US-Abdeckung (jede Story einem Task zugeordnet):**

| Story | Inhalt | Tasks |
|---|---|---|
| **US28** | Inbox listet gekippte Positionen; Anzahl speist Topbar-Badge | A1 (Vertrag), A2 (`openCount`), A3/A4 (Fixture/Naht), B2 (Liste), **B3 (Badge echt)** |
| **US29** | Beratendes Verdikt EXIT/HOLD/REVERSE + Begründung, Default hervorgehoben | A2 (`suggestVerdict`), A3 (im Fixture gesetzt), **B1 (Default hervorgehoben in der Karte)** |
| **US30** | Offen→erledigt (gefolgt/ignoriert/vertagt) protokollieren; Erledigt = Audit-Trail; Querlinks Portfolio/Deep-Dive | B1 (Aktionen + Links), **B2 (Tabs + Status + Audit-Trail)** |

**Platzhalter-Scan:** Keine absichtlichen Fehlermarker, kein `never`-Trick, keine „entferne diese Zeile". Jeder gezeigte Code (Vertrag, `lib/inbox.ts`, Naht, Tests) ist direkt verwendbar. `/inbox`-Platzhalter (`PlaceholderPage`) wird in B3 ersetzt.

**Typ-Konsistenz:** `ConflictDTO` nutzt `Underlying`/`Wrapper`/`LongVerdict`/`ShortVerdict` aus `contract/common.ts` und `Direction` aus `contract/portfolio.ts`; `detectConflict`/`conflictNote` aus `lib/conflict.ts` werden unverändert wiederverwendet (Argument `PositionJudgmentDTO`), `verdictToVisual`/`ConfidenceBar`/`UnderlyingWrapperBadge`/`DemoBadge`/`useView` werden wiederverwendet. `openCount` nimmt `Pick<ConflictDTO,"status">[]` → funktioniert auch über den Reducer-State.

**Naht-Treue:** `loadInbox(deps?)` spiegelt `loadPortfolio` exakt (Demo heute, echte Zeile auskommentiert, `isDemo:true` nur im Fixture). Umstieg = eine Zeile.

**Verifikation vor „fertig":** `npm test` (= `vitest run`) im `frontend/` grün; Ergebnis nennen. Keine Erfolgsmeldung ohne grünen Lauf (AGENTS.md §4).

**Scratch/Report:** Reports nach `.superpowers/sdd/...` (git-ignoriert). Keine Scratch-Datei committen; nur die in der File-Structure-Tabelle gelisteten Pfade explizit stagen (kein `git add -A`/`-f`).

---

# Dispatch-Gruppierung

- **Dispatch A — Naht + pure Logik** (sequenziell, da A3/A4 auf A1/A2 aufbauen): **A1** Vertrag · **A2** `suggestVerdict`/`openCount` · **A3** Demo-Fixture (aus `detectConflict`) · **A4** Naht + Naht-Test.
- **Dispatch B — UI + Verdrahtung** (baut auf committetem A auf): **B1** ConflictCard · **B2** InboxPage (Tabs/Status/Audit-Trail) · **B3** Badge-Verdrahtung + Routing · **B4** Logbuch.

Reihenfolge: erst Dispatch A vollständig (Vertrag/Naht/Logik stehen + grün), dann Dispatch B. Innerhalb B: B1 → B2 → B3 → B4.
