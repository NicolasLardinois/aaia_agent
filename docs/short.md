# Shorts — Gesamtbericht (alles zum Thema an einem Ort)

**Stand:** 2026-06-18 · **Status:** Design abgeschlossen für den Foundation-Block; Umsetzung beginnt.
Dieser Bericht ist die **eine Anlaufstelle** zum Thema Short. Überschneidungen mit `docs/open_todos.md` §9 sind bewusst.

Verwandte Dokumente:
- Spec Foundation-Block: `docs/superpowers/specs/2026-06-18-foundation-aktions-taxonomie-design.md`
- Backlog/Notizen: `docs/open_todos.md` §9 „SHORTS AUSBAUEN"

---

## Inhalt
1. Vision & Ziel
2. Zwei Tracks (A aggressiv / B Hedge)
3. Die 4 Blöcke
4. Architektur-Entscheidung (geteilte Fakten + Short-Schicht; A vor B)
5. Aktions-Taxonomie (long + short)
6. Equity-Short-Thesis-Engine (Kriterien-Katalog)
7. Archetypen & Gating-Regeln
8. `ShortAssessment`-Modell
9. Risiko & Sizing (#2)
10. Asset-Klassen-Roadmap (Equity → Rohstoff/Anleihe/Edelmetall; Futures-Idee)
11. Momentum (gemeinsam long + short)
12. Portfolio-Manager (Befund + Ausbau)
13. Profi-Kritik (CFA-L3 / Hedgefonds-Sicht)
14. Foundation-Block (erster Bauabschnitt)
15. Datenlage (was vorhanden, was dormant)
16. Build-Reihenfolge
17. Entscheidungs-Log

---

## 1. Vision & Ziel
Heute analysiert das Tool, ob ein Wertpapier **kaufenswert** (long) ist. Ziel: dieselbe Tiefe für die **Short-Seite** — das Tool gibt für eine Aktie auch ein **eigenständiges Short-Urteil** ab (inkl. Top-Down-Kontext), und hilft, bestehende Short-Positionen zu **managen** (eröffnen/aufstocken/halten/eindecken).

**Grundsatz:** Ein Short ist **nicht** das Spiegelbild eines Longs. „Teuer" allein ist nie ein Short (teure Werte bleiben oft jahrelang teuer). Es braucht einen echten Grund zu **fallen** (Bilanz-Distress, Earnings-Kollaps, Betrug) + möglichst einen **Katalysator**.

## 2. Zwei Tracks (nicht vermischen)
- **Track A — Aggressiver Einzelaktien-Short** (Gewinn-Motiv): „diese Aktie ist schlecht → Gewinn bei Fall". Input = Einzelaktien-Tiefenanalyse. Heimat = **Stock Deep Dive / Judgment**.
- **Track B — Defensiver Hedge** (Schutz-Motiv): „mein Buch ist zu exponiert → absichern". Input = **Portfolio-Aggregat** (Netto-Long, Beta, Klumpen) + **Makro-Regime**. Instrument = breiter Index/ETF. Heimat = **Portfolio-Manager + Cockpit**.

Andere Inputs, Logik, Instrumente, Risiken. **Block #3** ist die Weiche, welcher Track gilt.

## 3. Die 4 Blöcke
| # | Ebene | Frage | Inhalt |
|---|---|---|---|
| **1** | Signal | WAS shorten? | eigene Short-These (Kriterien-Katalog) → Note + Archetyp + Gründe |
| **2** | Risiko | WIE VIEL / WIE GEFÄHRLICH? | Borrow/Squeeze, asymmetrisches Risiko, Positionsgröße, Stop |
| **3** | Strategie | OB / WANN überhaupt? | Regime-/Track-Weiche; Track-B-Hedge im Portfolio-Manager |
| **4** | Bewertung | HAT'S FUNKTIONIERT? | Short-Backtest (gespiegelte Returns, Borrow-Kosten, getrennt) |

Reihenfolge: **Foundation-Block → #1+#2 (Track A, Equity) → #3 → #4**. B (LLM-These) quer dazu.

## 4. Architektur-Entscheidung
**Geteilte Fakten + Short-Schicht:** Die bestehenden Deep-Dive-Sub-Agenten beschaffen die Fakten **einmal**; eine eigene Short-Schicht interpretiert sie short-spezifisch. **Ein Analyselauf → zwei unabhängige Urteile** (Long via `derive_recommendation`, Short via neuer `derive_short_assessment`).

Verworfen: (a) komplett getrenntes Short-Subsystem (dupliziert Faktenbeschaffung); (b) invertierte Schwellen in `derive_recommendation` (vermischt Long/Short).

**A zuerst, B später (beide fest):**
- **A** = reine Funktion `derive_short_assessment` + `ShortAssessment`-Modell + Feld auf `DeepDiveResult` (strukturiertes Urteil, kein LLM, voll testbar).
- **B** = `ShortThesisAgent` (LLM-Fließtext-These + XAI) **auf** A — sobald die Engine steht. B ohne A wäre halluzinationsanfällig.

**Asset-class-dispatched:** Equity-Zweig zuerst voll; andere Klassen → Fallback „bearish + Sizing", bis ihr eigener Zweig kommt.

## 5. Aktions-Taxonomie (long + short)
Jede Analyse gibt **pro Linse genau eine Aktion**. **HOLD ≠ NONE:** HOLD setzt eine bestehende Position voraus; NONE = nicht investiert + kein belastbares Urteil. **Aufstocken (+)**: hält man bereits und das Einstiegssignal gilt weiter/verstärkt → nicht HOLD, sondern nachlegen.

| Lage | Long-Linse | Short-Linse |
|---|---|---|
| nicht gehalten + klares Einstiegssignal | **BUY** | **SHORT** |
| nicht gehalten + kein belastbares Urteil | **NONE** | **NONE** |
| gehalten + Signal gilt weiter/verstärkt | **BUY+** | **SHORT+** (selten sinnvoll) |
| gehalten + Lage unklar | **HOLD** | **HOLD** |
| gehalten + These gekippt | **SELL** | **COVER** |

**Defer-Symmetrie:** Genau die Linse der *gehaltenen* Seite ist aktiv; die Gegen-Linse gibt NONE. `LONG` → Short deferiert; `SHORT` → Long deferiert; flach → beide aktiv. (Man eröffnet keine Gegenposition zur bestehenden.)

**Short+ stark gegated:** Nachlegen in Shorts ist gefährlich (Risiko wächst überproportional, Squeeze) → nur wenn These verstärkt UND Position nicht im Verlust/Squeeze; nie gegen einen laufenden Short nachlegen. Default konservativ/aus. Buy+ (z. B. Nestlé, erneut starke Fundamentaldaten → zweite Tranche) ist unkritischer.

## 6. Equity-Short-Thesis-Engine (Kriterien-Katalog)
Modelliert als **Flag-Registry**: Liste von Flag-Definitionen (`name`, `kategorie`, `benötigte Felder`, `schwelle`, `gewicht`). Jedes Flag wird **defensiv** geprüft — fehlt die Quelle (`None`), feuert es nicht (kein Crash). Verfügbare Flags fließen in die **Konfidenz**; nicht-verfügbare sind **dormant**, bis ein Adapter die Quelle liefert (dann automatisch aktiv, ohne Logik-Änderung).

**Kern-These (allein ausreichend — mind. 1 nötig für einen Kandidaten):**
- **Distress/Bilanz** — `quality.altman_z` < 1,8 (Konkurszone), `interest_coverage` < 1, negativer `fcf_margin` + hohe Verschuldung, `current_ratio` < 1.
- **Earnings-Kollaps/Katalysator** — stark negative `earnings_trend.estimate_revision`, fallende `beat_rate`, Guidance-Cut.
- **Wachstums-Kollaps** — `fundamentals.revenue_cagr_3y` stark negativ.
- **Accounting-Fraud** (dormant) — Beneish M-Score.

**Verstärker (nur in Kombi mit ≥1 Kern-These; allein → NONE/„none"):**
- **Bewertungs-Extrem („teuer")** — `valuation_range` + `fundamentals` (KGV, EV/EBITDA, P/Book, P/FCF, PEG, Shiller-CAPE). Erhöht nur die Fallhöhe.
- **Schwacher Burggraben** — `moat.total_score`.
- **Insider-Verkäufe** — `insider.net_direction`.
- **Momentum/Technik** (dormant), **relative Schwäche** (dormant), **Sentiment/Positionierung** (dormant).
- **Squeeze/Short-Interest** — `short_interest` (DTC/Float): **Risiko-Modifikator**, kein Thesen-Treiber.

**Regel:** Kandidat nur, wenn **≥1 Kern-These** feuert. „teuer + schwacher Moat + Insider-Verkäufe" ohne Kern-These → **none**.

## 7. Archetypen & Gating-Regeln
**Archetyp(en)** (`ShortAssessment.archetypes` — eine **Menge, kein Ranking**): aus welchen Kern-Thesen feuern; macht das Urteil lesbar und sagt, was zu prüfen ist. Mehrere Typen gleichzeitig (z. B. `[distress, broken_growth]`) = **stärkere These → höhere Konfidenz**, keine Priorität.
Typen: `distress` (aktiv ← Bilanz-Distress) · `broken_growth` (aktiv ← Earnings-Kollaps **+** teuer) · `secular_decline` (aktiv ← `revenue_cagr_3y` stark negativ) · `fraud` (dormant ← Beneish) · `cyclical_peak` (dormant) · `none`.

**Hart-Gates (→ direkt NONE, VOR der Konfidenz, egal wie stark die These):**
- **Kein Top-Down** (`top_down_available == False`) — **Veto** (ohne Makro-Kontext zu riskant; deckt sich mit `FULL_ANALYSIS_MARKETS`), kein weicher Abschlag.
- **Keine Kern-These** — dann gibt es schlicht keine Short-These (kein Signal).

**Konfidenz-Modifikatoren (erst danach; formen `confidence` 0–1):**
- **Katalysator:** aktiver Katalysator (Earnings-Revision/Guidance-Cut, `earnings_trend.estimate_revision` = „Markt preist gerade ab") hebt die Obergrenze (volle Konfidenz möglich, broken_growth/Earnings-Fälle); **reine Distress-Lage** (Altman-Z rot) ohne aktive Verschlechterung → Konfidenz **gedeckelt** (Distress kann jahrelang krebsen). Harte Katalysatoren (Fälligkeits-Wall/Covenant) dormant.
- **Regime (Modifikator, KEIN Block):** bullisch/risk-on → **Gegenwind** (Konfidenz deutlich gedämpft, aber eine sehr starke Einzelthese kommt durch); neutral → kein Effekt; bearisch → Rückenwind.
- **Crowding:** hard-to-borrow + extremes DTC → Konfidenz runter (überfüllt/teuer = schlechter Trade).
- **Anomalien (geteilt mit Long, `AnomalyChiefAgent`):** statistisch abnormale bearishe Werte (Insider-Verkaufs-Cluster, Short-Interest-Spike, Bewertungs-z-Score-Extrem) **erhöhen die Konfidenz** — als **Modifikator, NICHT** als zusätzliches Flag (sonst Doppelzählung desselben Fakts). Erkannte Anomalien werden zudem im **finalen Nutzer-Output (LLM/XAI-Text)** ausgewiesen (Long-XAI enthält die `*_anomaly.summary` bereits; Short/B ebenso).
- **„Wird schlechter" vor „ist schlecht":** Verschlechterung (Trend) > statisches Niveau — heute fast nur dormant (Historie nötig; vorhanden bei `estimate_revision`).

**Aktion (aus Konfidenz + Position, analog Long):** nicht gehalten + Konfidenz ≥ Schwelle → **SHORT**, sonst **NONE**; short gehalten + ≥ Schwelle → **HOLD**, sonst **COVER**. **SHORT+ erst mit PM/Block #3** (braucht Einstand/P&L für „nie in Verlust nachlegen"). Long gehalten → Aktion **NONE**, aber **`conflict`** wenn Short-Konfidenz ≥ Schwelle (bidirektional, siehe §18).

**Positionierung:** vollwertiges Urteil = **Aktion + Konfidenz**, **identisch** zur Long-Seite — **nicht** „recherchier selbst". Die Vorsicht steckt in der **Konfidenz** (kalibriert), nicht in einem Hedge-Satz.

## 8. `ShortAssessment`-Modell (identisch zur Long-Seite: Aktion + Konfidenz)
- `asset_class`
- `short_action`: SHORT | COVER | HOLD | NONE  (**SHORT+ erst mit PM/Block #3**)
- `confidence`: 0–1 (short-spezifisch — aus Thesenstärke + **Anomalien** + Regime + Katalysator + Crowding + Kalibrierung; **KEIN `short_score`, KEINE 4-Stufen-Note**)
- `archetypes`: **Menge** der feuernden Typen (z. B. `[distress, broken_growth]`); **kein Ranking** — mehrere = stärkere These
- `thesis_flags`: list[str] (gefeuerte Gründe mit Zahlen = Begründung)
- `regime_effect`: „headwind" | „neutral" | „tailwind" (Konfidenz-Modifikator, **kein Block**)
- `conflict`: bool (+ Begründung) — bei gehaltener Gegenposition (Long-gehalten + Short-Signal); bidirektional via Judgment-Layer (§18)
- Risiko/Sizing: `squeeze_risk` (low/elevated/high), `hard_to_borrow` (Proxy-Flag), `borrow_rate_manual` (optional, default None), `suggested_size_pct`, `stop_pct`

## 9. Risiko & Sizing (#2)
- **Squeeze-Kennzahlen** vorhanden: `short_interest.short_float_pct`, `days_to_cover` (yfinance-Pfad). ✅
- **Positionsgröße/Stop** aus Confidence + Volatilität; konservativer als Long (asymmetrisches Verlustprofil — Verlust nach oben unbegrenzt). `_position_size_pct` existiert als Basis.
- **Borrow-Kosten** nicht frei verfügbar (IBKR/Ortex/S3, kostenpflichtig). → v1 **Hard-to-borrow-Proxy-Flag** (aus Short-Float/Float/DTC), KEIN erfundener Gebühren-Wert. Echte Leihgebühr später als **optionales manuelles Eingabefeld**.
- **Dividende beim Short:** wer short ist, zahlt die Dividende — realer Carry-Kostenpunkt (später).

## 10. Asset-Klassen-Roadmap
- **Equity — Bauabschnitt 1 (jetzt):** volle Short-These.
- **Rohstoff-Short (fest eingeplant, später):** eigene Spezifika — **Roll-Yield/Carry** (Contango/Backwardation), **Cost-Curve-Boden** (Mean-Reversion-Floor), **Angebotsschock-Squeeze**. Eigene Daten (Futures-Kurve, Produktionskosten).
- **Anleihen-Short (fest, später):** **Carry** (Kupon zahlt der Shortende), **Duration**, **Credit-Asymmetrie**.
- **Edelmetall-Short (fest, später):** analog Zyklus/Realzins.
- **Index/ETF:** kein „dieser Index ist schlecht"-Short → das ist **Track B (Hedge)**.
- **Futures als NEUE Anlageklasse** (Long UND Short) — unter Überlegung, **breiter als Shorts**, eigener Brainstorming-/Scope-Entscheid.

## 11. Momentum (gemeinsam long + short)
Equity hat heute **keinen** Momentum-Agenten (nur der Index hat einen). Sobald Momentum/Trend für Equity gebaut wird, kommt es als **neuer Bottom-up-Sub-Agent** (`MomentumSnapshot`, analog Index), der **beide** Seiten speist: Long-Empfehlung (Alignment) **und** Short-Schicht (aktiviert die dormanten Momentum-Flags). Begründung: nutzt Short Momentum, muss Long es auch. Eigener Folge-Block; in Block 1 dormant.

## 12. Portfolio-Manager (Befund + Ausbau)
**Heute long-only:** `data/portfolio.json`-Positionen haben **kein Richtungs-Feld** (`ticker, shares, buy_price, currency, sector, asset_class, country`). `agents/portfolio/portfolio_monitor_agent.py` rechnet P&L (`(current-buy)/buy`), Klumpen-/Exposure-Logik **als wäre alles long** — erkennt nicht long vs short. An die Urteilslogik geht nur ein **bool `in_portfolio`** (CLI-Flag).

**Ausbau (Track B / Block #3):** (1) `direction`/`side`-Feld je Position; (2) short-bewusste P&L (invertiert) + Netto-Long-vs-Short-Exposure; (3) daraus die **„aktuelle Position" (none/long/short)** ableiten, die die Short-Aktions-Logik speist; (4) **Reconciliation** (z. B. short + bullisches Signal → Short-Linse COVER, Long-Linse BUY — was tun, wenn beide feuern).

## 13. Profi-Kritik (CFA-L3 / Hedgefonds-Sicht)
**Stark:** „Valuation is not a catalyst" (teuer → nur Verstärker); Kern-These verpflichtend; Squeeze als Risiko, nicht Kaufgrund; Regime-Disziplin.
**Lücken (bewusst adressiert/dormant):**
- **Katalysator & Timing** fehlen als erste Klasse — Distress kann jahrelang bestehen; ohne zeitlich gebundenen Auslöser = Value-Trap-Short. → „kein Auslöser → max moderate".
- **Archetypen statt flacher Punkte-Summe** — verschiedene Short-Typen, verschiedene Risiken. → `archetype`-Tag.
- **Trend vor Level** — Verschlechterung schlägt statisches Niveau (sonst shortet man zyklische Titel am Margen-Tief). → dormant bis Historie.
- **Borrow/Crowding ins Go/No-Go**, nicht nur Sizing. → Crowding-Dämpfer auf die Note.
- **`confidence` ist long-kalibriert** — Short-Konviktion braucht eigene Kalibrierung (Block #4-Backtest).

## 14. Foundation-Block (erster Bauabschnitt)
Spec: `docs/superpowers/specs/2026-06-18-foundation-aktions-taxonomie-design.md`. Baut **nur** die Aktions-/Positions-Mechanik (nicht die Thesis-Engine):
- `current_position` (none/long/short) statt bool `in_portfolio`.
- `Recommendation`-Enum +NONE +BUY+; `derive_recommendation` auf Long-Matrix (BUY/BUY+/HOLD/SELL/NONE); **SHORT-Zweig entfernt**; Short-Position → Long-Linse deferiert.
- Neues `ShortAction`-Enum + **positionsbasierter Platzhalter** (NONE/HOLD; LONG → NONE = Short deferiert).
- Verdrahtung: `judgment_agent`, `judgment_orchestrator`, `result_cache`, `app/main.py` (CLI `--position long|short`, beide Aktionen anzeigen).
- **Bewusste Zwischenlücke:** Der naive SHORT entfällt; bis Block 1 gibt es für Short-Fälle kein Short-Signal (Short-Aktion NONE/HOLD). Akzeptiert.

## 15. Datenlage
**Vorhanden in `bottom_up` (BottomUpResult):** `fundamentals` (Multiples), `quality` (altman_z, interest_coverage, debt_to_equity, net_debt_ebitda, current_ratio, fcf_margin, roe/roa/roic, Margen), `earnings_trend` (beat_rate, estimate_revision), `moat` (total_score), `short_interest` (short_float_pct, days_to_cover), `insider` (net_direction), `valuation_range` (position, combined_low/high). Cockpit (Regime). Memory-Historie (für Trend/„verstärkt", später).
**Dormant (Quelle später):** Momentum/Technik, Katalysator (Fälligkeiten/Guidance), Accounting-Red-Flags (Beneish/Accruals/DSO), relative Schwäche, Verwässerung/Cash-Burn-Runway, echte Borrow-Rate.

## 16. Build-Reihenfolge
1. ~~Foundation-Block~~ ✅ **gemergt (PR #3)** — Aktions-Taxonomie (long + short).
2. **Block 1** — Equity-Short-Thesis-Engine (`derive_short_assessment`, **Aktion + Konfidenz**, Archetyp(en)/Flags/Risiko, Flag-Registry) + **Konflikt-Erkennung** (`conflict`-Flag im Judgment-Layer, bidirektional).
   - **Voraussetzung (shared, berührt Long):** `AnomalyReport` um `direction` (bearish/bullish/neutral) erweitern + `compute_confidence` gerichtet nutzen → bearishe Anomalie hebt Short-Konfidenz, bestätigt/penalisiert Long je nach These. Eigener abgegrenzter Schritt (Regressionsrisiko Long-Konfidenz).
3. **Konflikt-Agent (Folge-Block)** — spezialisierte Thesis-Reversal-Abwägung bei `conflict` (siehe §18). Nutzt Short-Assessment + PM-Positionsdaten.
4. **Block #3** — Regeln/Regime-Weiche + Track-B-Hedge + Portfolio-Manager-Ausbau (Richtung/Einstand/P&L/Reconciliation).
5. **Block #4** — Short-Backtest (inkl. **Bewertung/Kalibrierung des Konflikt-Agenten**).
- Quer: **B** (LLM-Short-These), **Momentum** (long+short), **Rohstoff-/Anleihe-/Edelmetall-Short**, ggf. **Futures**.

## 17. Entscheidungs-Log
- Short ≠ invertiertes Long. ✅
- Geteilte Fakten + Short-Schicht; A vor B (beide fest). ✅
- Equity zuerst, andere Klassen als Folge-Blöcke; asset-class-dispatch. ✅
- Aktions-Taxonomie mit NONE + Aufstocken (BUY+/SHORT+); HOLD≠NONE; Defer-Symmetrie. ✅ (betrifft auch Long-Seite → Foundation-Block)
- Kern/Verstärker; „teuer" allein = none; ≥1 Kern-These nötig. ✅
- Kein Top-Down → kein Short. ✅
- Archetyp-Tag; kein Auslöser → max moderate; Crowding-Dämpfer; Triage-Hedge-Wording verworfen (echtes Urteil). ✅
- Borrow: Proxy-Flag v1 + optionales manuelles Feld. ✅
- Flag-Registry (verfügbar + dormant); voller Katalog dokumentiert. ✅
- Total Return: bewusst NICHT umgesetzt (Price Return als CH-Default). ✅
- Short-Urteil **identisch zur Long-Seite**: Aktion + **Konfidenz** (kein `short_score`, keine 4-Stufen-Note). ✅
- Regime ist **Konfidenz-Modifikator**, kein Hard-Block (bullisch=Gegenwind, neutral=neutral, bearisch=Rückenwind). ✅
- Hart-Gates (→ NONE, vor Konfidenz): kein Top-Down (Veto), keine Kern-These (kein Signal). ✅
- Konflikt bidirektional + **eigener Konflikt-Agent** als Folge-Block (Block 1 erkennt nur). ✅
- Backtester bewertet + kalibriert den Konflikt-Agenten — kein Funktions-Overlap (rückblickend vs. vorwärts). ✅
- Anomalien (`AnomalyChiefAgent`) als geteilter Short-Input = **Konfidenz-Modifikator** (keine Doppelzählung). ✅
- Outputs der Linsen **vergleichen** (conflict), NICHT fusionieren — zwei eigenständige Urteile. ✅
- `archetypes` = **Menge** (kein Ranking); mehrere Treffer = stärkere These. ✅
- Anomalie-Richtung strukturiert (`AnomalyReport.direction`) — gerichteter Konfidenz-Effekt; shared Prerequisite für Block 1 (berührt Long-`compute_confidence`). ✅
- Flag-Registry: `ShortFlag` (name/kind/archetype/weight/needs/fires/detail), Engine iteriert die Liste; neue Quelle = neuer Eintrag. ✅
- Anomalien werden im **finalen Output** (LLM/XAI) ausgewiesen, nicht nur in der Konfidenz. ✅
- Konfidenz-Schwellen/Gewichte = **Erst-Heuristik** (an Long-Skala angelehnt, relative Ordnung begründet, Dezimalwerte nicht aus Daten) → **final via Backtest kalibriert** (Block #4, short-spezifische Trefferraten-Buckets). Auch Long-`compute_confidence` ist noch unkalibriert (Fallback 0.70). **Tests prüfen Verhaltens-Bänder, nicht Dezimalwerte.** ✅

## 18. Konflikt-Agent (Folge-Block, nach Block 1)
**Zweck:** „Hat sich die gehaltene These gedreht?" — die schwerste Entscheidung (eine kaputte Positions-These eingestehen) bekommt eine eigene, fokussierte Logik.
- **Trigger (bidirektional):** gehaltene Position + gegenläufiges Linsen-Signal feuert qualifiziert. *Long gehalten + Short-Signal* → „screent als Short trotz Long". *Short gehalten + Bullish-Read* → „screent bullish trotz Short".
- **Inputs:** gehaltene Position + (ursprüngliche/aktuelle) These + gegenläufiges Urteil (Short-Assessment bzw. Long-Read) + Anomalien + Backtester-Kalibrierung.
- **Output (Reconciliation):** These gekippt → **Ausstieg** (SELL/COVER) · Gegenwind, aber These hält → **halten** · ggf. **umkehren** (raus + Gegenposition).
- **LLM-gestützt** (nuancierte Zwei-Thesen-Abwägung), analog `JudgmentAgent`.
- **Orchestrator-Verdrahtung:** **bedingter Schritt** in `JudgmentOrchestrator.run()` — NACH dem `JudgmentChiefAgent` (der das `conflict`-Flag setzt): `if result.conflict: result.conflict_resolution = await conflict_chief.run(..., backtester_context=...)`. Läuft **nur** bei Konflikt → sonst kein Kostenaufwand. Bekommt beide Linsen + Position + Kalibrierung.
- **Verhältnis zum Backtester (kein Overlap):** Backtester = **rückblickender** Punkterichter/Kalibrierer; Konflikt-Agent = **vorwärtsgerichteter** Entscheider. Der Backtester **bewertet die Reversal-Calls separat** (haben „Ausstieg"-Entscheidungen historisch Geld gespart vs. Halten?) und **speist die Kalibrierung zurück** → kalibriert die Konfidenz des Konflikt-Agenten. Komplementär, nicht doppelt.

**Design-Entscheidungen (2026-06-19):**
- **Beratend (nicht handlungsverändernd):** Der Agent hängt ein **`ConflictResolution` (verdict + reasoning)** ans `DeepDiveResult`; die formalen Aktionen (HOLD) bleiben stehen — der User entscheidet.
- **Verdikte:** `EXIT` (These gekippt → Ausstieg: SELL bei Long / COVER bei Short) · `HOLD` (Gegenwind, aber These hält) · `REVERSE` (raus + Gegenposition, aggressiv). **Vom LLM bestimmt** (geparst aus einer `VERDICT: …`-Zeile); Parse-Fehler → `HOLD` + Roh-Text.
- **Komponenten:** `ConflictResolution`-Modell + `DeepDiveResult.conflict_resolution`; `ConflictAgent` (`agents/conflict/`, LLM-gestützt wie `JudgmentAgent`); **bedingter Call** im `judgment_orchestrator` (kein Chief nötig); Anzeige in `app/main.py`.
- **Lern-Schleife (Haken jetzt, Auswertung Block #4):** (1) `ConflictResolution` wird **mit der Analyse persistiert** (`memory.save_analysis`); (2) der Agent **konsumiert `backtester_context`** (eigener Track-Record im Prompt). Die **Verdikt-Auswertung gegen Forward-Returns + das Befüllen der Kalibrierung** ist **Block #4** (wie bei der Long-Konfidenz heute noch unbefüllt). Vorher: ehrliche, aber unkalibrierte Urteile.
