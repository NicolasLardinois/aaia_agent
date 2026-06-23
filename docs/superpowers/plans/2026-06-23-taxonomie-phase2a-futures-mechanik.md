# Taxonomie Phase 2a — Futures-Mechanik-Schicht + Nominal-Umstellung — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Beim `wrapper=future` (Basiswert Rohstoff/Edelmetall) eine Mechanik-Schicht (Kurve/Roll/Carry/Basis/Cost-of-Carry/Verfall/Hebel) zuschalten und Exposure-/Sizing-Kennzahlen wrapper-bewusst auf den **Nominalwert** rechnen.

**Architecture:** Reine Rechen-Helfer (`core/utils/futures_curve.py`) + Domänenmodelle (`FuturesCurveSnapshot` Roh-Input, `FuturesAssessment` berechneter Block). Neuer Port `FuturesCurveProvider` (Hexagonal) mit UNAVAILABLE-Stub. Der `BottomUpOrchestrator` legt die Schicht **nach** der Basiswert-Engine über das Ergebnis, wenn `wrapper=FUTURE`. `portfolio_monitor` rechnet Exposure wrapper-abhängig auf Notional. Verhaltens-erhaltend für alle Nicht-Future-Wrapper.

**Tech Stack:** Python 3.12, pytest, asyncio. Reine Funktionen ohne I/O in `core/`; I/O nur im Adapter.

## Global Constraints

- Sprache: Code-Kommentare + Docstrings **Deutsch** (Projektkonvention).
- Hexagonal: Agenten/Orchestratoren hängen nur von `core/ports/`, nie von `adapters/`.
- Type Hints moderne Syntax (`float | None`).
- TDD verpflichtend: erst Test (rot), dann Code, dann grün. Grenzfälle (genau auf Schwelle, knapp darüber/darunter, `None`, negativ) explizit.
- Lückenlose Schwellenbänder (AGENTS.md §2): jeder Wert fällt in genau eine Klasse.
- Defensive Defaults: fehlende Daten → `None`/UNAVAILABLE, nie Crash.
- Master-Design (verbindlich): `docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md` §6.3–6.5; Impact §F.
- Einheiten: Preise absolut; Zinssatz `r`, Lagerkosten `u`, Convenience-Yield `y` als **Dezimal p. a.** (0.03 = 3 %); `slope_ann`/`roll_yield_long_ann` Dezimal p. a.; Tage als Kalendertage.

---

### Task 1: Pure Math — Kurvenneigung, Roll-Yield, Basis, Cost-of-Carry, Convenience-Yield

**Files:**
- Create: `core/utils/futures_curve.py`
- Test: `tests/core/utils/test_futures_curve_math.py`

**Interfaces:**
- Produces:
  - `slope_ann(front: float, next_: float, days_between: int) -> float | None`
  - `roll_yield_long_ann(slope: float) -> float`
  - `basis(spot: float, front: float) -> float`
  - `cost_of_carry_fair(spot: float, r: float, u: float, y: float, T_years: float) -> float`
  - `implied_convenience_yield(spot: float, front: float, r: float, u: float, T_years: float) -> float | None`

**Fachliche Begründung (im Code als Kommentar):**
- `slope_ann = (next_/front − 1) · (365 / days_between)` — annualisierte Kurvenneigung zwischen Front- und Folgekontrakt (Design §6.3a). Contango `next_>front` ⇒ `slope_ann>0`.
- `roll_yield_long_ann = −slope_ann` — Roll-Yield für den Long ist die Neigung mit umgekehrtem Vorzeichen (Design §6.3b): Contango = Gegenwind.
- `basis = spot − front` — positiv ⇒ Backwardation (Design §6.3d).
- `cost_of_carry_fair = spot · e^((r+u−y)·T)` — theoretischer Fair-Future-Preis (Design §6.3c).
- `implied_convenience_yield = r + u − ln(front/spot)/T` — Cost-of-Carry nach `y` aufgelöst (Design §13.4: implizit aus Preisen, **kein** Mispricing-Flag).

- [ ] **Step 1: Write the failing test**

