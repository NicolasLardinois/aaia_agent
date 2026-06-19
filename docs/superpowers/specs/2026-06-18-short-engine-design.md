# Block 1b: Equity-Short-Thesis-Engine — Design

**Datum:** 2026-06-18
**Status:** Genehmigt (Design)
**Teil von:** Shorts-Programm (`docs/short.md`). Baut auf **Foundation** (ShortAction/PositionState/Taxonomie) + **1a** (`AnomalyReport.direction`).

## Kontext & Ziel

Heute liefert die Short-Seite nur einen **Platzhalter** (`derive_short_action_placeholder`: short gehalten → HOLD, sonst NONE). Ziel: eine echte **Short-Thesis-Engine** — eine reine Funktion `derive_short_assessment`, die aus den vorhandenen `bottom_up`-Fakten + `cockpit` ein vollwertiges Short-Urteil baut: **Aktion + Konfidenz** (symmetrisch zur Long-Seite), plus Archetyp(en), Begründungs-Flags und Risiko/Sizing. Dazu **bidirektionale Konflikt-Erkennung** im Judgment-Layer.

Design-Quelle: `docs/short.md` §5–9, §15 (Architektur, Kern/Verstärker, Konfidenz-Zusammenbau, Gating, Datenlage).

## Scope

**Im Block (1b):**
- `ShortAssessment`-Modell + `ShortFlag`-Registry (verfügbare Equity-Flags).
- `derive_short_assessment(...)` (Engine: Hart-Gates → Flags → Konfidenz → Aktion → Archetypen), inkl. Asset-Class-Dispatch (Equity voll; andere → Fallback).
- `DeepDiveResult` um `short_assessment`, `conflict`, `conflict_reason`.
- Verdrahtung im `judgment_agent` (ersetzt den Platzhalter) + `detect_conflict` (bidirektional).
- Tests (Verhaltens-Bänder, keine Dezimal-Pins).

