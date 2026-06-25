# Phase 3 — Futures-Short (Rohstoff + Edelmetall) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Einen kurven- und kostengetriebenen Short-Zweig für `wrapper=future` (Rohstoff + Edelmetall) bauen, der über die bestehende Short-Engine eine `ShortAction` erzeugt.

**Architecture:** Reine Termin-Mathematik (`futures_short.py`) + Domänen-Modell `FuturesShortAssessment` (Overlay an `BottomUpResult`) + Port/Stub für den Kostenboden + Single-Fetch-Overlay im `BottomUpOrchestrator` + Andocken an den Nicht-Equity-Zweig von `derive_short_assessment`. Spiegelt das `futures_curve`-Muster (Phase 2a).

**Tech Stack:** Python 3.11+ (moderne Type-Hints `float | None`), `@dataclass(frozen=True)`, `abc.ABC` für Ports, pytest (kein `pytest-asyncio` — Tests nutzen `asyncio.run`).

## Global Constraints

- Code-Kommentare und Commit-Messages auf **Deutsch** (bestehender Stil: `feat(short): …`).
- **Ports sind async** (`async def`); blockierendes I/O nur im Adapter. Stub gibt `None` zurück.
- **Defensive Defaults:** fehlende Quelle/Exception → `unavailable()`/`None`, **nie** Crash.
- **Einheiten:** slope/Roll-Yield als Dezimal p. a. (0.05 = 5 %); `floor_distance_pct` als Dezimal (0.50 = 50 %).
- **±5 %-Carry-Bänder** identisch zu `curve_signal` (Konsistenz Long/Short).
- **Schwelle** Short-Aktion = `0.50` (= `_THRESHOLD` in `short_assessment.py`).
- **TDD:** je Schritt erst der fehlschlagende Test, dann Minimal-Implementierung, dann Commit.
- Spec: `docs/superpowers/specs/2026-06-24-phase3-futures-short-design.md`.

---

### Task 1: Domänen-Modell `FuturesShortAssessment` + `BottomUpResult.futures_short`

**Files:**
- Modify: `core/domain/models.py` (nach `FuturesAssessment`, ~Zeile 113; und `BottomUpResult` nach `fund_info`, ~Zeile 826)
- Test: `tests/test_futures_short_model.py`

**Interfaces:**
- Produces: `FuturesShortAssessment(roll_yield_short_ann: float|None, carry_state: str, cost_floor: float|None, floor_distance_pct: float|None, floor_binds: bool, floor_applied: bool, short_confidence: float, engine_action: ShortAction, available: bool)` mit `@classmethod unavailable() -> FuturesShortAssessment`; `BottomUpResult.futures_short: Optional[FuturesShortAssessment] = None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_futures_short_model.py
"""Phase 3: FuturesShortAssessment-Modell + BottomUpResult-Feld."""
from core.domain.models import FuturesShortAssessment, ShortAction


def test_unavailable_is_neutral_and_not_available():
    a = FuturesShortAssessment.unavailable()
    assert a.available is False
    assert a.engine_action == ShortAction.NONE
    assert a.floor_binds is False
    assert a.floor_applied is False
    assert a.short_confidence == 0.10
    assert a.roll_yield_short_ann is None


def test_can_construct_available():
    a = FuturesShortAssessment(
        roll_yield_short_ann=0.06, carry_state="contango_tailwind",
        cost_floor=60.0, floor_distance_pct=0.40, floor_binds=False,
        floor_applied=True, short_confidence=0.55, engine_action=ShortAction.SHORT,
        available=True)
    assert a.available is True
    assert a.carry_state == "contango_tailwind"


def test_bottom_up_result_defaults_futures_short_none():
    from core.domain.models import BottomUpResult
    import dataclasses
    f = {fld.name for fld in dataclasses.fields(BottomUpResult)}
    assert "futures_short" in f
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_futures_short_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'FuturesShortAssessment'`

- [ ] **Step 3: Write minimal implementation**

In `core/domain/models.py` direkt nach der `FuturesAssessment`-Klasse (nach deren `unavailable()`-Methode) einfügen:

```python
@dataclass(frozen=True)
class FuturesShortAssessment:
    """Kurven-/kostengetriebener Futures-Short-Block (Phase 3). available=False ⇒ keine Kurvendaten.

    engine_action ist die positions-AGNOSTISCHE Engine-Sicht (SHORT/COVER/NONE); die
    positions-bewusste ShortAction entsteht später in derive_short_assessment via _action()."""
    roll_yield_short_ann: float | None    # +slope: der Short profitiert von Contango
    carry_state: str                      # "contango_tailwind" | "neutral" | "backwardation_headwind"
    cost_floor: float | None              # Produktionskosten-/AISC-Boden als Preis
    floor_distance_pct: float | None      # (spot − floor)/floor = Fallhöhe nach unten
    floor_binds: bool                     # Preis nahe/unter Boden → Deckel aktiv
    floor_applied: bool                   # Floor-Daten vorhanden und im Deckel berücksichtigt
    short_confidence: float               # 0.10–1.0 (Schwelle 0.50)
    engine_action: ShortAction            # positions-agnostische Engine-Sicht
    available: bool

    @classmethod
    def unavailable(cls) -> "FuturesShortAssessment":
        return cls(None, "neutral", None, None, False, False, 0.10, ShortAction.NONE, False)
```

`ShortAction` ist in `models.py` bereits definiert (Zeile 49) — kein neuer Import nötig.

In `BottomUpResult` direkt nach der `fund_info`-Zeile einfügen:

```python
    # Phase 3: Futures-Short-Schicht — nur bei wrapper=FUTURE & Rohstoff/Edelmetall befüllt, sonst None.
    futures_short: Optional["FuturesShortAssessment"] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_futures_short_model.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/domain/models.py tests/test_futures_short_model.py
git commit -m "feat(short): FuturesShortAssessment-Modell + BottomUpResult.futures_short"
```

---

### Task 2: Reine Mathematik — Roll-Yield-Short, Floor-Distanz, Carry-State

**Files:**
- Create: `core/utils/futures_short.py`
- Test: `tests/core/utils/test_futures_short_math.py`

**Interfaces:**
- Consumes: nichts (reine Float-Funktionen).
- Produces: `roll_yield_short_ann(slope: float) -> float`; `floor_distance_pct(spot: float, floor: float | None) -> float | None`; `carry_state(slope: float | None) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/utils/test_futures_short_math.py
"""Phase 3: reine Futures-Short-Mathematik (Roll-Yield-Short, Floor-Distanz, Carry-State)."""
from core.utils.futures_short import roll_yield_short_ann, floor_distance_pct, carry_state


def test_roll_yield_short_is_plus_slope():
    # Contango (slope>0) ⇒ Short profitiert ⇒ positiver Roll-Yield
    assert roll_yield_short_ann(0.06) == 0.06
    assert roll_yield_short_ann(-0.04) == -0.04
    assert roll_yield_short_ann(0.0) == 0.0


def test_floor_distance_basic():
    assert floor_distance_pct(140.0, 100.0) == 0.40      # 40 % über Kosten
    assert floor_distance_pct(100.0, 100.0) == 0.0       # genau am Boden
    assert floor_distance_pct(90.0, 100.0) == -0.10      # unter den Kosten


def test_floor_distance_no_floor():
    assert floor_distance_pct(100.0, None) is None
    assert floor_distance_pct(100.0, 0.0) is None        # 0/negativ = kein gültiger Boden


def test_carry_state_bands():
    assert carry_state(0.05) == "contango_tailwind"      # genau auf der Bandgrenze
    assert carry_state(0.051) == "contango_tailwind"
    assert carry_state(-0.05) == "backwardation_headwind"
    assert carry_state(0.04) == "neutral"
    assert carry_state(0.0) == "neutral"
    assert carry_state(None) == "neutral"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/utils/test_futures_short_math.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.utils.futures_short'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/utils/futures_short.py
"""Reine Futures-Short-Mathematik (Phase 3).

Keine I/O, keine Provider — nur Float/Modell-in/-out. Begründungen siehe
docs/superpowers/specs/2026-06-24-phase3-futures-short-design.md §3/§6.
Einheiten: slope/Roll-Yield als Dezimal p. a. (0.05 = 5 %); floor_distance als Dezimal."""
from core.domain.models import FuturesShortAssessment, ShortAction
from core.domain.models import FuturesCurveSnapshot
from core.utils.futures_curve import slope_ann


def roll_yield_short_ann(slope: float) -> float:
    """Roll-Yield für den Short = +slope (Contango = positiver Roll = Rückenwind).

    Spiegelbild zu roll_yield_long_ann = −slope: der Short rollt die Kurve runter und
    profitiert, wenn der Folgekontrakt teurer ist (Contango)."""
    return slope


def floor_distance_pct(spot: float, floor: float | None) -> float | None:
    """Fallhöhe nach unten = (spot − floor)/floor. None, wenn kein gültiger Boden (≤0/None)."""
    if not floor or floor <= 0:
        return None
    return (spot - floor) / floor


def carry_state(slope: float | None) -> str:
    """±5 %-Bänder (identisch zu curve_signal). Contango ⇒ Rückenwind Short, Backwardation ⇒ Gegenwind."""
    if slope is None:
        return "neutral"
    if slope >= 0.05:
        return "contango_tailwind"
    if slope <= -0.05:
        return "backwardation_headwind"
    return "neutral"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/utils/test_futures_short_math.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add core/utils/futures_short.py tests/core/utils/test_futures_short_math.py
git commit -m "feat(short): reine Futures-Short-Mathematik (Roll-Yield-Short, Floor-Distanz, Carry-State)"
```