```python
import math
import pytest
from core.utils.futures_curve import (
    slope_ann, roll_yield_long_ann, basis,
    cost_of_carry_fair, implied_convenience_yield,
)


def test_slope_ann_contango_positive():
    # next_ 5% über front auf 182.5 Tage (halbes Jahr) → ~+10% p.a.
    s = slope_ann(front=100.0, next_=105.0, days_between=182)
    assert s == pytest.approx(0.05 * 365 / 182, rel=1e-6)
    assert s > 0


def test_slope_ann_backwardation_negative():
    assert slope_ann(front=100.0, next_=95.0, days_between=182) < 0


def test_slope_ann_guards_zero_days_and_zero_front():
    assert slope_ann(front=100.0, next_=105.0, days_between=0) is None
    assert slope_ann(front=0.0, next_=105.0, days_between=182) is None


def test_roll_yield_is_negated_slope():
    assert roll_yield_long_ann(0.08) == -0.08
    assert roll_yield_long_ann(-0.08) == 0.08


def test_basis_sign():
    assert basis(spot=101.0, front=100.0) == pytest.approx(1.0)   # Backwardation
    assert basis(spot=99.0, front=100.0) == pytest.approx(-1.0)   # Contango


def test_cost_of_carry_fair_pure_rate_for_metals():
    # u=y=0 → reiner Zins-Carry F = S·e^(r·T)
    f = cost_of_carry_fair(spot=2000.0, r=0.05, u=0.0, y=0.0, T_years=1.0)
    assert f == pytest.approx(2000.0 * math.exp(0.05))


def test_implied_convenience_yield_inverts_cost_of_carry():
    # Backwardation (front<spot) bei r,u klein → positive Convenience-Yield
    y = implied_convenience_yield(spot=100.0, front=98.0, r=0.05, u=0.0, T_years=0.5)
    expected = 0.05 + 0.0 - math.log(98.0 / 100.0) / 0.5
    assert y == pytest.approx(expected)
    assert y > 0


def test_implied_convenience_yield_guards():
    assert implied_convenience_yield(spot=0.0, front=98.0, r=0.05, u=0.0, T_years=0.5) is None
    assert implied_convenience_yield(spot=100.0, front=98.0, r=0.05, u=0.0, T_years=0.0) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/utils/test_futures_curve_math.py -v`
Expected: FAIL mit `ModuleNotFoundError: core.utils.futures_curve`.

- [ ] **Step 3: Write minimal implementation**

```python
"""Reine Termin­kurven-Mathematik (Futures-Mechanik-Schicht, Phase 2a).

Keine I/O, keine Modelle — nur Float-in/Float-out. Begründungen siehe
docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md §6.3.
Einheiten: r/u/y und Rückgaben als Dezimal p. a. (0.03 = 3 %); Tage = Kalendertage.
"""
import math


def slope_ann(front: float, next_: float, days_between: int) -> float | None:
    """Annualisierte Kurvenneigung (next_/front − 1)·(365/Δtage). Contango ⇒ > 0."""
    if not front or days_between <= 0:
        return None
    return (next_ / front - 1.0) * (365.0 / days_between)


def roll_yield_long_ann(slope: float) -> float:
    """Roll-Yield für den Long = −slope (Contango = negativer Roll = Gegenwind)."""
    return -slope


def basis(spot: float, front: float) -> float:
    """Basis = Spot − Future. Positiv ⇒ Backwardation."""
    return spot - front


def cost_of_carry_fair(spot: float, r: float, u: float, y: float, T_years: float) -> float:
    """Theoretischer Fair-Future-Preis F = S·e^((r+u−y)·T) (stetige Verzinsung)."""
    return spot * math.exp((r + u - y) * T_years)


def implied_convenience_yield(spot: float, front: float, r: float, u: float, T_years: float) -> float | None:
    """Implizite Convenience-Yield: Cost-of-Carry nach y aufgelöst.
    y = r + u − ln(front/spot)/T. Kein Mispricing-Urteil (Design §13.4)."""
    if not spot or T_years <= 0:
        return None
    return r + u - math.log(front / spot) / T_years
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/utils/test_futures_curve_math.py -v`
Expected: PASS (alle 8).

- [ ] **Step 5: Commit**

```bash
git add core/utils/futures_curve.py tests/core/utils/test_futures_curve_math.py
git commit -m "feat(futures): reine Termin­kurven-Mathematik (slope/roll/basis/carry/convenience)"
```

---

### Task 2: Signal-Bänder + Verfall-Warnung (pure)

**Files:**
- Modify: `core/utils/futures_curve.py`
- Test: `tests/core/utils/test_futures_curve_signal.py`

**Interfaces:**
- Consumes: `slope_ann` (Task 1).
- Produces:
  - `curve_signal(slope: float | None) -> Signal`
  - `roll_warning(days_to_front_expiry: int | None) -> bool`

**Fachliche Begründung:** ±5 %-Bänder (Design §6.3a): unter ~5 % p. a. liegt die Neigung im Bereich normaler Lager-/Zins-Carry und ist nicht richtungsweisend. Backwardation (`slope ≤ −0.05`) ⇒ Knappheit + positiver Roll ⇒ **BULLISH**; Contango (`slope ≥ +0.05`) ⇒ Überangebot + negativer Roll ⇒ **BEARISH**; dazwischen **NEUTRAL**. Lückenlos (`≤ −0.05 | −0.05<…<+0.05 | ≥ +0.05`). Verfall < 5 Handelstage ⇒ Roll-Warnung (Design §6.3f).

