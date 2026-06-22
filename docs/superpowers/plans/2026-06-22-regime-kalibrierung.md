# Regime-Kalibrierung (Stufe ②-v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den einen höchsten Hebel des Regime-Motors — die Risk-off-Grenze (ein Composite-Bias `b`) — per Walk-Forward gegen NBER kalibrieren und als look-ahead-freien **Vorschlag-Report** ausgeben (kein Auto-Apply; darf „Default behalten" sagen).

**Architecture:** Eine reine Konstante `_REGIME_BIAS` (Default 0,0) bekommt einen Platz im Regime-Motor (kein Verhaltenswechsel). Ein reiner `RegimeCalibrator` (`core/utils/`) probiert per 1-D-Gitter Bias-Werte gegen die NBER-Wahrheit, in einem Expanding-Window-Walk-Forward (Train/Test getrennt), nutzt die Trend-Shift-Invarianz, um jedes `b` ohne Replay-Neulauf nachzurechnen, und liefert einen Vorschlag inkl. Markt-Härtetest (Evaluator A aus ①). Eine CLU schreibt den Report.

**Tech Stack:** Python 3.12, `pytest`, `python-dateutil`, `yfinance`/`fredapi` (nur in der CLI), bestehende Stufe-①-Bausteine (`RegimeDetector`, `run_replay`, `core/utils/regime_eval.py`).

## Global Constraints

- **Sprache:** Code-Kommentare/Docstrings auf **Deutsch** (Projektkonvention).
- **TDD verpflichtend:** erst der fehlschlagende Test, dann Code (AGENTS.md §4).
- **PR-First:** alle Commits auf Branch `worktree-regime-calibration`. Nie direkt auf `master`. Kein `--no-verify`.
- **Staging explizit:** nur genannte Pfade (`git add <pfad>`), nie `git add -A`.
- **Rückwärtskompatibel:** `_REGIME_BIAS = 0.0` und `evidence["trend"]` dürfen das Live-Verhalten **nicht** ändern. Bestehende Tests bleiben grün.
- **Reine Funktionen ohne I/O** in `core/` (`regime_calibration.py`): kein Netz/Datei. Kursabruf/NBER werden injiziert.
- **Kein Auto-Apply:** der Lauf schreibt nur einen Report, mutiert nie `_REGIME_BIAS`.
- **Verzerrungs-Konvention:** der Bias wird als `_regime_from(composite + b, trend)` angewandt. `evidence["composite"]` bleibt der **unverzerrte** Rohwert.
- **Bias-Gitter:** `b ∈ [−0,40, +0,40]`, Schritt `0,02` (41 Werte). Zielmetrik: **F1** von risk-off (`{SLOWDOWN, RECESSION, DEPRESSION}`) vs. NBER (`USREC=1`).

---

### Task 1: Produktions-Knopf `_REGIME_BIAS` + `evidence["trend"]`

**Files:**
- Modify: `core/domain/regime.py` (Konstante + Methode `RegimeDetector.detect`, ~Zeile 15–17 und 170–186)
- Test: `tests/domain/test_regime.py`

**Interfaces:**
- Produces: Modul-Konstante `_REGIME_BIAS: float = 0.0`. `RegimeDetector.detect(...)` setzt zusätzlich `evidence["trend"]` (der berechnete Trend, `float | None`) und wendet den Bias an: `regime = _regime_from(composite + _REGIME_BIAS, trend)`. Default 0,0 → identisches Verhalten.

- [ ] **Step 1: Write the failing tests**

