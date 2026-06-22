# Frontend — Cockpit-Regime-Übersicht (erste Scheibe) — Design

> **Status:** Spezifikation / Design-Entwurf · **Datum:** 2026-06-22
> **Scope:** Die **erste lauffähige Frontend-Scheibe** — die Cockpit-Regime-Übersicht (Landing), live an die bestehende API-Brücke angebunden und auf Render deployt. Zugleich das **Fundament** für alle weiteren Frontend-Scheiben (Projekt-Gerüst, API-/WebSocket-Client, Deploy, Basis-Komponenten).
> **Erdung:** Setzt das **Frontend-Konzept** `docs/superpowers/specs/2026-06-21-frontend-konzept.md` (§4.1 Regime-Übersicht, §5.4 UNAVAILABLE, §6 entschiedene Punkte: React, Desktop-first, WebSocket) um und konsumiert den **API-Brücke-Vertrag** aus `docs/superpowers/specs/2026-06-22-api-bridge-cockpit-design.md` (PR #24, gemergt).
> **Wichtig:** Reines Design-Dokument (*Warum/Wie*). Der **laufende Status** (Roadmap, PR-Protokoll, Folge-Aufgaben) gehört ausschließlich ins Logbuch `docs/open_todos.md` (AGENTS.md §5).

---

## 1. Zusammenfassung & Scope

Das gesamte Frontend (Cockpit, Deep-Dive, Portfolio, Inbox, Backtester) ist zu groß für eine einzige Spec. Es wird in Scheiben gebaut. **Diese Scheibe** ist die kleinste durchgängig lauffähige Einheit, die das vorhandene Backend bereits vollständig bedient:

- **Cockpit-Regime-Übersicht** (§4.1 des Frontend-Konzepts): Regime-Banner, vier Domänen-Kacheln, Daten-Health-Indikator, „Analyse starten"-Steuerung — mit **Live-Fortschritt** während eines Laufs.
- **Fundament für alles Weitere:** React-Projekt im Monorepo, typisierter API-Client, WebSocket-Client, Render-Deploy (zwei Dienste), erste wiederverwendbare Anzeige-Bausteine.

**Bewusst NICHT in dieser Scheibe** (eigene spätere Scheiben, brauchen z. T. erst Backend-Erweiterungen): Domänen-Drill-downs (Zinskurve/Buffett/Big-Mac), Deep-Dive, Portfolio, Inbox, Backtester, Charting-Bibliothek, Auth/Rate-Limiting.

## 2. Architektur & Stack

- **Monorepo:** neuer Ordner `frontend/` im bestehenden `aaia_agent`-Repo. Python-Backend und JS-Frontend bleiben durch den Unterordner sauber getrennt; API-Vertrag und UI entwickeln sich synchron in einem Repo.
- **React + TypeScript:** TypeScript prüft statisch, dass die konsumierten Daten der API-Form entsprechen (fester Vertrag → früh Fehler statt Laufzeit-Überraschung).
- **Vite** als Build-Tool → erzeugt rein statische Dateien (HTML/JS/CSS), die Render als *Static Site* ausliefert.
- **Tailwind CSS** für das Styling der dichten Dashboard-Optik (volle Kontrolle, KI-codegen-freundlich).
- **Vitest + React Testing Library** für Tests; TDD wie im Projekt (AGENTS.md §4).
- **Bewusst weggelassen (YAGNI bei einem Bildschirm):** keine Server-State-/Cache-Bibliothek (z. B. React Query) — ein schlanker eigener Hook genügt; **kein** Charting (Kurven erst mit den Drill-downs); kein globaler State-Store (Redux o. Ä.).

## 3. Datenfluss & Zustände

Drei Endpunkte der API-Brücke (PR #24):
- `GET /api/cockpit` → `200` mit Übersicht-Vertrag **oder** `204` (noch kein Lauf).
- `POST /api/cockpit/run` → `202 { run_id }`, startet Lauf als Hintergrund-Task.
- `WS /ws/cockpit` → Strom von Event-Nachrichten; am Ende ein terminales `CockpitResultReady` mit dem vollen Ergebnis.

**Verhalten:**
1. **Beim Laden:** `GET`. `200` → Übersicht anzeigen. `204` → **Leerzustand** „Noch keine Analyse — jetzt starten".
2. **„Analyse starten":** **Reihenfolge bewusst (1) WebSocket öffnen, dann (2) `POST …/run`.** So gehen keine frühen `*Ready`-Events verloren (adressiert Backend-Folgeaufgabe #3 „frühe Events können verloren gehen"). Während des Laufs aktualisiert der Live-Strom den Fortschritt; das terminale `CockpitResultReady` füllt die Übersicht. `GET` bleibt Rückfall, falls die WS-Verbindung abbricht.
3. **Kein Auto-Start:** Ein Lauf ruft echte externe Quellen (FRED/Yahoo) ab → nur auf bewusste Nutzeraktion (Button), nie automatisch beim Laden.
4. **Fehlerzustände explizit:** Backend nicht erreichbar / WS-Abbruch → sichtbarer Hinweis (kein stiller Leerzustand). WS-Wiederverbindung mit `GET`-Rückfall.

## 4. UI-Aufbau & Komponenten

**Ehrlicher Abgleich mit Wireframe §4.1:** Das Wireframe zeigt 5 gleichartige Kacheln (inkl. „Makro"). Der **echte Datenvertrag** stellt Makro als **Regime-Banner** dar (Makro hat kein einzelnes Signal, sondern *ein Regime* + Konfidenz), darunter die **vier Sub-Domänen** als Kacheln. Daher: **1 Regime-Banner + 4 Kacheln** (statt 5 gleichartiger Kacheln). Der Health-Zähler zählt weiterhin alle 5 (Makro + 4) über `sources_active/total`.

**Bildschirm-Komponenten:**
- **`RegimeBanner`** — Regime-Wort + `ConfidenceBar` (aus `regime_confidence`); markiert „nicht verfügbar", falls `macro_status = "unavailable"`.
- **`DomainTile` ×4** — je Domäne (Rohstoffe, Sentiment, Zinskurve, Sektoren): `SignalBadge` + Status. Bei `status = "unavailable"` → gestreift-graues `UnavailableField`, kein Signal.
- **`DataHealthIndicator`** — „x/5 Quellen aktiv" (aus `sources_active`/`sources_total`); Klick listet die ausgefallenen Domänen.
- **`RunControl`** — „Analyse starten"-Button + Live-Status („läuft … / fertig") aus dem WS-Strom.

**Wiederverwendbare Basis-Bausteine** (Keim der Komponenten-Bibliothek aus Frontend-Konzept §5/§7):
- **`SignalBadge`** — Signal (`"bullish" | "bearish" | "neutral" | null`) → Wort + Farbe (grün/rot/grau-blau) bzw. UNAVAILABLE-Stil.
- **`ConfidenceBar`** — 0–1 als Balken **mit %-Label** (Barrierefreiheit, nicht nur Farbe).
- **`UnavailableField`** — gestreift-graues „nicht verfügbar"-Feld mit Grund-Tooltip.

**UNAVAILABLE-Vertrag (Leitidee §5.4):** Eine ausgefallene Domäne liefert vom Backend `signal = null` (nicht `"neutral"`). Die Kachel zeigt dann das UNAVAILABLE-Feld — **nie** ein grünes/neutrales Signal — und zählt nicht in „aktiv".

## 5. Pure, testbare Anzeige-Logik (TDD zuerst)

Als reine Funktionen gekapselt und **zuerst** getestet (AGENTS.md §4), unabhängig von React:
- `signalToVisual(signal: Signal | null)` → `{ label, colorClass }` bzw. UNAVAILABLE-Stil.
- `formatConfidence(value: number)` → z. B. `"71 %"`.
- `sourcesLabel(active: number, total: number)` → `"4/5 Quellen aktiv"`.
- `isUnavailable(domain)` → `boolean` (Status `"unavailable"` **oder** `signal === null`).
- Grenzfälle: `null`-Signal, Konfidenz 0/1, `sources_active === 0`, `204`-Leerzustand.

## 6. Backend-Vertrag (konsumiert, unverändert)

- **`GET /api/cockpit` `200`:** `{ regime: string, regime_confidence: number, macro_status: "available"|"unavailable", domains: Array<{ key: "commodities"|"sentiment"|"yield_curve"|"sectors", signal: "bullish"|"bearish"|"neutral"|null, status: "available"|"unavailable" }>, sources_active: number, sources_total: number }`. `signal` ist `null`, wenn die Domäne `unavailable` ist.
- **`GET` `204`:** kein Lauf vorhanden → Leerzustand.
- **`POST /api/cockpit/run` `202`:** `{ run_id: string }`.
- **`WS /ws/cockpit`:** Nachrichten `{ type: string, source: string, payload: object, timestamp: string, run_id: string }`. Fortschritts-Events (z. B. `type = "MacroChiefReady"`) während des Laufs; terminal `type = "CockpitResultReady"` mit `payload` = derselbe Übersicht-Vertrag wie `GET 200`.
- **Hinweis (Folge-Aufgabe #4):** `timestamp` ist heute zeitzonenlos (`utcnow` ohne `Z`) — fürs Frontend als lokale-Zeit-Falle vermerkt; rein anzeigend unkritisch.

## 7. Deploy & Konfiguration (Render)

- **Zwei Dienste:** bestehender **Web Service** (FastAPI-Backend) + neue **Static Site** (gebautes Frontend, CDN-ausgeliefert).
- **Backend-Adresse** kommt über Umgebungsvariable `VITE_API_BASE_URL` ins Frontend (kein hartcodierter Link); daraus werden HTTP- (`https://…`) und WebSocket-URL (`wss://…`) abgeleitet.
- **Backend-CORS:** die echte Frontend-Adresse zu den erlaubten Origins aufnehmen (für HTTP **und** den Cross-Origin-WebSocket). Dev-Origins (`localhost`) bleiben.
- **Eine Instanz** (kein Autoscaling): der Backend-Zustand (letztes Ergebnis, WS-Verbindungen, Event-Bus pro Lauf) liegt im Speicher eines Prozesses — Mehr-Instanz erst nach Persistenz + Redis-Bus (Backend-Folge-Aufgaben).
- **Sicherheit:** `POST …/run` ist unauthentifiziert. Diese Scheibe bleibt für eine geschützte/private Render-Umgebung gedacht; **vor** öffentlicher Exposition zwingend Auth + Rate-Limiting + Lauf-Lock (Backend-Folge-Aufgabe #7).

## 8. Tests

- **Pure Funktionen (§5) zuerst** (Vitest), Grenzfälle explizit.
- **Komponenten-Smoke-Tests** (React Testing Library) für die Zustände: `200`-Übersicht rendert Banner + 4 Kacheln; `204` rendert Leerzustand; eine `unavailable`-Domäne rendert UNAVAILABLE statt Signal; Health zeigt „x/5".
- **Daten-/WS-Anbindung** gegen einen Fake (kein echter Netz-Call im Test): GET-Lade-Pfad, „Start → WS-Events → terminal → Übersicht gefüllt".
- Das Backend ist bereits getestet (PR #24); diese Scheibe testet nur die Frontend-Seite.

## 9. Abgrenzung / Nicht-Ziele

Drill-downs (Zinskurve/Buffett/Big-Mac), Deep-Dive/Portfolio/Inbox/Backtester, Charting, Auth/Rate-Limiting, Mehr-Instanz-Skalierung, Ergebnis-Persistenz über Server-Neustart. Alle als Folge-Scheiben bzw. bestehende Backend-Folge-Aufgaben im Logbuch.

---

*Querverweise: `docs/superpowers/specs/2026-06-21-frontend-konzept.md` (Gesamt-Konzept, Leitideen, Wireframes), `docs/superpowers/specs/2026-06-22-api-bridge-cockpit-design.md` (konsumierter Backend-Vertrag). Status/PR-Protokoll/Folge-Aufgaben: `docs/open_todos.md`.*
