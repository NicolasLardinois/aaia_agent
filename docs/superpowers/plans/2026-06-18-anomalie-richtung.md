# Block 1a: Anomalie-Richtung — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `AnomalyReport` um eine strukturierte `direction` (bearish/bullish/neutral) erweitern, beide Anomalie-Agenten füllen sie, und `compute_confidence` nutzt sie richtungs-bewusst (bestätigende Anomalie → kein Abzug).

**Architecture:** Reine Domänen-/Agenten-Änderungen über vorhandene Strukturen. Default `direction="neutral"` hält die Long-Regression eng begrenzt (nur bestätigende Fälle ändern sich).

**Tech Stack:** Python, dataclasses, pytest.

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-18-anomalie-richtung-design.md`.
- `direction` ∈ {`"bearish"`, `"bullish"`, `"neutral"`}, Default `"neutral"`.
- **Verhaltenswechsel nur bei bestätigenden Anomalien** (Richtung passt zum `alignment`) → kein Abzug. Alles andere (widersprechend / neutral / nicht-aligned) → Abzug wie bisher.
- Branch `feat/shorts-anomaly-direction`. Runner: `python -m pytest -q`. Am Ende (Task 4) gesamte Suite grün.

---

## Task 1: `AnomalyReport.direction`

**Files:**
- Modify: `core/domain/models.py` (`AnomalyReport` ~Zeile 727–740)
- Test: `tests/test_anomaly_direction_model.py` (Create)

**Interfaces:**
- Produces: `AnomalyReport.direction: str = "neutral"`; `AnomalyReport.empty().direction == "neutral"`.

- [ ] **Step 1: Failing test** — `tests/test_anomaly_direction_model.py`:
```python
from core.domain.models import AnomalyReport


def test_direction_defaults_neutral():
    r = AnomalyReport(has_anomalies=False, statistical=[], contradictions=[],
                      severity="none", summary="")
    assert r.direction == "neutral"


def test_empty_is_neutral():
    assert AnomalyReport.empty().direction == "neutral"


def test_direction_can_be_set():
    r = AnomalyReport(has_anomalies=True, statistical=["x"], contradictions=[],
                      severity="high", summary="s", direction="bearish")
    assert r.direction == "bearish"
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_anomaly_direction_model.py -q`.

- [ ] **Step 3: Implement** — in `core/domain/models.py`, `AnomalyReport` als **letztes** Feld ergänzen:
```python
    direction: str = "neutral"   # "bearish" | "bullish" | "neutral"
```
und in `AnomalyReport.empty()` `direction="neutral"` explizit setzen (sofern die anderen Felder dort gesetzt werden).

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_anomaly_direction_model.py -q`.

- [ ] **Step 5: Commit** — `git add core/domain/models.py tests/test_anomaly_direction_model.py && git commit -m "feat(anomaly): AnomalyReport.direction (Default neutral)"`

---

## Task 2: `compute_confidence` richtungs-bewusst

**Files:**
- Modify: `core/domain/recommendation.py` (`compute_confidence` ~Zeile 60–96, neuer Helfer)
- Test: `tests/test_confidence_direction.py` (Create)

**Interfaces:**
- Consumes: `AnomalyReport.direction` (Task 1).
- Produces: `_anomaly_deduction(alignment: str, report: AnomalyReport) -> float`; geändertes `compute_confidence`.

- [ ] **Step 1: Failing test** — `tests/test_confidence_direction.py`:
```python
from core.domain.models import AnomalyReport
from core.domain.recommendation import compute_confidence


def _rep(direction, severity="high"):
    return AnomalyReport(has_anomalies=True, statistical=["x"], contradictions=[],
                         severity=severity, summary="s", direction=direction)


def _neutral_none():
    return AnomalyReport.empty()


def test_confirming_anomaly_no_penalty():
    # aligned_bearish + bearishe Anomalie = bestätigend → KEIN Abzug
    conf_confirm = compute_confidence("aligned_bearish", 0.6, _neutral_none(), _rep("bearish"))
    conf_neutral = compute_confidence("aligned_bearish", 0.6, _neutral_none(), _rep("neutral"))
    assert conf_confirm > conf_neutral


def test_contradicting_anomaly_keeps_penalty():
    # aligned_bullish + bearishe Anomalie = widersprechend → Abzug wie neutral
    conf_contra  = compute_confidence("aligned_bullish", 0.6, _neutral_none(), _rep("bearish"))
    conf_neutral = compute_confidence("aligned_bullish", 0.6, _neutral_none(), _rep("neutral"))
    assert conf_contra == conf_neutral


def test_neutral_direction_keeps_penalty():
    conf_with = compute_confidence("aligned_bearish", 0.6, _neutral_none(), _rep("neutral"))
    conf_none = compute_confidence("aligned_bearish", 0.6, _neutral_none(), _neutral_none())
    assert conf_with < conf_none   # echte neutrale Anomalie zieht ab
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_confidence_direction.py -q`.