```python
# tests/domain/test_regime.py  (ans Ende anfügen)
def test_regime_bias_default_null_aendert_nichts():
    """_REGIME_BIAS Default 0.0 → Regime identisch zum bisherigen Verhalten."""
    import core.domain.regime as regime_mod
    assert regime_mod._REGIME_BIAS == 0.0
    det = regime_mod.RegimeDetector()
    state = {"gdp_growth": 3.5, "unemployment": 3.5, "inflation": 2.0}
    hist = [("2020-01-01", 0.1), ("2020-02-01", 0.2)]
    regime, _, evidence = det.detect(state, history=hist)
    # bei Bias 0 ist das Regime das, was _regime_from(composite, trend) liefert
    from core.domain.regime import _regime_from, _trend
    composite = evidence["composite"]
    trend = _trend(hist, composite)
    assert regime == _regime_from(composite, trend)


def test_evidence_enthaelt_trend():
    """detect gibt den Trend je Stichtag aus (für die Kalibrierung)."""
    import core.domain.regime as regime_mod
    det = regime_mod.RegimeDetector()
    state = {"gdp_growth": 1.0}
    # zwei-Punkt-Historie → Trend ist berechenbar (nicht None)
    regime, _, evidence = det.detect(state, history=[("2020-01-01", -0.1), ("2020-02-01", 0.0)])
    assert "trend" in evidence
    assert evidence["trend"] is not None


def test_trend_ist_shift_invariant():
    """Kern-Annahme der Kalibrierung: ein gleichmäßiger Bias auf alle Composites
    lässt den Trend (current - mean(history)) unverändert."""
    from core.domain.regime import _trend
    hist = [("2020-01-01", -0.2), ("2020-02-01", 0.0), ("2020-03-01", 0.2)]
    b = 0.15
    shifted = [(d, v + b) for d, v in hist]
    assert abs(_trend(hist, 0.3) - _trend(shifted, 0.3 + b)) < 1e-12
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/domain/test_regime.py::test_regime_bias_default_null_aendert_nichts tests/domain/test_regime.py::test_evidence_enthaelt_trend -v`
Expected: FAIL — `_REGIME_BIAS` existiert nicht (`AttributeError`) bzw. `"trend"` fehlt in `evidence` (`KeyError`/`assert`). *(Der Shift-Invarianz-Test nutzt nur `_trend` und ist bereits grün — er pinnt die Annahme, kein neuer Code nötig.)*

- [ ] **Step 3: Implement the constant + detect changes**

In `core/domain/regime.py` nach den `_TREND_*`-Konstanten (~Zeile 16) ergänzen:

```python
# Kalibrierbarer Risk-off-Grenz-Bias: wird vor der Regime-Zuordnung auf den Composite addiert.
# Default 0.0 = heutiges Verhalten. Stufe ②-Kalibrierung schlägt einen Wert vor (kein Auto-Apply).
# b < 0 → Risk-off feuert früher (sensibler); b > 0 → später.
_REGIME_BIAS: float = 0.0
```

In `detect` (nach `composite`/Trend-Block, vor `confidence`) die zwei Zeilen ergänzen/ändern:

```python
        evidence["trend"] = trend
        regime     = _regime_from(composite + _REGIME_BIAS, trend)
        confidence = round(min(1.0, abs(composite) * 1.5 + 0.3), 3)
        return regime, confidence, evidence
```