---

### Task 3: Aggregation — `assess_futures_short` (Konfidenz + Deckel)

**Files:**
- Modify: `core/utils/futures_short.py`
- Test: `tests/core/utils/test_futures_short_assess.py`

**Interfaces:**
- Consumes: `roll_yield_short_ann`, `floor_distance_pct`, `carry_state` (Task 2); `slope_ann` (aus `futures_curve`); `FuturesShortAssessment` (Task 1); `FuturesCurveSnapshot`.
- Produces: `assess_futures_short(snap: FuturesCurveSnapshot | None, cost_floor: float | None) -> FuturesShortAssessment`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/utils/test_futures_short_assess.py
"""Phase 3: assess_futures_short — Konfidenz aus Carry × Floor + Cost-Curve-Deckel."""
from core.domain.models import FuturesCurveSnapshot, ShortAction
from core.utils.futures_short import assess_futures_short


def _snap(spot, front, next_):
    # days_between 182 ⇒ slope ≈ (next_/front − 1)·2 ; days_to_front 30 für T_years
    return FuturesCurveSnapshot(spot=spot, front=front, next_=next_,
                                days_to_front_expiry=30, days_between_expiries=182,
                                risk_free_rate=0.05, storage_cost=0.0, margin_quote=0.10)


def test_none_snap_is_unavailable():
    a = assess_futures_short(None, 100.0)
    assert a.available is False
    assert a.engine_action == ShortAction.NONE


def test_far_above_floor_plus_contango_is_short():
    # spot 140 vs floor 100 ⇒ dist 0.40 ⇒ Basis 0.45 ; starkes Contango ⇒ +0.10 ⇒ 0.55
    a = assess_futures_short(_snap(140.0, 100.0, 106.0), 100.0)
    assert a.carry_state == "contango_tailwind"
    assert a.floor_applied is True
    assert a.floor_binds is False
    assert a.short_confidence == 0.55
    assert a.engine_action == ShortAction.SHORT
    assert a.roll_yield_short_ann is not None and a.roll_yield_short_ann > 0


def test_near_floor_binds_and_caps_below_threshold():
    # spot 105 vs floor 100 ⇒ dist 0.05 (<0.10) ⇒ floor_binds ⇒ conf ≤ 0.49 ⇒ COVER
    a = assess_futures_short(_snap(105.0, 100.0, 106.0), 100.0)
    assert a.floor_binds is True
    assert a.short_confidence <= 0.49
    assert a.engine_action == ShortAction.COVER


def test_missing_floor_caps_below_threshold():
    # Kein Boden bekannt ⇒ floor_applied False ⇒ conf ≤ 0.49 ⇒ kein frischer Short
    a = assess_futures_short(_snap(140.0, 100.0, 106.0), None)
    assert a.floor_applied is False
    assert a.floor_binds is False
    assert a.short_confidence <= 0.49
    assert a.engine_action == ShortAction.NONE