- [ ] **Step 3: Implement** — in `core/domain/recommendation.py` Helfer ergänzen (vor `compute_confidence`):
```python
def _anomaly_deduction(alignment: str, report: AnomalyReport) -> float:
    """Bestätigt die Anomalie-Richtung die These (bearish↔aligned_bearish, bullish↔aligned_bullish)?
    Dann kein Abzug. Sonst (widersprechend/neutral/nicht-aligned) Severity-Abzug wie bisher."""
    confirms = (
        (alignment == "aligned_bearish" and report.direction == "bearish") or
        (alignment == "aligned_bullish" and report.direction == "bullish")
    )
    if confirms:
        return 0.0
    return _SEVERITY_DEDUCTION.get(report.severity, 0.0)
```
und in `compute_confidence` die zwei Zeilen
```python
        score += _SEVERITY_DEDUCTION.get(td_anomaly.severity, 0.0)
        score += _SEVERITY_DEDUCTION.get(bu_anomaly.severity, 0.0)
```
ersetzen durch
```python
        score += _anomaly_deduction(alignment, td_anomaly)
        score += _anomaly_deduction(alignment, bu_anomaly)
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_confidence_direction.py -q`.

- [ ] **Step 5: Regression** — `python -m pytest tests/test_confidence.py -q` → grün (bestehende Tests nutzen `AnomalyReport` mit Default-`direction="neutral"` → Abzug unverändert).

- [ ] **Step 6: Commit** — `git add core/domain/recommendation.py tests/test_confidence_direction.py && git commit -m "feat(confidence): gerichtete Anomalie-Wertung (bestaetigend → kein Abzug)"`

---

## Task 3: `BottomUpAnomalyAgent` setzt `direction`

**Files:**
- Modify: `agents/anomaly/bottom_up_anomaly_agent.py`
- Test: `tests/test_bottom_up_anomaly_direction.py` (Create)

**Interfaces:**
- Produces: `BottomUpAnomalyAgent.run(...).direction` aus der Tendenz der erkannten Anomalien.

- [ ] **Step 1: Failing test** — `tests/test_bottom_up_anomaly_direction.py`. Nutzt das bestehende Test-Muster für Bottom-Up-Anomalien (≥20 History-Snapshots, damit Z-Checks greifen):
```python
from agents.anomaly.bottom_up_anomaly_agent import BottomUpAnomalyAgent
from core.domain.models import (
    BottomUpResult, ShortInterestSnapshot, InsiderSnapshot, Signal,
)


def _hist(short_floats=None, insider_tx=None):
    snaps = []
    for i in range(25):
        snap = {}
        if short_floats is not None:
            snap["short_float_pct"] = 5.0   # ruhige Historie
        if insider_tx is not None:
            snap["insider_transactions"] = 1.0
        snaps.append({"indicators_snapshot": snap})
    return snaps


def _bottom_up(short_float=None, insider=None):
    return BottomUpResult(
        ticker="X", asset_class="equity",
        fundamentals=None, quality=None, short_interest=short_float,
        insider=insider, earnings_trend=None, moat=None, valuation_range=None,
    )


def test_short_float_spike_is_bearish():
    bu = _bottom_up(short_float=ShortInterestSnapshot(short_float_pct=80.0, days_to_cover=10.0, signal=Signal.BEARISH))
    rep = BottomUpAnomalyAgent().run(bu, _hist(short_floats=True))
    assert rep.direction == "bearish"


def test_insider_buy_cluster_is_bullish():
    ins = InsiderSnapshot(net_direction="buying", recent_transactions=40, signal=Signal.BULLISH)
    bu = _bottom_up(insider=ins)
    rep = BottomUpAnomalyAgent().run(bu, _hist(insider_tx=True))
    assert rep.direction == "bullish"


def test_no_anomaly_is_neutral():
    rep = BottomUpAnomalyAgent().run(_bottom_up(), [])
    assert rep.direction == "neutral"
```
> Falls die echten Modell-Konstruktoren (`BottomUpResult`, `InsiderSnapshot`) andere Pflichtfelder haben, an die realen Signaturen anpassen (Konstruktor aus `core/domain/models.py` prüfen) — das Verhalten (bearish/bullish/neutral) bleibt das Testziel.

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_bottom_up_anomaly_direction.py -q`.

- [ ] **Step 3: Implement** — in `agents/anomaly/bottom_up_anomaly_agent.py` eine Tendenz-Zählung führen und am Ende `direction` setzen:
  - Vor den Checks: `lean = {"bearish": 0, "bullish": 0}`.
  - `_check` um Richtungs-Argumente erweitern und bei Treffer zählen:
    ```python
    def _check(label, current, key, high_dir, low_dir):
        ...
        if abs(z) > threshold:
            dir_ = "hoch" if z > 0 else "niedrig"
            d = high_dir if z > 0 else low_dir
            if d in lean: lean[d] += 1
            statistical.append(f"{label}={current:.1f} ist ungewöhnlich {dir_} (robust-Z={z:.1f})")
    ```
    Aufrufe: KGV → `_check("KGV", fu.pe_ratio, "pe_ratio", "bearish", "bullish")`; Short-Float → `_check("Short-Float", si.short_float_pct, "short_float_pct", "bearish", "neutral")`.
  - Im Insider-Block bei Treffer: `lean["bullish"] += 1` wenn `"buy" in direction.lower()`, `lean["bearish"] += 1` wenn `"sell" in direction.lower()`.
  - Im Widerspruchs-Block: bei „Mehrheit der Bottom-Up-Signale bearish" `lean["bearish"] += 1`.
  - Am Ende: `direction = "bearish" if lean["bearish"] > lean["bullish"] else "bullish" if lean["bullish"] > lean["bearish"] else "neutral"` und `direction=direction` im zurückgegebenen `AnomalyReport` setzen.

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_bottom_up_anomaly_direction.py -q`.

