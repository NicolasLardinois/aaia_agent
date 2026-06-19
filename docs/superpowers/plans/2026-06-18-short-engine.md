# Block 1b: Equity-Short-Thesis-Engine — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Eine reine `derive_short_assessment`-Funktion, die aus `bottom_up` + `cockpit` ein `ShortAssessment` (Aktion + Konfidenz + Archetypen + Risiko) baut, plus bidirektionale `detect_conflict`-Erkennung, verdrahtet im Judgment-Layer (ersetzt den Platzhalter).

**Architecture:** Reine Domänen-Funktionen + Flag-Registry; Konfidenz analog Long; defensiv (kein Crash bei `None`-Snapshots).

**Tech Stack:** Python, dataclasses, pytest.

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-18-short-engine-design.md`. Design: `docs/short.md` §5–9.
- Schwellen/Gewichte = **Erst-Heuristik**; Tests prüfen **Verhaltens-Bänder, keine Dezimalwerte**.
- `derive_short_assessment` **wirft nie**; Hart-Gates: kein Top-Down / keine Kern-These.
- Aktionsschwelle Konfidenz **0.50**. SHORT+ ist NICHT Teil dieses Blocks.
- Branch `feat/shorts-engine`. Runner `python -m pytest -q`. Am Ende (Task 5) Gesamtsuite grün.

---

## Task 1: `ShortAssessment`-Modell + `DeepDiveResult`-Felder

**Files:** Modify `core/domain/models.py`; Test `tests/test_short_assessment_model.py` (Create).

**Interfaces:** Produces `ShortAssessment` (dataclass); `DeepDiveResult.short_assessment/conflict/conflict_reason`.

- [ ] **Step 1: Failing test** — `tests/test_short_assessment_model.py`:
```python
from core.domain.models import ShortAssessment, ShortAction, DeepDiveResult


def test_short_assessment_defaults():
    a = ShortAssessment(asset_class="equity", short_action=ShortAction.NONE, confidence=0.1,
                        archetypes=[], thesis_flags=[], regime_effect="neutral",
                        squeeze_risk="low", hard_to_borrow=False)
    assert a.borrow_rate_manual is None
    assert a.suggested_size_pct is None
    assert a.stop_pct is None


def test_deepdive_has_conflict_fields():
    import dataclasses
    names = {f.name for f in dataclasses.fields(DeepDiveResult)}
    assert {"short_assessment", "conflict", "conflict_reason"} <= names
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_short_assessment_model.py -q`.

- [ ] **Step 3: Implement** — in `core/domain/models.py`:
```python
@dataclass
class ShortAssessment:
    asset_class: str
    short_action: ShortAction
    confidence: float
    archetypes: list[str]
    thesis_flags: list[str]
    regime_effect: str            # "headwind" | "neutral" | "tailwind"
    squeeze_risk: str             # "low" | "elevated" | "high"
    hard_to_borrow: bool
    borrow_rate_manual: Optional[float] = None
    suggested_size_pct: Optional[float] = None
    stop_pct: Optional[float] = None
```
(Platzierung nach `ShortAction`/vor `DeepDiveResult`.) In `DeepDiveResult` als **letzte** Felder ergänzen:
```python
    short_assessment: Optional["ShortAssessment"] = None
    conflict: bool = False
    conflict_reason: str = ""
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_short_assessment_model.py -q`.

- [ ] **Step 5: Commit** — `git add core/domain/models.py tests/test_short_assessment_model.py && git commit -m "feat(short): ShortAssessment-Modell + DeepDiveResult-Felder (short_assessment/conflict)"`

---

## Task 2: `ShortFlag` + Registry (`core/domain/short_flags.py`)

**Files:** Create `core/domain/short_flags.py`; Test `tests/test_short_flags.py` (Create).

**Interfaces:** Produces `ShortFlag` (dataclass), `SHORT_FLAGS: list[ShortFlag]`. Jeder `fires(bottom_up) -> bool` ist **defensiv** (False bei fehlenden Snapshots/Feldern).

- [ ] **Step 1: Failing test** — `tests/test_short_flags.py`:
```python
from types import SimpleNamespace as NS
from core.domain.short_flags import SHORT_FLAGS


