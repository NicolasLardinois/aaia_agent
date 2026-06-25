# Frontend Onboarding + Erklär-/Metrik-Fundament — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine selbsterklärende Willkommen-Seite (`/willkommen`) + ein wiederverwendbarer Erklär-/Metrik-Baukasten, damit ein neuer Nutzer sofort versteht, wie AAIA funktioniert und wo was zu finden ist.

**Architecture:** Reines Frontend (kein Backend/keine Tausch-Naht). Onboarding-Status in `localStorage` (`useOnboarding`-Hook, Muster wie `useAuth`/`useTheme`). Index-Route wird onboarding-bewusst (erster Besuch → `/willkommen`, sonst → `/cockpit`). Dauerhaft erreichbar über „?" in der Topbar + Sidebar-Eintrag. Baukasten (`InfoTip`, `SectionCard`, `MetricRow`, `MetricCard`, `glossary`) wird in Teil-Projekt B/C wiederverwendet.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind v3, react-router-dom v7, Vitest + React Testing Library (jsdom).

## Global Constraints

- Sprache durchgehend **Deutsch** (UI-Texte + Code-Kommentare).
- **TDD verpflichtend:** erst der fehlschlagende Test, dann minimaler Code.
- **Build-Pflicht nach Import-Änderungen:** `npm run build` (tsc) — `vitest` typecheckt ungenutzte Importe nicht (bekannte Falle TS6133).
- **UNAVAILABLE ≠ 0:** fehlender Wert → „n.v.", nie „0".
- Bestehenden Stil spiegeln: Tailwind-Klassen wie im Code, `role`-basierte RTL-Queries, deutsche Testnamen.
- Arbeitsverzeichnis: `frontend/` (alle Pfade unten relativ dazu). Commits: `feat(onboarding): …`.

---

### Task 1: Glossar (pure)

**Files:**
- Create: `frontend/src/lib/glossary.ts`
- Test: `frontend/src/lib/glossary.test.ts`

**Interfaces:**
- Produces: `glossaryLookup(term: string): string | null`

- [ ] **Step 1: Failing test** — `frontend/src/lib/glossary.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { glossaryLookup } from "./glossary";

describe("glossaryLookup", () => {
  it("liefert eine deutsche Erklärung für einen bekannten Begriff", () => {
    const text = glossaryLookup("Top-Down");
    expect(text).toBeTruthy();
    expect(text).toContain("oben");
  });
  it("liefert null für einen unbekannten Begriff", () => {
    expect(glossaryLookup("Quatschbegriff")).toBeNull();
  });
});
```

- [ ] **Step 2: Run → FAIL** — `npx vitest run src/lib/glossary.test.ts` (Modul fehlt).

- [ ] **Step 3: Implement** — `frontend/src/lib/glossary.ts`

```ts
// Pure Begriff→Erklärung-Quelle. Eine Quelle für InfoTip-Tooltips und eine
// spätere Glossar-Seite (Teil-Projekt B). Erklärungen kurz + auf Deutsch.
const ENTRIES: Record<string, string> = {
  "Top-Down": "Analyse von oben nach unten: zuerst das große Bild (Konjunktur, Zinsen, Inflation), das den Rahmen für einzelne Anlagen setzt.",
  "Bottom-Up": "Analyse von unten nach oben: die Tiefenprüfung eines einzelnen Titels (Bewertung, Qualität, Bilanz) unabhängig vom Gesamtmarkt.",
  "Regime": "Die aktuelle Großwetterlage am Markt (z. B. Aufschwung, Abschwung, Rezession), abgeleitet aus Makro-Daten.",
  "Urteil": "Die Zusammenführung von Top-Down und Bottom-Up zu einer Gesamteinschätzung pro Anlage.",
  "Demo-Daten": "Beispielwerte, die echte Daten nachstellen, solange die echte Quelle noch nicht angebunden ist — am Etikett erkennbar.",
  "Exposure": "Wie stark dein Kapital insgesamt im Markt steckt (brutto = Summe aller Positionen, netto = long minus short).",
};

export function glossaryLookup(term: string): string | null {
  return ENTRIES[term] ?? null;
}
```