- [ ] **Step 5: Commit** — `git add agents/anomaly/bottom_up_anomaly_agent.py tests/test_bottom_up_anomaly_direction.py && git commit -m "feat(anomaly): BottomUp-direction aus Anomalie-Tendenz"`

---

## Task 4: `TopDownAnomalyAgent` setzt `direction` + Gesamt-Regression

**Files:**
- Modify: `agents/anomaly/top_down_anomaly_agent.py`
- Test: `tests/test_top_down_anomaly_direction.py` (Create)

**Interfaces:**
- Produces: `TopDownAnomalyAgent.run(...).direction` = Mehrheit der vier Bereichs-Signale (`macro_sig`, `sentiment_sig`, `yield_sig`, `commodity_sig`).

- [ ] **Step 1: Failing test** — `tests/test_top_down_anomaly_direction.py`. Nutzt das bestehende TopDown-Anomalie-Test-Muster (gemockter `cockpit`); falls eines existiert, dessen Fixtures wiederverwenden. Ziel-Asserts:
```python
# Cockpit so mocken, dass macro_sig + sentiment_sig + yield_sig bearish sind
# (commodity neutral) → Mehrheit bearish → direction == "bearish".
# Und ein bullisches Pendant → "bullish".
```
> Den genauen Cockpit-Mock aus einem vorhandenen `top_down`-Test übernehmen (Signale auf `Signal.BEARISH` bzw. `Signal.BULLISH` setzen für vix/fear_greed/put_call, inflation/gdp, yield, energy/industrial_metals). Assert: `rep.direction == "bearish"` / `"bullish"` / `"neutral"`.

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_top_down_anomaly_direction.py -q`.

- [ ] **Step 3: Implement** — in `agents/anomaly/top_down_anomaly_agent.py`, NACH der Berechnung von `macro_sig`, `sentiment_sig`, `yield_sig`, `commodity_sig` (die vor den Widerspruchs-Pairs bereits existieren), vor dem `return`:
```python
        _areas = [macro_sig, sentiment_sig, yield_sig, commodity_sig]
        _b = _areas.count(Signal.BEARISH)
        _u = _areas.count(Signal.BULLISH)
        direction = "bearish" if _b > _u else "bullish" if _u > _b else "neutral"
```
und `direction=direction` im zurückgegebenen `AnomalyReport` setzen.

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_top_down_anomaly_direction.py -q`.

- [ ] **Step 5: Gesamt-Regression** — `python -m pytest -q` → **0 failed** (Lauf ~3 Min). Bei Fehlern: superpowers:systematic-debugging.

- [ ] **Step 6: Commit** — `git add agents/anomaly/top_down_anomaly_agent.py tests/test_top_down_anomaly_direction.py && git commit -m "feat(anomaly): TopDown-direction aus Bereichs-Signalen + Regression gruen (Block 1a)"`

---

## Abdeckung (Spec → Task)
| Spec-Element | Task |
|---|---|
| `AnomalyReport.direction` (Default neutral) | 1 |
| `compute_confidence` gerichtet (bestätigend → kein Abzug) | 2 |
| BottomUp-`direction` aus Anomalie-Tendenz | 3 |
| TopDown-`direction` aus Bereichs-Signalen | 4 |
| Regression Long-Konfidenz (neutral unverändert) | 2 (Step 5), 4 (Step 5) |

## Self-Review (durchgeführt)
- **Spec-Abdeckung:** alle vier Komponenten je ein Task. ✅
- **Platzhalter:** Task 3/4-Tests verweisen auf reale Konstruktoren/Fixtures (Hinweis zum Anpassen an echte Signaturen) — Verhalten ist das Testziel, kein erfundener Wert. ✅
- **Typ-Konsistenz:** `direction`-Strings einheitlich; `_anomaly_deduction`-Name in Task 2 definiert+genutzt; Reihenfolge (Modell → Konsumenten) korrekt. ✅
