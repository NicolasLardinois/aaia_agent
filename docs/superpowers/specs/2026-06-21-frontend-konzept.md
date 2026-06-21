# Frontend-Konzept — AAIA (Adaptive AI Investment Agent)

> **Status:** Spezifikation / Design-Entwurf · **Datum:** 2026-06-21
> **Scope:** Durchgängiges Frontend-Konzept für das fertige AAIA-Tool — User-Stories, Informationsarchitektur, Schlüssel-Ansichten/Widgets, Spezialfälle und offene Entscheidungen.
> **Erdung:** Baut auf `README.md` (System-Architektur, 3-Schichten-Analyse) und `docs/frontend_notes.md` (Buffett-/Big-Mac-Widget, UI-Prinzipien, offene Fragen) auf. Bereits getroffene Punkte aus `frontend_notes.md` werden übernommen und referenziert, nicht überschrieben.
> **Wichtig:** Dies ist ein reines Design-Dokument. Der **laufende Status** (Roadmap, PR-Protokoll, Reihenfolge) gehört ausschließlich ins Logbuch `docs/open_todos.md` — hier steht das *Warum* und *Wie* des Designs (AGENTS.md §5).

---

## 1. Zusammenfassung

AAIA ist ein dreischichtiges Analyse-System (Top-Down **Market Cockpit**, Bottom-Up **Stock Deep Dive**, **Judgment**). Das Frontend muss diese drei Schichten so abbilden, dass ein Nutzer ohne tiefes Finanz-Jargon-Wissen (siehe User-Profil) trotzdem **schnell zu einem begründeten Urteil** kommt — und das Urteil *anzweifeln* kann, weil jede Zahl erklärt und jede fehlende Zahl ehrlich als „nicht verfügbar" gezeigt wird.

Das Frontend wird um **fünf Leitideen** herum gebaut:

1. **Zwei Etiketten statt einer Asset-Klasse.** Jede Anlage trägt künftig zwei Badges: **`underlying`** (Basiswert: equity · equity_index · bond · commodity · precious_metal · [VIX später als Hedge]) × **`wrapper`** (Hülle: single · fund · future · physical_etc). Das ist das zentrale neue Modell und durchzieht die gesamte UI (Suche, Deep-Dive-Header, Portfolio-Tabelle, Filter).
2. **Long- und Short-Linse gleichberechtigt.** Jede Analyse liefert **zwei** Urteile nebeneinander: Long (BUY/SELL/HOLD/NONE) und Short (SHORT/COVER/HOLD/NONE), je mit Konfidenz und XAI-Begründung. Kein „Short als Nachgedanke".
3. **XAI vor Zahl.** Konfidenz, entscheidende Signale, Widersprüche und „was würde das kippen" sind first-class — nicht in einem Tooltip versteckt.
4. **UNAVAILABLE ist ein eigener Zustand.** Viele Datenquellen sind aktuell Stubs. Fehlende Daten werden **nie als 0 oder neutral verfälscht**, sondern explizit als „nicht verfügbar" markiert und aus Aggregationen/Konfidenz ausgenommen.
5. **Portfolio als Risikolinse.** Das Tool ist nicht nur ein Einzeltitel-Analyzer, sondern kennt long/short-Positionen, Netto-/Brutto-Exposure, `net_beta`, Klumpen-Warnungen und Track-B-Hedge-Vorschläge — plus eine **Konflikt-Inbox**, wenn eine gehaltene These kippt.

**Entscheidungen (am 2026-06-21 mit dem Nutzer getroffen — Details + Begründung in Abschnitt 6):** Framework → **React** (überstimmt die ursprüngliche Svelte-Empfehlung; chart-/tabellen-lastig + KI-gestützt); Layout → **Desktop-first mit responsivem Tablet-Fallback**; Updates → **WebSocket (live) von Anfang an** (überstimmt Polling-zuerst; der Server pollt die abruf-basierten Quellen und pusht an den Browser); Buffett-Widget → **Tabelle als Default, Weltkarte als optionaler Tab, Einzelland-10-J-Drill-down**; Big-Mac-Refresh → **automatischer Abruf (geplanter CSV-Pull, Rückfall auf zuletzt gespeicherte Version)** (überstimmt manuelle Pflege).

---

## 2. User-Stories (gruppiert)

Form durchgängig: *„Als <Rolle> möchte ich <Ziel>, damit <Nutzen>."*

**Rollen im Tool** (eine Person kann mehrere sein):
- **Makro-Beobachter** — schaut zuerst aufs große Bild (Regime, Zinsen, Sentiment).
- **Analyst** — gräbt sich in einen konkreten Titel.
- **Portfolio-Manager (PM)** — denkt in Positionen, Exposure und Risiko.
- **Skeptiker** — will jede Empfehlung hinterfragen, bevor er ihr traut.

### 2.1 Markt-Dashboard / Top-Down (Market Cockpit)