def _bu(**kw):
    base = dict(asset_class="equity", quality=None, earnings_trend=None,
                fundamentals=None, valuation_range=None, moat=None,
                insider=None, short_interest=None)
    base.update(kw)
    return NS(**base)


def _flag(name):
    return next(f for f in SHORT_FLAGS if f.name == name)


def test_altman_distress_fires_and_is_defensive():
    f = _flag("altman_distress")
    assert f.fires(_bu(quality=NS(altman_z=1.4))) is True
    assert f.fires(_bu(quality=NS(altman_z=3.0))) is False
    assert f.fires(_bu(quality=None)) is False          # defensiv


def test_earnings_collapse_on_down_revision():
    f = _flag("earnings_collapse")
    assert f.fires(_bu(earnings_trend=NS(estimate_revision="down", beat_rate=0.9))) is True
    assert f.fires(_bu(earnings_trend=NS(estimate_revision="up", beat_rate=0.9))) is False
    assert f.fires(_bu(earnings_trend=None)) is False


def test_valuation_extreme_overvalued():
    f = _flag("valuation_extreme")
    assert f.fires(_bu(valuation_range=NS(position="overvalued"), fundamentals=NS(peg_ratio=1.0))) is True
    assert f.fires(_bu(valuation_range=NS(position="fair"), fundamentals=NS(peg_ratio=1.0))) is False


def test_kinds_and_archetypes():
    kern = {f.name for f in SHORT_FLAGS if f.kind == "kern"}
    assert {"altman_distress", "earnings_collapse", "growth_collapse"} <= kern
    assert _flag("valuation_extreme").kind == "verstaerker"
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_short_flags.py -q`.

- [ ] **Step 3: Implement** — `core/domain/short_flags.py`:
```python
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class ShortFlag:
    name: str
    kind: str                  # "kern" | "verstaerker"
    archetype: Optional[str]   # nur kern
    weight: float
    fires: Callable
    detail: Callable


def _q(bu):   return getattr(bu, "quality", None)
def _et(bu):  return getattr(bu, "earnings_trend", None)
def _fu(bu):  return getattr(bu, "fundamentals", None)
def _vr(bu):  return getattr(bu, "valuation_range", None)
def _mo(bu):  return getattr(bu, "moat", None)
def _in(bu):  return getattr(bu, "insider", None)


def _lt(v, t):  # v < t, defensiv
    return v is not None and v < t