def test_backwardation_headwind_reduces_confidence():
    # spot 140 vs floor 100 ⇒ Basis 0.45 ; Backwardation (next_<front) ⇒ −0.12 ⇒ 0.33
    a = assess_futures_short(_snap(140.0, 100.0, 94.0), 100.0)
    assert a.carry_state == "backwardation_headwind"
    assert a.short_confidence == 0.33
    assert a.engine_action == ShortAction.NONE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/utils/test_futures_short_assess.py -v`
Expected: FAIL with `ImportError: cannot import name 'assess_futures_short'`

- [ ] **Step 3: Write minimal implementation**

In `core/utils/futures_short.py` anhängen:

```python
def assess_futures_short(snap: FuturesCurveSnapshot | None,
                         cost_floor: float | None) -> FuturesShortAssessment:
    """Kombiniert Carry (Roll-Yield-Short) + Bewertung (Fallhöhe zum Kostenboden) zur
    Short-Konfidenz. Cost-Curve-Boden als Deckel: nahe/unter Boden ODER ohne Boden-Daten
    wird die Konfidenz unter die 0.50-Schwelle gedrückt (Spec §6). Defensiv: snap None → unavailable."""
    if snap is None:
        return FuturesShortAssessment.unavailable()
    slope = slope_ann(snap.front, snap.next_, snap.days_between_expiries)
    ry_short = roll_yield_short_ann(slope) if slope is not None else None
    cstate = carry_state(slope)
    dist = floor_distance_pct(snap.spot, cost_floor)
    floor_applied = dist is not None

    # Bewertungs-Basis: viel Fallhöhe über den Kosten ⇒ mehr Short-Potenzial.
    if dist is None:
        base, floor_binds = 0.10, False
    elif dist >= 0.50:
        base, floor_binds = 0.55, False
    elif dist >= 0.25:
        base, floor_binds = 0.45, False
    elif dist >= 0.10:
        base, floor_binds = 0.30, False
    else:                       # < 0.10 (inkl. negativ) ⇒ am/unter dem Boden
        base, floor_binds = 0.10, True

    # Carry-Adjustment: Contango zahlt den Short (+), Backwardation kostet ihn (−).
    if cstate == "contango_tailwind":
        carry_adj = 0.10
    elif cstate == "backwardation_headwind":
        carry_adj = -0.12
    else:
        carry_adj = 0.0

    conf = max(0.10, min(1.0, base + carry_adj))
    # Cost-Curve-Boden als Deckel + fehlende Boden-Daten ⇒ unter die Schwelle.
    if floor_binds or not floor_applied:
        conf = min(conf, 0.49)

    if floor_binds:
        engine_action = ShortAction.COVER     # am Boden: raus/meiden
    elif conf >= 0.50:
        engine_action = ShortAction.SHORT
    else:
        engine_action = ShortAction.NONE

    return FuturesShortAssessment(
        roll_yield_short_ann=ry_short,
        carry_state=cstate,
        cost_floor=cost_floor,
        floor_distance_pct=dist,
        floor_binds=floor_binds,
        floor_applied=floor_applied,
        short_confidence=round(conf, 2),
        engine_action=engine_action,
        available=True,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/utils/test_futures_short_assess.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/utils/futures_short.py tests/core/utils/test_futures_short_assess.py
git commit -m "feat(short): assess_futures_short — Konfidenz aus Carry×Floor + Cost-Curve-Deckel"
```

---

### Task 4: Port `CostFloorProvider` + Stub

**Files:**
- Create: `core/ports/cost_floor.py`
- Create: `adapters/data/cost_floor_stub.py`
- Test: `tests/adapters/test_cost_floor_stub.py`

**Interfaces:**
- Produces: `CostFloorProvider(ABC)` mit `async def get_cost_floor(self, underlying: Underlying, symbol: str) -> float | None`; `StubCostFloorProvider` (gibt `None`).

- [ ] **Step 1: Write the failing test**

```python
# tests/adapters/test_cost_floor_stub.py
"""Phase 3: Stub-Kostenboden liefert None (UNAVAILABLE), bis echte Quelle steht."""
import asyncio

from adapters.data.cost_floor_stub import StubCostFloorProvider
from core.ports.cost_floor import CostFloorProvider
from core.domain.taxonomy import Underlying


def test_stub_is_a_cost_floor_provider():
    assert isinstance(StubCostFloorProvider(), CostFloorProvider)


def test_stub_returns_none():
    stub = StubCostFloorProvider()
    assert asyncio.run(stub.get_cost_floor(Underlying.COMMODITY, "CL")) is None
    assert asyncio.run(stub.get_cost_floor(Underlying.PRECIOUS_METAL, "GC")) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/adapters/test_cost_floor_stub.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.ports.cost_floor'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/ports/cost_floor.py
from abc import ABC, abstractmethod

from core.domain.taxonomy import Underlying


class CostFloorProvider(ABC):
    """Port für den Produktionskosten-Boden (Mean-Reversion-Stütze unter dem Preis)."""

    @abstractmethod
    async def get_cost_floor(self, underlying: Underlying, symbol: str) -> float | None:
        """Kostenboden als Preis. Rohstoff: Grenzproduktionskosten; Edelmetall: AISC der Minen.
        None (UNAVAILABLE), wenn keine Daten vorliegen."""
        ...
```

```python
# adapters/data/cost_floor_stub.py
from core.domain.taxonomy import Underlying
from core.ports.cost_floor import CostFloorProvider


class StubCostFloorProvider(CostFloorProvider):
    """Platzhalter, bis eine echte Kostenboden-Quelle angebunden ist (Stubs-Initiative).

    Liefert immer None → der Futures-Short deckelt mangels Boden konservativ (kein frischer Short)."""

    async def get_cost_floor(self, underlying: Underlying, symbol: str) -> float | None:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/adapters/test_cost_floor_stub.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add core/ports/cost_floor.py adapters/data/cost_floor_stub.py tests/adapters/test_cost_floor_stub.py
git commit -m "feat(short): CostFloorProvider-Port + UNAVAILABLE-Stub"
```

---

### Task 5: Orchestrator — Single-Fetch + Short-Overlay

**Files:**
- Modify: `orchestrators/bottom_up_orchestrator.py` (Imports; Konstruktor; `_futures_overlay` ersetzen; `_run_commodity`/`_run_precious_metals`)
- Test: `tests/test_bottom_up_futures_short_overlay.py`

**Interfaces:**
- Consumes: `assess_futures_short` (Task 3); `CostFloorProvider` (Task 4); `FuturesShortAssessment` (Task 1).
- Produces: `BottomUpOrchestrator.__init__(..., cost_floor_provider: CostFloorProvider | None = None)`; `_fetch_curve_snap(symbol, wrapper)`; `_futures_long_overlay(snap, wrapper)`; `async _futures_short_overlay(snap, symbol, underlying, wrapper)`. `BottomUpResult.futures_short` an Rohstoff/Edelmetall-Future befüllt.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bottom_up_futures_short_overlay.py
"""Phase 3: Short-Overlay bei wrapper=FUTURE & Rohstoff/Edelmetall + Single-Fetch der Kurve."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from core.domain.models import FuturesCurveSnapshot
from core.domain.taxonomy import Underlying, Wrapper
from core.ports.futures_curve import FuturesCurveProvider
from orchestrators.bottom_up_orchestrator import BottomUpOrchestrator


def _snap():
    return FuturesCurveSnapshot(spot=140.0, front=100.0, next_=106.0,
                                days_to_front_expiry=30, days_between_expiries=182,
                                risk_free_rate=0.05, storage_cost=0.0, margin_quote=0.10)


def _orchestrator(futures_curve_provider=None, cost_floor_provider=None):
    orch = BottomUpOrchestrator(
        fundamentals_provider=MagicMock(), macro_provider=MagicMock(),
        market_provider=MagicMock(), llm=MagicMock(), bus=MagicMock(),
        futures_curve_provider=futures_curve_provider, cost_floor_provider=cost_floor_provider,
    )
    orch.commodity_chief = MagicMock()
    orch.commodity_chief.run = AsyncMock(return_value=MagicMock())
    pm_result = MagicMock(); pm_result.valuation_range = None
    orch.precious_metals_chief = MagicMock()
    orch.precious_metals_chief.run = AsyncMock(return_value=pm_result)
    return orch


def test_commodity_future_attaches_futures_short():
    provider = MagicMock(spec=FuturesCurveProvider)
    provider.get_curve = AsyncMock(return_value=_snap())
    orch = _orchestrator(futures_curve_provider=provider)
    res = asyncio.run(orch.run("CL", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE))
    assert res.futures_short is not None
    assert res.futures_short.available is True


def test_single_fetch_curve_called_once():
    provider = MagicMock(spec=FuturesCurveProvider)
    provider.get_curve = AsyncMock(return_value=_snap())
    orch = _orchestrator(futures_curve_provider=provider)
    asyncio.run(orch.run("CL", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE))
    # Long- UND Short-Overlay teilen denselben Snapshot ⇒ genau EIN Provider-Aufruf.
    assert provider.get_curve.call_count == 1


def test_non_future_commodity_has_no_futures_short():
    provider = MagicMock(spec=FuturesCurveProvider)
    provider.get_curve = AsyncMock(return_value=_snap())
    orch = _orchestrator(futures_curve_provider=provider)
    res = asyncio.run(orch.run("DBC", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUND))
    assert res.futures_short is None


def test_cost_floor_provider_exception_does_not_crash():
    provider = MagicMock(spec=FuturesCurveProvider)
    provider.get_curve = AsyncMock(return_value=_snap())
    floor = MagicMock()
    floor.get_cost_floor = AsyncMock(side_effect=RuntimeError("boom"))
    orch = _orchestrator(futures_curve_provider=provider, cost_floor_provider=floor)
    res = asyncio.run(orch.run("CL", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE))
    assert res.futures_short is not None
    assert res.futures_short.floor_applied is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_bottom_up_futures_short_overlay.py -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'cost_floor_provider'`

- [ ] **Step 3: Write minimal implementation**

In `orchestrators/bottom_up_orchestrator.py` die Imports ergänzen:

```python
from core.domain.models import BottomUpResult, FundInfo, FuturesAssessment, FuturesShortAssessment, RiskAffinity
from core.ports.cost_floor import CostFloorProvider
from core.utils.futures_curve import assess_futures_curve
from core.utils.futures_short import assess_futures_short
```

Im Konstruktor den Parameter + das Feld ergänzen:

```python
        futures_curve_provider: "FuturesCurveProvider | None" = None,
        cost_floor_provider: "CostFloorProvider | None" = None,
    ):
```
…
```python
        self.futures_curve_provider = futures_curve_provider
        self.cost_floor_provider    = cost_floor_provider
```

Die bestehende `async def _futures_overlay(...)` **ersetzen** durch drei Methoden:

```python
    async def _fetch_curve_snap(self, symbol: str, wrapper: Wrapper):
        """Holt die Terminkurve EINMAL (defensiv). None bei Nicht-Future/fehlendem Provider/Fehler.
        Long- und Short-Overlay teilen sich dieses Ergebnis (kein Doppel-Fetch)."""
        if wrapper != Wrapper.FUTURE or self.futures_curve_provider is None:
            return None
        try:
            return await self.futures_curve_provider.get_curve(symbol)
        except Exception:
            return None

    def _futures_long_overlay(self, snap, wrapper: Wrapper) -> "FuturesAssessment | None":
        """Long-Mechanik (Phase 2a) aus dem bereits geholten Snapshot. wrapper≠FUTURE → None;
        Future ohne Daten → unavailable() (via assess_futures_curve(None))."""
        if wrapper != Wrapper.FUTURE:
            return None
        return assess_futures_curve(snap)

    async def _futures_short_overlay(self, snap, symbol: str, underlying: Underlying,
                                     wrapper: Wrapper) -> "FuturesShortAssessment | None":
        """Short-Mechanik (Phase 3) nur bei wrapper=FUTURE & Rohstoff/Edelmetall. Kostenboden
        defensiv: fehlender Provider/Exception → floor=None (Deckel via floor_applied=False)."""
        if wrapper != Wrapper.FUTURE or underlying not in (Underlying.COMMODITY, Underlying.PRECIOUS_METAL):
            return None
        floor = None
        if self.cost_floor_provider is not None:
            try:
                floor = await self.cost_floor_provider.get_cost_floor(underlying, symbol)
            except Exception:
                floor = None
        return assess_futures_short(snap, floor)
```

In `_run_commodity` den Body so umstellen (snap einmal holen, beide Overlays daraus):

```python
    async def _run_commodity(self, ticker: str, wrapper: Wrapper = Wrapper.FUTURE) -> BottomUpResult:
        try:
            commodity_result = await self.commodity_chief.run(ticker)
        except Exception:
            commodity_result = CommodityChiefAgentMikro.default(ticker)
        snap = await self._fetch_curve_snap(ticker, wrapper)
        return BottomUpResult(
            ticker=ticker,
            underlying=Underlying.COMMODITY,
            wrapper=wrapper,
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=None, index=None, commodity_deep=commodity_result,
            futures_curve=self._futures_long_overlay(snap, wrapper),
            futures_short=await self._futures_short_overlay(snap, ticker, Underlying.COMMODITY, wrapper),
        )
```

In `_run_precious_metals` analog:

```python
    async def _run_precious_metals(self, metal: str, wrapper: Wrapper = Wrapper.FUTURE) -> BottomUpResult:
        try:
            pm_result = await self.precious_metals_chief.run(metal)
        except Exception:
            pm_result = PreciousMetalsChiefAgent.default(metal)
        snap = await self._fetch_curve_snap(metal, wrapper)
        return BottomUpResult(
            ticker=metal,
            underlying=Underlying.PRECIOUS_METAL,
            wrapper=wrapper,
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None,
            valuation_range=pm_result.valuation_range,
            precious_metals=pm_result, bond=None, index=None, commodity_deep=None,
            futures_curve=self._futures_long_overlay(snap, wrapper),
            futures_short=await self._futures_short_overlay(snap, metal, Underlying.PRECIOUS_METAL, wrapper),
        )
```

- [ ] **Step 4: Run tests to verify they pass (neu + bestehendes Long-Overlay)**

Run: `python -m pytest tests/test_bottom_up_futures_short_overlay.py tests/test_bottom_up_futures_overlay.py -v`
Expected: PASS (alle) — der bestehende Long-Overlay-Test bleibt grün (Verhalten unverändert).

- [ ] **Step 5: Commit**

```bash
git add orchestrators/bottom_up_orchestrator.py tests/test_bottom_up_futures_short_overlay.py
git commit -m "feat(short): Single-Fetch-Kurve + Futures-Short-Overlay im BottomUpOrchestrator"
```

---

### Task 6: Andocken an die Short-Engine — `derive_short_assessment`

**Files:**
- Modify: `core/domain/short_assessment.py` (Nicht-Equity-Zweig ~Zeile 72)
- Test: `tests/test_short_assessment_futures.py`

**Interfaces:**
- Consumes: `BottomUpResult.futures_short` (Task 1/5); bestehende `_action`, `_mk`, `_position_size_pct`, `_THRESHOLD`; `Underlying`, `Wrapper`, `PositionState`, `ShortAction`.
- Produces: `derive_short_assessment(...)` liefert für commodity/precious_metal + wrapper=future eine `ShortAssessment` mit kurven-/kostenbasierter `short_action`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_short_assessment_futures.py
"""Phase 3: derive_short_assessment-Zweig für Rohstoff/Edelmetall-Future-Shorts."""
from types import SimpleNamespace

from core.domain.models import FuturesShortAssessment, ShortAction, PositionState
from core.domain.short_assessment import derive_short_assessment
from core.domain.taxonomy import Underlying, Wrapper


def _bottom_up(fs, underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE):
    return SimpleNamespace(underlying=underlying, wrapper=wrapper,
                           short_interest=None, futures_short=fs)


def _fs(conf, floor_binds=False, action=ShortAction.SHORT, available=True):
    return FuturesShortAssessment(
        roll_yield_short_ann=0.06, carry_state="contango_tailwind", cost_floor=100.0,
        floor_distance_pct=0.40, floor_binds=floor_binds, floor_applied=True,
        short_confidence=conf, engine_action=action, available=available)


def _derive(bu, current_position):
    return derive_short_assessment(bu, cockpit=None, current_position=current_position,
                                   top_down_available=True, bu_anomaly=None, td_anomaly=None)


def test_strong_curve_no_position_yields_short():
    a = _derive(_bottom_up(_fs(0.55)), PositionState.NONE)
    assert a.short_action == ShortAction.SHORT
    assert a.confidence == 0.55
    assert "carry_short" in a.archetypes


def test_floor_binds_no_position_yields_none():
    a = _derive(_bottom_up(_fs(0.20, floor_binds=True, action=ShortAction.COVER)), PositionState.NONE)
    assert a.short_action == ShortAction.NONE


def test_floor_binds_existing_short_yields_cover():
    a = _derive(_bottom_up(_fs(0.20, floor_binds=True, action=ShortAction.COVER)), PositionState.SHORT)
    assert a.short_action == ShortAction.COVER


def test_unavailable_futures_short_falls_back():
    a = _derive(_bottom_up(_fs(0.55, available=False)), PositionState.SHORT)
    assert a.short_action == ShortAction.HOLD          # bisheriger Fallback (kein Crash)
    assert a.confidence == 0.10


def test_long_position_defers_to_none():
    a = _derive(_bottom_up(_fs(0.55)), PositionState.LONG)
    assert a.short_action == ShortAction.NONE          # Long-Titel → kein Short
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_short_assessment_futures.py -v`
Expected: FAIL — z. B. `test_strong_curve_no_position_yields_short` erwartet SHORT, bekommt aber den alten Fallback (NONE/HOLD, conf 0.10).

- [ ] **Step 3: Write minimal implementation**

In `core/domain/short_assessment.py` den bestehenden Block

```python
    if underlying != Underlying.EQUITY:
        action = ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE
        return _mk(underlying, wrapper, action, 0.10, [],
                   ["Fallback: klassenspezifische Short-Logik folgt"], regime, squeeze, htb)
```

ersetzen durch:

```python
    if underlying != Underlying.EQUITY:
        # Phase 3: kurven-/kostengetriebener Futures-Short für Rohstoff/Edelmetall (wrapper=future).
        fs = getattr(bottom_up, "futures_short", None)
        if (underlying in (Underlying.COMMODITY, Underlying.PRECIOUS_METAL)
                and wrapper == Wrapper.FUTURE and fs is not None and fs.available):
            conf = fs.short_confidence
            action = _action(current_position, conf, position_pnl_pct)
            dist = "n/v" if fs.floor_distance_pct is None else f"{fs.floor_distance_pct:.2f}"
            flags = [f"carry={fs.carry_state}", f"floor_distance={dist}",
                     "floor_binds" if fs.floor_binds else "floor_room"]
            size = None
            if action == ShortAction.SHORT:
                size = round(_position_size_pct(conf) * 0.5, 1)
            elif action == ShortAction.SHORT_PLUS:
                size = round(_position_size_pct(conf) * 0.25, 1)
            stop = 15.0
            return _mk(underlying, wrapper, action, conf, ["carry_short"], flags,
                       regime, squeeze, htb, size, stop)
        # andere Nicht-Equity (bond; oder commodity/metal ohne Future-Wrapper): bisheriger Fallback.
        action = ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE
        return _mk(underlying, wrapper, action, 0.10, [],
                   ["Fallback: klassenspezifische Short-Logik folgt"], regime, squeeze, htb)
```

`PositionState`, `Wrapper`, `_position_size_pct` sind in `short_assessment.py` bereits importiert.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_short_assessment_futures.py tests/test_short_assessment_engine.py -v`
Expected: PASS (neu + bestehende Engine-Tests bleiben grün)

- [ ] **Step 5: Commit**

```bash
git add core/domain/short_assessment.py tests/test_short_assessment_futures.py
git commit -m "feat(short): Futures-Short-Zweig in derive_short_assessment (Rohstoff/Edelmetall)"
```

---

### Task 7: Volllauf + Logbuch

**Files:**
- Modify: `docs/open_todos.md` (Phase-3-Eintrag abhaken + Folge-Aufgaben)

- [ ] **Step 1: Volle Test-Suite grün**

Run: `python -m pytest -q`
Expected: alle grün (keine Regression). Ergebniszahl notieren.

- [ ] **Step 2: Logbuch pflegen**

In `docs/open_todos.md` den Phase-3-Eintrag (`Phase 3 — Long/Short-Feinschliff …`) abhaken mit **Lösung:**-Hinweis (Roll-Yield-Short + Cost-Curve-Deckel, eigenes FuturesShortAssessment, Andocken via derive_short_assessment; Quellen weiter Stub). Folge-Aufgaben ergänzen: Regime-Tilt (v2), Take-Profit am Boden (v2), echte Kurven-/Kostenquelle, Aktienindex-/Anleihe-Futures-Short, Schwellen-Kalibrierung ③/④.

- [ ] **Step 3: Commit**

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): Phase 3 (Futures-Short) umgesetzt — Folge-Aufgaben ergänzt"
```

- [ ] **Step 4: Branch pushen + PR öffnen**

```bash
git push -u origin feat/phase3-futures-short
```
PR-Beschreibung (Deutsch): was (Futures-Short-Zweig Rohstoff/Edelmetall), warum (Phase 3 der Taxonomie), wie (reine Mathematik + Overlay + Port/Stub + Engine-Andockung; Stub-First). **Nicht mergen** — auf den zweiten Blick + OK des Users warten.

---

## Hinweise zur Reihenfolge

Tasks 1→6 sind strikt abhängig (jeder baut auf dem Vorgänger). Task 7 erst, wenn 1–6 grün sind. Jeder Task endet mit einem eigenständig testbaren Commit.
