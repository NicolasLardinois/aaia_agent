# Regime-Kalibrierung (Stufe ②-v1) — Risk-off-Grenze per Walk-Forward — Design-Spec

> Stand: 2026-06-22 · Status: Entwurf zur Abnahme
> Kontext: **Stufe ②** der Regime-Replay-Initiative (Spec `2026-06-22-regime-replay-backtest-design.md` §10).
> Stufe ① (Validierung) ist via **PR #26 gemergt**. Jetzt der zweite Teil des Nutzer-Ziels: aus „nur
> validieren" wird **kalibrieren** — den Motor mit der Historie messbar besser machen.

---

## 0. Einordnung (das „Warum")

Das AAIA-Entscheidungssystem ist regelbasiert; „trainieren" heißt hier **explizite Zahlen justieren**, kein
ML. Stufe ① hat die Maschine gebaut, die ② braucht: den Point-in-Time-Replay + die Evaluatoren (A = Markt,
B = NBER). Diese v1 dreht **genau eine** Stellschraube — die **Risk-off-Grenze** — gegen die rauscharme
NBER-Wahrheit, validiert das Ergebnis out-of-sample am Markt und gibt einen **Vorschlag** aus (kein
Auto-Apply). Bewusst **ein** Parameter, weil die wenigen Rezessions-Ereignisse Overfitting erzwingen (siehe §10).

## 1. Ziel

Den höchsten Einzelhebel des Regime-Motors — *wo auf der Composite-Skala der Motor von „risk-on" auf
„risk-off" umschaltet* — per **Walk-Forward** gegen NBER kalibrieren und als **Vorschlag-Report** ausgeben:
bester Grenz-Bias `b*`, Out-of-Sample-Gewinn auf **B (NBER)** und **A (Markt)** vs. heutiger Default, plus
ein klares Übernehmen-oder-Behalten-Urteil. Übernahme erfolgt später durch den User per normalem PR.

## 2. Nicht-Ziele / Out of Scope

- **Keine Indikator-Gewichte** (`INDICATOR_WEIGHTS`) tunen — höher-dimensional, mit ~20 Ereignissen zu
  riskant. Bewusst spätere Ausbaustufe (§11).
- **Kein Auto-Apply.** Der Lauf mutiert **nie** selbst eine Produktions-Zahl; er schlägt nur vor.
- **Keine neuen Datenquellen / EU/CH.** Rein USA, rein auf dem in ① gemergten Fundament.
- **Keine Kalibrierung der `_score_indicator`-Bänder, Trend-Schwellen oder der Confidence-Formel.** Nur die
  eine Grenze.

## 3. Die Stellschraube — ein Composite-Bias `b`