- [ ] **Step 1: Write the failing test**

```python
import pytest
from core.domain.models import Signal
from core.utils.futures_curve import curve_signal, roll_warning


@pytest.mark.parametrize("slope,expected", [
    (-0.06, Signal.BULLISH),   # klare Backwardation
    (-0.05, Signal.BULLISH),   # genau auf der Schwelle
    (-0.04, Signal.NEUTRAL),   # knapp darüber
    (0.0,   Signal.NEUTRAL),
    (0.04,  Signal.NEUTRAL),
    (0.05,  Signal.BEARISH),   # genau auf der Schwelle
    (0.06,  Signal.BEARISH),   # klares Contango
])
def test_curve_signal_bands(slope, expected):
    assert curve_signal(slope) == expected


def test_curve_signal_none_is_neutral():
    assert curve_signal(None) == Signal.NEUTRAL


def test_roll_warning_threshold():
    assert roll_warning(4) is True
    assert roll_warning(5) is False     # 5 Tage = Fenstergrenze, keine Warnung mehr
    assert roll_warning(10) is False
    assert roll_warning(None) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/utils/test_futures_curve_signal.py -v`
Expected: FAIL mit `ImportError: cannot import name 'curve_signal'`.

- [ ] **Step 3: Write minimal implementation** (an `core/utils/futures_curve.py` anhängen)

```python
from core.domain.models import Signal


def curve_signal(slope: float | None) -> Signal:
    """±5 %-Bänder (Design §6.3a). Lückenlos, jeder Wert in genau einer Klasse."""
    if slope is None:
        return Signal.NEUTRAL
    if slope <= -0.05:
        return Signal.BULLISH      # Backwardation: Knappheit + positiver Roll
    if slope >= 0.05:
        return Signal.BEARISH      # Contango: Überangebot + negativer Roll
    return Signal.NEUTRAL


def roll_warning(days_to_front_expiry: int | None) -> bool:
    """True, wenn der Front-Kontrakt < 5 Handelstage vor Verfall steht (Roll steht an)."""
    if days_to_front_expiry is None:
        return False
    return days_to_front_expiry < 5
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/utils/test_futures_curve_signal.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/utils/futures_curve.py tests/core/utils/test_futures_curve_signal.py
git commit -m "feat(futures): Signal-Bänder (±5%) + Verfall-Roll-Warnung"
```

---

### Task 3: Domänenmodelle `FuturesCurveSnapshot` + `FuturesAssessment` + Aggregator

**Files:**
- Modify: `core/domain/models.py` (zwei `@dataclass(frozen=True)` ergänzen)
- Modify: `core/utils/futures_curve.py` (Aggregator `assess_futures_curve`)
- Test: `tests/core/utils/test_futures_curve_assess.py`

**Interfaces:**
- Consumes: alle Funktionen aus Task 1+2.
- Produces:
  - `FuturesCurveSnapshot(spot, front, next_, days_to_front_expiry, days_between_expiries, risk_free_rate, storage_cost, margin_quote)` — Roh-Input (alle `float`/`int`, `margin_quote: float | None`).
  - `FuturesAssessment(signal, slope_ann, roll_yield_long_ann, basis, fair_value, implied_convenience_yield, leverage, roll_warning, available)` + Klassenmethode `FuturesAssessment.unavailable()`.
  - `assess_futures_curve(snap: FuturesCurveSnapshot | None) -> FuturesAssessment`.

**Begründung:** Trennt Roh-Marktdaten (Port-Output) von der berechneten Bewertung. `leverage = 1/margin_quote` (z. B. 10 % Margin ⇒ 10× Hebel); fehlt `margin_quote` → `leverage=None`. `T_years = days_to_front_expiry/365`.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from core.domain.models import FuturesCurveSnapshot, FuturesAssessment, Signal
from core.utils.futures_curve import assess_futures_curve


def _snap(**kw):
    base = dict(spot=100.0, front=100.0, next_=106.0, days_to_front_expiry=30,
                days_between_expiries=182, risk_free_rate=0.05, storage_cost=0.0,
                margin_quote=0.10)
    base.update(kw)
    return FuturesCurveSnapshot(**base)


def test_assess_none_is_unavailable():
    a = assess_futures_curve(None)
    assert a.available is False
    assert a.signal == Signal.NEUTRAL


