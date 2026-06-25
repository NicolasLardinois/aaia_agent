# Frontend-Ausbau — Teil-Projekt B (Slice B1): Deep-Dive-Kennzahlen (Aktien)

> **Design-Dokument** · 2026-06-25 · Branch `feat/frontend-deepdive-metrics` (gestapelt auf `feat/frontend-onboarding`)
> Laufender Status steht **ausschließlich** im Logbuch `docs/open_todos.md` (AGENTS.md §5). Baut auf Teil-Projekt A auf (Spec `2026-06-25-frontend-onboarding-fundament-design.md`).

## 1. Kontext & Ziel

Teil-Projekt B („Kennzahlen sichtbar machen") startet — wie mit dem Nutzer am 2026-06-25 bestätigt — **mit dem Deep-Dive (Aktien)**. Heute zeigt der Equity-Deep-Dive nur ~10 Kennzahlen in schlichten Zeilen (`EquityTabs.tsx`). Das Backend-Modell `FundamentalsSnapshot` (`core/domain/models.py`) berechnet aber **15+** Kennzahlen, die im Frontend fehlen: Forward-KGV, Shiller-CAPE, PEG, EV/Umsatz, KBV, KUV, P/FCF, Dividendenrendite, WACC, Umsatz-CAGR (3J), Verschuldungsgrad.

**Ziel:** Den **vollen Aktien-Kennzahlen-Katalog** im Deep-Dive zeigen — übersichtlich gruppiert, mit kurzer **Erklärung je Kennzahl** (InfoTip aus A), fehlende Werte ehrlich als „n.v." (UNAVAILABLE ≠ 0). Fehlende Daten bleiben **Demo** (Tausch-Naht unverändert).

## 2. Scope (bewusst eng — eine reviewbare Slice)

- **Nur der Aktien-Deep-Dive** (`equity`-Block). Bond/Index/Rohstoff/Futures-Tabs folgen als eigene Slices (B2…).
- **Kein Backend-/Serializer-Change.** Demo-Fixtures werden erweitert; die echte Anbindung (`fetchDeepDive`) bleibt Folge-Aufgabe (im Logbuch erfasst).
- Wiederverwendung des A-Baukastens: `MetricRow`, `SectionCard`, `InfoTip`, `lib/glossary`.

## 3. Datenmodell (Frontend-Vertrag)

Neuer optionaler Block am `EquityBlockDTO` (`contract/deepdive.ts`) — **optional**, damit bestehende Nicht-AAPL-Fixtures unberührt bleiben:

```ts
export interface EquityFundamentalsDTO {
  forwardPe: number | null;        // erwartetes KGV auf Basis Gewinnschätzung nächste 12M
  shillerCape: number | null;      // zyklisch bereinigtes KGV (10J inflationsbereinigte Gewinne)
  pegRatio: number | null;         // KGV ÷ Gewinnwachstum (≈1 fair)
  evRevenue: number | null;        // Unternehmenswert / Umsatz
  priceBook: number | null;        // KBV — Kurs / Buchwert je Aktie
  priceSales: number | null;       // KUV — Kurs / Umsatz je Aktie
  priceFcf: number | null;         // Kurs / freier Cashflow
  dividendYieldPct: number | null; // Dividendenrendite in %
  waccPct: number | null;          // gewichtete Kapitalkosten in %
  revenueCagr3yPct: number | null; // Umsatzwachstum p.a. über 3 Jahre, in %
  debtToEquity: number | null;     // Verschuldungsgrad (Fremd-/Eigenkapital)
}
```

`EquityBlockDTO` erhält `fundamentals?: EquityFundamentalsDTO`. Namen spiegeln `FundamentalsSnapshot` (snake→camel), damit der spätere Echt-Anschluss eine reine 1:1-Abbildung ist.

## 4. Demo-Daten

`data/demo/deepdive.ts`: AAPL-Fixture um einen fachlich plausiblen `fundamentals`-Block ergänzen (z. B. `forwardPe 28.2`, `shillerCape 34.0`, `pegRatio 2.4`, `evRevenue 8.1`, `priceBook 46.0`, `priceSales 8.3`, `priceFcf 30.0`, `dividendYieldPct 0.5`, `waccPct 8.4`, `revenueCagr3yPct 8.0`, `debtToEquity 1.5`). Mind. **ein Feld `null`** (z. B. `pegRatio: null`) → demonstriert den „n.v."-Pfad. Vorhandene equity-Fixtures ohne `fundamentals` bleiben gültig (optional).

## 5. UI — Umbau der Equity-Tabs (ausgewogenes Design aus A)

`EquityTabs.tsx` wird auf den A-Baukasten umgestellt (statt schlichter `<div>`-Zeilen):

- **Tab „Bewertung"** (`valuation`): `SectionCard` „Bewertungs-Kennzahlen" mit `MetricRow` je Kennzahl + `InfoTip`: KGV, Forward-KGV, Shiller-CAPE, PEG, EV/EBITDA, EV/Umsatz, KBV, KUV, P/FCF, Dividendenrendite. Darunter unverändert die **Methoden-Bandbreite** (Tabelle + kombinierte Range + Position) — bestehende `lib/valuationRange`-Logik bleibt.
- **Tab „Qualität"** (`quality`): `SectionCard` „Profitabilität & Bilanz" mit `MetricRow`: Bruttomarge, Operative Marge, ROIC, WACC, Umsatzwachstum (3J), Verschuldungsgrad, Altman-Z (mit bestehender `altmanClass`-Einordnung).
- **Tab „Signale"** (`signals`): unverändert (Short-Interest, Insider, Earnings-Trend, Moat) — optional ebenfalls `InfoTip` ergänzen.
- Fehlende `fundamentals` (Block ganz `undefined`, z. B. Alt-Fixture): die neuen Zeilen entfallen, die bestehenden bleiben — kein Crash.
- `null`-Einzelwerte → `MetricRow` zeigt „n.v.".

## 6. Glossar (lib/glossary erweitern)

Einträge für jede neue Kennzahl (kurze, fachlich korrekte deutsche Erklärung mit Einheit), u. a.: KGV, Forward-KGV, Shiller-CAPE, PEG, EV/EBITDA, EV/Umsatz, KBV, KUV, P/FCF, Dividendenrendite, WACC, ROIC, Bruttomarge, Operative Marge, Umsatzwachstum, Verschuldungsgrad, Altman-Z, Short-Interest, Moat. (Etablierte Definitionen, AGENTS.md §3.)

## 7. Komponenten & Isolation

| Datei | Änderung |
|---|---|
| `contract/deepdive.ts` | `EquityFundamentalsDTO` + `equity.fundamentals?` |
| `data/demo/deepdive.ts` | AAPL `fundamentals` (inkl. 1× `null`) |
| `lib/glossary.ts` | neue Kennzahl-Einträge |
| `components/deepdive/tabs/EquityTabs.tsx` | Umbau auf `MetricRow`/`SectionCard`/`InfoTip` + neue Kennzahlen |
| ggf. `components/deepdive/MetricGroup.tsx` | optionaler kleiner Helfer: `SectionCard` + Liste von `MetricRow` (DRY, wenn mehrfach gebraucht) |

## 8. Tests (TDD)

- **Vertrag/Demo**: AAPL-Fixture hat `equity.fundamentals` mit den erwarteten Feldern; mind. ein `null`.
- **glossary**: Lookup liefert Erklärung für jede neue Kennzahl (Stichprobe + Vollständigkeits-Check über eine Liste der Schlüsselbegriffe).
- **EquityTabs (valuation)**: rendert die neuen Bewertungs-Kennzahlen mit Wert + `InfoTip`-Trigger; `null`-Feld → „n.v."; Methoden-Bandbreite weiterhin vorhanden.
- **EquityTabs (quality)**: rendert WACC/Umsatzwachstum/Verschuldungsgrad zusätzlich; Altman-Einordnung unverändert.
- **Robustheit**: equity-Block ohne `fundamentals` → kein Crash, bestehende Zeilen weiter sichtbar.
- **Build-Pflicht** nach Import-Änderungen (`npm run build`).

## 9. Nicht-Ziele / Folge-Slices

- B2+: Bond/Index/Rohstoff/Futures-Tabs analog mit dem Baukasten + Glossar; ggf. eigene **Glossar-Seite**.
- Cockpit-Drilldowns voll (Inflation Core/PPI/Realzins, Geldmenge, Zinsen, GDP, Arbeitsmarkt, Kredit, Sektoren) — nach dem Deep-Dive.
- Echter `fetchDeepDive`-Anschluss (Tausch-Naht) — separater PR, sobald ein Deep-Dive-Backend-Endpunkt steht.