- Als **Makro-Beobachter** möchte ich auf einen Blick das aktuelle **Marktregime** (Boom / Aufschwung / Abschwung / Rezession / Erholung) mit Konfidenz sehen, damit ich sofort weiß, ob das Umfeld grundsätzlich für Risk-on oder Risk-off spricht.
- Als **Makro-Beobachter** möchte ich die **fünf Cockpit-Domänen** (Makro, Rohstoffe, Sentiment, Zinskurve, Sektoren) als einzelne „Kacheln" mit jeweils einem zusammengefassten Signal sehen, damit ich erkenne, welche Domäne das Gesamtbild treibt und welche widerspricht.
- Als **Makro-Beobachter** möchte ich beim **Inflations-Signal** sehen, für welche Region es gilt (USA / Eurozone-Land / CH) und welcher Schwellenwert gerade greift, damit ich nicht versehentlich US-Schwellen auf die Schweiz anwende.
- Als **Makro-Beobachter** möchte ich die **Zinskurve** als Kurve sehen (10J/2J, 10J/3M, 30J/10J) mit Markierung, ob sie invertiert ist, damit ich ein klassisches Rezessions-Frühwarnsignal sofort erkenne.
- Als **Makro-Beobachter** möchte ich den **Buffett-Indikator** für ~150 Länder durchsuchen/sortieren und das aktuell analysierte Land hervorgehoben sehen — inklusive Z-Score gegen die *eigene* 10-Jahres-Geschichte und dem Datenjahr (wegen Weltbank-Verzögerung) — damit ich die Bewertung im richtigen Kontext lese und nicht einen veralteten Wert für aktuell halte. *(Quelle: `frontend_notes.md` → Buffett-Widget)*
- Als **Makro-Beobachter** möchte ich beim Buffett-Indikator die **Einschränkungen** (Globalisierung, Zinskontext, kein Timing-Tool, Aktienrückkäufe) direkt am Widget lesen, damit ich den Indikator nicht überinterpretiere. *(Pflicht laut `frontend_notes.md`.)*
- Als **Makro-Beobachter** möchte ich den **adjustierten Big-Mac-Index** als Balken/Tabelle der Über-/Unterbewertung vs. USD mit Publikationsdatum sehen, damit ich Währungsverzerrungen für mein analysiertes Land einordnen kann.
- Als **Makro-Beobachter** möchte ich die **Sektor-Rotation** passend zum erkannten Regime sehen (welche Sektoren das Regime üblicherweise begünstigt), damit ich Top-Down eine Sektor-Präferenz ableiten kann.
- Als **Skeptiker** möchte ich sehen, **welche Cockpit-Quellen gerade ausgefallen / UNAVAILABLE** sind und wie stark das die Regime-Konfidenz gedrückt hat, damit ich weiß, wie belastbar das Gesamtbild ist.

### 2.2 Bottom-Up Deep-Dive pro Anlage (inkl. underlying × wrapper)

- Als **Analyst** möchte ich einen Titel über Ticker suchen und sofort im Header **beide Etiketten** sehen — `underlying` (z. B. commodity) und `wrapper` (z. B. future) — damit ich von Anfang an weiß, *was* ich analysiere und *in welcher Hülle*.
- Als **Analyst** möchte ich **Gold als Future (`GC=F`) vs. Gold als physisches ETC** vergleichen und den Unterschied in **Roll-Yield und Hebel** sehen, damit ich verstehe, warum dieselbe Goldmeinung in zwei Hüllen unterschiedliche Renditen/Risiken bringt.
- Als **Analyst** möchte ich bei einer **Ölaktie** (underlying=equity) das **Öl-Signal aus dem Cockpit als Rücken- oder Gegenwind** angezeigt bekommen, damit ich sehe, ob der Rohstoff-Treiber für oder gegen meine Aktien-These spricht — ohne selbst die Verbindung herstellen zu müssen.
- Als **Analyst** (Aktie) möchte ich die **Fundamental-Bewertung** (KGV, EV/EBITDA, DCF), **Qualität** (Margen, ROIC, Altman-Z), **Short-Interest, Insider, Earnings-Trend, Moat** und die **Bewertungs-Bandbreite** über mehrere Methoden sehen, damit ich ein vollständiges Bottom-Up-Bild bekomme.
- Als **Analyst** (Anleihe, underlying=bond) möchte ich **Duration, Credit-Rating und Spread** sehen, damit ich Zins- und Ausfallrisiko getrennt einschätzen kann.
- Als **Analyst** (Index, underlying=equity_index) möchte ich **Bewertung, Breadth, Momentum und Sektorkomposition** sehen, damit ich erkenne, ob ein Index breit getragen oder von wenigen Titeln getrieben wird.
- Als **Analyst** (Rohstoff/Edelmetall) möchte ich **Supply/Demand, Saisonalität, COT** bzw. **Cross-Metal-Ratios** sehen, damit ich rohstoffspezifische Treiber statt Aktien-Logik nutze.
- Als **Skeptiker** möchte ich pro Deep-Dive sehen, **welche Sub-Agenten UNAVAILABLE** geliefert haben (Stub/Datenquelle aus), damit ich nicht ein „neutrales" Signal mit einem „fehlt"-Signal verwechsle.

### 2.3 Long- UND Short-Urteil pro Titel (XAI)

- Als **Analyst** möchte ich pro Titel **zwei Urteile nebeneinander** sehen — Long (BUY/SELL/HOLD/NONE) und Short (SHORT/COVER/HOLD/NONE) — je mit eigener Konfidenz, damit ich auf einen Blick sehe, ob die Long- und die Short-Seite konsistent oder widersprüchlich sind.
- Als **Skeptiker** möchte ich zu jedem Urteil die **XAI-Begründung** lesen: welche Signale entscheidend waren, wo Widersprüche lagen, warum diese Konfidenz und **was die Einschätzung kippen würde**, damit ich der Empfehlung begründet folgen oder widersprechen kann.
- Als **Skeptiker** möchte ich sehen, wenn die Konfidenz **< 0.50** ist (→ automatisch HOLD) bzw. **< 0.35** (→ Cash-Bias), damit ich „zu unsicher" nicht mit „neutral gut" verwechsle. *(Regel aus `frontend_notes.md`.)*
- Als **Analyst** möchte ich den **Backtester-Kontext** für diesen Ticker sehen (wie treffsicher war das System hier bisher), damit ich die aktuelle Konfidenz historisch einordne.
- Als **Skeptiker** möchte ich den **Anomalie-Report** (statistische Ausreißer |Z|>2.0 + Signalwidersprüche, Schwere none/low/medium/high) am Urteil sehen, damit ich gewarnt bin, wenn die Datenlage ungewöhnlich ist. *(Aus `frontend_notes.md`.)*