SHORT_FLAGS = [
    ShortFlag("altman_distress", "kern", "distress", 0.0,
              lambda bu: _q(bu) is not None and _lt(_q(bu).altman_z, 1.8),
              lambda bu: f"Altman-Z {_q(bu).altman_z:.1f} (Konkurszone)"),
    ShortFlag("coverage_weak", "kern", "distress", 0.0,
              lambda bu: _q(bu) is not None and _lt(_q(bu).interest_coverage, 1.0),
              lambda bu: f"Zinsdeckung {_q(bu).interest_coverage:.1f} (<1)"),
    ShortFlag("cash_burn_levered", "kern", "distress", 0.0,
              lambda bu: _q(bu) is not None and _lt(_q(bu).fcf_margin, 0.0)
                         and (_q(bu).debt_to_equity is not None and _q(bu).debt_to_equity > 1.0),
              lambda bu: f"negativer FCF + hohe Verschuldung (D/E {_q(bu).debt_to_equity:.1f})"),
    ShortFlag("liquidity_strain", "kern", "distress", 0.0,
              lambda bu: _q(bu) is not None and _lt(_q(bu).current_ratio, 1.0),
              lambda bu: f"Current Ratio {_q(bu).current_ratio:.2f} (<1)"),
    ShortFlag("earnings_collapse", "kern", "broken_growth", 0.0,
              lambda bu: _et(bu) is not None and (
                  getattr(_et(bu), "estimate_revision", None) == "down"
                  or _lt(getattr(_et(bu), "beat_rate", None), 0.4)),
              lambda bu: "Earnings kippen (Revision down / Beat-Rate niedrig)"),
    ShortFlag("growth_collapse", "kern", "secular_decline", 0.0,
              lambda bu: _fu(bu) is not None and _lt(getattr(_fu(bu), "revenue_cagr_3y", None), -5.0),
              lambda bu: f"Umsatz-CAGR(3J) {_fu(bu).revenue_cagr_3y:.1f}% (schrumpft)"),
    ShortFlag("valuation_extreme", "verstaerker", None, 0.05,
              lambda bu: (_vr(bu) is not None and getattr(_vr(bu), "position", None) == "overvalued")
                         or (_fu(bu) is not None and (getattr(_fu(bu), "peg_ratio", None) or 0) > 2.5),
              lambda bu: "Bewertung extrem (overvalued / PEG>2.5)"),
    ShortFlag("weak_moat", "verstaerker", None, 0.03,
              lambda bu: _mo(bu) is not None and (getattr(_mo(bu), "total_score", None) is not None)
                         and _mo(bu).total_score <= 3,
              lambda bu: f"schwacher Burggraben (Score {_mo(bu).total_score}/10)"),
    ShortFlag("insider_selling", "verstaerker", None, 0.04,
              lambda bu: _in(bu) is not None and "sell" in (getattr(_in(bu), "net_direction", "") or "").lower(),
              lambda bu: "Insider-Verkäufe"),
]
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_short_flags.py -q`.

- [ ] **Step 5: Commit** — `git add core/domain/short_flags.py tests/test_short_flags.py && git commit -m "feat(short): ShortFlag-Registry (Equity-Kern/Verstaerker, defensiv)"`

---

## Task 3: `derive_short_assessment` (Engine)

**Files:** Create `core/domain/short_assessment.py`; Test `tests/test_short_assessment_engine.py` (Create).

**Interfaces:**
- Consumes: `SHORT_FLAGS` (Task 2), `ShortAssessment` (Task 1), `ShortAction`, `PositionState`, `MarketRegime`, `AnomalyReport`, `_position_size_pct` (aus `recommendation.py`).
- Produces: `derive_short_assessment(bottom_up, cockpit, current_position, top_down_available, bu_anomaly, td_anomaly) -> ShortAssessment`.

- [ ] **Step 1: Failing test** — `tests/test_short_assessment_engine.py`:
```python
from types import SimpleNamespace as NS
from core.domain.models import (
    ShortAction, PositionState, MarketRegime, AnomalyReport,
)
from core.domain.short_assessment import derive_short_assessment


def _bu(**kw):
    base = dict(asset_class="equity", quality=None, earnings_trend=None, fundamentals=None,
                valuation_range=None, moat=None, insider=None, short_interest=None)
    base.update(kw)
    return NS(**base)


def _cockpit(regime):
    return NS(macro=NS(regime=regime))


_NA = AnomalyReport.empty()


def _run(bu, pos=PositionState.NONE, cockpit=None, td=True, bua=_NA, tda=_NA):
    return derive_short_assessment(bu, cockpit, pos, td, bua, tda)


def test_distress_only_is_moderate_short():
    bu = _bu(quality=NS(altman_z=1.4, interest_coverage=2.0, fcf_margin=5.0,
                        debt_to_equity=0.5, current_ratio=2.0))
    a = _run(bu)
    assert a.short_action == ShortAction.SHORT
    assert 0.50 <= a.confidence <= 0.70          # kein Katalysator → gedeckelt
    assert "distress" in a.archetypes


def test_no_kern_only_verstaerker_is_none():
    bu = _bu(valuation_range=NS(position="overvalued"), fundamentals=NS(peg_ratio=3.0),
             moat=NS(total_score=2))
    a = _run(bu)
    assert a.short_action == ShortAction.NONE
    assert a.archetypes == []


