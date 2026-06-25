# Frontend-Ausbau — Teil-Projekt A: Onboarding + Erklär-/Metrik-Fundament

> **Design-Dokument** · 2026-06-25 · Branch `feat/frontend-onboarding`
> Dauerhaftes Design (das „Warum"). **Laufender Status** (Reihenfolge, PR-Protokoll, Folge-Aufgaben) steht **ausschließlich** im Logbuch `docs/open_todos.md` (AGENTS.md §5).

## 1. Kontext & Ziel

Das Frontend (React 19 + TS + Vite + Tailwind, Tausch-Naht zu Demo/Echt) deckt funktional alle 36 User Stories ab, ist aber für einen **neuen Nutzer nicht selbsterklärend**: Es gibt keine Begrüßung, keine Erklärung, „wo was zu finden ist", und die reichen Kennzahlen, die die Agenten berechnen, sind im UI noch dünn dargestellt.

**Übergeordnetes Ziel (Nutzer-Vorgabe):** Das Tool viel **intuitiver** und **detaillierter** machen — *„ein neuer Nutzer muss direkt verstehen, wie das Tool funktioniert"* — und die **Kennzahlen/Metriken**, die die Agenten zur Analyse nutzen, sichtbar machen (fehlende Daten bleiben vorerst Demo). Inspiration: Trading-Plattformen (Swissquote o. ä.), übernommen wird das **Sinnvolle**.

Der Gesamtauftrag zerfällt in **drei Teil-Projekte** (mit dem Nutzer am 2026-06-25 bestätigt):

| # | Teil-Projekt | Eigene Spec |
|---|---|---|
| **A** | **Onboarding + gemeinsames Erklär-/Metrik-Fundament** | **dieses Dokument** |
| **B** | Kennzahlen sichtbar machen (Deep-Dive zuerst, dann Cockpit-Drilldowns) | Folge-Spec |
| **C** | UX-Politur / Trading-Plattform-Feel | Folge-Spec (querschnitt, teils in B eingewoben) |

Dieses Dokument spezifiziert **nur Teil-Projekt A**. A liefert bewusst auch den **wiederverwendbaren Baukasten** (Erklär-Tooltip, Metrik-Karte/-Zeile, Karten-Container, Glossar), auf dem B und C aufbauen.

## 2. Designentscheidungen (mit Nutzer bestätigt, 2026-06-25)

- **Onboarding-Form:** eigene **Willkommen-Seite** (`/willkommen`) als Erst-Besuch-Landing + dauerhaft über ein **„?"** erreichbar. (Nicht: Overlay, nicht: interaktive Tour.)
- **Designsprache:** **ausgewogen** — klare Karten, Details auf Klick aufklappbar, Fachbegriffe per Tooltip. (Nicht: dichtes Profi-Terminal, nicht: minimal.)
- **Reihenfolge danach:** Teil-Projekt B startet mit dem **Deep-Dive** (kennzahlreichste Ansicht).

## 3. Verhalten & Datenfluss

Reiner Frontend-Inhalt — **kein Backend-Call**, keine Tausch-Naht nötig.

- **Erst-Besuch-Routing:** Ist `localStorage["aaia_onboarding_seen"]` nicht gesetzt, leitet die Index-Route (`/`) auf `/willkommen` statt auf `/cockpit`. Nach „Verstanden, los geht's" wird das Flag gesetzt und auf `/cockpit` navigiert. Ist das Flag gesetzt, verhält sich `/` wie bisher (→ `/cockpit`).
- **Dauerhafte Erreichbarkeit:** Ein **„?"-Knopf in der Topbar** und ein **Sidebar-Eintrag „Willkommen"** verlinken jederzeit auf `/willkommen` (dort ist der Inhalt rein informativ; das „gesehen"-Flag wird durch erneutes Ansehen nicht zurückgesetzt).
- **Flag-Verwaltung:** kleiner Hook `useOnboarding` (Muster wie `useTheme`/`useAuth`): `{ seen: boolean, markSeen(): void }`, persistiert in `localStorage`, defensiv (try/catch).

## 4. Inhalt der Willkommen-Seite

Eine Quelle für die Bereichstexte: `data/welcomeContent.ts` (kein Hardcode verstreut).

1. **Hero:** *Was ist AAIA?* — 1–2 einfache Sätze (vollautomatischer, KI-gestützter Investment-Analyse-Assistent; bewertet Makro-Lage + Einzeltitel und bildet daraus ein Urteil).
2. **So funktioniert die Analyse** — drei verständliche Schritte: **Top-Down** (Makro-Umfeld/Regime) → **Bottom-Up** (Einzeltitel-Tiefenanalyse) → **Urteil** (Zusammenführung). Fachbegriffe per `InfoTip`.
3. **Bereichs-Karten** (eine je Navigationsbereich): Icon · Name · **„Welche Frage beantwortet dieser Bereich?"** · 1 Satz Bedienung · Link „→ öffnen". Bereiche: Cockpit, Deep-Dive, Portfolio, Inbox, Backtester. (Quelle = `welcomeContent.ts`, gespiegelt zur Sidebar-Reihenfolge.)
4. **Demo-Daten erklärt:** kurzer Hinweis, was das „Demo-Daten"-Etikett bedeutet (manche Bereiche zeigen Beispieldaten, bis die echte Quelle angebunden ist) — Ehrlichkeit/Vertrauen.
5. **Erste Schritte** — 3 konkrete Schritte (z. B. „1. Cockpit ansehen — wie ist die Großwetterlage? 2. Im Deep-Dive einen Titel öffnen. 3. Portfolio/Inbox auf Konflikte prüfen.").
6. **„Verstanden, los geht's"-Knopf** → `markSeen()` + Navigation ins Cockpit.

## 5. Gemeinsames Fundament (Baukasten für B & C)

- **`components/InfoTip.tsx`** — kleines „?"-Symbol; bei Hover/Fokus erscheint eine **kurze deutsche Erklärung** eines Begriffs. Barrierearm (`aria-label`, per Tastatur fokussierbar). Text kommt aus dem Glossar oder als Prop.
- **`lib/glossary.ts`** — **pure** Map `Begriff → kurze Erklärung` + Lookup `glossaryLookup(term): string | null`. Eine Quelle für Tooltips **und** eine spätere Glossar-Seite (Teil-Projekt B/C). Start-Inhalt: die auf der Welcome-Seite verwendeten Begriffe (Top-Down, Bottom-Up, Regime, Demo-Daten …).
- **`components/SectionCard.tsx`** — einheitlicher Karten-Container (Titel + optionaler Untertitel + Inhalt), die „ausgewogene" Designsprache an einem Ort.
- **`components/MetricCard.tsx`** / **`components/MetricRow.tsx`** — Grundbaustein für Teil-Projekt B: Label · Wert (+ Einheit) · optionaler `InfoTip` · optional **aufklappbarer** Detailbereich. `MetricRow` = kompakte Zeile (Label links, Wert rechts, „?"); `MetricCard` = umrahmte Einzel-Kennzahl mit optionalem Aufklapp-Detail. **UNAVAILABLE-fest:** Wert `null` → „n.v." (nicht „0"), passend zur Projekt-Regel UNAVAILABLE ≠ 0.

## 6. Komponenten & Isolation

| Datei | Verantwortung | Hängt ab von |
|---|---|---|
| `pages/WelcomePage.tsx` | Komposition der Welcome-Seite | `welcomeContent`, `SectionCard`, `InfoTip`, `useOnboarding`, Router |
| `data/welcomeContent.ts` | Bereichs-Texte (eine Quelle) | — (pure Daten) |
| `lib/glossary.ts` | Begriff→Erklärung + Lookup | — (pure) |
| `components/InfoTip.tsx` | Erklär-Tooltip | `glossary` (optional) |
| `components/SectionCard.tsx` | Karten-Container | — |
| `components/MetricCard.tsx`, `MetricRow.tsx` | Kennzahl-Darstellung (Fundament B) | `InfoTip` |
| `shell/useOnboarding.ts` | „gesehen"-Flag (localStorage) | — |
| `routes.tsx` | onboarding-bewusster Index-Redirect + `/willkommen`-Route | `useOnboarding` |
| `shell/Topbar.tsx` | „?"-Hilfe-Link | Router |
| `shell/Sidebar.tsx` | „Willkommen"-Eintrag | Router |

Jede Einheit hat genau einen Zweck, klare Schnittstelle, isoliert testbar.

## 7. Tests (TDD — verpflichtend, Vitest + RTL)

- **`useOnboarding`**: Default `seen=false` ohne Flag; `markSeen()` setzt Flag → `seen=true`; liest bestehendes Flag.
- **`glossary`**: `glossaryLookup` liefert Erklärung für bekannten Begriff, `null` für unbekannten (Grenzfall).
- **`InfoTip`**: rendert Trigger mit `aria-label`; Erklärung im DOM/zugänglich.
- **`MetricRow`/`MetricCard`**: rendert Label + Wert + Einheit; `null`-Wert → „n.v."; mit `InfoTip` wenn Begriff gesetzt; `MetricCard` klappt Detail auf/zu.
- **`WelcomePage`**: rendert **alle fünf** Bereichs-Karten mit korrektem Link-Ziel (`/cockpit`, `/deep-dive`, `/portfolio`, `/inbox`, `/backtester`); „Verstanden"-Knopf ruft `markSeen` + navigiert.
- **Routing (`routes.test`)**: ohne Flag landet `/` auf `/willkommen`; mit Flag auf `/cockpit`; „?"/Sidebar-Link führt zu `/willkommen`.
- **Build-Pflicht:** nach Import-Änderungen `npm run build` (tsc) laufen lassen — `vitest` typecheckt ungenutzte Importe nicht (bekannte Falle).

## 8. Nicht-Ziele (bewusst ausgeklammert → Folge-Specs)

- **Teil-Projekt B** (eigene Spec): die eigentliche Kennzahlen-Tiefe je Bereich (Deep-Dive zuerst: alle Fundamental-/Bewertungs-/Qualitäts-Metriken; danach Cockpit-Drilldowns: Inflation Core/PPI/Realzins, Geldmenge, Zinsen, GDP, Arbeitsmarkt, Kredit, Sektoren …), inkl. Glossar-Seite. Demo-Daten, wo Backend/Serializer noch nicht liefert (Tausch-Naht).
- **Teil-Projekt C** (eigene Spec): tiefergehende UX-Politur (Sparklines, globale Suche/Watchlist-Gefühl, Tabellen-Interaktionen), aufbauend auf dem Baukasten aus A.
- Kein Backend-/Serializer-Change in A. Keine neue Datenquelle.

## 9. Risiken / offene Punkte

- **Flag-Verhalten bei mehreren Geräten/Browsern:** localStorage ist pro Browser — akzeptabel (Demo/Einzelnutzer), wie beim Token.
- **Bestehende Routing-Tests:** der Index-Redirect ändert sich (→ onboarding-bewusst); bestehende Tests, die `/` → Cockpit erwarten, müssen ein gesetztes Flag annehmen oder werden angepasst (im Plan berücksichtigt).
