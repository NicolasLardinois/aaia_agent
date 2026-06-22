# Regime-Replay-Backtest — Point-in-Time-Fundament & Makro/Regime-Validierung — Design-Spec

> Stand: 2026-06-22 · Status: Entwurf zur Abnahme
> Kontext: Der Nutzer will das Entscheidungssystem mit historischen Daten „füttern", es an
> historischen Stichtagen entscheiden lassen und gegen die tatsächliche Kursentwicklung prüfen.
> Dieses Teilprojekt ist **Stufe 1 von 4** einer größeren Vision (siehe §10).

---

## 0. Wichtige Einordnung (das „Warum" der Architektur)

Das AAIA-System ist **kein ML-Modell**, sondern ein **regelbasiertes Expertensystem**: Die finale
Kauf-/Verkauf-Entscheidung fällt in den deterministischen Funktionen `derive_recommendation()` und
`compute_confidence()` (`core/domain/recommendation.py`); der LLM (Claude) liefert nur den
**Erklärungstext**, nicht die Entscheidung. „Trainieren" heißt hier deshalb **nicht** Gradient Descent,
sondern das systematische Justieren der vielen **expliziten Schwellenwerte und Gewichte**.

Daraus folgt die Zerlegung in zwei Maschinen, die aufeinander aufbauen:

1. **Validieren (Backtest)** — Vergangenheit durchspielen, *als-ob* an historischen Tagen entscheiden,
   gegen die Realität messen. Schwellen bleiben unverändert. ← **dieses Teilprojekt**
2. **Kalibrieren (Walk-Forward-Optimierung)** — die Schwellen mit den historischen Ergebnissen
   nachjustieren. Setzt (1) zwingend voraus, sonst optimiert man ins Blaue. ← spätere Spec (§10)

## 1. Ziel

Den **Top-Down-Regime-Motor** (`core/domain/regime.py`, `RegimeDetector`) über die US-Historie
**ab 1960** monatsweise durchspielen und seine Regime-Urteile an zwei unabhängigen Wahrheiten messen:

- **(A) Markt-Wahrheit** — hätte das Regime-Urteil als Marktrichtung Geld gebracht? (Forward-S&P-Return)
- **(B) Wirtschafts-Wahrheit** — hat es die reale Konjunkturlage erkannt? (NBER-Rezessionsdaten)

Ergebnis ist ein **reproduzierbarer, look-ahead-freier Offline-Lauf**, der einen **datierten Report**
erzeugt. Zweitnutzen: Der `RegimeDetector` ist laut Logbuch (`docs/open_todos.md` §6) bislang
**komplett ungetestet**, treibt aber *jede* Empfehlung an — die Validierung schließt diese Lücke.

## 2. Nicht-Ziele / Out of Scope

- **Kein Tuning/keine Optimierung** der Schwellen/Gewichte. Reine Messung. (→ Stufe 2, §10.)
- **Keine Einzelaktien-Validierung** (Bottom-Up-Urteil). Fundamentaldaten reichen nicht bis 1960
  zurück → eigenes Teilprojekt mit kurzem, jüngerem Fenster. (→ Stufe 3, §10.)
- **Nur USA.** EU/CH-Regime-Indikatoren bleiben in der Historie schlicht leer; der Detektor
  re-normiert seine Gewichte bereits selbst über fehlende Keys. Kein Sonderpfad nötig.
- **Kein Scheduler, kein Live-Loop, keine Frontend-Anbindung.** Anstoßbarer Batch-Lauf + Report-Datei.
- **Keine Anbindung der Stub-APIs** (ECB/SNB). Irrelevant, da USA-only über FRED läuft.

## 3. Wie „richtig" gemessen wird

### 3.1 (A) Markt-Wahrheit — Forward-Return

Jedes Regime wird in eine **erwartete Marktrichtung** übersetzt:

| Regime | Richtung |
|---|---|
| Boom, Aufschwung, Erholung | bullish |
| Abschwung, Rezession, Depression | bearish |