def test_no_top_down_is_none():
    bu = _bu(quality=NS(altman_z=1.0, interest_coverage=0.5, fcf_margin=-5.0,
                        debt_to_equity=2.0, current_ratio=0.8))
    assert _run(bu, td=False).short_action == ShortAction.NONE


def test_catalyst_enables_high_confidence():
    bu = _bu(quality=NS(altman_z=1.4, interest_coverage=2.0, fcf_margin=5.0,
                        debt_to_equity=0.5, current_ratio=2.0),
             earnings_trend=NS(estimate_revision="down", beat_rate=0.3),
             valuation_range=NS(position="overvalued"), fundamentals=NS(peg_ratio=3.0),
             insider=NS(net_direction="selling"))
    a = _run(bu, cockpit=_cockpit(MarketRegime.RECESSION))   # tailwind
    assert a.short_action == ShortAction.SHORT
    assert a.confidence > 0.70
    assert "broken_growth" in a.archetypes


def test_risk_on_regime_dampens():
    bu = _bu(quality=NS(altman_z=1.6, interest_coverage=2.0, fcf_margin=5.0,
                        debt_to_equity=0.5, current_ratio=2.0))   # milder Distress
    on  = _run(bu, cockpit=_cockpit(MarketRegime.BOOM))
    off = _run(bu, cockpit=_cockpit(MarketRegime.RECESSION))
    assert off.confidence > on.confidence
    assert on.regime_effect == "headwind"


def test_short_held_strong_holds_weak_covers():
    strong = _bu(quality=NS(altman_z=1.0, interest_coverage=0.5, fcf_margin=-5.0,
                            debt_to_equity=2.0, current_ratio=0.8),
                 earnings_trend=NS(estimate_revision="down", beat_rate=0.3))
    weak = _bu()   # keine These
    assert _run(strong, pos=PositionState.SHORT).short_action == ShortAction.HOLD
    assert _run(weak, pos=PositionState.SHORT).short_action == ShortAction.COVER


def test_long_held_defers_but_keeps_confidence():
    bu = _bu(quality=NS(altman_z=1.0, interest_coverage=0.5, fcf_margin=-5.0,
                        debt_to_equity=2.0, current_ratio=0.8),
             earnings_trend=NS(estimate_revision="down", beat_rate=0.3))
    a = _run(bu, pos=PositionState.LONG)
    assert a.short_action == ShortAction.NONE
    assert a.confidence >= 0.50          # für Konflikt-Erkennung


def test_bearish_anomaly_boosts():
    bu = _bu(quality=NS(altman_z=1.6, interest_coverage=2.0, fcf_margin=5.0,
                        debt_to_equity=0.5, current_ratio=2.0))
    bear = AnomalyReport(has_anomalies=True, statistical=["x"], contradictions=[],
                         severity="high", summary="s", direction="bearish")
    assert _run(bu, bua=bear).confidence > _run(bu).confidence


def test_non_equity_fallback():
    bu = _bu(asset_class="commodity")
    a = _run(bu)
    assert a.short_action == ShortAction.NONE
    assert "Fallback" in a.thesis_flags[0]
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_short_assessment_engine.py -q`.

- [ ] **Step 3: Implement** — `core/domain/short_assessment.py`:
```python
from typing import Optional

from core.domain.models import (
    AnomalyReport, ShortAssessment, ShortAction, PositionState, MarketRegime,
)
from core.domain.short_flags import SHORT_FLAGS
from core.domain.recommendation import _position_size_pct

_RISK_ON  = {MarketRegime.BOOM, MarketRegime.EXPANSION, MarketRegime.RECOVERY}
_RISK_OFF = {MarketRegime.SLOWDOWN, MarketRegime.RECESSION, MarketRegime.DEPRESSION}
_BASE = {"distress": 0.60, "broken_growth": 0.62, "secular_decline": 0.58}
_THRESHOLD = 0.50