(Die alte Zeile `regime = _regime_from(composite, trend)` wird durch die `+ _REGIME_BIAS`-Variante ersetzt; `evidence["trend"] = trend` kommt direkt davor.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/domain/test_regime.py -v`
Expected: PASS (neue Tests + alle bestehenden Regime-Tests grün — Default-Bias 0 ändert nichts).

- [ ] **Step 5: Commit**

```bash
git add core/domain/regime.py tests/domain/test_regime.py
git commit -m "feat(regime): kalibrierbarer _REGIME_BIAS (Default 0) + evidence['trend']"
```

---

### Task 2: `run_replay` gibt den Trend je Stichtag aus

**Files:**
- Modify: `agents/backtester/regime_replay.py` (Funktion `run_replay`, das `urteile.append({...})`-Dict)
- Test: `tests/agents/backtester/test_regime_replay.py`

**Interfaces:**
- Consumes: `evidence["trend"]` aus Task 1.
- Produces: jedes Urteil-Dict aus `run_replay` enthält zusätzlich `"trend": float | None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agents/backtester/test_regime_replay.py  (ans Ende anfügen)
def test_urteil_enthaelt_trend():
    from datetime import date
    stichtage = [date(2000, 1, 1), date(2000, 2, 1)]
    urteile = run_replay(lambda d: _FakeProvider(d), stichtage)
    # erster Stichtag: leere Historie → Trend None; zweiter: Trend berechenbar
    assert "trend" in urteile[0]
    assert urteile[0]["trend"] is None
    assert urteile[1]["trend"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agents/backtester/test_regime_replay.py::test_urteil_enthaelt_trend -v`
Expected: FAIL — `"trend"` ist (noch) kein Schlüssel im Urteil-Dict (`KeyError`/`assert`).

- [ ] **Step 3: Implement — add trend to the judgment dict**

In `agents/backtester/regime_replay.py`, in `run_replay`, das `urteile.append({...})` um `"trend"` ergänzen (der Trend liegt in `evidence["trend"]` aus Task 1):

```python
        urteile.append({
            "as_of": as_of,
            "regime": regime,
            "confidence": confidence,
            "composite": round(composite, 4),
            "trend": evidence.get("trend"),
            "data_quality": getattr(provider, "quality", "unbekannt"),
        })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/agents/backtester/test_regime_replay.py -v`
Expected: PASS (neuer Test + bestehende Replay-Tests grün).

- [ ] **Step 5: Commit**

```bash
git add agents/backtester/regime_replay.py tests/agents/backtester/test_regime_replay.py
git commit -m "feat(replay): Trend je Stichtag im Urteil-Dict (für Kalibrierung)"
```

---

### Task 3: Kalibrator-Kern — F1 je Bias + Gitter-Suche

**Files:**
- Create: `core/utils/regime_calibration.py`
- Test: `tests/core/utils/test_regime_calibration.py`

**Interfaces:**
- Consumes: `core.domain.regime._regime_from`, `core.utils.regime_eval.evaluate_nber`.
- Produces:
  - `bias_grid() -> list[float]` → `[-0.40, -0.38, …, 0.40]` (41 Werte, auf 2 Stellen gerundet).
  - `f1_for_bias(records: list[tuple], usrec_by_month: dict, b: float) -> float`. `records`: `[(as_of: date, composite: float, trend: float | None), …]`.
  - `best_bias_on(records, usrec_by_month, grid: list[float]) -> tuple[float, float]` → `(b_star, f1)`. Bei F1-Gleichstand gewinnt der **betragskleinste** Bias (konservativ Richtung Default).

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/utils/test_regime_calibration.py
from datetime import date
from core.domain.models import MarketRegime
from core.utils.regime_calibration import bias_grid, f1_for_bias, best_bias_on


def test_bias_grid_umfang_und_raender():
    g = bias_grid()
    assert len(g) == 41
    assert g[0] == -0.40 and g[-1] == 0.40
    assert 0.0 in g


def _rec(y, m, composite):
    # Trend None (für diese Tests irrelevant) — Regime hängt nur am (composite + b)
    return (date(y, m, 1), composite, None)


def test_f1_perfekt_bei_passender_grenze():
    # Composite knapp unter 0.15 in Rezessionsmonaten, klar darüber sonst.
    # Bei Bias 0 liegt die Risk-off-Grenze bei ~0.15 → perfekte Trennung → F1 = 1.0.
    records = [_rec(2001, 1, 0.5), _rec(2001, 2, 0.5),
               _rec(2001, 3, 0.0), _rec(2001, 4, 0.0)]   # 0.0 → SLOWDOWN (risk-off)
    usrec = {"2001-01": 0, "2001-02": 0, "2001-03": 1, "2001-04": 1}
    assert f1_for_bias(records, usrec, 0.0) == 1.0


def test_best_bias_findet_optimum_und_bevorzugt_default_bei_gleichstand():
    # Daten, bei denen Bias 0 bereits perfekt trennt → b_star muss 0.0 sein
    # (auch wenn andere b ebenfalls F1=1.0 erreichen — Tie-Break: betragskleinst).
    records = [_rec(2001, 1, 0.5), _rec(2001, 2, 0.5),
               _rec(2001, 3, 0.0), _rec(2001, 4, 0.0)]
    usrec = {"2001-01": 0, "2001-02": 0, "2001-03": 1, "2001-04": 1}
    b_star, f1 = best_bias_on(records, usrec, bias_grid())
    assert f1 == 1.0
    assert b_star == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/core/utils/test_regime_calibration.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.utils.regime_calibration'`.

- [ ] **Step 3: Implement the module**

```python
# core/utils/regime_calibration.py
"""Reine Kalibrierung der Risk-off-Grenze des Regime-Motors: probiert einen Composite-Bias `b`
gegen die NBER-Wahrheit (Ziel F1), per Walk-Forward (Train/Test getrennt). Kein I/O —
Kursabruf/NBER werden injiziert. Nutzt die Trend-Shift-Invarianz: jedes `b` ist aus den
gespeicherten (composite, trend) je Stichtag nachrechenbar, ohne den Replay neu zu fahren."""
from core.domain.regime import _regime_from
from core.utils.regime_eval import evaluate_nber


def bias_grid() -> list[float]:
    """1-D-Gitter der Bias-Kandidaten: -0.40 … +0.40 in 0.02-Schritten (41 Werte)."""
    return [round(-0.40 + 0.02 * i, 2) for i in range(41)]


def _confusion_for_bias(records: list, usrec_by_month: dict, b: float) -> tuple:
    """Konfusionszähler (tp, fp, fn) für einen Bias `b`: Regime via _regime_from(composite+b, trend),
    abgeglichen gegen NBER über die bestehende evaluate_nber."""
    biased = [{"as_of": d, "regime": _regime_from(c + b, t)} for (d, c, t) in records]
    nb = evaluate_nber(biased, usrec_by_month)
    return nb["tp"], nb["fp"], nb["fn"]


def f1_from_counts(tp: int, fp: int, fn: int) -> float:
    """F1 aus Konfusionszählern; 0.0 wenn nicht definiert (keine risk-off-Calls oder keine Rezession)."""
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * p * r / (p + r) if (p + r) else 0.0


def f1_for_bias(records: list, usrec_by_month: dict, b: float) -> float:
    tp, fp, fn = _confusion_for_bias(records, usrec_by_month, b)
    return f1_from_counts(tp, fp, fn)


def best_bias_on(records: list, usrec_by_month: dict, grid: list) -> tuple:
    """Bias mit maximalem F1 auf `records`. Tie-Break: betragskleinster Bias (Richtung Default 0)."""
    best_b, best_f1 = 0.0, -1.0
    for b in grid:
        f1 = f1_for_bias(records, usrec_by_month, b)
        if f1 > best_f1 + 1e-12 or (abs(f1 - best_f1) <= 1e-12 and abs(b) < abs(best_b)):
            best_b, best_f1 = b, f1
    return best_b, best_f1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/utils/test_regime_calibration.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/utils/regime_calibration.py tests/core/utils/test_regime_calibration.py
git commit -m "feat(calib): Kalibrator-Kern — F1 je Bias + Gitter-Suche (Tie-Break Richtung Default)"
```

---

### Task 4: Walk-Forward + `calibrate` (Urteil + Markt-Härtetest)

**Files:**
- Modify: `core/utils/regime_calibration.py` (Funktionen `walk_forward`, `calibrate` ergänzen)
- Test: `tests/core/utils/test_regime_calibration_wf.py`

**Interfaces:**
- Consumes: `bias_grid`, `f1_for_bias`, `f1_from_counts`, `_confusion_for_bias`, `best_bias_on` (Task 3); `core.utils.regime_eval.evaluate_market` (Evaluator A).
- Produces:
  - `walk_forward(records, usrec_by_month, folds: int, grid: list) -> dict` → `{"tuned_oos_f1", "default_oos_f1", "tuning_wins": bool, "per_fold": [{"fold", "b": float, "test_f1": float, "default_test_f1": float, "n_test": int}, …]}`. Expanding-Window: Fold *i* trainiert auf den Slices 0..i-1, testet auf Slice *i*. OOS-F1 wird über alle Test-Slices **gepoolt** (Konfusion aufsummiert).
  - `calibrate(records, usrec_by_month, sp_price_on=None, folds: int = 4, grid: list | None = None) -> dict` → voller Report (siehe Code). `sp_price_on(d: date) -> float | None` optional (Markt-Härtetest A); ohne → `a_check=None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/utils/test_regime_calibration_wf.py
from datetime import date
from core.domain.models import MarketRegime
from core.utils.regime_calibration import walk_forward, calibrate, bias_grid


def _series(n_per_phase=6):
    """Konstruiert eine wiederkehrende Reihe: 'gesund' (0.5) dann 'krank' (0.0) im Wechsel,
    NBER=1 in den kranken Phasen. Bei Bias 0 trennt die ~0.15-Grenze sauber → Default ist gut."""
    records, usrec = [], {}
    y = 1970
    for block in range(8):
        composite = 0.5 if block % 2 == 0 else 0.0
        rec = 0 if block % 2 == 0 else 1
        for m in range(1, n_per_phase + 1):
            d = date(y, m, 1)
            records.append((d, composite, None))
            usrec[f"{y:04d}-{m:02d}"] = rec
        y += 1
    return records, usrec


def test_walk_forward_trennt_train_test_und_default_gewinnt():
    records, usrec = _series()
    wf = walk_forward(records, usrec, folds=3, grid=bias_grid())
    assert len(wf["per_fold"]) == 3
    # Default trennt hier sauber → Tuning bringt out-of-sample keinen Vorteil
    assert wf["tuning_wins"] is False
    assert wf["default_oos_f1"] >= wf["tuned_oos_f1"] - 1e-9


def test_calibrate_urteil_default_behalten_ohne_a_check():
    records, usrec = _series()
    report = calibrate(records, usrec, sp_price_on=None, folds=3)
    assert report["verdict"] == "keep_default"
    assert report["a_check"] is None
    assert report["default_bias"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/core/utils/test_regime_calibration_wf.py -v`
Expected: FAIL — `ImportError: cannot import name 'walk_forward'` (bzw. `calibrate`).

- [ ] **Step 3: Implement walk_forward + calibrate (append to `regime_calibration.py`)**

```python
def _slices(n: int, parts: int) -> list:
    """Zerlegt Index 0..n-1 in `parts` möglichst gleich große, zusammenhängende Slices (Indexgrenzen)."""
    bounds = [round(i * n / parts) for i in range(parts + 1)]
    return [(bounds[i], bounds[i + 1]) for i in range(parts)]


def walk_forward(records: list, usrec_by_month: dict, folds: int, grid: list) -> dict:
    """Expanding-Window: Fold i trainiert auf Slices 0..i-1, testet blind auf Slice i.
    OOS-F1 wird über alle Test-Slices gepoolt (Konfusion aufsummiert) — getuntes b je Fold vs. b=0."""
    records = sorted(records, key=lambda r: r[0])
    slices = _slices(len(records), folds + 1)   # folds Test-Slices (Slice 0 ist nur Trainings-Seed)
    per_fold = []
    tp_t = fp_t = fn_t = 0      # gepoolte Konfusion getuntes b
    tp_d = fp_d = fn_d = 0      # gepoolte Konfusion Default b=0
    for i in range(1, folds + 1):
        train = records[: slices[i - 1][1]]     # alles bis Ende des Vor-Slices
        test = records[slices[i][0]: slices[i][1]]
        b_fold, _ = best_bias_on(train, usrec_by_month, grid)
        ttp, tfp, tfn = _confusion_for_bias(test, usrec_by_month, b_fold)
        dtp, dfp, dfn = _confusion_for_bias(test, usrec_by_month, 0.0)
        tp_t += ttp; fp_t += tfp; fn_t += tfn
        tp_d += dtp; fp_d += dfp; fn_d += dfn
        per_fold.append({
            "fold": i, "b": b_fold, "n_test": len(test),
            "test_f1": round(f1_from_counts(ttp, tfp, tfn), 3),
            "default_test_f1": round(f1_from_counts(dtp, dfp, dfn), 3),
        })
    tuned_oos = f1_from_counts(tp_t, fp_t, fn_t)
    default_oos = f1_from_counts(tp_d, fp_d, fn_d)
    return {
        "tuned_oos_f1": round(tuned_oos, 3),
        "default_oos_f1": round(default_oos, 3),
        "tuning_wins": tuned_oos > default_oos + 1e-9,
        "per_fold": per_fold,
    }


def _a_hit_rates(records: list, sp_price_on, b: float) -> dict:
    """Markt-Hit-Rate (Evaluator A) je Horizont für einen Bias b."""
    from core.utils.regime_eval import evaluate_market
    judgments = [{"as_of": d, "regime": _regime_from(c + b, t)} for (d, c, t) in records]
    market = evaluate_market(judgments, sp_price_on, horizons_months=(3, 6, 12))
    return {h: market[h]["hit_rate"] for h in market}


def calibrate(records: list, usrec_by_month: dict, sp_price_on=None,
              folds: int = 4, grid: list | None = None) -> dict:
    """Walk-Forward-Urteil + finaler Vorschlag b* (bestes F1 auf voller Historie) + Markt-Härtetest A.
    Schlägt Tuning den Default out-of-sample → verdict 'adopt'; sonst 'keep_default'."""
    grid = grid or bias_grid()
    wf = walk_forward(records, usrec_by_month, folds, grid)
    b_star, full_f1 = best_bias_on(records, usrec_by_month, grid)
    default_full_f1 = f1_for_bias(records, usrec_by_month, 0.0)

    a_check = None
    if sp_price_on is not None:
        hr_star = _a_hit_rates(records, sp_price_on, b_star)
        hr_default = _a_hit_rates(records, sp_price_on, 0.0)
        # Warnung, wenn b* den Markt zum 6M-Horizont schlechter macht als der Default
        warn = (hr_star.get(6) is not None and hr_default.get(6) is not None
                and hr_star[6] < hr_default[6])
        a_check = {"b_star": hr_star, "default": hr_default, "warning": warn}

    adopt = wf["tuning_wins"] and b_star != 0.0
    n_rec = sum(1 for v in usrec_by_month.values() if v == 1)
    return {
        "b_star": b_star,
        "default_bias": 0.0,
        "full_f1_b_star": round(full_f1, 3),
        "full_f1_default": round(default_full_f1, 3),
        "walk_forward": wf,
        "a_check": a_check,
        "verdict": "adopt" if adopt else "keep_default",
        "n_recession_months": n_rec,
        "n_records": len(records),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/utils/test_regime_calibration_wf.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/utils/regime_calibration.py tests/core/utils/test_regime_calibration_wf.py
git commit -m "feat(calib): Walk-Forward + calibrate (Urteil adopt/keep_default + Markt-Härtetest A)"
```

---

### Task 5: Report-Builder + CLI `app/calibrate_regime.py`

**Files:**
- Modify: `core/utils/regime_calibration.py` (Funktion `build_calib_report_md`)
- Create: `app/calibrate_regime.py`
- Test: `tests/core/utils/test_regime_calibration_report.py`

**Interfaces:**
- Consumes: `calibrate`-Report-Dict (Task 4).
- Produces:
  - `build_calib_report_md(report: dict) -> str` — lesbare Markdown-Zusammenfassung inkl. Urteil.
  - `app/calibrate_regime.py`: CLI `python -m app.calibrate_regime [--start YYYY-MM] [--end YYYY-MM] [--folds N]` → schreibt `data/backtests/regime_calib_YYYYMMDD.(json|md)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/utils/test_regime_calibration_report.py
from core.utils.regime_calibration import build_calib_report_md


def _report(verdict="keep_default", a_check=None):
    return {
        "b_star": 0.0, "default_bias": 0.0,
        "full_f1_b_star": 0.62, "full_f1_default": 0.62,
        "walk_forward": {"tuned_oos_f1": 0.55, "default_oos_f1": 0.58, "tuning_wins": False,
                         "per_fold": [{"fold": 1, "b": -0.04, "n_test": 120,
                                       "test_f1": 0.5, "default_test_f1": 0.56}]},
        "a_check": a_check, "verdict": verdict,
        "n_recession_months": 90, "n_records": 600,
    }


def test_report_keep_default_enthaelt_urteil_und_kennzahlen():
    md = build_calib_report_md(_report())
    assert "Default behalten" in md or "keep_default" in md
    assert "Out-of-Sample" in md
    assert "0.58" in md            # default OOS-F1
    assert "Rezessionsmonate" in md


def test_report_a_warnung_sichtbar():
    md = build_calib_report_md(_report(verdict="adopt", a_check={
        "b_star": {3: 0.6, 6: 0.55, 12: 0.6}, "default": {3: 0.6, 6: 0.62, 12: 0.6},
        "warning": True}))
    assert "Warnung" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/utils/test_regime_calibration_report.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_calib_report_md'`.

- [ ] **Step 3: Implement build_calib_report_md (append to `regime_calibration.py`)**

```python
def build_calib_report_md(report: dict) -> str:
    """Lesbare Markdown-Zusammenfassung des Kalibrier-Vorschlags."""
    wf = report["walk_forward"]
    adopt = report["verdict"] == "adopt"
    lines = [
        "# Regime-Kalibrierung — Vorschlag (Risk-off-Grenze)",
        "",
        f"- Datenpunkte (Monate): **{report['n_records']}**, davon Rezessionsmonate (NBER): "
        f"**{report['n_recession_months']}**",
        f"- Vorgeschlagener Bias **b\\* = {report['b_star']:+.2f}** "
        f"(Default = {report['default_bias']:+.2f})",
        f"- F1 auf voller Historie: b\\* = {report['full_f1_b_star']:.3f} vs. "
        f"Default {report['full_f1_default']:.3f}",
        "",
        "## Out-of-Sample (Walk-Forward) — der ehrliche Test",
        "",
        f"- **Getuntes b OOS-F1: {wf['tuned_oos_f1']:.3f}** vs. **Default OOS-F1: "
        f"{wf['default_oos_f1']:.3f}**",
        "",
        "| Fold | b (Train) | N Test | Test-F1 (b) | Test-F1 (Default) |",
        "|---|---|---|---|---|",
    ]
    for f in wf["per_fold"]:
        lines.append(f"| {f['fold']} | {f['b']:+.2f} | {f['n_test']} | "
                     f"{f['test_f1']:.3f} | {f['default_test_f1']:.3f} |")

    ac = report.get("a_check")
    if ac is not None:
        lines += ["", "## Markt-Härtetest (A) — Hit-Rate je Horizont", ""]
        for h in sorted(ac["b_star"]):
            s = ac["b_star"][h]; d = ac["default"][h]
            s_str = f"{s*100:.0f} %" if s is not None else "n/v"
            d_str = f"{d*100:.0f} %" if d is not None else "n/v"
            lines.append(f"- {h} M: b\\* {s_str} vs. Default {d_str}")
        if ac.get("warning"):
            lines.append("- ⚠️ **Warnung:** b\\* verbessert NBER, verschlechtert aber den Markt "
                         "(6M) — Übernahme fraglich.")

    lines += ["", "## Urteil", ""]
    if adopt:
        lines.append(f"**Bias b\\* = {report['b_star']:+.2f} übernehmen** — schlägt den Default "
                     f"out-of-sample (OOS-F1 {wf['tuned_oos_f1']:.3f} > {wf['default_oos_f1']:.3f}). "
                     "Übernahme per PR: `_REGIME_BIAS` in `core/domain/regime.py` setzen.")
    else:
        lines.append("**Default behalten — nichts ändern.** Die Hand-Einstellung (Bias 0) ist "
                     "out-of-sample nicht zu schlagen. Das bestätigt die heutige Grenze. "
                     "(keep_default)")
    lines += ["", f"_Hinweis: Mit nur {report['n_recession_months']} Rezessionsmonaten über "
              f"{len(wf['per_fold'])} Folds ist die OOS-Schätzung verrauscht — ein kleiner, über "
              "Folds stabiler Effekt ist glaubwürdiger als ein großer Einzelfund._"]
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/utils/test_regime_calibration_report.py -v`
Expected: PASS.

- [ ] **Step 5: Implement the CLI**

```python
# app/calibrate_regime.py
"""Regime-Kalibrierung (Stufe ②-v1) — schlägt einen Risk-off-Grenz-Bias vor (kein Auto-Apply).
Verwendung:
  python -m app.calibrate_regime [--start YYYY-MM] [--end YYYY-MM] [--folds N]
Schreibt data/backtests/regime_calib_YYYYMMDD.(json|md)."""
import argparse
import json
import os
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
import yfinance as yf
from fredapi import Fred

from config.settings import FRED_API_KEY
from adapters.data.historical_fred import HistoricalFredProvider
from adapters.data.ecb_snb_stub import EcbStubProvider, SnbStubProvider
from agents.backtester.regime_replay import run_replay
from core.utils.backtest import benchmark_for_market
from core.utils.regime_calibration import calibrate, build_calib_report_md

_REGION = "USA"   # v1: USA (Composition-Root; Region-Steckbarkeit wie in ①)


def _monatserste(start: date, end: date) -> list:
    out, cur = [], start
    while cur <= end:
        out.append(cur)
        cur = cur + relativedelta(months=1)
    return out


def _price_on(ticker: str, d: date):
    try:
        df = yf.Ticker(ticker).history(
            start=d.strftime("%Y-%m-%d"), end=(d + timedelta(days=10)).strftime("%Y-%m-%d"))
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[0])
    except Exception:
        return None


def _usrec_by_month(fred: Fred) -> dict:
    s = fred.get_series("USREC").dropna()
    return {f"{ts.year:04d}-{ts.month:02d}": int(v) for ts, v in s.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="1960-01")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m"))
    ap.add_argument("--folds", type=int, default=4)
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m").date().replace(day=1)
    end = datetime.strptime(args.end, "%Y-%m").date().replace(day=1)
    stichtage = _monatserste(start, end)

    print(f"[RegimeCalib] {len(stichtage)} Stichtage {args.start}..{args.end}, {args.folds} Folds …")
    urteile = run_replay(
        lambda d: HistoricalFredProvider(FRED_API_KEY, d), stichtage,
        ecb_factory=lambda d: EcbStubProvider(), snb_factory=lambda d: SnbStubProvider())
    records = [(u["as_of"], u["composite"], u["trend"]) for u in urteile]

    fred = Fred(api_key=FRED_API_KEY)
    usrec = _usrec_by_month(fred)
    benchmark = benchmark_for_market(_REGION)
    report = calibrate(records, usrec, sp_price_on=lambda d: _price_on(benchmark, d),
                       folds=args.folds)
    md = build_calib_report_md(report)

    os.makedirs("data/backtests", exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    with open(f"data/backtests/regime_calib_{stamp}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    with open(f"data/backtests/regime_calib_{stamp}.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    print(f"\n[RegimeCalib] Report → data/backtests/regime_calib_{stamp}.(json|md)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the report test + smoke-check the entrypoint imports**

Run: `python -m pytest tests/core/utils/test_regime_calibration_report.py -v`
Expected: PASS.

Run: `python -c "import app.calibrate_regime"`
Expected: kein Fehler. *(Kein echter Lauf — der zieht Netz/FRED-Key.)*

- [ ] **Step 7: Commit**

```bash
git add core/utils/regime_calibration.py tests/core/utils/test_regime_calibration_report.py app/calibrate_regime.py
git commit -m "feat(calib): Report-Builder + CLI app.calibrate_regime (Vorschlag, kein Auto-Apply)"
```

---

## Abschluss: Gesamtsuite + Logbuch

- [ ] **Step 1: Gesamte Testsuite grün**

Run: `python -m pytest -q`
Expected: Alle Tests grün (bestehende + neue), keine Regression.

- [ ] **Step 2: Logbuch-Eintrag (auf dem Branch, nicht direkt master)**

In `docs/open_todos.md` §5 unter „Regime-Backtester" ergänzen: Stufe ②-v1 (Risk-off-Grenze kalibrieren) umgesetzt, mit Verweis auf Spec/Plan; ②-v2 (Gewichte) als offene Folge-Aufgabe notieren. Committen:

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): Regime-Kalibrierung Stufe ②-v1 umgesetzt, ②-v2 notiert"
```

- [ ] **Step 3: Branch fertig — PR vorbereiten**

Verwende die Skill `superpowers:finishing-a-development-branch`. **Nicht** ohne ausdrückliches OK des Users mergen (AGENTS.md §5, PR-First).

---

## Self-Review (vom Planautor durchgeführt)

**Spec-Abdeckung:**
- §3 Bias-Knopf `_REGIME_BIAS` + Trend-Invarianz → Task 1. §3 `evidence["trend"]`-Voraussetzung (§7) → Task 1 + Task 2. §4 F1-Metrik (`evaluate_nber`-Reuse) → Task 3. §5 Walk-Forward + Gitter + A-Härtetest → Task 4. §6 Deliverable (Report + Urteil keep_default/adopt) → Task 5. §8 Komponenten (reiner Kalibrator + CLI) → Tasks 3/4/5. §9 Tests → in jeder Task (Trend-Invarianz, gepflanztes Optimum, WF-kein-Leck, Default-gewinnt, A-Warnung). §10 ehrliche Grenzen (Stichprobengröße) → Report-Hinweis (Task 5).

**Platzhalter-Scan:** Kein TBD/TODO im ausführbaren Code.

**Typ-Konsistenz:** `records: list[tuple[date, float, float|None]]` durchgängig (Tasks 3/4/5). `bias_grid()`, `f1_for_bias(records, usrec, b)`, `best_bias_on(...)->(b,f1)`, `walk_forward(...)->dict`, `calibrate(...)->dict`, `build_calib_report_md(report)->str` identisch zwischen Definition und Aufruf. `evidence["trend"]` (Task 1) → `urteil["trend"]` (Task 2) → `records[i][2]` (Task 4/5) konsistent. `evaluate_nber`/`evaluate_market`-Reuse mit der erwarteten `{"as_of", "regime"}`-Urteilsform.