### 2.4 Portfolio-Manager (Track B)

- Als **PM** möchte ich **alle Positionen** (long und short) mit beiden Etiketten, Größe, Einstand und aktuellem AAIA-Urteil in einer Tabelle sehen, damit ich Bestand und Meinung an einem Ort habe.
- Als **PM** möchte ich **Netto- und Brutto-Exposure** sowie das **`net_beta`** (aktien-only, datierte Vola — vgl. PR #11) sehen, damit ich weiß, wie marktsensitiv mein Portfolio netto ist.
- Als **PM** möchte ich **Klumpen-Warnungen** (Sektor, Asset-Klasse/underlying, Geographie) sehen, damit ich Konzentrationsrisiken früh erkenne.
- Als **PM** möchte ich **Hedge-Vorschläge (Track B)** bekommen (z. B. „net_beta zu hoch → erwäge Index-Short / VIX-Hedge"), damit ich konkrete Schritte zur Risikoreduktion habe — beratend, nicht ausführend.
- Als **PM** möchte ich, dass das System keine Trades ausführt, sondern nur **vorschlägt**, damit ich die Kontrolle behalte.

### 2.5 Konflikt-Inbox (gehaltene These gekippt)

- Als **PM** möchte ich eine **Inbox**, die mich benachrichtigt, wenn das AAIA-Urteil zu einer **gehaltenen Position kippt** (z. B. ich bin long, neues Urteil ist SELL/SHORT), damit ich nicht manuell jeden Titel nachprüfen muss.
- Als **PM** möchte ich pro Konflikt ein **beratendes Verdikt EXIT / HOLD / REVERSE** mit Begründung sehen, damit ich eine klare Handlungsoption (mit Argumenten) habe.
- Als **PM** möchte ich Konflikte als **offen → erledigt** abarbeiten (entschieden: gefolgt / ignoriert / vertagt) und die Entscheidung protokollieren, damit ich später nachvollziehe, warum ich wie gehandelt habe.

### 2.6 Backtester

- Als **Skeptiker** möchte ich sehen, **ob die alten Calls Geld gebracht hätten** — getrennt nach Top-Down (Regime korrekt? 30/60/90 Tage), Bottom-Up (dominantes Signal korrekt?) und Judgment (BUY/SELL/HOLD/SHORT profitabel?) — damit ich dem System nur so weit traue, wie seine Historie es rechtfertigt.
- Als **Analyst** möchte ich die Treffsicherheit **pro Ticker / pro Asset-Klasse / pro Regime** filtern, damit ich erkenne, *wo* das System gut und wo es schwach ist.

### 2.7 Futures-spezifisch

- Als **Analyst** möchte ich bei `wrapper=future` die **Terminkurve** (Contango vs. Backwardation) als Kurve über die Kontraktmonate sehen, damit ich die Form der Kurve sofort lese.
- Als **Analyst** möchte ich den **Roll-Yield** (positiv bei Backwardation, negativ bei Contango) als Zahl + Vorzeichen sehen, damit ich den strukturellen Rücken-/Gegenwind beim Halten verstehe.
- Als **Analyst** möchte ich **Verfallsdatum und nächsten Roll-Termin** sehen, damit ich weiß, wann gerollt werden muss und wann Roll-Kosten anfallen.
- Als **PM** möchte ich **Margin und effektiven Hebel** der Future-Position sehen, damit ich das wahre Risiko (nicht nur den Nominalwert) einschätze.

---

## 3. Informationsarchitektur (Navigation)

Globale, persistente Seitennavigation (links bei Desktop). Fünf Hauptbereiche + globale Suche + Konflikt-Inbox-Badge.

```
┌──────────────────────────────────────────────────────────────────────┐
│  AAIA   [ 🔍 Ticker/Markt suchen … ]            Inbox(3) ▣   ⚙  ◐/☀  │
├───────────────┬──────────────────────────────────────────────────────┤
│ ▣ Cockpit     │                                                        │
│ ◆ Deep-Dive   │   < Inhaltsbereich des aktiven Hauptbereichs >         │
│ ⬚ Portfolio   │                                                        │
│ ✉ Inbox  (3)  │                                                        │
│ ↺ Backtester  │                                                        │
│ ───────────── │                                                        │
│ ⚙ Einstellung │                                                        │
└───────────────┴──────────────────────────────────────────────────────┘
```

**Hauptbereiche und Verschachtelung:**

1. **Cockpit (Top-Down)** — Landing-Page.
   - Übersicht (Regime + 5 Domänen-Kacheln)
   - Drill-downs je Domäne: Makro · Rohstoffe · Sentiment · Zinskurve · Sektoren
   - Spezial-Tabs: Buffett-Indikator · Big-Mac-Index
2. **Deep-Dive (Bottom-Up + Judgment)** — pro Ticker.
   - Header mit **underlying × wrapper**-Badges + Long/Short-Urteilspanel
   - Tabs (kontextabhängig je underlying): Bewertung · Qualität · Signale (Short-Interest/Insider/Earnings/Moat) · **Futures** (nur wenn wrapper=future) · XAI · Backtest-Kontext
   - **Vergleichsmodus**: zwei Wrapper desselben underlying nebeneinander (Gold-Future vs. Gold-ETC)
3. **Portfolio (Track B)** — Positionen, Exposure, Risiko, Hedge-Vorschläge.
4. **Inbox (Konflikte)** — offen → erledigt, beratendes EXIT/HOLD/REVERSE.
5. **Backtester** — Trefferquoten Top-Down / Bottom-Up / Judgment, filterbar.

**Querverbindungen (wichtig für den Flow):**
- Ticker-Klick in *Portfolio*, *Inbox* oder *Cockpit-Sektor* → öffnet den passenden *Deep-Dive*.
- Im *Deep-Dive* verlinkt das relevante Cockpit-Signal (z. B. Öl) zurück ins *Cockpit*-Drill-down.
- *Inbox*-Konflikt verlinkt auf die Position im *Portfolio* und den *Deep-Dive*.

---

## 4. Schlüssel-Ansichten / Widgets (mit Wireframe-Beschreibungen)

Konventionen für alle Widgets:
- **Signal-Farben:** BULLISH/BUY/COVER = grün, BEARISH/SELL/SHORT = rot, NEUTRAL/HOLD = grau-blau, **UNAVAILABLE = gestreift-grau** (eigener Zustand, siehe 5.4).
- **Konfidenz** immer als Balken 0–1 **mit Prozent-Label** daneben (nicht nur Farbe — Barrierefreiheit).
- Jede aggregierte Zahl ist **aufklappbar** zu „woraus berechnet" inkl. ausgefallener Quellen.

### 4.1 Cockpit — Regime-Übersicht (Landing)

```
┌─ MARKTREGIME ────────────────────────────────────────────────┐
│  ▶  AUFSCHWUNG            Konfidenz ▓▓▓▓▓▓▓░░░ 71%             │
│     „Frühzyklisch: fallende Inflation + steile Kurve.        │
│      Gegenwind: Sentiment leicht überhitzt."   [XAI ▾]        │
│  Quellen aktiv: 4/5   ·   ⚠ Sektoren UNAVAILABLE             │
└──────────────────────────────────────────────────────────────┘

┌ Makro ───────┐ ┌ Rohstoffe ──┐ ┌ Sentiment ──┐ ┌ Zinskurve ─┐ ┌ Sektoren ─┐
│ ● BULLISH    │ │ ◐ NEUTRAL   │ │ ● BEARISH   │ │ ● BULLISH  │ │ ▦ UNAVAIL │
│ Infl ↓ (USA) │ │ Öl +, Cu –  │ │ VIX hoch    │ │ 10/2 +0.4% │ │ Stub      │
│ Conf 78%     │ │ Conf 55%    │ │ Conf 64%    │ │ Conf 80%   │ │ —         │
└──────────────┘ └─────────────┘ └─────────────┘ └────────────┘ └───────────┘
        (Klick auf Kachel → Drill-down der Domäne)
```
**Zweck:** In drei Sekunden „wo stehen wir + wie sicher + was treibt/widerspricht". Die UNAVAILABLE-Kachel ist bewusst nicht grün/neutral, sondern als „fehlt" markiert.

### 4.2 Cockpit — Zinskurven-Drill-down

```
┌ ZINSKURVE ───────────────────────────────────────────────────┐
│  Rendite                                                       │
│   5% ┤                         ╭──────●30J                     │
│   4% ┤        ╭───●10J────────╯                                │
│   3% ┤   ●2J─╯                                                 │
│   2% ┤ ●3M                                                     │
│      └──┬────┬─────┬──────┬──────┬──── Laufzeit                │
│  Spreads:  10J/2J +0.40 ● │ 10J/3M +1.10 ● │ 30J/10J +0.70 ● │
│  Status: NICHT invertiert  →  BULLISH (kein Rezessions-Frühsignal) │
└──────────────────────────────────────────────────────────────┘
```
**Zweck:** Kurvenform + die drei benannten Spreads (Richtung explizit: `10J–2J`, vgl. AGENTS.md §3) + Invertierungs-Flag.

### 4.3 Cockpit — Buffett-Indikator-Widget *(aus `frontend_notes.md`)*

Default = **sortierbare Tabelle** (entscheidbar, siehe §6.3); optionaler **Weltkarten-Tab**.

```
┌ BUFFETT-INDIKATOR  (Marktkap/BIP × 100)   [Tabelle ▣][Karte ◻] │
│ Filter: [ ] nur Z-Ausreißer  [ ] nur BEARISH    Global-Median: 92% │
│ ── Berechnung: USA via FRED (Echtzeit) · andere via Weltbank (jährl.)│
│ ┌──────┬────────┬────────┬───────┬──────┬──────────────────────┐ │
│ │ Land │ Ratio% │ Signal │ Z-Sc. │ Jahr │ vs. Median           │ │
│ ├──────┼────────┼────────┼───────┼──────┼──────────────────────┤ │
│ │►USA◄ │ 198%   │ BEAR ● │ +2.1⚠ │ live │ ▓▓▓▓▓▓▓▓▓ deutl. >    │ │ ← analysiertes Land hervorgehoben
│ │ CH   │ 220%   │ BEAR ● │ +0.6  │ 2024 │ ▓▓▓▓▓▓▓▓▓▓ >          │ │
│ │ DE   │  58%   │ BULL ● │ -0.9  │ 2024 │ ▓▓▓ <                 │ │
│ └──────┴────────┴────────┴───────┴──────┴──────────────────────┘ │
│ ⓘ Einschränkungen: Globalisierung · Zinskontext · kein Timing ·   │
│   Aktienrückkäufe   (verzerren nach oben)              [mehr ▾]    │
│ Asset-Filter: nur Aktien/ETF/Index relevant — bei Bond/Commodity ausgeblendet │
└──────────────────────────────────────────────────────────────────┘
```
**Zweck & übernommene Regeln:** Z-Score gegen *eigene* 10-J-Historie, |Z|≥1.5 = auffällig (⚠), **Datenjahr** sichtbar (Weltbank-Verzögerung), Global-Median als Referenz, analysiertes Land hervorgehoben, Einschränkungen Pflicht, Asset-Klassen-Filter. **Offene Punkte (§6):** Karte vs. Tabelle, Einzelland-10-J-Drill-down.

### 4.4 Cockpit — Big-Mac-Index-Widget *(aus `frontend_notes.md`)*

Horizontaler Balken (Über-/Unterbewertung vs. USD), analysiertes Land hervorgehoben, **Publikationsdatum** sichtbar (halbjährlich Jan/Jul). Einschränkungen optional einklappbar.

### 4.5 Deep-Dive — Header mit zwei Etiketten + Long/Short-Panel

```
┌ GC=F  ·  Gold ───────────────────────────────────────────────┐
│  [ underlying: PRECIOUS_METAL 🥇 ]  [ wrapper: FUTURE ⏳ ]      │  ← zwei Badges
│  Kurs 2.380 USD   ·   Markt: COMEX   ·   ⤳ vergleichen mit ▾   │
├──────────────────────────────┬───────────────────────────────┤
│  LONG-LINSE                   │  SHORT-LINSE                   │
│  ▶ HOLD                       │  ▶ NONE                        │
│  Konfidenz ▓▓▓▓░░░░ 47%       │  Konfidenz ▓▓░░░░░░ 22%        │
│  ⚠ <0.50 → auto-HOLD          │                               │
│  „Roll-Gegenwind (Contango)   │  „Kein tragfähiger Short:      │
│   bremst Long; Makro stützt." │   Realzins-Druck nicht stark." │
│  [ XAI ▾ ]                    │  [ XAI ▾ ]                     │
└──────────────────────────────┴───────────────────────────────┘
   Tabs: [Bewertung][Qualität][Signale][⏳ Futures][XAI][Backtest]
```
**Zweck:** Beide Etiketten oben, **Long und Short strikt gleichwertig nebeneinander**, Konfidenz mit %-Label, Auto-HOLD-/Cash-Bias-Hinweise inline. Tab-Set ist kontextabhängig (z. B. „Moat/Insider" nur bei underlying=equity; „Futures" nur bei wrapper=future).

### 4.6 Deep-Dive — XAI-Panel

```
┌ XAI — warum HOLD (long), Konfidenz 47% ──────────────────────┐
│  Entscheidende Signale (Treiber):                             │
│   + Makro-Regime AUFSCHWUNG stützt Edelmetall   (+)           │
│   – Contango → Roll-Yield −3,1%/Jahr Gegenwind  (−)           │
│   – Sentiment überhitzt                          (−)          │
│  Widersprüche: Top-Down bullish vs. Roll-Struktur bearish     │
│  Konfidenz-Begründung: 2 starke Gegensignale + 1 Quelle UNAVAIL │
│  Was es kippen würde: Wechsel in Backwardation ODER Realzins ↓ │
└──────────────────────────────────────────────────────────────┘
```
**Zweck:** Macht die vier README-XAI-Fragen explizit (entscheidende Signale · Widersprüche · warum diese Konfidenz · was kippt). Treiber mit Vorzeichen (+/−) — keine magischen Zahlen ohne Begründung (AGENTS.md §3).

### 4.7 Deep-Dive — Futures-Tab (Terminkurve + Roll)

Siehe Spezialfall 5.1.

### 4.8 Portfolio — Übersicht & Risiko (Track B)

```
┌ PORTFOLIO-RISIKO ────────────────────────────────────────────┐
│  Brutto-Exposure 142%  │  Netto-Exposure +38%  │  net_beta 0.62 │
│  (Σ|Pos|)              │  (long−short)         │  (aktien-only) │
│  ⚠ KLUMPEN: Tech 41% (Limit 30%)  ·  USA 78%  ·  equity 84%    │
│  HEDGE-VORSCHLÄGE (beratend):                                  │
│   • net_beta 0.62 senken → Index-Short SPY ~8% oder VIX-Hedge  │
│   • Tech-Klumpen → Teilverkauf oder Sektor-Short               │
└──────────────────────────────────────────────────────────────┘

┌ POSITIONEN ──────────────────────────────────────────────────┐
│ Titel │ L/S │ underlying×wrapper │ Größe │ Einstand │ AAIA-Urteil │
├───────┼─────┼────────────────────┼───────┼──────────┼─────────────┤
│ AAPL  │ LONG│ equity · single    │  12%  │  185.20  │ HOLD 52% ◐  │
│ GC=F  │ LONG│ precious · future⏳ │   6%  │  2.310   │ HOLD 47% ◐  │
│ TSLA  │ SHORT│ equity · single   │  -5%  │  240.00  │ SHORT 61% ●▼│ ← Urteil stützt Position
│ XLE   │ LONG│ equity_idx · fund  │   9%  │   88.40  │ SELL 58% ●▲ │ ← ⚠ Urteil gegen Position → Inbox
└───────┴─────┴────────────────────┴───────┴──────────┴─────────────┘
```
**Zweck:** Exposure-Kennzahlen mit kurzer Definition inline (PM ist evtl. nicht Jargon-fest). `net_beta` als **aktien-only** gekennzeichnet (vgl. PR #11). Klumpen-Warnungen mit Limit-Bezug. **Konflikt-Markierung** (Urteil vs. Positionsrichtung) speist die Inbox.

### 4.9 Inbox — Konflikt-Karten (offen → erledigt)

```
┌ KONFLIKT-INBOX  ────────────  [ Offen (3) ][ Erledigt ]  ─────┐
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ XLE — du bist LONG, neues Urteil: SELL (58%)             │ │
│ │ Verdikt:  ⟨ EXIT ⟩   HOLD    REVERSE        (beratend)   │ │
│ │ „Energie-Sektor dreht im Regimewechsel; Öl-Signal kippt." │ │
│ │ [ Folgen → Position schließen-Notiz ] [ Ignorieren ] [↗ Deep-Dive ] │ │
│ └──────────────────────────────────────────────────────────┘ │
│ … weitere Karten …                                            │
└──────────────────────────────────────────────────────────────┘
```
**Zweck:** Eine Karte pro gekipptem Titel; **beratendes** Verdikt EXIT/HOLD/REVERSE (Default hervorgehoben), Begründung, Aktionen führen *keine* Trades aus, sondern markieren erledigt + protokollieren die Entscheidung. Erledigt-Tab = Audit-Trail.

### 4.10 Backtester — Trefferquoten

Drei Karten (Top-Down / Bottom-Up / Judgment) mit Trefferquote, Stichprobengröße und Equity-/Trefferkurve; Filter nach Ticker / Asset-Klasse / Regime / Zeitfenster (30/60/90 T). **Zweck:** „hätten die alten Calls Geld gebracht" — und *wo* das System stark/schwach ist.

---

## 5. Spezialfälle

### 5.1 Futures-Terminkurve + Roll-Yield

Nur sichtbar bei `wrapper=future`. Zwei Teile: **Kurvenform** (Contango/Backwardation) + **Roll-Kennzahlen**.

```
┌ FUTURES — TERMINKURVE ───────────────────────────────────────┐
│  Preis                          CONTANGO (aufwärts → Gegenwind)│
│  2.45k ┤                       ╭─────●Dez                      │
│  2.42k ┤              ╭───●Sep─╯                               │
│  2.40k ┤   ●Spot──●Jun                                         │
│        └────┬───────┬─────────┬───────── Kontraktmonat         │
│                                                                │
│  Roll-Yield:  −3,1 %/Jahr  ▼  (negativ = Halten kostet)        │
│  Form:        CONTANGO                                          │
│  Verfall akt. Kontrakt:  2026-06-26                            │
│  Nächster Roll:          in 5 Tagen  ⏳                         │
│  Margin (Initial):       7.150 USD   →  Hebel ≈ 33×            │
└──────────────────────────────────────────────────────────────┘
```
**Fachliche Korrektheit (AGENTS.md §3):**
- **Contango** = Terminpreis > Spot → Kurve steigt → **Roll-Yield negativ** (Gegenwind beim Rollen). **Backwardation** = umgekehrt → Roll-Yield positiv. Vorzeichen und Richtung werden **im Widget benannt**, nicht nur als Farbe.
- Roll-Yield als **%/Jahr** annualisiert, Vorzeichen explizit.
- **Hebel = Nominalwert / Margin** — als Faktor, damit das wahre Risiko (nicht der Nominalwert) sichtbar ist.
- Verfall + nächster Roll-Termin mit Countdown, damit Roll-Kosten/Timing nicht überraschen.

### 5.2 underlying × wrapper sichtbar machen

- **Zwei farbcodierte Badges** überall, wo eine Anlage auftaucht (Suchergebnis, Deep-Dive-Header, Portfolio-Zeile, Inbox-Karte). `underlying` = Form/Material-Icon (🥇 Edelmetall, 🛢 Commodity, 🏛 Bond, 📈 equity_index, 🏢 equity); `wrapper` = Hüllen-Icon (single, fund, future ⏳, physical_etc).
- **Doppelter Filter** in Suche/Portfolio: „zeige alle `commodity`" **und/oder** „zeige alle `future`". So findet der Nutzer z. B. *alle Future-Positionen* (Roll-/Margin-Risiko) quer über underlyings.
- **Vergleichsmodus** im Deep-Dive: gleicher `underlying`, zwei `wrapper` nebeneinander.

```
┌ VERGLEICH — underlying GOLD, zwei Hüllen ────────────────────┐
│                  │  GC=F (FUTURE ⏳)   │  4GLD (PHYSICAL_ETC) │
│  Basiswert       │  Gold              │  Gold                │
│  Roll-Yield      │  −3,1 %/Jahr ▼     │  — (kein Roll)       │
│  Hebel           │  ≈ 33×             │  1× (voll besichert) │
│  laufende Kosten │  Roll-Kosten       │  TER ~0,2 %/Jahr     │
│  Gegenparteirisk │  Börse/Clearing    │  phys. hinterlegt    │
│  Long-Urteil     │  HOLD 47%          │  BUY 58%             │
└──────────────────────────────────────────────────────────────┘
```
**Zweck:** Dieselbe Gold-Meinung, unterschiedliche Hülle → unterschiedliche Rendite/Risiko. Macht „Roll/Hebel vs. physisch" greifbar (User-Story 2.2).

### 5.3 Long- vs. Short-Linse nebeneinander + Konfidenz

- **Immer zwei Spalten** (links Long, rechts Short), nie eine Spalte mit Umschalter — die Gleichwertigkeit ist Teil der Aussage.
- Jede Linse: Urteil (Wort + Farbe), Konfidenzbalken **mit %**, Kurzbegründung, XAI-Aufklapp.
- **Konsistenz-Hinweis**: Wenn beide Linsen in dieselbe Richtung zeigen (z. B. Long=SELL & Short=SHORT) → starkes bearishes Gesamtbild markieren; wenn beide schwach/NONE → „kein Edge".
- **Schwellen-Flags** inline: Konfidenz <0.50 → Auto-HOLD-Badge; <0.35 → Cash-Bias-Badge (`frontend_notes.md`).

### 5.4 „Daten nicht verfügbar" (UNAVAILABLE) — eigener Zustand

Viele Quellen sind aktuell Stubs. Leitprinzip (AGENTS.md §3, „Datenrealität"): **UNAVAILABLE ≠ 0 ≠ NEUTRAL.**

- **Eigene Visualität:** gestreift-graues Feld + „nicht verfügbar"-Label + Grund-Tooltip („Datenquelle Stub / API-Fehler / verzögert"). Niemals als 0, leerer Balken oder grünes Neutral darstellen.
- **Aus Aggregation ausgenommen:** Ein UNAVAILABLE-Sub-Agent zählt **nicht** als neutrales Signal; er **senkt die Konfidenz** der übergeordneten Kachel/des Urteils. Die Kachel zeigt „Quellen aktiv: 4/5".
- **Sichtbarer Daten-Health-Indikator:** Pro Cockpit-Domäne und pro Deep-Dive ein kleiner „x/y Quellen aktiv"-Zähler; Klick listet die ausgefallenen Quellen.
- **Stale vs. fehlend unterscheiden:** Verzögerte aber vorhandene Werte (z. B. Weltbank-Jahreszahl, Big-Mac halbjährlich) tragen ein **Datums-/Jahres-Label** (kein UNAVAILABLE) — nur *ganz* fehlende Werte sind UNAVAILABLE.

```
Beispiel Kachel:   ┌ Sektoren ─────┐      Beispiel Zeile:
                   │ ▦▦▦ UNAVAIL   │      ROIC:  ▦ nicht verfügbar (Stub)
                   │ Stub-Quelle   │      Margin: 18,4 %  (Q1 2026)
                   │ Konf-Beitrag 0│
                   └───────────────┘
```

---

## 6. Entscheidungen (am 2026-06-21 mit dem Nutzer getroffen)

> **Status: am 2026-06-21 entschieden** (Werte je Punkt unten als „ENTSCHIEDEN" markiert). Drei Punkte überstimmen bewusst die ursprüngliche Agenten-Empfehlung (Framework, Echtzeit, Big-Mac). Die Entscheidungen sind beim Finalisieren ins Logbuch `docs/open_todos.md` zu übernehmen. Ausgangspunkt: `frontend_notes.md` → „Offene Entscheidungen" plus die im Auftrag genannten Fragen.

### 6.1 Framework: React / Vue / Svelte — *ENTSCHIEDEN (2026-06-21): React*
- **Entscheidung: React** (überstimmt die ursprüngliche SvelteKit-Empfehlung). Begründung: Das Tool ist **chart-/tabellen-lastig** und wird **stark KI-gestützt** gebaut → React bietet das größte Ökosystem fertiger Chart-/Tabellen-Bausteine und die **zuverlässigste KI-Codegenerierung**; „weniger Code" (Sveltes Vorteil) zählt wenig, da der Code nicht von Hand getippt wird. Charting bleibt framework-agnostisch (ECharts/Lightweight-Charts).
- **Empfehlung: Svelte/SvelteKit.** Begründung: Das Frontend ist **datendicht** (viele kleine reaktive Widgets, Tabellen, Kurven), aber kein riesiges Team-Projekt. Svelte hat das kleinste Runtime-/Build-Gewicht, sehr direkte Reaktivität (gut für viele Live-Zahlen) und eine flache Lernkurve — passt zu einem FHNW-BI-Projekt mit einer/wenigen Personen.
- **Gegen React:** mächtigstes Ökosystem (Charting-Libs!), aber mehr Boilerplate/Overhead. **Falls Charting-Bibliotheken** (z. B. ausgereifte Finanz-Charts) den Ausschlag geben, ist React die sichere Alternative — das ist das einzige starke Argument, das die Empfehlung kippen könnte. **Vue** liegt dazwischen, ohne in einem Punkt klar zu gewinnen.
- **Charting unabhängig vom Framework:** ECharts oder Lightweight-Charts (TradingView) für Terminkurve/Zinskurve/Equity-Kurven — beide framework-agnostisch.

### 6.2 Mobile-first vs. Desktop-first — *ENTSCHIEDEN (2026-06-21): Desktop-first, responsiv*
- **Empfehlung: Desktop-first** mit responsivem Tablet-Fallback. Begründung: Side-by-side-Vergleiche (Long/Short, Future/ETC), breite Portfolio-Tabellen mit zwei Badges + Exposure, Cockpit mit 5 Kacheln und Kurven brauchen **Bildschirmbreite**. Analyse/PM-Arbeit passiert am Desktop. Mobile dient eher der **Inbox-Benachrichtigung** → dafür eine schlanke Inbox-/Alert-Ansicht responsiv anbieten, nicht das ganze Tool für Handy optimieren.

### 6.3 Buffett-Widget: Weltkarte vs. Tabelle — *ENTSCHIEDEN (2026-06-21): Tabelle (Default) + Karte als Tab + Drill-down*
- **Empfehlung: sortierbare Tabelle als Default, Choropleth-Weltkarte als optionaler Tab.** Begründung: Die Kernaufgaben sind *sortieren, filtern (Z-Ausreißer/BEARISH), exakte Werte + Datenjahr ablesen, ein Land hervorheben* — das kann eine Tabelle präziser als eine Karte. Die Karte liefert die schnelle globale Intuition (rot/grün-Cluster) und ist ein starkes Demo-Feature, daher als zweiter Tab. **Drill-down Einzelland-10-J-Zeitreihe** (aus `frontend_notes.md`) in beiden Ansichten via Zeilen-/Länder-Klick — ebenfalls noch zu entscheiden, aber empfohlen, weil der Z-Score ohne Verlaufskontext schwer zu deuten ist.

### 6.4 Echtzeit-Refresh: WebSocket vs. Polling — *ENTSCHIEDEN (2026-06-21): WebSocket (live) von Anfang an*
- **Entscheidung: WebSocket/Live von Beginn** (überstimmt die Polling-zuerst-Empfehlung). Wichtige Einordnung: WebSocket macht nur die Strecke **Server → Browser** sofort; die **externen Quellen** (FRED, yfinance …) bleiben abruf-basiert — der Server muss sie weiterhin **geplant pollen** und pusht dann an den Browser. „Live" = der Browser sieht neue Daten, sobald der Server sie hat (nicht: externe Quellen werden sekundengenau).
- **Empfehlung: mit Polling starten** (Cockpit/Deep-Dive alle 60–120 s; Daten ändern sich makro-/tageszeitlich, nicht im Sekundentakt). **WebSocket später gezielt für die Konflikt-Inbox** (Push, wenn eine gehaltene These kippt — da ist Latenz wirklich relevant). Begründung: Polling ist deutlich einfacher und für den Datencharakter (verzögerte Quellen!) ausreichend; WebSocket nur dort, wo „sofort erfahren" echten Wert hat.

### 6.5 Big-Mac-Refresh: manuelle Pflege vs. API — *ENTSCHIEDEN (2026-06-21): Automatischer Abruf*
- **Entscheidung: automatischer Abruf** (überstimmt die manuelle-Pflege-Empfehlung). Da es keine offizielle API gibt: ein **geplanter Abruf** der CSV vom Economist-GitHub (z. B. wöchentlich/monatlich) mit **Rückfall auf die zuletzt gespeicherte Version**, falls die Quelle nicht erreichbar ist (defensiv). Publikationsdatum im UI weiterhin anzeigen.
- **Empfehlung: manuelle halbjährliche Pflege** über einen versionierten Datensatz (Economist veröffentlicht Jan/Jul, öffentlich, keine stabile Gratis-API). Im UI das **Publikationsdatum** zeigen (bereits in `frontend_notes.md` gefordert), damit klar ist, wie alt die Daten sind. Aufwand: 2×/Jahr — vertretbar gegenüber einer fragilen Scraping-/API-Lösung.

### 6.6 Daten-Health / UNAVAILABLE-Sichtbarkeit — *ENTSCHIEDEN (2026-06-21): aufnehmen*
- Über die explizit gestellten Fragen hinaus, aber zentral: **Empfehlung, einen globalen „Daten-Health"-Indikator** (x/y Quellen aktiv, Liste der Stubs) im Header zu führen, weil aktuell viele Quellen Stubs sind. Verhindert, dass UNAVAILABLE als „alles okay" missverstanden wird. (Verknüpft mit 5.4.)

---

## 7. Nächste Schritte

1. **Entscheidungen finalisieren** (Abschnitt 6) — Framework, Layout, Refresh, Buffett-Darstellung, Big-Mac-Pflege — und die getroffenen Entscheidungen ins Logbuch `docs/open_todos.md` übertragen (Status gehört dorthin, nicht in dieses Design-Dokument; AGENTS.md §5).
2. **Backend-Vertrag prüfen:** Liefert die Domäne bereits `underlying`/`wrapper`, Long- *und* Short-Urteil, Future-Roll-Kennzahlen, Portfolio-`net_beta`/Exposure, Konflikt-Verdikt? Lücken als Folge-Tasks im Logbuch erfassen (mit Lösungsansatz).
3. **UNAVAILABLE-Kontrakt definieren:** Einheitliches Feld/Enum (`UNAVAILABLE`) im Backend-Output, das das Frontend eindeutig vom Wert 0/NEUTRAL trennt — Grundlage für 5.4.
4. **Wireframes → klickbarer Prototyp** der drei wichtigsten Flows: Cockpit-Übersicht, Deep-Dive (mit Long/Short + Futures-Tab), Inbox-Konflikt.
5. **Komponenten-Bibliothek** der wiederkehrenden Bausteine: Signal-Badge, underlying×wrapper-Doppelbadge, Konfidenzbalken-mit-%, XAI-Aufklapp, UNAVAILABLE-Feld, Kurven-Chart (Zins/Termin).
6. **TDD beibehalten:** Reine Anzeige-Logik (Farbzuordnung Signal→Farbe, Roll-Yield-Vorzeichen, Konfidenz-Schwellen-Flags <0.50/<0.35, UNAVAILABLE-Ausschluss aus Aggregaten) als testbare pure Funktionen kapseln und zuerst testen (AGENTS.md §4).

---

*Querverweise: `README.md` (Architektur, Methoden, Backtester), `docs/frontend_notes.md` (Buffett-/Big-Mac-Widget, UI-Prinzipien, Ausgangs-Fragen). Status/PR-Protokoll: `docs/open_todos.md`.*