Pro Stichtag wird der **Forward-Return des S&P 500** (`^GSPC`) über die Horizonte **3, 6, 12 Monate**
berechnet. Das Vorzeichen muss zur Richtung passen (`is_correct` aus `core/utils/backtest.py`).
Bewusst **kein** Markt-Benchmark-Abzug (Alpha) wie bei Einzelaktien: das Regime *ist* die Wette auf
den Gesamtmarkt, der S&P selbst ist die zu prognostizierende Größe.

Aggregation pro Horizont, **gesamt und je Regime**:
- Hit-Rate + **Wilson-Konfidenzintervall** (`hit_rate_ci`),
- mittlerer Forward-Return der bullish- vs. bearish-Calls (Plausibilität: bullish-Calls sollten im
  Schnitt positiver laufen als bearish-Calls).

Die Per-Regime-Aufschlüsselung ist diagnostisch zentral: Sie zeigt, *welche* Phasen der Motor gut
und welche er schlecht trifft (z. B. „Rezession" verlässlich, „Erholung" schwach).

### 3.2 (B) Wirtschafts-Wahrheit — NBER

FRED-Reihe **`USREC`** (1 = vom NBER markierter Rezessionsmonat, monatlich, bis 1854 zurück) als
unabhängiges Label. Regime werden in zwei Lager geteilt:

- **risk-off** = {Abschwung, Rezession, Depression}
- **risk-on** = {Erholung, Aufschwung, Boom}

Daraus:
- **Konfusionsmatrix** risk-off × `USREC` → Precision/Recall (rief das System Risk-off, *als* real
  Rezession war?).
- **Vorlauf/Nachlauf** (die wertvollste Zahl): Wie viele Monate **vor** (gut, antizipierend) oder
  **nach** (schlecht, hinterherlaufend) dem NBER-Rezessionsbeginn schaltet der Motor auf risk-off?
  Gemessen je Rezessionsepisode als Differenz (erster risk-off-Monat im Umfeld − NBER-Startmonat).

(A) und (B) zusammen sagen, *woher* ein Fehler kommt: Wirtschaft falsch gelesen (B schlecht) oder
Markt kurzfristig verrauscht (B gut, A schlecht).

## 4. Architektur (vier Bausteine, hexagonal eingepasst)

```
   as_of-Datum (Monats-Schritt 1960→heute)
        │
        ▼
   HistoricalFredProvider(as_of)   ← NEU (Adapter, erfüllt MacroDataProvider-Port)
        │   Vintage-Makrodaten, kein Look-Ahead
        ▼
   RegimeDetector(state, history=…) ← BESTEHEND, nur Trend-Historie injizierbar gemacht
        │
        ▼
   Regime-Urteil (Datum · Regime · Konfidenz · Composite · Evidence)
        │
        ▼
   RegimeEvaluator   ← NEU (reine Mathematik in core/utils/)
        │   A: Forward-S&P-Return (3/6/12 M)   B: NBER-Abgleich
        ▼
   Datierter Report (JSON + lesbare .md)
   ──────────────────────────────────────
   Fundament: Point-in-Time — nie Daten aus der Zukunft des Stichtags
```

### 4.1 `HistoricalFredProvider(as_of)` — Adapter (NEU)

- Liegt in `adapters/data/historical_fred.py`, implementiert **dasselbe** `MacroDataProvider`-Port
  wie der bestehende `FredDataProvider`. **Folge:** `TopDownOrchestrator` und der Regime-Code ändern
  sich nicht — es wird nur ein anderer Adapter injiziert (Lohn der hexagonalen Architektur).
- Statt `.iloc[-1]` (neuester Wert) liefert er den letzten Wert **mit Beobachtungsdatum ≤ `as_of`**.
- **Vintage:** nutzt `fredapi.Fred.get_series_as_of_date(series_id, as_of)` — liefert den Stand, der
  am Stichtag *veröffentlicht* war (vor späteren Revisionen). Wo FRED **keine** Vintage-Stände hat
  (flächendeckend erst ~1990er), Rückfall auf die normale (revidierte) Serie, geschnitten auf
  `≤ as_of`. Pro Lauf/Reihe wird die verwendete Datenqualität (`vintage` | `revised`) protokolliert.
