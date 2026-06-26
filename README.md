# AAIA — Adaptive AI Investment Agent

**Modul:** Business Intelligence | FHNW
**Architektur:** EDA + Hexagonal | Multi-Agent System
**Stack:** Python 3.12 · FastAPI · React/TypeScript · Supabase/PostgreSQL · Claude (Anthropic)

---

## Inhaltsverzeichnis

1. [Was ist AAIA?](#was-ist-aaia)
2. [Die Analyse-Modi](#die-analyse-modi)
3. [Long- und Short-Urteil](#long--und-short-urteil)
4. [Die Anlageklassen-Taxonomie (underlying × wrapper)](#die-anlageklassen-taxonomie-underlying--wrapper)
5. [Die Multi-Agenten-Architektur](#die-multi-agenten-architektur)
6. [Resilience: Was passiert wenn etwas ausfällt?](#resilience-was-passiert-wenn-etwas-ausfällt)
7. [Urteil und Erklärbarkeit (XAI)](#urteil-und-erklärbarkeit-xai)
8. [Bewertungsmethoden](#bewertungsmethoden)
9. [Datenspeicherung, Backtesting & Selbstkalibrierung](#datenspeicherung-backtesting--selbstkalibrierung)
10. [Web-API & Frontend (Cockpit)](#web-api--frontend-cockpit)
11. [Datenquellen — angebunden vs. Stub](#datenquellen--angebunden-vs-stub)
12. [Technologie-Stack](#technologie-stack)
13. [Architekturprinzipien](#architekturprinzipien)
14. [Installation & Ausführung](#installation--ausführung)
15. [Tests & CI](#tests--ci)
16. [Projektstruktur](#projektstruktur)
17. [Aktueller Stand & offene Punkte](#aktueller-stand--offene-punkte)
18. [Roadmap / In Planung](#roadmap--in-planung)
19. [Weiterführende Dokumentation](#weiterführende-dokumentation)

---

## Was ist AAIA?

AAIA ist ein vollautomatisches, KI-gestütztes Investitionsanalyse-System. Es beobachtet kontinuierlich das globale Marktumfeld — von Inflation und Zinsen über Rohstoffpreise und Marktstimmung bis hin zu Unternehmenskennzahlen — und leitet daraus strukturierte Investitionsentscheidungen ab.

Das System arbeitet in zwei Richtungen: **von oben nach unten** (Was passiert gerade im Markt als Ganzes?) und **von unten nach oben** (Ist dieses konkrete Asset kaufens- oder shortenswert?). Beide Perspektiven werden am Ende zu einem einzigen, begründeten Urteil zusammengeführt.

Das Besondere: Hinter jeder Analyse steckt nicht ein einzelner Agent, sondern ein hierarchisches Netz aus **über 40 spezialisierten Agenten**, die parallel und unabhängig voneinander arbeiten — und deren Ergebnisse stufenweise verdichtet werden. Das System **handelt nie selbst**: Es liefert Empfehlungen, Konfidenzen und Erklärungen, die Entscheidung bleibt beim Nutzer.

> **Zwei oberste Prinzipien** prägen den ganzen Code: **(1) Code-Qualität** und **(2) finanzielle/fachliche Korrektheit**. Wo eine Datenquelle fehlt, gibt das System ehrlich „keine Daten" (`UNAVAILABLE`/`None`) aus, statt eine plausibel klingende, aber erfundene Zahl zu liefern.

---

## Die Analyse-Modi

AAIA wird über fünf CLI-Modi gesteuert (`python -m app.main <modus> …`) — und zusätzlich über eine Web-API/Frontend (siehe [Web-API & Frontend](#web-api--frontend-cockpit)).

| Modus | Befehl | Zweck |
|---|---|---|
| **1 — Dashboard** | `dashboard` | Top-Down: Market Cockpit (Regime + alle Makro-/Markt-Domänen) |
| **2 — Bottom-Up** | `bottomup <ticker> [underlying] [wrapper] [sector]` | Asset-Tiefenanalyse (long **und** short) |
| **3 — Judge** | `judge <ticker> [market]` | Kombiniert Top-Down + Bottom-Up zum finalen Urteil |
| **4 — Conflicts** | `conflicts` | Listet offene Positions-Konflikte (gekippte These) |
| **5 — Resolve** | `resolve <id> <held\|closed>` | Protokolliert die Nutzer-Entscheidung zu einem Konflikt (kein Trade) |

### Modus 1 — Top-Down: Market Cockpit

Das Market Cockpit beantwortet die Frage: *In welcher Phase befindet sich der Markt gerade, und was bedeutet das für die Kapitalallokation?*

Dafür analysiert AAIA gleichzeitig fünf Bereiche — **Makroökonomie, Rohstoffe, Marktstimmung, Zinskurven und Sektoren** — und synthetisiert daraus ein Gesamtbild. Das Ergebnis ist ein klar klassifiziertes **Marktregime** (Boom, Aufschwung, Abschwung, Rezession oder Erholung) mit einer Konfidenzangabe.

Die Makroanalyse umfasst u. a. den **Buffett-Indikator** (Gesamtmarktkapitalisierung zu BIP) für ~150 Länder weltweit sowie den **adjustierten Big Mac Index** als Indikator für Kaufkraftparität und Währungsbewertungen.

### Modus 2 — Bottom-Up: Stock Deep Dive

Wird ein konkretes Asset angegeben (z. B. „AAPL", „SPY", „GC=F"), startet eine Tiefenanalyse. Anhand des **Basiswerts (`underlying`)** wählt das System den richtigen Analyse-Pfad und aktiviert die passende Engine. Es gibt **fünf** Analyse-Engines:

- **Aktie (`equity`):** Fundamentalanalyse (KGV, EV/EBITDA, DCF-Bewertung), Qualitätsprüfung (Margen, ROIC, Altman-Z), Short-Interesse, Insider-Aktivitäten, Gewinntrends, Burggraben-Bewertung nach Warren Buffetts Moat-Konzept und eine Bandbreiten-Bewertung über mehrere Methoden.
- **Index (`equity_index`):** Preis, Bewertung (Earnings Yield / ERP / Shiller-CAPE), Breadth, Momentum, Sektorkomposition und Bandbreiten-Bewertung.
- **Rohstoff (`commodity`):** Angebot/Nachfrage, Saisonalität, COT (Commitment of Traders) und Bewertungs-Bandbreite.
- **Edelmetall (`precious_metal`):** Preisanalyse, Cross-Metal-Ratios (z. B. Gold/Silber) und Realzins-Anker-Bewertung.
- **Anleihe (`bond`):** Kennzahlen, Duration, Credit-Rating und Spread — gewichtet über ein **Risikoaffinitäts-Modell** (`--risk-affinity konservativ|neutral|risikofreudig` ist für Anleihen Pflicht).

### Modus 3 — Judge

Der `judge`-Modus lädt die zwischengespeicherten Cockpit- und Bottom-Up-Ergebnisse und führt sie zum finalen, begründeten Urteil zusammen (siehe [Urteil und Erklärbarkeit](#urteil-und-erklärbarkeit-xai)).

### Modus 4/5 — Conflicts & Resolve

Kippt die ursprüngliche These zu einer **bereits gehaltenen Position**, schreibt der `ConflictAgent` einen Konflikt in den Store. `conflicts` listet alle offenen Konflikte; `resolve` protokolliert die Nutzer-Entscheidung (`held`/`closed`) — **ohne** je selbst zu handeln.

---

## Long- und Short-Urteil

Jede Bottom-Up-Analyse erzeugt **zwei** Urteile aus **einem** Analyselauf — die Fakten werden einmal beschafft, dann durch zwei unabhängige Linsen interpretiert. **Short ≠ invertiertes Long.**

| Lage | Long-Linse (`derive_recommendation`) | Short-Linse (`derive_short_assessment`) |
|---|---|---|
| nicht gehalten + klares Einstiegssignal | **BUY** | **SHORT** |
| nicht gehalten + kein belastbares Urteil | **NONE** | **NONE** |
| gehalten + Signal gilt weiter/verstärkt | **BUY+** | **SHORT+** (stark gegated) |
| gehalten + Lage unklar | **HOLD** | **HOLD** |
| gehalten + These gekippt | **SELL** | **COVER** |

- **HOLD vs. NONE:** HOLD = Position existiert, Lage unklar → halten. NONE = nicht investiert **und** kein belastbares Urteil.
- **`current_position` (none/long/short)** steuert die Aktionswahl — nicht ein simples „im Portfolio ja/nein".
- Die Short-Seite ist heute für **Aktien** voll ausgebaut (eigene Short-These: Bewertungs-Extrem, Distress/Bilanz, Earnings-Verfall, schwacher Moat, Insider-Verkäufe, Squeeze-Flags). Andere Klassen fallen vorerst auf einen neutralen Short-Default zurück (Ausbau eingeplant, siehe [offene Punkte](#aktueller-stand--offene-punkte)).

---

## Die Anlageklassen-Taxonomie (underlying × wrapper)

AAIA trennt **zwei voneinander unabhängige Fragen**, die früher ein einziges `asset_class`-Feld vermischt hat:

- **`underlying`** (Basiswert: `equity` / `equity_index` / `bond` / `commodity` / `precious_metal`) — bestimmt, **welche Analyse-Engine** läuft.
- **`wrapper`** (Hülle: `single` / `fund` / `future` / `physical_etc`) — schaltet eine zusätzliche **Mechanik-/Info-Schicht** zu.

Dasselbe Öl ist über eine Öl-**Aktie**, einen Öl-**Fonds** oder einen Öl-**Future** investierbar — gleicher Basiswert, andere richtige Analyse. „Futures" ist damit ein **Wrapper-Wert**, **keine** eigene Anlageklasse: Die Futures-Mechanik wird einmal gebaut und gilt für jeden Basiswert, der per Future gehalten wird.

**Legacy-Kompatibilität:** Alte CLI-Werte werden automatisch gemappt — z. B. `etf` → (`equity_index`, `fund`), `index` → (`equity_index`, `single`). Damit landet ein Sektor-ETF wie XLE korrekt bei der Index-Engine statt stillschweigend bei der Aktien-Engine.

> **Stand:** Das Zwei-Etiketten-Modell und die Wrapper-Mechanik (inkl. Fund-Info-Overlay) sind in der CLI bereits aktiv; einzelne Wrapper-/Short-Ausbaustufen sind noch offen (siehe Logbuch). Design: [`docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md`](docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md).

---

## Die Multi-Agenten-Architektur

Das System ist in drei Schichten aufgebaut:

```
Orchestratoren  →  ChiefAgents  →  Sub-Agents
```

### Schicht 1 — Orchestratoren

Orchestratoren sind die oberste Koordinationsebene. Sie starten die Analyse und delegieren sofort an ChiefAgents. Es gibt drei:

- **TopDownOrchestrator** — koordiniert das Market Cockpit (5 ChiefAgents parallel)
- **BottomUpOrchestrator** — wählt anhand des `underlying` den richtigen ChiefAgent und aktiviert dessen Engine
- **JudgmentOrchestrator** — verbindet Top-Down- und Bottom-Up-Ergebnisse zu einem Urteil (inkl. Konflikt-Verdikt bei gekippter These)

### Schicht 2 — ChiefAgents

ChiefAgents sind Domain-Koordinatoren. Jeder ist für genau eine fachliche Domäne verantwortlich, startet seine Sub-Agents **parallel**, fängt Fehler ab und gibt **immer** ein vollständiges Ergebnis zurück — auch wenn einzelne Datenquellen ausgefallen sind. Jeder aggregierende Chief synthetisiert ein **Gesamtsignal** (z. B. via `weighted_signal` / `aggregate_bond_signal`).

**Market Cockpit ChiefAgents:**

| ChiefAgent | Verantwortlich für |
|---|---|
| `MacroChiefAgent` | BIP, Inflation (USA/Eurozone/CH), Zinsen, Geldmenge, Arbeitsmarkt, Kredit, Buffett-Indikator (~150 Länder) |
| `CommodityChiefAgentMakro` | Energie (WTI, Brent, Gas), Industriemetalle, Edelmetalle (makro), Agrar |
| `SentimentChiefAgent` | VIX, VSTOXX, Fear & Greed Index, Put/Call-Ratio |
| `YieldCurveChiefAgent` | Yield Spreads (10J/2J, 10J/3M, 30J/10J), Sovereign Spreads (BTP/Bund, OAT/Bund) |
| `SectorChiefAgent` | Sektor-Performance (USA/Eurozone), Sektor-Rotation nach Regime |

**Stock Deep Dive ChiefAgents:**

| ChiefAgent | Basiswert | Analysiert |
|---|---|---|
| `EquityChiefAgent` | Aktien | Fundamentals, Quality, Short Interest, Insider, Earnings Trend, Moat, Valuation Range |
| `BondChiefAgent` | Anleihen | Metrics, Duration, Credit Rating, Spread (gewichtet nach Risikoaffinität) |
| `IndexChiefAgent` | Indizes | Preis, Bewertung, Earnings, Breadth, Momentum, Sektorkomposition, Valuation Range |
| `CommodityChiefAgentMikro` | Rohstoffe | Supply/Demand, Saisonalität, COT, Valuation Range |
| `PreciousMetalsChiefAgent` | Edelmetalle | Preisanalyse, Cross-Metal Ratios, Valuation |

**Übergreifende ChiefAgents:**

| ChiefAgent | Funktion |
|---|---|
| `AnomalyChiefAgent` | Erkennt statistische Ausreisser und widersprüchliche Signale (Z-Score-basiert, richtungsbewusst) |
| `BacktesterChiefAgent` | Lädt vergangene Analysen und bewertet die bisherige Treffsicherheit des Systems |
| `JudgmentChiefAgent` | Synthetisiert alles zu einer finalen Empfehlung mit Konfidenz und XAI-Begründung — Long-Linse **und** Short-Linse |
| `ConflictAgent` | Liefert ein **beratendes** Verdikt (EXIT / HOLD / REVERSE), wenn die These einer gehaltenen Position gekippt ist (LLM-gestützt) |

### Schicht 3 — Sub-Agents

Sub-Agents sind die eigentlichen Spezialisten. Jeder beherrscht genau eine Aufgabe und greift auf eine spezifische Datenquelle zu. Sie wissen nichts voneinander — ihre Koordination übernimmt ausschliesslich der ChiefAgent.

Aktuell gibt es **über 40 Sub-Agents** in 10 Domänen. Die vollständige Übersicht steht in [`docs/agent_structure.md`](docs/agent_structure.md); alle Metriken je Sub-Agent in [`docs/sub_agents_metrics.md`](docs/sub_agents_metrics.md).

---

## Resilience: Was passiert wenn etwas ausfällt?

AAIA ist darauf ausgelegt, auch bei partiellen Ausfällen immer ein vollständiges Ergebnis zu liefern. Dafür gibt es zwei Sicherheitsebenen:

**Ebene 1 — Sub-Agent fällt aus:** Der ChiefAgent fängt den Fehler ab und ersetzt das Ergebnis mit einem neutralen Fallback-Wert. Die anderen Sub-Agents laufen ungestört weiter.

**Ebene 2 — ChiefAgent fällt aus:** Der Orchestrator fängt den Fehler ab und ersetzt das Ergebnis mit einem neutralen Fallback. Die anderen ChiefAgents laufen ungestört weiter.

Das System gibt **niemals einen Hard-Crash** zurück. Stattdessen enthält das Ergebnis im Fehlerfall neutrale Werte, und die Gesamtkonfidenz des Urteils sinkt entsprechend.

> **Hinweis zum aktuellen Stand:** Mehrere Datenquellen sind bewusst noch **Stubs** und liefern `UNAVAILABLE`/`None` (u. a. COT, Angebot/Nachfrage, Bond-Rohdaten, Index-Holdings). Die **Logik** dieser Agenten ist fertig gebaut und getestet; sie schalten automatisch auf echte Signale um, sobald der jeweilige Daten-Adapter angebunden ist — ohne Änderung am Agenten-Code. Ein ehrliches „keine Daten" ist besser als erfundene Zahlen. Siehe [Datenquellen](#datenquellen--angebunden-vs-stub).

---

## Urteil und Erklärbarkeit (XAI)

Nachdem Top-Down- und Bottom-Up-Analyse abgeschlossen sind, übernimmt der `JudgmentOrchestrator`. Er kombiniert:

- Das Makro-Regime mit Konfidenz (aus dem Market Cockpit)
- Die Asset-spezifische Tiefenanalyse (aus dem Stock Deep Dive)
- Den Anomalie-Report (statistische Ausreisser und Signalwidersprüche)
- Den Backtester-Kontext (historische Treffsicherheit des Systems für diesen Ticker)

Aus diesen vier Inputs berechnet der `JudgmentChiefAgent` eine **dynamische Konfidenz (0.0–1.0)** und gibt eine finale Empfehlung aus. Liegt die Konfidenz unter **0.50**, empfiehlt das System automatisch **HOLD** — zu viel Widerspruch, zu wenig Sicherheit. Unter **0.35** wird zusätzlich **Cash-Bias** signalisiert.

Zu jeder Empfehlung generiert ein zweiter LLM-Call eine ausführliche **XAI-Erklärung**: Was waren die entscheidenden Signale? Wo lagen die Widersprüche? Warum diese Konfidenz? Was könnte die Einschätzung kippen?

Kippt die These zu einer **bereits gehaltenen Position**, schaltet sich der `ConflictAgent` ein und liefert ein **beratendes Verdikt** (EXIT / HOLD / REVERSE) — das System macht den Konflikt sichtbar und überlässt die Entscheidung dem Nutzer.

---

## Bewertungsmethoden

AAIA kombiniert klassische und unkonventionelle Bewertungsansätze:

**Für Einzelaktien und Indizes:**
- KGV-Multiple, EV/EBITDA-Multiple, DCF (Discounted Cashflow)
- **Shiller-CAPE** (Cyclically Adjusted P/E): glättet Gewinne über 10 Jahre, um Bewertungszyklen sichtbar zu machen
- Altman-Z Score (Insolvenzwahrscheinlichkeit)
- Burggraben-Analyse (Moat) nach Warren Buffett: immaterielle Werte, Wechselkosten, Netzwerkeffekte, Kostenvorteile, effiziente Skalierung

**Für den Gesamtmarkt:**
- **Buffett-Indikator** (Total Market Cap / BIP): globale Implementierung für ~150 Länder. USA via FRED (Echtzeit, monatlich), alle anderen via Weltbank API (jährlich). Jedes Land wird gegen seine **eigene** 10-Jahres-Geschichte verglichen (Z-Score) — nicht gegen einen universellen Schwellenwert. Relevant nur für Aktien, ETFs und Indizes.

  *Dagegen spricht:*
  - **Globalisierung** — S&P-500-Unternehmen erwirtschaften einen Grossteil ihrer Gewinne ausserhalb der USA; das BIP misst aber nur die US-Wirtschaft → strukturell verzerrter Vergleich
  - **Zinsniveau wird ignoriert** — bei 0 % Zinsen sind höhere Bewertungen rational; der Indikator kennt keinen Zinskontext
  - **Kein Timing-Tool** — kann jahrelang „überteuert" anzeigen, ohne dass der Markt fällt (z. B. 2016–2021)
  - **Aktienrückkäufe** — erhöhen die Marktkapitalisierung ohne realwirtschaftlichen Gegenwert und verzerren den Quotienten nach oben

**Für Währungs- und Kaufkraftanalyse:**
- **Adjustierter Big Mac Index**: vergleicht Kaufkraftparität zwischen Ländern adjustiert für Einkommensniveaus — hilft bei der Einschätzung von Währungsüber- oder -unterbewertungen.

---

## Datenspeicherung, Backtesting & Selbstkalibrierung

Jede abgeschlossene Analyse wird in einer **Supabase-Datenbank (PostgreSQL)** gespeichert — inklusive Ticker, Basiswert, Regime, Empfehlung, Konfidenz, Kurs zum Analysezeitpunkt und der vollständigen XAI-Erklärung. Das DB-Schema liegt versioniert im Repo (`db/schema.sql`).

**Tägliches Backtesting (Windows Task Scheduler / `background_runner`):** Ein Hintergrund-Runner vergleicht alle vergangenen Analysen mit der tatsächlichen Kursentwicklung:

- `TopDownBacktesterAgent` — war das vorhergesagte Regime korrekt? (30/60/90 Tage)
- `BottomUpBacktesterAgent` — hat das dominante Signal (bullish/bearish/neutral) gestimmt?
- `JudgmentBacktesterAgent` — war BUY/SELL/HOLD/SHORT tatsächlich profitabel?

Die Treffsicherheits-Statistiken fliessen direkt in die Konfidenzberechnung der nächsten Analyse ein — das System verbessert sich kontinuierlich selbst.

**Regime-Replay-Backtest (historische Validierung & Kalibrierung):** Mit `app/replay_regime.py` und `app/calibrate_regime.py` lässt sich der Regime-Detektor **point-in-time** gegen die Historie (ab 1960, USA) testen — gegen Forward-S&P-Renditen und NBER-Rezessionsdaten — und die Risk-off-Schwelle datenbasiert kalibrieren. Design/Plan unter `docs/superpowers/{specs,plans}/2026-06-22-regime-replay-backtest*`.

**Portfolio-Monitor:** Der `PortfolioMonitorAgent` überwacht das Portfolio täglich, **richtungsbewusst** (jede Position ist long oder short), und rechnet:

- **Netto- und Brutto-Exposure** (Long minus/plus Short), getrennt ausgewiesen
- **`net_beta`** — beta-bereinigtes Netto-Aktienmarkt-Risiko als $-Hedge-Notional (aktien-/indexbasiert; Bonds, Rohstoffe, Edelmetalle gehen bewusst nicht ein)
- **Portfolio-Volatilität** aus echten Kursreihen (Korrelation per Datum zusammengeführt)
- **Klumpen-Warnungen** je Bucket (Sektor, Basiswert, Geografie) und offene Verlustpositionen

---

## Web-API & Frontend (Cockpit)

Über die CLI hinaus gibt es eine **Web-Schicht** — eine React-App, die live über eine FastAPI-Brücke an die Agenten angebunden ist.

**Backend — FastAPI (`app/server.py`, `adapters/api/`):**

| Endpunkt | Zweck |
|---|---|
| `GET /healthz` | Health-Check (öffentlich, ohne Token — für den Deploy-Health-Check) |
| `GET /api/cockpit` | Letztes Cockpit-Ergebnis (`204`, wenn noch keines vorliegt) |
| `POST /api/cockpit/run` | Startet einen Analyselauf im Hintergrund (`202` + `run_id`) |
| `WS /ws/cockpit` | Live-Event-Stream während des Laufs (jedes `*Ready`-Event) |

- **Zugriffsschutz:** Shared-Token (`AAIA_ACCESS_TOKEN`) schützt GET/POST/WS (constant-time-Vergleich; leer = Auth aus + Warn-Log, in Produktion fail-closed).
- **Lauf-Lock:** ein zweiter `POST /run` während eines laufenden Laufs wird mit `409 Conflict` abgewiesen.
- **UNAVAILABLE-Vertrag:** eine ausgefallene Domäne liefert `signal: null` (statt eines erfundenen „neutral"), plus pro-Domäne-`status`.
- **Erster echter EDA-Subscriber:** Der `WebSocketBroadcaster` abonniert über `subscribe_all` alle `*Ready`-Events des In-Memory-Event-Bus und streamt sie an verbundene Clients.

**Frontend — React 19 / TypeScript / Vite / Tailwind (`frontend/`):** eine mehrseitige App mit Login-Gate (Passwortschutz), gemeinsamer Shell/Sidebar und einer **Fuzzy-Suche über das Anlage-Universum** (Ticker- und Namensauflösung statt blossem `ticker.upper()`):

| Seite | Inhalt |
|---|---|
| **Cockpit** | Regime-Banner + Markt-Puls-Synthese/Regime-Deutung, Domänen-Kacheln, Daten-Health-Indikator, Drilldowns (z. B. Buffett-Karte, Charts), „Analyse starten" — **live** über `GET`/`POST`/`WS` |
| **Deep-Dive** | Hero-Kopf mit „Urteil auf einen Blick" (Long **und** Short), Tab-Pills je Analysebereich, Kurschart |
| **Portfolio** | Überblick, Allokation, Long/Short-Balance, `net_beta`, Klumpen-Warnungen |
| **Inbox** | offene Positions-Konflikte (gekippte These) mit beratendem Verdikt |
| **Backtester** | historische Treffsicherheit des Systems |
| **Einstellungen** | echte Settings-Seite (Risikoaffinität, Token u. a.) |

> **Stand:** Das **Cockpit** ist voll an das echte Backend angebunden. Deep-Dive, Portfolio, Inbox und Backtester sind UI-seitig fertig, laufen aber teils noch auf **Demo-Daten** — die „Naht" zu echten Endpunkten ist im Code vorbereitet und wird scheibenweise pro Bereich verdrahtet (Status im Logbuch). UNAVAILABLE (`signal: null`) wird überall sauber dargestellt.

**Deployment — Render (`render.yaml`):** zwei Services — `aaia-api` (uvicorn) und `aaia-frontend` (Static Site). Health-Check auf `/healthz`. Anleitung: [`docs/deploy-render.md`](docs/deploy-render.md).

---

## Datenquellen — angebunden vs. Stub

AAIA folgt der Hexagonal-Regel: Agenten hängen nur von **Ports** ab, echte Quellen stecken in **Adaptern**. Ein fehlender Adapter bedeutet `UNAVAILABLE`, nie einen Crash.

**Angebunden (live):**

| Quelle | Liefert |
|---|---|
| **FRED** | USA-Makro (BIP, Inflation, Zinsen, Realzins DFII10), Buffett-Indikator USA |
| **Yahoo Finance** | Kurse, Indizes, Renditen |
| **Finnhub** | Aktien-Fundamentals, Earnings-Historie |
| **ECB SDW + Eurostat** | Eurozone-Makro: HICP/Kern-HICP/PPI, reales BIP, Arbeitslosigkeit, Geldmenge M2/M3 |
| **CNN Fear & Greed** | Marktstimmungs-Index (0–100) |
| **Weltbank API** | Buffett-Indikator für ~150 Länder |
| **CBOE** | Put/Call-Ratio |
| **FMP** | LME-Industriemetalle, EU/CH Shiller-CAPE (10J-EPS) |
| **Claude (Anthropic)** | Moat-Analyse, XAI-Erklärungen, Konflikt-Verdikt |
| **Supabase / PostgreSQL** | Analyse-History, Backtester-Reports, Konflikt-Store |

**Noch Stub / offen (Logik fertig, Daten fehlen):** native SNB-/BFS-/SECO-Quellen für die Schweiz (heute teils via FRED-Proxy), **Bond-Rohdaten** (`get_bond_data` → `{}`), **COT** (CFTC), **Commodity Supply/Demand** (EIA/USDA/LME), **Index-Holdings/-Konstituenten**, sowie der **Redis-Event-Bus** für den verteilten Betrieb (aktuell `InMemoryEventBus`). Der vollständige, laufend gepflegte Stand steht im Logbuch [`docs/open_todos.md`](docs/open_todos.md) (§2/§3).

---

## Technologie-Stack

| Komponente | Technologie |
|---|---|
| Sprache | Python 3.12 |
| Async | `asyncio` — alle Sub-Agents laufen parallel |
| Web-API | FastAPI + uvicorn (`app/server.py`) |
| Frontend | React 19 / TypeScript / Vite / Tailwind (`frontend/`) |
| Daten | FRED, Yahoo Finance, Finnhub, ECB SDW/Eurostat, Weltbank, CBOE, FMP, CNN Fear & Greed |
| LLM | Claude (Anthropic) — Moat-Analyse, XAI, Konflikt-Verdikt |
| Event Bus | In-Memory (EDA); Redis-Adapter als Stub für verteilten Betrieb |
| Datenbank | Supabase / PostgreSQL — History, Backtester-Reports, Konflikte |
| Caching | In-Memory Cache + JSON-Persistenz (datierte Reihen, Portfolio) |
| Deploy | Render (`render.yaml`) — `aaia-api` + `aaia-frontend` |
| CI | GitHub Actions (`ci.yml` pytest je PR; `background_runner.yml` täglich) |

---

## Architekturprinzipien

AAIA folgt zwei Architekturmustern, die zusammen eine klare Trennung von Fachlogik und Infrastruktur sicherstellen:

**EDA (Event-Driven Architecture):** Jeder Agent publiziert nach Abschluss ein Event auf dem Bus (z. B. `MacroChiefReady`, `EquityChiefReady`). Der erste echte Subscriber ist der WebSocket-Broadcaster der API-Brücke, der diese Events live ans Frontend streamt.

**Hexagonale Architektur (Ports & Adapters):** Die Kern-Fachlogik (`core/domain/`, `agents/`) kennt keine konkreten Datenquellen. Sie kommuniziert ausschliesslich über abstrakte Interfaces (`core/ports/`). Die konkreten Implementierungen (FRED, Yahoo, ECB, Claude, Redis, Supabase) stecken in `adapters/`. Dadurch lässt sich jede Datenquelle austauschen, ohne den Kern zu berühren.

> **Nicht verhandelbar:** Ein Agent importiert **nie** direkt aus `adapters/` (Port injizieren); kein I/O in `core/`; keine Geschäftslogik in einem Adapter. Numerische Schwellenbänder sind lückenlos (jeder Wert fällt in genau eine Klasse). Details: [`AGENTS.md`](AGENTS.md).

---

## Installation & Ausführung

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. API-Keys konfigurieren
cp .env.example .env
# FRED_API_KEY       — kostenlos: https://fred.stlouisfed.org/docs/api/api_key.html
# FINNHUB_API_KEY    — Aktien-Fundamentals
# ANTHROPIC_API_KEY  — Claude (Moat/XAI/Konflikt)
# FMP_API_KEY        — EU/CH Shiller-CAPE und LME-Metalle (optional; ohne → graceful None)
# SUPABASE_DB_URL    — Analyse-History & Backtester
```

**CLI:**

```bash
# Modus 1 — Market Cockpit (Top-Down, füllt den Dashboard-Cache)
python -m app.main dashboard

# Modus 2 — Bottom-Up-Analyse
#   underlying: equity | equity_index | bond | commodity | precious_metal   (default: equity)
#   wrapper:    single | fund | future | physical_etc                       (default: single)
python -m app.main bottomup AAPL                       # Aktie (Default)
python -m app.main bottomup XLE etf                    # Legacy 'etf' → equity_index/fund
python -m app.main bottomup SPY equity_index single    # neuer Stil
python -m app.main bottomup TLT bond --risk-affinity neutral   # Anleihe (risk-affinity Pflicht)

# Modus 3 — Kombinations-Urteil (market: USA | CH | ISO-2-Länderkode)
python -m app.main judge AAPL USA
python -m app.main judge NESN.SW CH

# Modus 4/5 — Konflikte ansehen / entscheiden (kein Trade)
python -m app.main conflicts
python -m app.main resolve 7 held
```

**Web-API + Frontend lokal:**

```bash
# Backend (FastAPI)
uvicorn app.server:app --reload

# Frontend (in frontend/)
cd frontend && npm install && npm run dev
```

---

## Tests & CI

**TDD ist im Projekt verpflichtend** — erst der fehlschlagende Test, dann die Implementierung. Grenzfälle (genau auf der Schwelle, knapp darüber/darunter, `None`, negative Werte) und Fehlerpfade (Datenquelle wirft → Agent liefert trotzdem den Default) werden explizit getestet.

```bash
python -m pytest -q                                       # alle Tests
python -m pytest tests/agents/market_cockpit/macro/ -q    # gezielt ein Paket
```

**CI (GitHub Actions):** `ci.yml` läuft `pytest` (Python 3.12) bei jedem PR und beim Push auf `master`; Datenquellen werden in Tests gemockt (Ports), echte API-Keys sind nicht nötig. Das Frontend wird mit Vitest getestet.

---

## Projektstruktur

```
aaia_agent/
├── app/
│   ├── main.py                      ← CLI-Einstiegspunkt (dashboard/bottomup/judge/conflicts/resolve)
│   ├── server.py                    ← FastAPI-App (Web-API)
│   ├── replay_regime.py             ← Regime-Replay-Backtest (Validierung)
│   └── calibrate_regime.py          ← Risk-off-Schwelle kalibrieren
│
├── orchestrators/
│   ├── top_down_orchestrator.py     ← Modus 1
│   ├── bottom_up_orchestrator.py    ← Modus 2
│   └── judgment_orchestrator.py     ← Urteil
│
├── agents/                          ← siehe docs/agent_structure.md
│   ├── market_cockpit/              ← Top-Down ChiefAgents + Sub-Agents
│   ├── stock_deep_dive/             ← Bottom-Up ChiefAgents + Sub-Agents
│   ├── anomaly/  backtester/  judgment/  portfolio/
│   ├── anomaly_chief_agent.py
│   ├── backtester_chief_agent.py
│   └── judgment_chief_agent.py
│
├── core/
│   ├── domain/                      ← Modelle, Events, Enums (reine Domäne)
│   │   ├── models.py  regime.py  recommendation.py
│   │   ├── taxonomy.py              ← underlying × wrapper
│   │   ├── short_assessment.py  short_flags.py   ← Short-Linse
│   │   ├── conflict_inbox.py        ← Konflikt-Modell
│   │   ├── portfolio.py  regime_inputs.py  top_down_context.py
│   │   └── events.py
│   ├── ports/                       ← abstrakte Schnittstellen (Hexagonal)
│   │   ├── data_provider.py  llm_provider.py  memory_port.py  event_bus.py
│   │   ├── portfolio_port.py  conflict_store.py  dated_history.py  fund_info.py
│   └── utils/                       ← reine Rechen-Helfer (pure functions)
│       ├── valuation_math.py  bond_math.py  credit.py  bond_risk.py
│       ├── scoring.py  statistics.py  aggregation.py  momentum.py
│       └── regime_eval.py  regime_calibration.py  performance_metrics.py
│
├── adapters/
│   ├── data/                        ← FRED, Yahoo, Finnhub, ECB SDW, Eurostat, CNN F&G, …
│   ├── api/                         ← FastAPI-Brücke (Routen, WS-Broadcaster, Run-Manager, Auth)
│   ├── memory/                      ← Supabase-Memory
│   ├── persistence/                 ← JSON-Reihen/-Portfolio, Supabase-Konflikt-Store
│   ├── cache/                       ← Ergebnis-Cache
│   ├── event_bus/                   ← In-Memory (+ Redis-Stub)
│   └── llm/                         ← Claude (Anthropic)
│
├── frontend/                        ← React/TS/Vite/Tailwind-Cockpit
├── db/
│   └── schema.sql                   ← autoritatives DB-Schema
├── config/
│   └── settings.py                  ← zentrale Konfiguration (.env)
├── tests/                           ← pytest (spiegelt agents/-Struktur)
├── .github/workflows/               ← ci.yml + background_runner.yml
├── render.yaml                      ← Render-Deploy (aaia-api + aaia-frontend)
├── docs/                            ← Specs, Pläne, Reviews, Logbuch (open_todos.md)
└── archive/                         ← Alte Implementierung (v1, Einzeldatei-System)
```

---

## Aktueller Stand & offene Punkte

> Der **laufende, detaillierte Status** (Reihenfolge, Folge-Aufgaben, PR-Protokoll mit Datum/Nummer, Entscheidungen) wird **ausschliesslich** im Logbuch [`docs/open_todos.md`](docs/open_todos.md) gepflegt — das ist die einzige Quelle der Wahrheit. Diese Liste hier gibt nur die **stabile Kategorien-Übersicht**, damit sie nicht mit dem Logbuch auseinanderdriftet.

**Datenquellen anbinden (Stubs → echt):**
- Native CH-Quellen (SNB/BFS/SECO) statt FRED-Proxy
- Bond-Rohdaten (`get_bond_data`) für die fertige Fixed-Income-Engine
- COT (CFTC), Commodity Supply/Demand (EIA/USDA/LME), Index-Holdings/-Konstituenten
- Redis-Event-Bus für den verteilten Betrieb

**Agenten-Logik vervollständigen (Logik teils vorhanden, Verdrahtung/Daten fehlen):**
- Inflation: USA Core CPI/PCE, EU-Realzins 10J, CH-PPI, CPI-Trend-Verschärfung
- Zinsrichtung & Money-Supply-Velocity verdrahten (DatedHistory durchreichen)
- Yield-Curve-Bull-Steepening-Signal aktivieren
- EU/CH-Kredit & -Löhne, EU-PMI (Lizenzfrage), Sahm-Regel für EU/CH
- Precious-Metals-Momentum (RSI/MA/Performance), ETF-Holdings via echte APIs
- Konfidenz-Kalibrierungs-Buckets in Produktion befüllen (Backtest → `compute_confidence`)

**Short-Engine ausbauen:** Track A (aggressiver Einzelaktien-Short) ist gebaut; offen sind Rohstoff-/Anleihen-Short-Spezifika, Momentum-Flags (long+short geteilt) und Track B (regime-getriebener Portfolio-Hedge).

**Web/Frontend Go-Live:** echte Backend-Endpunkte je Drilldown-Bereich anbinden (Deep-Dive, Portfolio, Inbox, Backtester laufen UI-seitig teils noch auf Demo-Daten); `bottomup`/`judge`-Endpunkte nach dem Cockpit-Muster; Ergebnis-Persistenz (überlebt Neustart → Voraussetzung für Mehr-Instanz/Autoscaling); WS-Reconnect/Replay; **Auth + Rate-Limiting + Lauf-Lock**, bevor die API über die Dozenten-Demo hinaus exponiert wird (Repo wird öffentlich).

**Architektur- & Test-Feinschliff (laufend):** Der projektweite Rollout des geteilten Fehler-Schutz-Helfers `core/utils/safe.py` (`safe_result`/`safe_provider_call`, kapselt Provider-Ausfälle + Logging zentral) läuft paketweise. Daneben kleinere Hygiene-Punkte (DB-Lese-Indizes, Modul-Aufteilung von `statistics.py`) und einzelne Test-Lücken/flaky Frontend-Tests unter paralleler Last.

---

## Roadmap / In Planung

- **Anlageklassen-Taxonomie** — Zwei-Etiketten-Modell ist aktiv; offen sind weitere Wrapper-Ausbaustufen (Fonds-/Futures-Mechanik je Basiswert: Terminkurve/Contango–Backwardation, Roll-Yield/Carry, Hebel/Margin, Verfall) sowie physisch hinterlegte Metall-ETCs.
- **VIX als Hedge-Instrument** (nicht als eigenständige Anlage) — später.
- **Shorts** — Rohstoff-/Anleihen-Short, Track-B-Hedge, Momentum-Sub-Agent (siehe oben).

Design-Dokumente unter [`docs/superpowers/specs/`](docs/superpowers/specs/); der verbindliche Status steht im Logbuch.

---

## Weiterführende Dokumentation

| Dokument | Inhalt |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Verbindliche Arbeits-/Architekturregeln (einzige Quelle der Wahrheit für Beitragende) |
| [`docs/open_todos.md`](docs/open_todos.md) | **Logbuch** — laufender Status, offene Aufgaben, PR-Protokoll |
| [`docs/agent_structure.md`](docs/agent_structure.md) | Vollständige Agent-Übersicht (alle Schichten) |
| [`docs/sub_agents_metrics.md`](docs/sub_agents_metrics.md) | Alle Metriken & Kennzahlen je Sub-Agent |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | Design-Spezifikationen (das „Warum") |
| [`docs/superpowers/plans/`](docs/superpowers/plans/) | Umsetzungspläne |
| [`docs/deploy-render.md`](docs/deploy-render.md) | Render-Deployment (Backend + Frontend) |
```