**Außerhalb (spätere Blöcke):**
- **SHORT+** (braucht Einstand/P&L → PM/Block #3).
- **B** (LLM-Short-These + XAI).
- **Konflikt-Agent** (§18; 1b erkennt nur, setzt `conflict`).
- **Dormante Flags** (Beneish/Momentum/Katalysator-Hard/relative Schwäche/…) — kommen mit ihrer Datenquelle; v1-Registry enthält nur implementierbare Flags.
- **Voll-Short-Zweige** für Rohstoff/Anleihe/Edelmetall (Fallback bis dahin).
- **Backtester-Kalibrierung** der Short-Konfidenz (Block #4) — v1 nutzt nur die Heuristik.

## Komponenten

### 1. `core/domain/models.py` — `ShortAssessment`
```python
@dataclass
class ShortAssessment:
    asset_class: str
    short_action: ShortAction              # SHORT | COVER | HOLD | NONE
    confidence: float                      # 0.10–1.0
    archetypes: list[str]                  # Teilmenge: distress/broken_growth/secular_decline/(fraud/cyclical_peak dormant)
    thesis_flags: list[str]                # gefeuerte Gründe mit Zahlen (Begründung)
    regime_effect: str                     # "headwind" | "neutral" | "tailwind"
    squeeze_risk: str                      # "low" | "elevated" | "high"
    hard_to_borrow: bool
    borrow_rate_manual: Optional[float] = None
    suggested_size_pct: Optional[float] = None
    stop_pct: Optional[float] = None
```
Plus `DeepDiveResult` (als letzte Felder): `short_assessment: Optional[ShortAssessment] = None`, `conflict: bool = False`, `conflict_reason: str = ""`. (`short_action` bleibt, jetzt aus dem Assessment.)

### 2. `core/domain/short_flags.py` (neu) — `ShortFlag` + Registry
```python
@dataclass(frozen=True)
class ShortFlag:
    name: str
    kind: str                       # "kern" | "verstaerker"
    archetype: Optional[str]        # nur kern: "distress"/"broken_growth"/"secular_decline"
    weight: float                   # Verstärker-Beitrag (kern nutzt Basis, s. Engine)
    fires: Callable[[BottomUpResult], bool]   # defensiv: False bei fehlenden Feldern
    detail: Callable[[BottomUpResult], str]   # "Altman-Z 1.4 (Konkurszone)"
```
**SHORT_FLAGS (v1, alle defensiv — fehlt ein Feld/Snapshot → `fires`=False):**

| name | kind | archetype | feuert wenn | weight/Basis |
|---|---|---|---|---|
| `altman_distress` | kern | distress | `quality.altman_z < 1.8` | Basis 0.60 (< 1.0 → 0.68) |
| `coverage_weak` | kern | distress | `quality.interest_coverage < 1.0` | (distress) |
| `cash_burn_levered` | kern | distress | `quality.fcf_margin < 0` **und** `quality.debt_to_equity > 1.0` | (distress) |
| `liquidity_strain` | kern | distress | `quality.current_ratio < 1.0` | (distress) |
| `earnings_collapse` | kern | broken_growth | `earnings_trend.estimate_revision == "down"` **o.** `beat_rate < 0.4` | Basis 0.62 **(= aktiver Katalysator)** |
| `growth_collapse` | kern | secular_decline | `fundamentals.revenue_cagr_3y < -5.0` | Basis 0.58 |
| `valuation_extreme` | verstaerker | — | `valuation_range.position == "overvalued"` **o.** `fundamentals.peg_ratio > 2.5` | +0.05 |
| `weak_moat` | verstaerker | — | `moat.total_score <= 3` | +0.03 |
| `insider_selling` | verstaerker | — | `"sell" in insider.net_direction.lower()` | +0.04 |

*(Schwellen/Gewichte = Erst-Heuristik, später via Backtest kalibriert. Dormante Flags — Beneish/Momentum/Katalysator-Hard/relative Schwäche/Verwässerung/Sentiment — werden mit ihrer Datenquelle ergänzt; nicht in v1-Registry.)*

### 3. `core/domain/short_assessment.py` (neu) — `derive_short_assessment`
```python
def derive_short_assessment(
    bottom_up: BottomUpResult,
    cockpit: Optional[CockpitResult],
    current_position: PositionState,
    top_down_available: bool,
    bu_anomaly: AnomalyReport,
    td_anomaly: AnomalyReport,
) -> ShortAssessment
```
**Ablauf (Equity-Zweig):**
1. **Asset-Class-Dispatch:** `asset_class != "equity"` → Fallback (s. u.).
2. **Hart-Gates → NONE** (Konfidenz 0.10, keine Archetypen): `top_down_available == False` **oder** keine Kern-These feuert.
3. **Flags auswerten:** über `SHORT_FLAGS`; je `fires(bottom_up)` → Treffer sammeln (kind, archetype, detail). Verstärker zählen **nur**, wenn ≥1 Kern feuerte.
4. **Konfidenz-Zusammenbau:**
   - `base` = höchste Kern-Basis der gefeuerten Kern-Flags (Distress tief `altman_z < 1.0` → 0.68, sonst 0.60; earnings_collapse 0.62; growth_collapse 0.58).
   - `+ 0.04` je **weiterem distinct archetype** über den ersten hinaus.
   - `+` Verstärker-Gewichte (valuation 0.05, moat 0.03, insider 0.04).
   - **Katalysator-Cap:** feuert `earnings_collapse` **nicht** → `min(score, 0.70)`.
   - **Regime** (`cockpit.macro.regime`): risk-on {BOOM, EXPANSION, RECOVERY} → −0.12 (`headwind`); risk-off {SLOWDOWN, RECESSION, DEPRESSION} → +0.05 (`tailwind`); `cockpit is None` → 0 (`neutral`).
   - **Crowding:** `days_to_cover >= 8` **und** `hard_to_borrow` → −0.10.
   - **Bearishe Anomalie (1a):** für `bu_anomaly`/`td_anomaly` mit `direction == "bearish"`: medium → +0.05, high → +0.10 (je Report; nutzt `severity`).
   - **Clamp** `[0.10, 1.0]`.
5. **Risiko/Sizing:** `squeeze_risk` = "high" wenn `days_to_cover>=8` o. `short_float_pct>=20`; "elevated" wenn `days_to_cover>=5`; sonst "low". `hard_to_borrow` = `short_float_pct>=20` **und** `days_to_cover>=8`. `suggested_size_pct` = konservativ aus Konfidenz (`_position_size_pct(confidence) * 0.5`, nur bei Aktion SHORT), bei „high" squeeze zusätzlich halbiert. `stop_pct` = 15.0 (bei „high" squeeze 10.0).
6. **Aktion** (Schwelle 0.50):
   - `current_position == LONG` → **NONE** (Defer; Konfidenz/Archetypen trotzdem berechnet → Konflikt-Erkennung).
   - `current_position == SHORT` → `confidence >= 0.50` ? **HOLD** : **COVER**.
   - `current_position == NONE` → `confidence >= 0.50` ? **SHORT** : **NONE**.
7. **archetypes** = Menge der Archetypen der gefeuerten Kern-Flags. **thesis_flags** = `detail(...)` aller Treffer.

**Fallback (Nicht-Equity):** `short_action` positionsbasiert wie der bisherige Platzhalter (short→HOLD, sonst NONE); `confidence=0.10`; `archetypes=[]`; `thesis_flags=["Fallback: klassenspezifische Short-Logik folgt"]`; Risiko-Felder neutral. (Volle Zweige später.)

### 4. `core/domain/recommendation.py` — `detect_conflict`
```python
def detect_conflict(current_position, alignment, dominant_signal, short_assessment, long_confidence) -> tuple[bool, str]:
    # LONG gehalten + echter Short (confidence ≥ 0.50 & Archetyp vorhanden) → Konflikt
    # SHORT gehalten + Long bullish (alignment aligned_bullish o. dominant BULLISH) & long_confidence ≥ 0.50 → Konflikt
```
Gibt `(False, "")` wenn kein Konflikt.

### 5. `agents/judgment/judgment_agent.py` — Verdrahtung
- `short_action = derive_short_action_placeholder(...)` **ersetzen** durch:
  ```python
  short_assessment = derive_short_assessment(
      bottom_up, cockpit, current_position, top_down_available,
      bottom_up_anomaly, top_down_anomaly)
  conflict, conflict_reason = detect_conflict(
      current_position, alignment, dominant_sig, short_assessment, confidence)
  ```
- `DeepDiveResult(...)` um `short_assessment=short_assessment`, `short_action=short_assessment.short_action`, `conflict=conflict`, `conflict_reason=conflict_reason`.
- `app/main.py`: zusätzlich `short_assessment.confidence` + `archetypes` + ggf. `conflict_reason` anzeigen.

## Datenfluss
`judgment_agent.run()` → `derive_short_assessment(bottom_up, cockpit, position, top_down_available, bu_anomaly, td_anomaly)` → `ShortAssessment` (Aktion+Konfidenz+Archetypen+Risiko) → `detect_conflict(...)` vergleicht mit dem Long-Read → `DeepDiveResult(short_assessment, short_action, conflict, conflict_reason)`.

## Fehlerbehandlung
- Jeder Flag defensiv (`fires` fängt fehlende Felder → False). Kein Crash bei `None`-Snapshots.
- Hart-Gates (kein Top-Down / keine Kern-These) → sichere NONE-Rückgabe.
- `cockpit is None` → Regime neutral; `derive_short_assessment` wirft nie.

## Tests (`tests/` — Verhaltens-Bänder, KEINE Dezimal-Pins)
- **Flags** (`test_short_flags.py`): je Flag feuert/feuert-nicht bei gesetztem/fehlendem Feld (defensiv).
- **Engine** (`test_short_assessment.py`):
  - reine Distress-Lage (Altman-Z rot), kein Katalysator → Konfidenz im moderate-Bereich (≥0.50, ≤0.70) → bei `NONE`-Position **SHORT**.
  - Earnings-Kollaps + teuer + Insider + risk-off → Konfidenz hoch (>0.70) → SHORT; `archetypes` enthält broken_growth.
  - nur Verstärker (kein Kern) → **NONE** (Hart-Gate).
  - `top_down_available=False` → **NONE**.
  - risk-on-Regime senkt Konfidenz (milder Distress unter 0.50 → NONE); tiefer Distress feuert trotzdem.
  - `current_position=SHORT` + starke These → **HOLD**; schwache These → **COVER**.
  - `current_position=LONG` + starke These → Aktion **NONE**, aber Konfidenz ≥0.50 (→ Konflikt).
  - bearishe Anomalie hebt die Konfidenz (vs. neutrale).
  - Nicht-Equity → Fallback (NONE/HOLD, flag „Fallback").
- **Konflikt** (`test_detect_conflict.py`): LONG + starker Short → conflict; SHORT + bullish Long → conflict; sonst nicht.
- **Verdrahtung + Regression** (`tests/`): `judgment_agent` setzt `short_assessment`/`conflict`; Gesamtsuite grün.

## Akzeptanzkriterien
1. `derive_short_assessment` liefert ein `ShortAssessment` mit Aktion+Konfidenz+Archetypen+Risiko; wirft nie.
2. Kern-Pflicht (kein Kern → NONE), Hart-Gate kein Top-Down → NONE.
3. Aktion korrekt aus Konfidenz+Position (SHORT/HOLD/COVER/NONE); LONG → NONE + Konflikt-Pfad.
4. Konfidenz nutzt Katalysator-Cap, Regime, Crowding, bearishe Anomalie (1a).
5. `detect_conflict` bidirektional; `DeepDiveResult.conflict`/`conflict_reason`/`short_assessment` gesetzt.
6. Nicht-Equity → sauberer Fallback (kein Crash).
7. Tests prüfen Verhaltens-Bänder; Gesamtsuite grün (0 failed).