Der Motor rechnet je Monat einen **Composite** (das „Wirtschafts-Thermometer"); `_regime_from(composite,
trend)` ordnet daraus per Fuzzy-Glocken ein Regime zu. Die Risk-off-Grenze liegt heute *implizit* bei
Composite ≈ 0,15 (zwischen den Glocken SLOWDOWN −0,10 und EXPANSION +0,40, gleiche Breite 0,22).

**Knopf:** ein einzelner Bias `b`, angewandt als `_regime_from(composite + b, trend)`. `b = 0` = heutiges
Verhalten. `b < 0` → Risk-off feuert **früher** (sensibler); `b > 0` → **später**.

Eigenschaften:
- **Trend-Invarianz gegen den Shift:** Der Trend ist `current − mean(history)`; ein gleichmäßiger Bias auf
  *alle* Composites kürzt sich heraus (`(c+b) − mean(hist+b) = c − mean(hist)`). **Folge:** Jedes Kandidaten-`b`
  ist exakt nachrechenbar aus den gespeicherten `(composite, trend)` je Stichtag — **ohne** den Replay neu
  zu fahren. Der Kalibrator bleibt reine, schnelle Nachbearbeitung.
- **Ehrliche Nebenwirkung:** `b` verschiebt *alle* Regime-Grenzen gleichmäßig (auch BOOM↔Aufschwung) — eine
  globale Neueichung der Composite-Skala. Für die B-Metrik zählt nur die risk-on↔risk-off-Grenze; die
  Verschiebung der übrigen Grenzen ändert das Produktions-Regime kohärent mit und wird vom **A-Härtetest**
  (§5) abgesichert.

**Wo der Knopf in Produktion lebt (minimaler, rückwärtskompatibler Zusatz):** eine Modul-Konstante
`_REGIME_BIAS = 0.0` in `core/domain/regime.py`; `detect` ruft `_regime_from(composite + _REGIME_BIAS, trend)`.
Default 0 → **kein** Verhaltenswechsel. Die Übernahme eines Vorschlags ist dann **eine Zeile**: `_REGIME_BIAS = b*`.

## 4. Zielmetrik (B = NBER)

Pro Monat: ist das Regime risk-off (`∈ {SLOWDOWN, RECESSION, DEPRESSION}`) **und** ist der Monat ein
NBER-Rezessionsmonat (`USREC=1`)? Daraus die Konfusionsmatrix → **F1** = `2·P·R/(P+R)` (balanciert
Treffer *und* Fehlalarme). **F1 ist die Optimierungsgröße.** Mitberichtet (nicht optimiert): **Vorlauf**
(Monate vor Rezessionsbeginn), Precision, Recall — damit sichtbar ist, *wie* ein `b` gewinnt.

Wiederverwendung: `core/utils/regime_eval.py::evaluate_nber` liefert tp/fp/tn/fn/precision/recall bereits;
F1 wird daraus abgeleitet. Der Kalibrator baut je Kandidaten-`b` „neu-gelabelte" Urteile
(`regime = _regime_from(composite + b, trend)`) und ruft `evaluate_nber`.

## 5. Walk-Forward + Suche (Overfitting-Schutz)

- **1-D-Gitter:** `b ∈ [−0,40, +0,40]`, Schritt 0,02 (41 Kandidaten). Erschöpfend, interpretierbar, kein
  Black-Box-Optimierer — ein Parameter braucht keinen.
- **Expanding-Window-Walk-Forward:** Folds über die Zeit (Default ~4, jeder Test-Block enthält
  Rezession[en]). Je Fold: auf [Start … T_k] das F1-maximierende `b` finden, auf dem **blind gehaltenen**
  Block (T_k … T_{k+1}] dessen F1 messen. So entsteht ein **Out-of-Sample-F1 des Tunings**.
- **Vergleich gegen Default:** dasselbe Out-of-Sample-F1 für `b = 0`. **Kernfrage:** schlägt das
  per-Fold-getunte `b` den Default `b=0` *out-of-sample*?
- **Finaler Vorschlag:** Schlägt Tuning den Default OOS → schlage das `b*` vor, das F1 über die **gesamte**
  Historie maximiert (Deployment nutzt alle Daten), **begründet** durch die OOS-Evidenz. Schlägt es nicht →
  Empfehlung **„Default behalten"**.
- **A-Härtetest:** für `b*` und `b = 0` zusätzlich die **Markt-Hit-Rate** über `evaluate_market` (Evaluator A
  aus ①). Verbessert die NBER-Kalibrierung den Markt **auch** (oder schadet zumindest nicht)? Ein `b*`, das B
  hebt aber A senkt, wird im Report **als Warnung** markiert (Adoption fraglich).

## 6. Deliverable

`python -m app.calibrate_regime [--start YYYY-MM] [--end YYYY-MM] [--folds N]` →
**Vorschlag-Report** unter `data/backtests/regime_calib_YYYYMMDD.(json|md)`:
- bestes `b*` und Default `b=0` nebeneinander,
- OOS-F1 (B) + Markt-Hit-Rate (A) je Fold und aggregiert, plus Vorlauf/Precision/Recall,
- **Urteil:** „Bias `b*` übernehmen (OOS-F1-Gewinn …, A neutral/positiv)" **oder** „Default schlägt alles —
  nichts ändern" — Letzteres ist ein **vollwertiges, die Hand-Werte bestätigendes Ergebnis**,
- Stichprobengröße je Fold (Rezessionsmonate/-episoden) — die Unsicherheit transparent (§10).

## 7. Voraussetzung in ① (kleiner rückwärtskompatibler Zusatz)

Der Kalibrator braucht je Stichtag **Composite und Trend**. `evidence["composite"]` liefert ① bereits;
ergänzt wird **`evidence["trend"]`** (der in `detect` ohnehin berechnete Trend, ggf. `None`). `run_replay`
nimmt `trend` ins Urteil-Dict auf. Kein Verhaltenswechsel, nur ein zusätzlich ausgegebener Wert.

## 8. Komponenten (hexagonal, reine Trennung)

- **`RegimeCalibrator`** — reine Mathematik in `core/utils/regime_calibration.py` (kein I/O). Eingaben:
  `[(date, composite, trend)]`, NBER-Dict, Fold-Definition, optional die A-Kursfunktion. Ausgabe: ein
  Report-Dict (`b_star`, `default`, per-Fold + aggregierte OOS-Metriken, A-Check, Urteil). Wiederverwendet
  `_regime_from` (Re-Labeling je `b`), `evaluate_nber` (B), `evaluate_market` (A).
- **CLI** `app/calibrate_regime.py` — Composition-Root: fährt den Replay (oder lädt einen ①-Report), lädt
  NBER (`USREC`) + S&P, ruft den Kalibrator, schreibt den Report. Einziger Ort mit I/O/Netz.
- **`core/domain/regime.py`** — `_REGIME_BIAS = 0.0` + Anwendung in `detect` (§3). Sonst unverändert.

## 9. Tests (TDD verpflichtend, AGENTS.md §4)

Mit Fakes/Fixtures, deterministisch, ohne Netz:
- **Trend-Invarianz:** `_regime_from(c+b, trend)` == Regime bei gleich verschobener History → der Trend
  ändert sich nicht (pinnt die Kern-Annahme aus §3).
- **`evidence["trend"]`** wird gesetzt (Zusatz aus §7), Default-Pfad unverändert.
- **Kalibrator findet das gepflanzte Optimum:** konstruierte Composite-Reihe + NBER-Episode, bei der ein
  bekanntes `b` F1 maximiert → der Kalibrator liefert genau dieses `b*`.
- **Walk-Forward leckt nicht:** Train/Test sind disjunkt; ein `b`, das nur im Test-Block glänzt, wird **nicht**
  gewählt (Auswahl rein aus Train).
- **„Default gewinnt"-Fall:** Daten, bei denen `b=0` OOS am besten ist → Urteil „Default behalten".
- **A-Warnung:** konstruierter Fall, in dem `b*` B hebt aber A senkt → Report markiert die Warnung.

## 10. Ehrliche Grenzen (vom Nutzer angestoßen — wichtig)

- **Viele Kennzahlen *nutzen* ≠ viele Regler *lernen*.** Der Motor verarbeitet viele Indikatoren — deren
  Bedeutung kommt aus der **Wirtschaftstheorie** (von Hand gesetzt), **nicht** aus den Rezessionen gelernt.
  Das ist unbegrenzt erlaubt. Begrenzt ist nur, **wie viele Regler wir frei gegen die Rezessionen drehen**.
  Jeder frei getunte Regler kann Zufall auswendig lernen → genau **deshalb** v1 = *ein* Knopf.
- **Zwei Stichprobengrößen:** zum *Messen* einer Grenze ~780 Monate (viel); zum *Verallgemeinern* zählen die
  **unabhängigen Ereignisse** ~20 Rezessionen (Monate innerhalb einer Rezession sind korreliert). Letzteres
  ist die echte Grenze → OOS-Schätzung ist **verrauscht**; der Report nennt die Stichprobengröße je Fold.
- **Daten-Reichweite, nicht Ereignis-Mangel:** Rezessionen gab es mehr (NBER bis 1854), aber die
  Eingabe-Reihen (FRED) reichen meist nur bis ~1960 (Zinskurve erst 1976). Mehr Ereignisse gibt es nur über
  **mehr/längere Datenquellen** (spätere Stufe), nicht über härteres Tunen.
- **Robust vor groß:** ein kleiner, über Folds stabiler `b`-Effekt ist glaubwürdiger als ein großer
  Einzelfund. Der Report bevorzugt in der Darstellung Stabilität über Spitzenwerte.

## 11. Spätere Stufen (eigene Specs)

| Stufe | Inhalt | Voraussetzung |
|---|---|---|
| **②-v1 (diese Spec)** | Risk-off-Grenze kalibrieren (1 Knopf, USA, Vorschlag) | ① (gemergt) |
| ②-v2 | Indikator-Gewichte kalibrieren (mehr Regler) | mehr Ereignisse/Daten + bewährte v1-Mechanik |
| ④ | Einzelaktien kalibrieren | ③ (Einzelaktien-Validierung) |

Walk-Forward + Vorschlag-statt-Auto-Apply bleiben in allen Kalibrier-Stufen die Leitplanken.