def _regime_effect(cockpit) -> str:
    reg = getattr(getattr(cockpit, "macro", None), "regime", None) if cockpit else None
    if reg in _RISK_ON:  return "headwind"
    if reg in _RISK_OFF: return "tailwind"
    return "neutral"


def _squeeze(si):
    dtc = getattr(si, "days_to_cover", None) if si else None
    flt = getattr(si, "short_float_pct", None) if si else None
    high = (dtc is not None and dtc >= 8) or (flt is not None and flt >= 20)
    elevated = dtc is not None and dtc >= 5
    risk = "high" if high else ("elevated" if elevated else "low")
    htb = (flt is not None and flt >= 20) and (dtc is not None and dtc >= 8)
    return risk, htb, dtc


def _anomaly_boost(rep) -> float:
    if rep is None or getattr(rep, "direction", "neutral") != "bearish":
        return 0.0
    return {"high": 0.10, "medium": 0.05}.get(getattr(rep, "severity", "none"), 0.0)


def _action(pos, confidence) -> ShortAction:
    if pos == PositionState.LONG:
        return ShortAction.NONE
    if pos == PositionState.SHORT:
        return ShortAction.HOLD if confidence >= _THRESHOLD else ShortAction.COVER
    return ShortAction.SHORT if confidence >= _THRESHOLD else ShortAction.NONE


def _mk(asset_class, action, conf, archetypes, flags, regime, squeeze, htb, size=None, stop=None):
    return ShortAssessment(
        asset_class=asset_class, short_action=action, confidence=round(conf, 2),
        archetypes=archetypes, thesis_flags=flags, regime_effect=regime,
        squeeze_risk=squeeze, hard_to_borrow=htb, suggested_size_pct=size, stop_pct=stop)


def derive_short_assessment(bottom_up, cockpit, current_position,
                            top_down_available, bu_anomaly, td_anomaly) -> ShortAssessment:
    asset_class = getattr(bottom_up, "asset_class", "equity")
    regime = _regime_effect(cockpit)
    squeeze, htb, dtc = _squeeze(getattr(bottom_up, "short_interest", None))

    # Nicht-Equity → Fallback (positionsbasiert wie alter Platzhalter)
    if asset_class != "equity":
        action = ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE
        return _mk(asset_class, action, 0.10, [],
                   ["Fallback: klassenspezifische Short-Logik folgt"], regime, squeeze, htb)

    # Kein Top-Down → hartes Veto (nicht bewertbar): short→HOLD, sonst NONE
    if not top_down_available:
        action = ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE
        return _mk(asset_class, action, 0.10, [],
                   ["Kein Top-Down — Short nicht bewertbar"], regime, squeeze, htb)

    # Flags
    kern, verst, details, archetypes = [], [], [], []
    for f in SHORT_FLAGS:
        try:
            if f.fires(bottom_up):
                details.append(f.detail(bottom_up))
                if f.kind == "kern":
                    kern.append(f)
                    if f.archetype and f.archetype not in archetypes:
                        archetypes.append(f.archetype)
                else:
                    verst.append(f)
        except Exception:
            continue

    # Keine Kern-These → confidence-Floor (generische Aktion: short→COVER, sonst NONE)
    if not kern:
        conf = 0.10
        action = _action(current_position, conf)
        return _mk(asset_class, action, conf, [], details or ["Keine Kern-These"],
                   regime, squeeze, htb)

    # Konfidenz-Zusammenbau
    bases = [_BASE[f.archetype] for f in kern]
    q = getattr(bottom_up, "quality", None)
    if "distress" in archetypes and q is not None and getattr(q, "altman_z", None) is not None and q.altman_z < 1.0:
        bases.append(0.68)
    conf = max(bases)
    conf += 0.04 * (len(archetypes) - 1)
    conf += sum(f.weight for f in verst)
    has_catalyst = any(f.name == "earnings_collapse" for f in kern)
    if not has_catalyst:
        conf = min(conf, 0.70)
    if regime == "headwind":  conf -= 0.12
    elif regime == "tailwind": conf += 0.05
    if dtc is not None and dtc >= 8 and htb:
        conf -= 0.10
    conf += _anomaly_boost(bu_anomaly) + _anomaly_boost(td_anomaly)
    conf = max(0.10, min(1.0, conf))

    action = _action(current_position, conf)
    size = stop = None
    if action == ShortAction.SHORT:
        size = round(_position_size_pct(conf) * 0.5, 1)
        if squeeze == "high":
            size = round(size * 0.5, 1)
    stop = 10.0 if squeeze == "high" else 15.0
    return _mk(asset_class, action, conf, archetypes, details, regime, squeeze, htb, size, stop)
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_short_assessment_engine.py -q`.

- [ ] **Step 5: Commit** — `git add core/domain/short_assessment.py tests/test_short_assessment_engine.py && git commit -m "feat(short): derive_short_assessment-Engine (Konfidenz/Aktion/Archetypen/Fallback)"`

---

## Task 4: `detect_conflict`

**Files:** Modify `core/domain/recommendation.py`; Test `tests/test_detect_conflict.py` (Create).

**Interfaces:** Produces `detect_conflict(current_position, alignment, dominant_signal, short_assessment, long_confidence) -> tuple[bool, str]`.

- [ ] **Step 1: Failing test** — `tests/test_detect_conflict.py`:
```python
from core.domain.models import (
    ShortAssessment, ShortAction, PositionState, Signal,
)
from core.domain.recommendation import detect_conflict


