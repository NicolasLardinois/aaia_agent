# Phase 3 — Long/Short-Futures: Short-Zweig für `wrapper=future` (Rohstoff + Edelmetall)

> Spec (dauerhaftes Design). Status/Reihenfolge/PR-Protokoll stehen **ausschließlich** im Logbuch
> (`docs/open_todos.md`) — hier kein Status.
> Teil der Anlageklassen-Taxonomie (Phase 3). Vorgänger: Phase 2a (Futures-Mechanik, PR #42),
> Phase 2b (Fund-Info, PR #43). Design-Hub Short: `docs/short.md`.

## 1. Ziel & Abgrenzung

Heute ist die Futures-Mechanik **rein long**: `core/utils/futures_curve.py` liefert
`roll_yield_long_ann = −slope` und `curve_signal` interpretiert die Kurve aus Long-Sicht.
Für eine **Short-Position auf einen Future** dreht sich die Mechanik. Dieser Slice ergänzt den
**kurven- und kostengetriebenen Short-Zweig** für `wrapper=future` mit
`underlying ∈ {commodity, precious_metal}`.

**Im Scope:**
- **Roll-Yield für den Short** (Short profitiert von Contango).
- **Cost-Curve-Boden als Deckel** (Produktionskosten-Boden deckelt die Short-Konviktion;
  nahe/unter Kosten dominiert Mean-Reversion nach oben).
- Eigenes Modell `FuturesShortAssessment` (Overlay an `BottomUpResult`), das über die **bestehende**
  Short-Engine (`derive_short_assessment` → `_action`) eine `ShortAction` erzeugt und damit an
  Judgment/Memory/Monitor andockt.

**Bewusst NICHT im Scope:**
- **Kein Borrow/Squeeze** — das sind Aktien-Short-Konzepte; Futures haben keinen Leihezins.
- **Aktienindex- und Anleihe-Futures** — Roll-Yield-Short gälte zwar auch dort, aber der
  Cost-Curve-Boden ist nur bei förderbaren Gütern sinnvoll; eigene Logik in einem späteren Slice.
- **Echte Datenquellen** — Terminkurve und Kostenboden bleiben Stubs (eigene spätere Slices,
  Stub-First-Muster wie Phase 2a). End-to-End ruht der Futures-Short, bis beide Quellen live sind;
  Wert dieses Slices ist die **getestete, einsatzbereite Mechanik**.
- **Regime-Tilt** (Rohstoff fällt in Rezession / Edelmetall steigt risk-off) — als Folge-Aufgabe
  notiert, nicht in v1.

## 2. Architektur (Hexagonal, spiegelt das `futures_curve`-Muster)

```
core/utils/futures_short.py      reine Mathematik (Roll-Yield-Short, Floor-Distanz, Konfidenz)
core/domain/models.py            FuturesShortAssessment (+ .unavailable()); BottomUpResult.futures_short
core/ports/cost_floor.py         CostFloorProvider (ABC)
adapters/data/cost_floor_stub.py StubCostFloorProvider → None
orchestrators/bottom_up_orchestrator.py  _futures_short_overlay (nur commodity/precious_metal + future)
core/domain/short_assessment.py  Nicht-Equity-Zweig konsumiert futures_short → ShortAction
```

Agenten/Domäne hängen nur von Ports ab; echtes I/O nur im Adapter (heute Stub).

## 3. Reine Mathematik — `core/utils/futures_short.py`

- `roll_yield_short_ann(slope: float) -> float` → `+slope`. Der Short rollt die Kurve runter und
  **profitiert** von Contango. Sauber symmetrisch zu `roll_yield_long_ann = −slope`
  (d. h. `roll_yield_short_ann = −roll_yield_long_ann`).
- `floor_distance_pct(spot: float, floor: float | None) -> float | None` → `(spot − floor) / floor`.
  Fallhöhe nach unten in Prozent. `floor` None/≤0 → `None` (kein Boden bekannt).
- `carry_state(slope: float | None) -> str` → `"contango_tailwind"` (slope ≥ +0.05),
  `"backwardation_headwind"` (slope ≤ −0.05), sonst `"neutral"`. Gleiche ±5 %-Bänder wie `curve_signal`.
- `assess_futures_short(snap: FuturesCurveSnapshot | None, cost_floor: float | None) -> FuturesShortAssessment`
  — kombiniert Carry + Floor zur Short-Konfidenz und baut das Modell (s. §6 Schwellen).
  `snap is None` → `FuturesShortAssessment.unavailable()`.

Alle Funktionen pure, keine Seiteneffekte, keine I/O.

## 4. Domänen-Modell — `FuturesShortAssessment`

In `core/domain/models.py`, analog zu `FuturesAssessment`:

| Feld | Typ | Bedeutung |
|---|---|---|
| `roll_yield_short_ann` | `float \| None` | annualisierter Roll-Yield des Shorts (`+slope`) |
| `carry_state` | `str` | `"contango_tailwind"` / `"neutral"` / `"backwardation_headwind"` |
| `cost_floor` | `float \| None` | verwendeter Kostenboden-Preis |
| `floor_distance_pct` | `float \| None` | `(spot − floor)/floor` |
| `floor_binds` | `bool` | Preis nahe/unter Boden → Deckel aktiv |
| `floor_applied` | `bool` | Floor-Daten vorhanden und im Deckel berücksichtigt |
| `short_confidence` | `float` | Engine-Konfidenz 0.10–1.0 (Schwelle 0.50) |
| `engine_action` | `ShortAction` | positions-**agnostische** Engine-Sicht (SHORT/COVER/NONE) |
| `available` | `bool` | Terminkurve vorhanden |

`FuturesShortAssessment.unavailable()` → alle Zahlen `None`/neutral, `engine_action=NONE`,
`floor_binds=False`, `floor_applied=False`, `available=False`.

`BottomUpResult.futures_short: FuturesShortAssessment | None = None` (trailing Optional,
analog zu `futures_curve`/`fund_info`).

## 5. Port + Stub — Kostenboden

`core/ports/cost_floor.py`:
```python
class CostFloorProvider(ABC):
    @abstractmethod
    def get_cost_floor(self, underlying: Underlying, symbol: str) -> float | None:
        """Produktionskosten-Boden als Preis. Rohstoff: Grenzproduktionskosten;
        Edelmetall: All-in-Sustaining-Cost (AISC) der Minen. None = unbekannt."""
```
`adapters/data/cost_floor_stub.py`: `StubCostFloorProvider.get_cost_floor(...) -> None`.
Echte Quelle = eigener späterer Slice; Stub bewusst **nicht** im Composition Root verdrahtet
(wie Phase 2a).

## 6. Schwellen (fachlich begründet, kalibrierbar)

Konfidenz = `clamp(bewertungs_basis + carry_adj, 0.10, 1.0)`, danach Floor-Deckel.

**Carry-Adjustment** (slope = annualisierter Term-Structure-Slope):
- `slope ≥ +0.05` (Contango ≥ +5 %) → `+0.10` (Rückenwind: Kurve zahlt den Short)
- `−0.05 < slope < +0.05` → `0`
- `slope ≤ −0.05` (Backwardation ≤ −5 %) → `−0.12` (Gegenwind: Short zahlt den Roll)

**Bewertungs-Basis** (Fallhöhe `dist = floor_distance_pct`):
- `dist ≥ +0.50` (≥ 50 % über Kosten) → `0.55`
- `+0.25 ≤ dist < +0.50` → `0.45`
- `+0.10 ≤ dist < +0.25` → `0.30`
- `dist < +0.10` (inkl. negativ) → `0.10` **und `floor_binds = True`**

**Cost-Curve-Boden als Deckel:**
- `floor_binds` → `short_confidence = min(conf, 0.49)` → unter Schwelle → Aktion kippt auf
  NONE (kein neuer Short) bzw. COVER (bestehenden eindecken).
  *Begründung:* nahe/unter Produktionskosten dominiert Mean-Reversion nach oben — Short gefährlich.
- **Floor-Daten fehlen** (Stub → None): `floor_applied = False` → ebenfalls `conf = min(conf, 0.49)`.
  *Begründung:* ohne bekannten Kostenboden kein frischer Rohstoff-Short (fachliche Vorsicht).

**Schwelle Aktion** = `0.50` (wiederverwendet `_THRESHOLD` aus `short_assessment.py`).
Kalibrierung später über die Regime-Replay-Initiative (Stufen ③/④).

Die `engine_action` (positions-agnostisch) im Modell: `SHORT` wenn `conf ≥ 0.50`,
`COVER` wenn `floor_binds` (klares „raus/meiden"), sonst `NONE`.

## 7. Orchestrator-Overlay — `bottom_up_orchestrator.py`

- Konstruktor: neuer optionaler `cost_floor_provider: CostFloorProvider | None = None`.
- `_futures_short_overlay(symbol, underlying, wrapper, snap)`:
  - aktiv **nur** bei `wrapper == Wrapper.FUTURE` **und** `underlying ∈ {COMMODITY, PRECIOUS_METAL}`;
    sonst `None`.
  - **Single-Fetch:** die Terminkurven-`snap` wird im Pfad **einmal** geholt und sowohl an das
    Long- (`assess_futures_curve`) als auch an das Short-Assessment weitergereicht — kein
    Doppel-Fetch, keine Inkonsistenz. Refactor von `_run_commodity`/`_run_precious_metals`:
    snap einmal holen, beide Assessments daraus ableiten.
  - Kostenboden defensiv: fehlender Provider/Exception → `floor=None` (Deckel via `floor_applied=False`).
  - Defensiv: snap None / Exception → `FuturesShortAssessment.unavailable()` statt Crash.
- Ergebnis an `BottomUpResult.futures_short`.

## 8. Andocken an die Short-Engine — `core/domain/short_assessment.py`

Der bestehende Nicht-Equity-Fallback
(`if underlying != Underlying.EQUITY: … "Fallback: klassenspezifische Short-Logik folgt"`)
wird für `underlying ∈ {COMMODITY, PRECIOUS_METAL}` **und** `wrapper == FUTURE` ersetzt:

1. `fs = getattr(bottom_up, "futures_short", None)`.
2. Fehlt `fs` oder `not fs.available` → bisheriger konservativer Fallback (HOLD wenn SHORT, sonst NONE,
   conf 0.10) bleibt.
3. Sonst: `conf = fs.short_confidence`; `action = _action(current_position, conf, position_pnl_pct)`
   (positions-bewusst: COVER bei gebrochener These, HOLD/SHORT/SHORT+ sonst — **bestehende**
   `_action`-Logik; `position_pnl_pct` durchreichen, damit SHORT+ in einen gewinnenden Future-Short
   symmetrisch zur Equity-Logik feuern kann).
4. `archetypes`/`thesis_flags` aus den Futures-Fakten: z. B. `["carry_short"]` plus Detail-Strings
   (`carry_state`, `floor_distance_pct`, `floor_binds`). Equity-Felder (`squeeze_risk="low"`,
   `hard_to_borrow=False`) neutral — passt, da kein Borrow/Squeeze.
5. `suggested_size_pct`: bei `action == SHORT` analog Equity konservativ
   (`_position_size_pct(conf) * 0.5`); Hebel-Berücksichtigung erbt der bestehende Sizing-Pfad
   (Phase 2a). `stop_pct = 15.0` (Default; futures-spezifischer Take-Profit am Boden = Folge-Aufgabe).

Andere Nicht-Equity-Fälle (z. B. bond, oder commodity/metal ohne `wrapper=future`) behalten den
bisherigen Fallback.

## 9. Testplan (TDD, Rot→Grün je Einheit)

**`tests/utils/test_futures_short.py`:**
- `roll_yield_short_ann`: Vorzeichen (Contango → positiv), slope=0 → 0, Symmetrie zu long.
- `floor_distance_pct`: spot=floor → 0.0; spot<floor → negativ; floor None/0 → None.
- `carry_state`: Bandgrenzen genau (±0.05), None.
- `assess_futures_short`: jede Carry×Floor-Zelle (Erwartungswert Konfidenz + Aktion);
  `floor_binds`-Deckel (conf < 0.50); `floor_applied=False`-Pfad (floor None → Deckel greift);
  `snap=None` → `unavailable()`.

**`tests/orchestrators/` (Overlay):**
- aktiv nur bei commodity/precious_metal + future; equity/index/bond oder wrapper≠future → `futures_short is None`.
- Single-Fetch: Terminkurven-Provider wird im Pfad genau **einmal** aufgerufen (Long+Short teilen snap).
- Provider wirft → `unavailable()`, kein Crash (Default-Pfad).

**`tests/.../test_short_assessment*.py` (Engine-Zweig):**
- commodity/metal + future: `current_position` none/long/short × Konfidenz-Bänder → erwartete `ShortAction`
  (none+conf≥0.5 → SHORT; short+conf<0.5 → COVER; short+conf≥0.5 → HOLD; long → NONE).
- `floor_binds` → conf gedeckelt → none→NONE / short→COVER.
- `futures_short` fehlt/unavailable → bisheriger Fallback unverändert.

**Fehlerpfade:** jede Datenquelle wirft → Default/`unavailable`, nie Absturz der Analyse.

## 10. Risiken & offene Folge-Aufgaben (ins Logbuch)

- **Regime-Tilt** (underlying-abhängig: Rohstoff-Short Rückenwind in Rezession; Edelmetall-Short
  Gegenwind risk-off) — v2.
- **Futures-Take-Profit am Kostenboden** (Boden als Ziel, nicht nur Deckel) — v2.
- **Echte Quellen:** Terminkurve (Phase-2a-Folge) + Kostenboden (Produktionskosten/AISC) anbinden,
  dann im Composition Root verdrahten.
- **Aktienindex-/Anleihe-Futures-Short** (Roll-Yield ohne Kostenboden) — eigener Slice.
- **Schwellen-Kalibrierung** über Regime-Replay ③/④.