def test_assess_contango_bearish_with_negative_roll():
    a = assess_futures_curve(_snap(front=100.0, next_=106.0))   # +6% → >5% p.a. Contango
    assert a.available is True
    assert a.signal == Signal.BEARISH
    assert a.slope_ann > 0
    assert a.roll_yield_long_ann < 0
    assert a.leverage == pytest.approx(10.0)


def test_assess_backwardation_bullish():
    a = assess_futures_curve(_snap(front=100.0, next_=92.0, spot=101.0))
    assert a.signal == Signal.BULLISH
    assert a.basis == pytest.approx(1.0)
    assert a.roll_yield_long_ann > 0


def test_assess_missing_margin_leaves_leverage_none():
    a = assess_futures_curve(_snap(margin_quote=None))
    assert a.leverage is None
    assert a.signal in (Signal.BULLISH, Signal.BEARISH, Signal.NEUTRAL)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/utils/test_futures_curve_assess.py -v`
Expected: FAIL mit `ImportError` (`FuturesCurveSnapshot` / `assess_futures_curve` fehlen).

- [ ] **Step 3: Write minimal implementation**

In `core/domain/models.py` (bei den übrigen `@dataclass(frozen=True)`-Modellen):

```python
@dataclass(frozen=True)
class FuturesCurveSnapshot:
    """Roh-Terminkurvendaten (Output des FuturesCurveProvider-Ports)."""
    spot: float
    front: float
    next_: float
    days_to_front_expiry: int
    days_between_expiries: int
    risk_free_rate: float          # Dezimal p. a.
    storage_cost: float            # Dezimal p. a. (Lagerkosten u)
    margin_quote: float | None     # Initial-Margin als Anteil des Nominals (0.10 = 10 %)


@dataclass(frozen=True)
class FuturesAssessment:
    """Berechneter Mechanik-Block (Design §6.3). available=False ⇒ keine Kurvendaten."""
    signal: Signal
    slope_ann: float | None
    roll_yield_long_ann: float | None
    basis: float | None
    fair_value: float | None
    implied_convenience_yield: float | None
    leverage: float | None
    roll_warning: bool
    available: bool

    @classmethod
    def unavailable(cls) -> "FuturesAssessment":
        return cls(Signal.NEUTRAL, None, None, None, None, None, None, False, False)
```

In `core/utils/futures_curve.py`:

```python
from core.domain.models import FuturesCurveSnapshot, FuturesAssessment