def _sa(conf, archetypes):
    return ShortAssessment(asset_class="equity", short_action=ShortAction.NONE, confidence=conf,
                           archetypes=archetypes, thesis_flags=[], regime_effect="neutral",
                           squeeze_risk="low", hard_to_borrow=False)


def test_long_held_strong_short_is_conflict():
    c, msg = detect_conflict(PositionState.LONG, "mixed", Signal.NEUTRAL, _sa(0.7, ["distress"]), 0.6)
    assert c is True and msg


def test_long_held_weak_short_no_conflict():
    c, _ = detect_conflict(PositionState.LONG, "mixed", Signal.NEUTRAL, _sa(0.3, []), 0.6)
    assert c is False


def test_short_held_bullish_long_is_conflict():
    c, msg = detect_conflict(PositionState.SHORT, "aligned_bullish", Signal.BULLISH, _sa(0.2, []), 0.7)
    assert c is True and msg


def test_flat_no_conflict():
    c, _ = detect_conflict(PositionState.NONE, "aligned_bullish", Signal.BULLISH, _sa(0.8, ["distress"]), 0.8)
    assert c is False
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_detect_conflict.py -q`.

- [ ] **Step 3: Implement** — in `core/domain/recommendation.py` (Signal/PositionState/ShortAssessment sind im Modul-Import vorhanden bzw. ergänzen):
```python
def detect_conflict(current_position, alignment, dominant_signal, short_assessment, long_confidence):
    """Bidirektional: gehaltene Position vs. gegenläufiges Linsen-Signal."""
    if current_position == PositionState.LONG:
        if short_assessment.confidence >= 0.50 and short_assessment.archetypes:
            return True, (f"Long gehalten, screent aber als Short "
                          f"(Konfidenz {short_assessment.confidence:.0%}; "
                          f"{', '.join(short_assessment.archetypes)}) — Long-These prüfen (evtl. SELL).")
    if current_position == PositionState.SHORT:
        bullish = alignment == "aligned_bullish" or dominant_signal == Signal.BULLISH
        if bullish and long_confidence >= 0.50:
            return True, (f"Short gehalten, screent aber bullish "
                          f"(Long-Konfidenz {long_confidence:.0%}) — Short-These prüfen (evtl. COVER).")
    return False, ""
```
(Falls `ShortAssessment` im Modul noch nicht importiert ist, zum bestehenden `from core.domain.models import ...` hinzufügen.)

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_detect_conflict.py -q`.