- Wiederverwendet die bestehenden Serien-Mappings/Transformationen aus `FredDataProvider` (CPIAUCSL,
  UNRATE, FEDFUNDS, T10Y2Y, T10Y3M, GDP, UMCSENT, INDPRO), damit die Berechnung **identisch** zum
  Live-Pfad bleibt (keine Logik-Divergenz).

### 4.2 `RegimeDetector` — Trend-Historie injizierbar (BESTEHEND, minimaler Eingriff)

**Problem heute:** `RegimeDetector.detect()` liest/schreibt die Trend-Historie aus einer **globalen**
Cache-Datei (`.cache/composite_history.json`, max. 8 Einträge, datiert auf `date.today()`). Für einen
Replay ist das doppelt falsch: es würde das *heutige* Datum schreiben und sich über alle historischen
Stichtage gegenseitig überschreiben.

**Lösung:** `detect()` akzeptiert die Composite-Historie als **Parameter** (z. B.
`detect(state, sub_signals=None, history=None)`); ist `history` gesetzt, wird **nichts** aus der Datei
gelesen oder geschrieben. Das **Live-Verhalten bleibt per Default unverändert** (ohne `history`-Arg
weiterhin Datei-basiert). Die Replay-Schleife baut die bis `as_of` aufgelaufene Composite-Reihe selbst
auf und reicht sie durch — die `_trend()`-Berechnung bleibt unangetastet.

### 4.3 `ReplayHarness` — die Schleife (NEU)

- Liegt unter `agents/backtester/` (z. B. `regime_replay.py`) bzw. wird über `app/replay_regime.py`
  angestoßen.
- Iteriert monatsweise von `start` (Default 1960-01) bis heute. Je Stichtag:
  1. `state = HistoricalFredProvider(as_of).get_economic_state()` (+ `get_extended_state` falls genutzt),
  2. Composite-Reihe der **vorherigen** Stichtage zusammenstellen,
  3. `regime, confidence, evidence = RegimeDetector().detect(state, history=…)`,
  4. Datensatz `(as_of, regime, confidence, composite, evidence, data_quality)` sammeln.

### 4.4 `RegimeEvaluator` — reine Mathematik (NEU)

- Liegt in `core/utils/` (z. B. `regime_eval.py`), **erweitert** `core/utils/backtest.py`
  (`forward_return`, `is_correct`, `hit_rate_ci` werden wiederverwendet). Keine I/O, keine Seiteneffekte.
- Bekommt die gesammelten Urteile + zwei datierte Reihen (S&P-Kurse, `USREC`) injiziert und liefert
  das Report-Dict (§3.1 + §3.2). Kursreihe/`USREC` werden vom Harness geladen (Adapter-Seite),
  nicht im Evaluator — der bleibt rein.

## 5. Look-Ahead-Disziplin (Korrektheits-Wächter, AGENTS.md §3)

Ein Backtest mit Zukunftswissen ist **wertlos**. Verbindlich:

1. Der Provider gibt **nie** eine Beobachtung mit Datum **> `as_of`** zurück.
2. **Vintage** wo möglich, damit spätere Datenrevisionen nicht rückwirkend einsickern.
3. Forward-Returns nutzen **ausschließlich** Kurse **nach** `as_of`.
4. Die Trend-Historie wird **nur** aus Composites vergangener Stichtage gebaut.
5. Jeder Report stempelt **pro Zeitraum** die Datenqualität (`vintage`/`revised`), damit erkennbar
   bleibt, welchen Zahlen wie weit zu trauen ist.

## 6. Daten & Reichweite (Defaults)

| Aspekt | Wert | Begründung |
|---|---|---|
| Region | nur USA | tiefste Datenhistorie; NBER + S&P passen genau |
| Kadenz | monatlich | Makrodaten ändern sich nicht täglich; ~800 Entscheidungspunkte |
| Fenster | 1960 → heute | Kern-Serien + NBER überlappen sauber |
| Horizonte (A) | 3, 6, 12 Monate | Regime sind langsam; Tages-Horizonte unpassend |
| Benchmark (A) | S&P 500 `^GSPC` | Yahoo-Daten bis 1927 vorhanden |
| Wirtschafts-Label (B) | FRED `USREC` | offizielle NBER-Rezessionsmonate |