- [ ] **Step 4: Run → PASS** — `npx vitest run src/lib/glossary.test.ts`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/glossary.ts frontend/src/lib/glossary.test.ts
git commit -m "feat(onboarding): pures Glossar (Begriff→Erklärung) + Lookup"
```

---

### Task 2: InfoTip (Erklär-Tooltip)

**Files:**
- Create: `frontend/src/components/InfoTip.tsx`
- Test: `frontend/src/components/InfoTip.test.tsx`

**Interfaces:**
- Consumes: `glossaryLookup` (Task 1)
- Produces: `<InfoTip term={string} text?={string} />` — rendert nichts, wenn keine Erklärung existiert.

- [ ] **Step 1: Failing test** — `frontend/src/components/InfoTip.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { InfoTip } from "./InfoTip";

describe("InfoTip", () => {
  it("zeigt einen beschrifteten Trigger + die Erklärung aus dem Glossar", () => {
    render(<InfoTip term="Top-Down" />);
    expect(screen.getByRole("button", { name: /Erklärung: Top-Down/i })).toBeInTheDocument();
    expect(screen.getByRole("tooltip")).toHaveTextContent(/oben/i);
  });
  it("erlaubt einen expliziten Erklärtext (überschreibt das Glossar)", () => {
    render(<InfoTip term="X" text="Eigener Text" />);
    expect(screen.getByRole("tooltip")).toHaveTextContent("Eigener Text");
  });
  it("rendert nichts, wenn keine Erklärung vorhanden ist", () => {
    const { container } = render(<InfoTip term="Unbekannt" />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run → FAIL** — `npx vitest run src/components/InfoTip.test.tsx`

- [ ] **Step 3: Implement** — `frontend/src/components/InfoTip.tsx`

```tsx
// Kleiner "?"-Hinweis: erklärt einen Fachbegriff kurz auf Deutsch. Die Erklärung
// liegt immer im DOM (per Tastatur/Hover sichtbar) — barrierearm via role="tooltip".
import { glossaryLookup } from "../lib/glossary";

export function InfoTip({ term, text }: { term: string; text?: string }) {
  const explanation = text ?? glossaryLookup(term);
  if (!explanation) return null;
  return (
    <span className="group relative inline-flex align-middle">
      <button
        type="button"
        aria-label={`Erklärung: ${term}`}
        className="grid h-4 w-4 place-items-center rounded-full border border-slate-300 text-[10px] leading-none text-slate-500 hover:bg-slate-100 focus:outline-none focus-visible:ring dark:border-slate-600"
      >
        ?
      </button>
      <span
        role="tooltip"
        className="invisible absolute left-1/2 top-5 z-10 w-56 -translate-x-1/2 rounded bg-slate-900 px-2 py-1 text-xs text-white shadow group-hover:visible group-focus-within:visible dark:bg-slate-700"
      >
        {explanation}
      </span>
    </span>
  );
}
```

- [ ] **Step 4: Run → PASS** — `npx vitest run src/components/InfoTip.test.tsx`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/InfoTip.tsx frontend/src/components/InfoTip.test.tsx
git commit -m "feat(onboarding): InfoTip — barrierearmer Fachbegriff-Tooltip"
```

---

### Task 3: SectionCard (Karten-Container)

**Files:**
- Create: `frontend/src/components/SectionCard.tsx`
- Test: `frontend/src/components/SectionCard.test.tsx`

**Interfaces:**
- Produces: `<SectionCard title={string} subtitle?={string}>{children}</SectionCard>`

- [ ] **Step 1: Failing test** — `frontend/src/components/SectionCard.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SectionCard } from "./SectionCard";

describe("SectionCard", () => {
  it("rendert Titel, Untertitel und Inhalt", () => {
    render(<SectionCard title="Makro" subtitle="Großwetterlage"><p>Inhalt</p></SectionCard>);
    expect(screen.getByRole("heading", { name: "Makro" })).toBeInTheDocument();
    expect(screen.getByText("Großwetterlage")).toBeInTheDocument();
    expect(screen.getByText("Inhalt")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run → FAIL** — `npx vitest run src/components/SectionCard.test.tsx`

- [ ] **Step 3: Implement** — `frontend/src/components/SectionCard.tsx`

```tsx
// Einheitlicher Karten-Container (die "ausgewogene" Designsprache an einem Ort).
import type { ReactNode } from "react";

export function SectionCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <h3 className="text-base font-semibold">{title}</h3>
      {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}
```

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SectionCard.tsx frontend/src/components/SectionCard.test.tsx
git commit -m "feat(onboarding): SectionCard — einheitlicher Karten-Container"
```

---

### Task 4: MetricRow + MetricCard (Kennzahl-Bausteine, Fundament für B)

**Files:**
- Create: `frontend/src/components/MetricRow.tsx`
- Create: `frontend/src/components/MetricCard.tsx`
- Test: `frontend/src/components/MetricRow.test.tsx`
- Test: `frontend/src/components/MetricCard.test.tsx`

**Interfaces:**
- Consumes: `<InfoTip />` (Task 2)
- Produces:
  - `<MetricRow label={string} value={string|number|null} unit?={string} term?={string} />`
  - `<MetricCard label={string} value={string|number|null} unit?={string} term?={string} detail?={ReactNode} />`

- [ ] **Step 1: Failing test** — `frontend/src/components/MetricRow.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricRow } from "./MetricRow";

describe("MetricRow", () => {
  it("zeigt Label, Wert und Einheit", () => {
    render(<MetricRow label="KGV" value={30.5} unit="x" />);
    expect(screen.getByText("KGV")).toBeInTheDocument();
    expect(screen.getByText("30.5 x")).toBeInTheDocument();
  });
  it("zeigt 'n.v.' statt eines Wertes, wenn value null ist (UNAVAILABLE ≠ 0)", () => {
    render(<MetricRow label="Earnings-Trend" value={null} />);
    expect(screen.getByText("n.v.")).toBeInTheDocument();
  });
  it("bindet einen InfoTip ein, wenn ein Begriff gesetzt ist", () => {
    render(<MetricRow label="Exposure" value={120} unit="%" term="Exposure" />);
    expect(screen.getByRole("button", { name: /Erklärung: Exposure/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run → FAIL** — `npx vitest run src/components/MetricRow.test.tsx`

- [ ] **Step 3: Implement** — `frontend/src/components/MetricRow.tsx`

```tsx
// Kompakte Kennzahl-Zeile: Label (+ optionalem Erklär-Tooltip) links, Wert rechts.
// null-Wert => "n.v." (UNAVAILABLE ≠ 0).
import { InfoTip } from "./InfoTip";

export function MetricRow({
  label, value, unit, term,
}: { label: string; value: string | number | null; unit?: string; term?: string }) {
  const missing = value === null || value === undefined;
  const display = missing ? "n.v." : `${value}${unit ? ` ${unit}` : ""}`;
  return (
    <div className="flex items-center justify-between border-b border-slate-100 py-1.5 text-sm last:border-0 dark:border-slate-700/50">
      <span className="flex items-center gap-1 text-slate-600 dark:text-slate-300">
        {label}
        {term && <InfoTip term={term} />}
      </span>
      <span className={missing ? "text-slate-400" : "font-medium"}>{display}</span>
    </div>
  );
}
```

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Failing test** — `frontend/src/components/MetricCard.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MetricCard } from "./MetricCard";

describe("MetricCard", () => {
  it("zeigt Label und Wert", () => {
    render(<MetricCard label="Altman-Z" value={6.1} />);
    expect(screen.getByText("Altman-Z")).toBeInTheDocument();
    expect(screen.getByText("6.1")).toBeInTheDocument();
  });
  it("klappt einen Detailbereich auf Klick auf", async () => {
    render(<MetricCard label="Altman-Z" value={6.1} detail={<p>Bonität sehr gut</p>} />);
    expect(screen.queryByText("Bonität sehr gut")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Details/i }));
    expect(screen.getByText("Bonität sehr gut")).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Run → FAIL** — `npx vitest run src/components/MetricCard.test.tsx`

- [ ] **Step 7: Implement** — `frontend/src/components/MetricCard.tsx`

```tsx
// Umrahmte Einzel-Kennzahl mit optional aufklappbarem Detail ("ausgewogenes" Design:
// Übersicht zuerst, Details auf Klick). null-Wert => "n.v.".
import { useState, type ReactNode } from "react";
import { InfoTip } from "./InfoTip";

export function MetricCard({
  label, value, unit, term, detail,
}: { label: string; value: string | number | null; unit?: string; term?: string; detail?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const missing = value === null || value === undefined;
  const display = missing ? "n.v." : `${value}${unit ? ` ${unit}` : ""}`;
  return (
    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
      <div className="flex items-center gap-1 text-xs text-slate-500">
        {label}
        {term && <InfoTip term={term} />}
      </div>
      <div className={`mt-1 text-lg ${missing ? "text-slate-400" : "font-semibold"}`}>{display}</div>
      {detail && (
        <>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className="mt-1 text-xs text-blue-600 hover:underline dark:text-blue-400"
          >
            {open ? "Details ausblenden" : "Details"}
          </button>
          {open && <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">{detail}</div>}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 8: Run → PASS** — `npx vitest run src/components/MetricCard.test.tsx`

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/MetricRow.tsx frontend/src/components/MetricRow.test.tsx frontend/src/components/MetricCard.tsx frontend/src/components/MetricCard.test.tsx
git commit -m "feat(onboarding): MetricRow + MetricCard (Kennzahl-Bausteine, n.v.-fest)"
```

---

### Task 5: useOnboarding (gesehen-Flag)

**Files:**
- Create: `frontend/src/shell/useOnboarding.ts`
- Test: `frontend/src/shell/useOnboarding.test.tsx`

**Interfaces:**
- Produces: `useOnboarding(): { seen: boolean; markSeen: () => void }` — Flag `localStorage["aaia_onboarding_seen"]`.

- [ ] **Step 1: Failing test** — `frontend/src/shell/useOnboarding.test.tsx`

```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOnboarding } from "./useOnboarding";

beforeEach(() => localStorage.clear());

describe("useOnboarding", () => {
  it("ist ohne Flag noch nicht gesehen", () => {
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.seen).toBe(false);
  });
  it("markSeen setzt das Flag dauerhaft", () => {
    const { result } = renderHook(() => useOnboarding());
    act(() => result.current.markSeen());
    expect(result.current.seen).toBe(true);
    expect(localStorage.getItem("aaia_onboarding_seen")).toBe("1");
  });
  it("liest ein bereits gesetztes Flag", () => {
    localStorage.setItem("aaia_onboarding_seen", "1");
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.seen).toBe(true);
  });
});
```

- [ ] **Step 2: Run → FAIL** — `npx vitest run src/shell/useOnboarding.test.tsx`

- [ ] **Step 3: Implement** — `frontend/src/shell/useOnboarding.ts`

```ts
// "Willkommen schon gesehen?"-Flag, persistiert in localStorage (Muster wie useAuth/useTheme).
import { useCallback, useState } from "react";

const KEY = "aaia_onboarding_seen";

export function useOnboarding() {
  const [seen, setSeen] = useState<boolean>(() => {
    try { return localStorage.getItem(KEY) === "1"; } catch { return false; }
  });
  const markSeen = useCallback(() => {
    try { localStorage.setItem(KEY, "1"); } catch { /* localStorage nicht verfügbar -> ignorieren */ }
    setSeen(true);
  }, []);
  return { seen, markSeen };
}
```

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shell/useOnboarding.ts frontend/src/shell/useOnboarding.test.tsx
git commit -m "feat(onboarding): useOnboarding — gesehen-Flag (localStorage)"
```

---

### Task 6: welcomeContent (Bereichs-Texte, pure Daten)

**Files:**
- Create: `frontend/src/data/welcomeContent.ts`
- Test: `frontend/src/data/welcomeContent.test.ts`

**Interfaces:**
- Produces: `AREAS: AreaInfo[]` mit `AreaInfo = { to: string; icon: string; name: string; question: string; howto: string }`.

- [ ] **Step 1: Failing test** — `frontend/src/data/welcomeContent.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { AREAS } from "./welcomeContent";

describe("welcomeContent.AREAS", () => {
  it("deckt genau die fünf Hauptbereiche mit korrekten Routen ab", () => {
    expect(AREAS.map((a) => a.to)).toEqual([
      "/cockpit", "/deep-dive", "/portfolio", "/inbox", "/backtester",
    ]);
  });
  it("jeder Bereich hat eine Leitfrage und einen Bedienhinweis", () => {
    for (const a of AREAS) {
      expect(a.question.length).toBeGreaterThan(0);
      expect(a.howto.length).toBeGreaterThan(0);
      expect(a.name.length).toBeGreaterThan(0);
    }
  });
});
```

- [ ] **Step 2: Run → FAIL** — `npx vitest run src/data/welcomeContent.test.ts`

- [ ] **Step 3: Implement** — `frontend/src/data/welcomeContent.ts`

```ts
// Eine Quelle für die Bereichs-Beschreibungen der Willkommen-Seite (Reihenfolge wie die Sidebar).
export interface AreaInfo {
  to: string;
  icon: string;
  name: string;
  question: string; // "Welche Frage beantwortet dieser Bereich?"
  howto: string;    // 1 Satz Bedienung
}

export const AREAS: AreaInfo[] = [
  { to: "/cockpit", icon: "▣", name: "Cockpit",
    question: "Wie ist die Großwetterlage am Markt?",
    howto: "Regime-Ampel + Domänen-Kacheln; ein Klick öffnet die jeweilige Detailseite." },
  { to: "/deep-dive", icon: "◆", name: "Deep-Dive",
    question: "Lohnt sich dieser eine Titel?",
    howto: "Oben einen Ticker suchen (z. B. AAPL) — Bewertung, Qualität und Urteil im Detail." },
  { to: "/portfolio", icon: "⬚", name: "Portfolio",
    question: "Wie steht mein Gesamtbestand da?",
    howto: "Exposure, Klumpenrisiken und Konflikte deiner Positionen auf einen Blick." },
  { to: "/inbox", icon: "✉", name: "Inbox",
    question: "Wo widerspricht ein neues Urteil meiner Position?",
    howto: "Konflikte mit beratendem Vorschlag — rein zur Notiz, ohne automatische Ausführung." },
  { to: "/backtester", icon: "↺", name: "Backtester",
    question: "Hätten die früheren Einschätzungen Geld gebracht?",
    howto: "Trefferquoten je Analyse-Bereich, rückblickend ausgewertet." },
];
```

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/welcomeContent.ts frontend/src/data/welcomeContent.test.ts
git commit -m "feat(onboarding): welcomeContent — Bereichs-Texte (eine Quelle)"
```

---

### Task 7: WelcomePage

**Files:**
- Create: `frontend/src/pages/WelcomePage.tsx`
- Test: `frontend/src/pages/WelcomePage.test.tsx`

**Interfaces:**
- Consumes: `AREAS` (Task 6), `SectionCard` (Task 3), `InfoTip` (Task 2), `useOnboarding` (Task 5), react-router (`Link`, `useNavigate`).
- Produces: `<WelcomePage />` — gerendert unter der AppShell-Route `/willkommen`.

- [ ] **Step 1: Failing test** — `frontend/src/pages/WelcomePage.test.tsx`

```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { WelcomePage } from "./WelcomePage";

function renderWelcome() {
  return render(
    <MemoryRouter initialEntries={["/willkommen"]}>
      <Routes>
        <Route path="/willkommen" element={<WelcomePage />} />
        <Route path="/cockpit" element={<h1>Cockpit-Ziel</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => localStorage.clear());

describe("WelcomePage", () => {
  it("erklärt jeden der fünf Bereiche mit Link", () => {
    renderWelcome();
    for (const [name, to] of [
      ["Cockpit", "/cockpit"], ["Deep-Dive", "/deep-dive"], ["Portfolio", "/portfolio"],
      ["Inbox", "/inbox"], ["Backtester", "/backtester"],
    ] as const) {
      const link = screen.getByRole("link", { name: new RegExp(name, "i") });
      expect(link).toHaveAttribute("href", to);
    }
  });
  it("setzt das gesehen-Flag und navigiert ins Cockpit beim 'los geht's'-Knopf", async () => {
    renderWelcome();
    await userEvent.click(screen.getByRole("button", { name: /los geht's/i }));
    expect(localStorage.getItem("aaia_onboarding_seen")).toBe("1");
    expect(screen.getByRole("heading", { name: "Cockpit-Ziel" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run → FAIL** — `npx vitest run src/pages/WelcomePage.test.tsx`

- [ ] **Step 3: Implement** — `frontend/src/pages/WelcomePage.tsx`

```tsx
// Willkommen-Seite (Teil-Projekt A): erklärt AAIA + jeden Bereich, "wo was zu finden ist".
// Reiner Inhalt, kein Backend. "Los geht's" merkt den Besuch und führt ins Cockpit.
import { Link, useNavigate } from "react-router-dom";
import { AREAS } from "../data/welcomeContent";
import { SectionCard } from "../components/SectionCard";
import { InfoTip } from "../components/InfoTip";
import { useOnboarding } from "../shell/useOnboarding";

export function WelcomePage() {
  const navigate = useNavigate();
  const { markSeen } = useOnboarding();

  function start() {
    markSeen();
    navigate("/cockpit");
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-xl font-bold">Willkommen bei AAIA</h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-300">
          AAIA ist dein KI-gestützter Investment-Analyse-Assistent: Er bewertet die Marktlage
          und einzelne Titel und führt beides zu einem nachvollziehbaren Urteil zusammen.
        </p>
      </div>

      <SectionCard title="So funktioniert die Analyse" subtitle="In drei Schritten">
        <ol className="grid gap-3 sm:grid-cols-3">
          <li className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
            <span className="font-semibold">1. Top-Down <InfoTip term="Top-Down" /></span>
            <p className="mt-1 text-slate-600 dark:text-slate-300">Das große Bild: Konjunktur, Zinsen, Inflation — das <InfoTip term="Regime" />.</p>
          </li>
          <li className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
            <span className="font-semibold">2. Bottom-Up <InfoTip term="Bottom-Up" /></span>
            <p className="mt-1 text-slate-600 dark:text-slate-300">Die Tiefenprüfung eines einzelnen Titels.</p>
          </li>
          <li className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
            <span className="font-semibold">3. Urteil <InfoTip term="Urteil" /></span>
            <p className="mt-1 text-slate-600 dark:text-slate-300">Beides zusammengeführt zu einer Einschätzung.</p>
          </li>
        </ol>
      </SectionCard>

      <SectionCard title="Wo finde ich was?" subtitle="Die fünf Bereiche">
        <div className="grid gap-3 sm:grid-cols-2">
          {AREAS.map((a) => (
            <Link
              key={a.to}
              to={a.to}
              className="block rounded-lg border border-slate-200 p-3 transition-colors hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              <div className="flex items-center gap-2 font-semibold">
                <span aria-hidden>{a.icon}</span>{a.name}
              </div>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{a.question}</p>
              <p className="mt-0.5 text-xs text-slate-500">{a.howto}</p>
            </Link>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Hinweis zu den Daten">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Manche Bereiche zeigen vorerst <strong>Demo-Daten <InfoTip term="Demo-Daten" /></strong> (Beispielwerte),
          bis die echte Quelle angebunden ist — erkennbar am „Demo-Daten"-Etikett oben in der jeweiligen Ansicht.
        </p>
      </SectionCard>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={start}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 dark:bg-slate-200 dark:text-slate-900"
        >
          Verstanden, los geht's →
        </button>
        <span className="text-xs text-slate-400">Diese Seite findest du jederzeit oben über „?".</span>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Run → PASS** — `npx vitest run src/pages/WelcomePage.test.tsx`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/WelcomePage.tsx frontend/src/pages/WelcomePage.test.tsx
git commit -m "feat(onboarding): WelcomePage — erklärt AAIA + alle Bereiche"
```

---

### Task 8: Routing onboarding-bewusst + Topbar-„?" + Sidebar-Eintrag

**Files:**
- Modify: `frontend/src/routes.tsx` (Index-Redirect + `/willkommen`-Route)
- Modify: `frontend/src/shell/Topbar.tsx` (Hilfe-Link)
- Modify: `frontend/src/shell/Sidebar.tsx` (Willkommen-Eintrag)
- Modify: `frontend/src/routes.test.tsx` (bestehenden „/ → Cockpit"-Test an Flag anpassen + neue Onboarding-Tests)

**Interfaces:**
- Consumes: `WelcomePage` (Task 7), `useOnboarding` (Task 5).

- [ ] **Step 1: Failing test** — in `frontend/src/routes.test.tsx` ergänzen (oben `beforeEach(() => localStorage.clear())` sicherstellen; falls schon ein `vi.mock("./hooks/useCockpit", …)` existiert, bleibt es):

```tsx
  it("leitet / beim ERSTEN Besuch (kein Flag) auf die Willkommen-Seite", async () => {
    localStorage.clear();
    renderAt("/");
    await waitFor(() => expect(screen.getByRole("heading", { name: /Willkommen bei AAIA/i })).toBeInTheDocument());
  });

  it("die Topbar bietet einen Hilfe-Link zur Willkommen-Seite", async () => {
    localStorage.setItem("aaia_onboarding_seen", "1");
    renderAt("/cockpit");
    expect(screen.getByRole("link", { name: /Hilfe|Willkommen/i })).toHaveAttribute("href", "/willkommen");
  });
```

- [ ] **Step 2: Bestehenden „/ → Cockpit"-Test anpassen** — der vorhandene Test `it("leitet / auf das Cockpit", …)` setzt jetzt zuerst das Flag (sonst landet er auf Willkommen):

```tsx
  it("leitet / auf das Cockpit (wenn Onboarding gesehen)", () => {
    localStorage.setItem("aaia_onboarding_seen", "1");
    renderAt("/");
    expect(screen.getByRole("heading", { name: /Cockpit — Übersicht/i })).toBeInTheDocument();
  });
```

- [ ] **Step 3: Run → FAIL** — `npx vitest run src/routes.test.tsx` (Willkommen-Route/Redirect fehlt).

- [ ] **Step 4: Implement Routing** — `frontend/src/routes.tsx`: Importe ergänzen, Index-Redirect onboarding-bewusst machen, `/willkommen`-Route einhängen.

```tsx
// oben bei den Imports:
import { WelcomePage } from "./pages/WelcomePage";
import { useOnboarding } from "./shell/useOnboarding";

// kleine Komponente: erster Besuch -> Willkommen, sonst Cockpit.
function IndexRedirect() {
  const { seen } = useOnboarding();
  return <Navigate to={seen ? "/cockpit" : "/willkommen"} replace />;
}
```

Im `<Routes>`-Block die index-Zeile ersetzen und die Route ergänzen:

```tsx
        <Route index element={<IndexRedirect />} />
        <Route path="/willkommen" element={<WelcomePage />} />
        <Route path="/cockpit" element={<CockpitPage deps={deps} />} />
```

- [ ] **Step 5: Implement Topbar-Hilfe** — `frontend/src/shell/Topbar.tsx`: vor dem Inbox-`NavLink` einen Hilfe-Link einfügen:

```tsx
        <NavLink to="/willkommen" className="text-sm" aria-label="Hilfe / Willkommen" title="Willkommen & Hilfe">?</NavLink>
```

- [ ] **Step 6: Implement Sidebar-Eintrag** — `frontend/src/shell/Sidebar.tsx`: dem `ITEMS`-Array einen Eintrag voranstellen:

```tsx
  { to: "/willkommen", label: "Willkommen", icon: "✺" },
```

- [ ] **Step 7: Run → PASS** — `npx vitest run src/routes.test.tsx`

- [ ] **Step 8: Volltests + Build (Pflicht)**

```bash
npx vitest run
npm run build
```
Expected: alle Tests grün, `tsc`+vite ohne Fehler.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/routes.tsx frontend/src/routes.test.tsx frontend/src/shell/Topbar.tsx frontend/src/shell/Sidebar.tsx
git commit -m "feat(onboarding): onboarding-bewusstes Routing + Hilfe-Link + Sidebar-Eintrag"
```

---

## Self-Review

**Spec-Abdeckung:**
- §3 Erst-Besuch-Routing + dauerhafte Erreichbarkeit → Task 8 (IndexRedirect, Topbar „?", Sidebar). ✓
- §3 Flag-Hook → Task 5. ✓
- §4 Welcome-Inhalt (Hero, 3 Schritte, 5 Bereichs-Karten, Demo-Hinweis, „los geht's") → Task 7 (+ Task 6 Daten). ✓
- §5 Fundament (InfoTip, glossary, SectionCard, MetricCard/Row) → Tasks 1–4. ✓
- §7 Tests inkl. „n.v.", Routing, alle 5 Karten → in den jeweiligen Tasks. ✓

**Platzhalter-Scan:** keine TBD/TODO; jeder Code-Schritt enthält vollständigen Code. ✓

**Typ-Konsistenz:** `glossaryLookup`, `AreaInfo/AREAS`, `useOnboarding(): {seen, markSeen}`, Props von `InfoTip/MetricRow/MetricCard/SectionCard` über Tasks hinweg identisch verwendet. ✓

**Hinweis Reihenfolge:** Tasks 1→8 in Reihenfolge ausführen (spätere konsumieren frühere). MetricCard nutzt `@testing-library/user-event` (bereits Dev-Dependency, in anderen Tests genutzt).