- [ ] **Step 5: Commit** — `git add core/domain/recommendation.py tests/test_detect_conflict.py && git commit -m "feat(short): detect_conflict (bidirektional Long/Short)"`

---

## Task 5: Verdrahtung (`judgment_agent` + `app/main.py`) + Gesamt-Regression

**Files:** Modify `agents/judgment/judgment_agent.py`, `app/main.py`; ggf. bestehende judgment-Tests.

- [ ] **Step 1: Implement Verdrahtung** — in `agents/judgment/judgment_agent.py`:
  - Importe ergänzen: `from core.domain.short_assessment import derive_short_assessment`; `from core.domain.recommendation import compute_confidence, derive_recommendation, detect_conflict` (detect_conflict ergänzen).
  - Den Platzhalter-Aufruf `short_action = derive_short_action_placeholder(current_position)` **ersetzen** durch:
    ```python
    short_assessment = derive_short_assessment(
        bottom_up, cockpit, current_position, top_down_available,
        bottom_up_anomaly, top_down_anomaly)
    conflict, conflict_reason = detect_conflict(
        current_position, alignment, dominant_sig, short_assessment, confidence)
    ```
    (`alignment`, `dominant_sig`, `confidence`, `current_position`, `bottom_up_anomaly`, `top_down_anomaly`, `cockpit`, `top_down_available` sind in `run()` vorhanden.)
  - Im `DeepDiveResult(...)`: `short_action=short_assessment.short_action`, plus `short_assessment=short_assessment`, `conflict=conflict`, `conflict_reason=conflict_reason`.
  - `derive_short_action_placeholder`-Import entfernen, falls dadurch ungenutzt.

- [ ] **Step 2: Anzeige** — in `app/main.py` nach der SHORT-AKTION-Zeile ergänzen:
```python
    if result.short_assessment:
        sa = result.short_assessment
        print(f"  Short-Konfidenz: {sa.confidence:.0%}"
              + (f" | Typ: {', '.join(sa.archetypes)}" if sa.archetypes else ""))
    if result.conflict:
        print(f"⚠️  KONFLIKT: {result.conflict_reason}")
```

- [ ] **Step 3: judgment-Tests anpassen** — `grep -rn "derive_short_action_placeholder\|short_action" tests/`; betroffene Tests, die den Platzhalter erwarten, auf das Assessment umstellen (z. B. `result.short_assessment.short_action` bzw. `result.short_action`). Einen Test ergänzen: `current_position=PositionState.SHORT` + starke Distress-`bottom_up` → `result.short_action == ShortAction.HOLD`; LONG + starke These → `result.conflict is True`.

- [ ] **Step 4: Gesamt-Regression** — `python -m pytest -q` → **0 failed** (~3 Min). Bei Fehlern: superpowers:systematic-debugging.

- [ ] **Step 5: Commit** — `git add agents/ app/ tests/ && git commit -m "feat(short): Engine im judgment_agent verdrahtet + Konflikt/Anzeige + Regression gruen (Block 1b)"`

---

## Abdeckung (Spec → Task)
| Spec-Element | Task |
|---|---|
| `ShortAssessment` + `DeepDiveResult`-Felder | 1 |
| `ShortFlag`-Registry (Equity-Flags, defensiv) | 2 |
| `derive_short_assessment` (Gates/Konfidenz/Aktion/Archetypen/Fallback) | 3 |
| `detect_conflict` bidirektional | 4 |
| Verdrahtung judgment_agent + Anzeige + Regression | 5 |

## Self-Review (durchgeführt)
- **Spec-Abdeckung:** alle Komponenten je Task. ✅
- **Platzhalter:** vollständiger Code je Task; Test-Mocks via `SimpleNamespace` (robust gegen reale Konstruktor-Pflichtfelder). ✅
- **Typ-Konsistenz:** `derive_short_assessment`-Signatur identisch in Task 3 (Def) und Task 5 (Aufruf); `detect_conflict`-Signatur identisch Task 4/5; `ShortAssessment`-Felder identisch Task 1/3/4. ✅