**Bekannte Lücke (dokumentiert, kein Bug):** Die Zinskurve `T10Y2Y` existiert bei FRED erst ab **1976**.
Davor fehlt dieser Indikator; der Detektor re-normiert seine Gewichte über die vorhandenen Keys selbst.
Der Report weist solche Lücken pro Zeitraum aus.

## 7. Tests zuerst (TDD verpflichtend, AGENTS.md §4)

Alle Tests **ohne Netz** (Fakes/Fixtures, deterministisch):

- **`HistoricalFredProvider`**: bei `as_of = X` wird der Wert von `X` (oder davor) geliefert, **nie**
  ein späterer — gegen eine Fake-Serie mit bekannten datierten Punkten (Look-Ahead-Regression).
  Vintage-Pfad und Revised-Fallback je ein Test inkl. korrektem `data_quality`-Flag.
- **`RegimeDetector` mit injizierter Historie**: pinnt ein bekanntes `(composite, trend) → Regime`
  und beweist, dass **keine** Datei gelesen/geschrieben wird (kein Seiteneffekt).
- **`RegimeEvaluator` (A)**: Richtungs-Mapping je Regime; Grenzfälle (Return exakt 0, `None`-Kurs);
  Wilson-CI an bekanntem Beispiel.
- **`RegimeEvaluator` (B)**: NBER-Konfusionsmatrix + Vorlauf/Nachlauf an einer konstruierten Episode
  (früh/spät/genau am Rezessionsbeginn).
- **Integration**: Mini-Replay über 3 Stichtage gegen einen Fake-Provider erzeugt **deterministisch**
  denselben Report.

## 8. Deliverable

- `python -m app.replay_regime [--start YYYY-MM] [--end YYYY-MM]` stößt den Lauf an.
- Schreibt einen **datierten Report** unter `data/backtests/`:
  - `regime_replay_YYYYMMDD.json` (maschinenlesbar, alle Urteile + Aggregate + `data_quality`),
  - `regime_replay_YYYYMMDD.md` (lesbare Zusammenfassung: Hit-Rate je Horizont mit CI,
    Per-Regime-Tabelle, NBER-Konfusion + mittlerer Vorlauf, Datenqualitäts-Hinweise).
- Kein Eingriff in den Live-Pfad außer dem rückwärtskompatiblen `history`-Parameter (§4.2).

## 9. Risiken & offene Punkte

- **Vintage-Abdeckung** ist vor den 1990ern lückenhaft → frühe Jahrzehnte laufen auf revidierten
  Daten und sind leicht „geschönt". Durch das `data_quality`-Flag transparent, nicht versteckt.
- **`USREC`-Definition**: NBER datiert Rezessions-*Beginne* rückblickend; das ist als Wahrheitslabel
  unproblematisch (wir vergleichen, der Motor prognostiziert), nur bei der Vorlauf-Interpretation
  zu bedenken.
- **`get_series_as_of_date`-Last**: zieht mehr Daten als der Live-Adapter. Bei ~800 Stichtagen × ~8
  Serien akzeptabel; ggf. Serien einmalig vollständig laden und lokal pro `as_of` schneiden
  (Implementierungs-Detail für den Plan).

## 10. Spätere Stufen (bewusst eigene Specs — hier nur als Ausblick)

| Stufe | Inhalt | Voraussetzung |
|---|---|---|
| ① **dieses Teilprojekt** | Makro/Regime **validieren** | — |
| ③ | Einzelaktien-Urteil **validieren** (kurzes Fenster) | Fundamental-Datenquelle |
| ② | Makro/Regime **kalibrieren** (Walk-Forward) | ① + Overfitting-Schutz (Train/Test-Split) |
| ④ | Einzelaktien **kalibrieren** | ③ |

Die Kalibrier-Stufen (②④) brauchen zwingend **Walk-Forward-Disziplin** (auf einem Zeitfenster tunen,
auf einem *anderen, blind gehaltenen* Fenster testen), sonst overfittet man auf die Historie. Das ist
Stoff der jeweiligen späteren Spec, nicht dieses Teilprojekts.