def assess_futures_curve(snap: "FuturesCurveSnapshot | None") -> "FuturesAssessment":
    """Aggregiert die reine Kurven-Mathematik zu einem Bewertungsblock (Design §6.3)."""
    if snap is None:
        return FuturesAssessment.unavailable()
    s = slope_ann(snap.front, snap.next_, snap.days_between_expiries)
    t_years = snap.days_to_front_expiry / 365.0
    return FuturesAssessment(
        signal=curve_signal(s),
        slope_ann=s,
        roll_yield_long_ann=roll_yield_long_ann(s) if s is not None else None,
        basis=basis(snap.spot, snap.front),
        fair_value=cost_of_carry_fair(snap.spot, snap.risk_free_rate, snap.storage_cost, 0.0, t_years),
        implied_convenience_yield=implied_convenience_yield(
            snap.spot, snap.front, snap.risk_free_rate, snap.storage_cost, t_years),
        leverage=(1.0 / snap.margin_quote) if snap.margin_quote else None,
        roll_warning=roll_warning(snap.days_to_front_expiry),
        available=True,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/utils/test_futures_curve_assess.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/domain/models.py core/utils/futures_curve.py tests/core/utils/test_futures_curve_assess.py
git commit -m "feat(futures): FuturesCurveSnapshot/FuturesAssessment + assess-Aggregator"
```

---

### Task 4: Port `FuturesCurveProvider` + UNAVAILABLE-Stub

**Files:**
- Create: `core/ports/futures_curve.py`
- Create: `adapters/data/futures_curve_stub.py`
- Test: `tests/adapters/test_futures_curve_stub.py`

**Interfaces:**
- Consumes: `FuturesCurveSnapshot` (Task 3).
- Produces: `FuturesCurveProvider(ABC).get_curve(symbol: str) -> FuturesCurveSnapshot | None`; `StubFuturesCurveProvider` gibt immer `None` (UNAVAILABLE), bis echte Quelle folgt.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from core.ports.futures_curve import FuturesCurveProvider
from adapters.data.futures_curve_stub import StubFuturesCurveProvider


@pytest.mark.asyncio
async def test_stub_returns_none():
    provider = StubFuturesCurveProvider()
    assert isinstance(provider, FuturesCurveProvider)
    assert await provider.get_curve("CL") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/adapters/test_futures_curve_stub.py -v`
Expected: FAIL mit `ModuleNotFoundError: core.ports.futures_curve`.

- [ ] **Step 3: Write minimal implementation**

`core/ports/futures_curve.py`:

```python
from abc import ABC, abstractmethod
from core.domain.models import FuturesCurveSnapshot


class FuturesCurveProvider(ABC):
    """Port für Terminkurvendaten (Front/Folgekontrakt, Verfall, Margin)."""

    @abstractmethod
    async def get_curve(self, symbol: str) -> FuturesCurveSnapshot | None:
        """Liefert die Kurve oder None (UNAVAILABLE), wenn keine Daten vorliegen."""
        ...
```

`adapters/data/futures_curve_stub.py`:

```python
from core.domain.models import FuturesCurveSnapshot
from core.ports.futures_curve import FuturesCurveProvider


class StubFuturesCurveProvider(FuturesCurveProvider):
    """Platzhalter, bis eine echte Terminkurven-Quelle angebunden ist (Stubs-Initiative)."""

    async def get_curve(self, symbol: str) -> FuturesCurveSnapshot | None:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/adapters/test_futures_curve_stub.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/ports/futures_curve.py adapters/data/futures_curve_stub.py tests/adapters/test_futures_curve_stub.py
git commit -m "feat(futures): FuturesCurveProvider-Port + UNAVAILABLE-Stub"
```

---

### Task 5: `BottomUpResult.futures_curve` + Overlay im Orchestrator

**Files:**
- Modify: `core/domain/models.py` (Feld `futures_curve: FuturesAssessment | None = None` an `BottomUpResult`)
- Modify: `orchestrators/bottom_up_orchestrator.py` (Konstruktor nimmt optional `futures_curve_provider`; `_run_commodity`/`_run_precious_metals` nehmen `wrapper`; Overlay bei `wrapper=FUTURE`)
- Test: `tests/test_bottom_up_futures_overlay.py`

**Interfaces:**
- Consumes: `assess_futures_curve` (Task 3), `FuturesCurveProvider` (Task 4).
- Produces: `BottomUpResult.futures_curve` ist bei `wrapper=FUTURE` ein `FuturesAssessment`, sonst `None`.

**Begründung:** Die Schicht ist kein neuer Chief, sondern eine Überlagerung **nach** der Basiswert-Engine (Design §6.5). Fehlt der Provider oder liefert er `None` → `FuturesAssessment.unavailable()` (defensiv, nie Crash). Nicht-Future-Wrapper bleiben unverändert (`futures_curve=None`).

- [ ] **Step 1: Write the failing test**

```python
import pytest
from core.domain.models import FuturesCurveSnapshot
from core.domain.taxonomy import Underlying, Wrapper
from core.ports.futures_curve import FuturesCurveProvider
from orchestrators.bottom_up_orchestrator import BottomUpOrchestrator
from tests._helpers_bottomup import make_orchestrator  # bestehender Test-Helfer-Stil


class _FakeCurve(FuturesCurveProvider):
    async def get_curve(self, symbol):
        return FuturesCurveSnapshot(spot=100.0, front=100.0, next_=106.0,
                                    days_to_front_expiry=30, days_between_expiries=182,
                                    risk_free_rate=0.05, storage_cost=0.0, margin_quote=0.10)


@pytest.mark.asyncio
async def test_commodity_future_attaches_assessment():
    orch = make_orchestrator(futures_curve_provider=_FakeCurve())
    res = await orch.run("CL", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE)
    assert res.futures_curve is not None
    assert res.futures_curve.available is True


@pytest.mark.asyncio
async def test_commodity_without_provider_is_unavailable_not_crash():
    orch = make_orchestrator(futures_curve_provider=None)
    res = await orch.run("CL", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE)
    assert res.futures_curve is not None
    assert res.futures_curve.available is False
```

> **Hinweis:** Falls `tests/_helpers_bottomup.make_orchestrator` nicht existiert, in Step 3 einen minimalen lokalen Builder im Test anlegen, der `BottomUpOrchestrator` mit Fakes für `fundamentals_provider/macro_provider/market_provider/llm/bus` baut (Muster aus `tests/test_bottom_up_dispatch.py` übernehmen).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_bottom_up_futures_overlay.py -v`
Expected: FAIL (Konstruktor kennt `futures_curve_provider` nicht / `futures_curve` fehlt).

- [ ] **Step 3: Write minimal implementation**

`BottomUpResult` (models.py): Feld `futures_curve: "FuturesAssessment | None" = None` ergänzen (ans Ende der Felder, Default `None` → alle bestehenden Konstruktor-Aufrufe bleiben gültig).

`bottom_up_orchestrator.py`:
- Konstruktor-Signatur um `futures_curve_provider: "FuturesCurveProvider | None" = None` erweitern, als `self.futures_curve_provider` speichern.
- `run(...)`: `_run_commodity`/`_run_precious_metals` mit `wrapper` aufrufen:
  ```python
  case Underlying.COMMODITY:
      return await self._run_commodity(ticker, wrapper)
  case Underlying.PRECIOUS_METAL:
      return await self._run_precious_metals(ticker, wrapper)
  ```
- Privater Helfer:
  ```python
  async def _futures_overlay(self, symbol: str, wrapper: Wrapper) -> "FuturesAssessment | None":
      """Mechanik-Schicht nur bei wrapper=FUTURE; defensiv → unavailable statt Crash."""
      if wrapper != Wrapper.FUTURE:
          return None
      from core.utils.futures_curve import assess_futures_curve
      from core.domain.models import FuturesAssessment
      if self.futures_curve_provider is None:
          return FuturesAssessment.unavailable()
      try:
          snap = await self.futures_curve_provider.get_curve(symbol)
      except Exception:
          snap = None
      return assess_futures_curve(snap)
  ```
- In `_run_commodity(ticker, wrapper)` und `_run_precious_metals(metal, wrapper)`: `futures = await self._futures_overlay(ticker, wrapper)` berechnen, im `BottomUpResult(..., futures_curve=futures)` setzen, und das hartkodierte `wrapper=Wrapper.FUTURE` durch den übergebenen `wrapper` ersetzen.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_bottom_up_futures_overlay.py -v`
Expected: PASS. Danach Regression: `python -m pytest tests/test_bottom_up_dispatch.py -q` (alte Dispatch-Tests bleiben grün).

- [ ] **Step 5: Commit**

```bash
git add core/domain/models.py orchestrators/bottom_up_orchestrator.py tests/test_bottom_up_futures_overlay.py
git commit -m "feat(futures): Mechanik-Overlay bei wrapper=FUTURE im BottomUpOrchestrator"
```

---

### Task 6: `Position.contract_multiplier` + JSON-Laden

**Files:**
- Modify: `core/domain/portfolio.py` (Feld `contract_multiplier: float = 1.0`)
- Modify: `adapters/persistence/json_portfolio.py` (Key `contract_multiplier` lesen, Default 1.0)
- Test: `tests/test_json_portfolio.py` (ergänzen)

**Interfaces:**
- Produces: `Position.contract_multiplier` (Default `1.0` → rückwärtskompatibel: single/fund/physical = 1.0; Future liefert Kontraktgröße).

**Begründung:** Notional eines Futures = `shares · price · contract_multiplier` (Impact §F). Ohne Multiplikator unterschätzt das Exposure den Hebel. Default 1.0 lässt alle bestehenden Positionen unverändert.

- [ ] **Step 1: Write the failing test** (in `tests/test_json_portfolio.py` ergänzen)

```python
def test_contract_multiplier_defaults_to_one(tmp_path):
    p = tmp_path / "pf.json"
    p.write_text('[{"ticker":"AAPL","shares":10,"buy_price":100,"direction":"long"}]', encoding="utf-8")
    positions = JsonPortfolioProvider(str(p)).load()
    assert positions[0].contract_multiplier == 1.0


def test_contract_multiplier_read_from_json(tmp_path):
    p = tmp_path / "pf.json"
    p.write_text('[{"ticker":"CL","shares":2,"buy_price":80,"direction":"long",'
                 '"underlying":"commodity","wrapper":"future","contract_multiplier":1000}]', encoding="utf-8")
    positions = JsonPortfolioProvider(str(p)).load()
    assert positions[0].contract_multiplier == 1000.0
```

> Klassennamen/Lade-Methode (`JsonPortfolioProvider().load()`) an die im Test bereits vorhandenen Importe angleichen.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_json_portfolio.py -k contract_multiplier -v`
Expected: FAIL (`Position` hat kein `contract_multiplier` bzw. Wert wird nicht gelesen).

- [ ] **Step 3: Write minimal implementation**

`portfolio.py`: nach `risk_affinity` ergänzen:
```python
    contract_multiplier: float = 1.0   # Future: Kontraktgröße fürs Notional; sonst 1.0
```
`json_portfolio.py`: beim Bauen der `Position` ergänzen:
```python
        contract_multiplier=float(raw.get("contract_multiplier", 1.0)),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_json_portfolio.py -q`
Expected: PASS (neue + alle bestehenden).

- [ ] **Step 5: Commit**

```bash
git add core/domain/portfolio.py adapters/persistence/json_portfolio.py tests/test_json_portfolio.py
git commit -m "feat(taxonomie): Position.contract_multiplier (Default 1.0) + JSON-Laden"
```

---

### Task 7: Nominal-Exposure wrapper-bewusst im `portfolio_monitor`

**Files:**
- Modify: `agents/portfolio/portfolio_monitor_agent.py` (`_evaluate_positions`: `val` notional-basiert)
- Test: `tests/test_portfolio_monitor.py` (ergänzen)

**Interfaces:**
- Consumes: `Position.contract_multiplier` (Task 6), `Wrapper` (vorhanden).
- Produces: Exposure-Kennzahlen (`net_exposure`, `gross_exposure`, HHI, Vola-Gewichte) rechnen für `wrapper=FUTURE` auf Notional.

**Begründung (Impact §F):** `notional = shares · price · contract_multiplier` (Future) vs. `wert = shares · price` (single/fund/physical_etc → multiplier=1.0). Ein gehebelter Future mit 100 k Notional bei 10 k Margin darf nicht als 10 k ins Netto eingehen — sonst sieht das Buch 10× sicherer aus. `net_beta` bleibt unverändert (Rohstoff/Edelmetall sind dort ohnehin ausgeschlossen).

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_future_exposure_uses_notional(monkeypatch):
    # Ein Future mit multiplier=1000 → Notional = shares·price·1000, nicht shares·price.
    future = Position(ticker="CL", shares=1, entry_price=80.0, direction="long",
                      current_price=80.0, underlying=Underlying.COMMODITY,
                      wrapper=Wrapper.FUTURE, contract_multiplier=1000.0)
    agent = _monitor_with([future])   # Test-Helfer im bestehenden Stil (fx=1, beta=1)
    snap = agent._evaluate_positions([future])
    assert snap["net_exposure"] == pytest.approx(80.0 * 1000.0)


@pytest.mark.asyncio
async def test_single_equity_exposure_unchanged():
    single = Position(ticker="AAPL", shares=10, entry_price=100.0, direction="long",
                      current_price=100.0, underlying=Underlying.EQUITY,
                      wrapper=Wrapper.SINGLE)
    agent = _monitor_with([single])
    snap = agent._evaluate_positions([single])
    assert snap["net_exposure"] == pytest.approx(10.0 * 100.0)
```

> `_monitor_with` an den bestehenden Konstruktions-Helfer in `tests/test_portfolio_monitor.py` angleichen (gleiche Fakes für memory/fx/beta).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_portfolio_monitor.py -k exposure -v`
Expected: FAIL (`net_exposure` rechnet noch ohne multiplier → 80.0 statt 80000.0).

- [ ] **Step 3: Write minimal implementation**

In `_evaluate_positions`, die Wert-Schleife notional-bewusst machen:
```python
        for i, p in enumerate(positions):
            cur = _price(i, p)
            cur_prices.append(cur)
            # Notional: Future rechnet mit Kontraktgröße (Hebel sichtbar machen, Impact §F);
            # single/fund/physical_etc haben multiplier=1.0 → unverändert.
            mult = p.contract_multiplier if p.wrapper == Wrapper.FUTURE else 1.0
            val = p.shares * cur * mult * self.fx_rate(p.currency, BASE_CURRENCY)
            values.append(val)
```
(`Wrapper` ist bereits importiert.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_portfolio_monitor.py -q`
Expected: PASS (neue + alle bestehenden — bestehende nutzen multiplier=1.0, unverändert).

- [ ] **Step 5: Commit**

```bash
git add agents/portfolio/portfolio_monitor_agent.py tests/test_portfolio_monitor.py
git commit -m "fix(risk): net_exposure/gross/HHI/Vola wrapper-bewusst auf Notional (Future-Hebel)"
```

---

### Task 8: Future-Sizing-Deckel in der Empfehlung (≤ 10 % Nominal)

**Files:**
- Modify: `core/domain/recommendation.py` (`_position_size_pct` um optionalen Hebel-Deckel erweitern; `derive_recommendation` reicht `leverage` durch)
- Test: `tests/test_recommendation.py` (ergänzen)

**Interfaces:**
- Consumes: `FuturesAssessment.leverage` (Task 3) — vom Aufrufer durchgereicht.
- Produces: `_position_size_pct(confidence: float, leverage: float | None = None) -> float`; `derive_recommendation(..., leverage: float | None = None)`.

**Begründung (Design §6.3e):** Hebel ändert nicht die Richtung, aber die Größe. Die konfidenz-skalierte Tranche bezieht sich auf **Nominal**; bei Hebel `L` muss der Kapitaleinsatz durch `L` geteilt werden, zusätzlich Deckel **≤ 10 % Nominal**. Ohne Hebel (`leverage=None`) unverändert.

- [ ] **Step 1: Write the failing test**

```python
from core.domain.recommendation import _position_size_pct


def test_size_unchanged_without_leverage():
    assert _position_size_pct(1.0) == 10.0
    assert _position_size_pct(1.0, leverage=None) == 10.0


def test_size_scaled_down_by_leverage():
    # 10× Hebel → Kapitaleinsatz = Nominal/10; Tranche entsprechend kleiner.
    assert _position_size_pct(1.0, leverage=10.0) == pytest.approx(1.0)


def test_size_never_negative_or_above_cap():
    assert _position_size_pct(0.50, leverage=10.0) >= 0.0
    assert _position_size_pct(1.0, leverage=1.0) <= 10.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_recommendation.py -k size -v`
Expected: FAIL (`_position_size_pct` kennt kein `leverage`).

- [ ] **Step 3: Write minimal implementation**

```python
def _position_size_pct(confidence: float, leverage: float | None = None) -> float:
    """Konfidenz→Positionsgröße, 2–10 %. Bei Future-Hebel L wird der Kapitaleinsatz
    durch L geteilt (Tranche bezieht sich auf Nominal, Design §6.3e); Deckel ≤ 10 %."""
    raw = (confidence - 0.50) / 0.50 * 10.0
    capped = max(2.0, min(10.0, raw))
    if leverage and leverage > 0:
        capped = capped / leverage
    return round(max(0.0, min(10.0, capped)), 1)
```
`derive_recommendation`: Parameter `leverage: float | None = None` ergänzen und an beide `_position_size_pct(confidence, leverage)`-Aufrufe (BUY, BUY_PLUS) durchreichen. Aufrufer (judgment) kann `result.futures_curve.leverage` übergeben; Default `None` hält bestehendes Verhalten.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_recommendation.py -q`
Expected: PASS (neue + alle bestehenden — Default `leverage=None` unverändert).

- [ ] **Step 5: Commit**

```bash
git add core/domain/recommendation.py tests/test_recommendation.py
git commit -m "feat(futures): Sizing-Deckel ≤10% Nominal bei Future-Hebel (Default unverändert)"
```

---

### Task 9: Volle Suite + PR

- [ ] **Step 1: Volle Suite**

Run: `python -m pytest -q`
Expected: alle grün außer den **vorbestehenden** `tests/adapters/api/test_routes_cockpit.py`-Isolationsfehlern (auf master identisch rot — separat zu beheben, nicht Teil dieser Slice).

- [ ] **Step 2: Branch + PR**

```bash
git push -u origin feat/taxonomie-phase2a-futures
gh pr create --base master --title "feat(taxonomie): Phase 2a — Futures-Mechanik-Schicht + Nominal-Exposure" --body-file <pr-body>
```
PR-Body (Deutsch): was (Mechanik-Schicht + Nominal), warum (Hebel sichtbar machen, Roll/Carry ins Signal), wie (Port+Stub, reine Mathematik, Overlay, notional-bewusstes Exposure). Hinweis auf die 2 vorbestehenden Cockpit-Isolationsfehler.

---

## Self-Review (gegen Spec §6.3–6.5 + Impact §F)

- **§6.3a Kurvenneigung + ±5 %-Bänder** → Task 1 (`slope_ann`) + Task 2 (`curve_signal`). ✓ lückenlos.
- **§6.3b Roll-Yield = −slope, getrennt benannt, einmal gezählt** → Task 1 + Task 3 (im `FuturesAssessment` getrennt geführt, Signal nur aus `slope`). ✓
- **§6.3c Cost-of-Carry-Anker** → Task 1 (`cost_of_carry_fair`). ✓
- **§6.3d Basis + Vorzeichenbrücke** → Task 1 (`basis`), Test prüft Backwardation positiv. ✓
- **§6.3e Hebel/Margin → Sizing, nicht Richtung** → Task 3 (`leverage`) + Task 8 (Sizing-Deckel). ✓
- **§6.3f Verfall < 5 Tage Roll-Warnung** → Task 2 (`roll_warning`). ✓
- **§13.4 implizite Convenience-Yield, kein Mispricing** → Task 1 (`implied_convenience_yield`), kein Mispricing-Flag erzeugt. ✓
- **§6.5 Overlay nach Engine, kein neuer Chief, defensiv** → Task 5. ✓
- **Impact §F Notional-Exposure (Future ≫ Margin), net_beta unverändert** → Task 6 (multiplier) + Task 7 (notional). ✓
- **Offen/bewusst NICHT in 2a:** echte Terminkurven-Datenquelle (Stub bleibt; eigene Stubs-Slice), Cost-Curve-Boden (braucht `CommoditySupplyProvider`), Short-Zweig für Futures (Phase 3).
