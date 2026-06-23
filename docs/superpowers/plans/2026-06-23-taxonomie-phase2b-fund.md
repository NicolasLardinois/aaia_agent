# Taxonomie Phase 2b — Fund-Info-Schicht (TER + Tracking-Error) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development oder superpowers:executing-plans. Checkbox-Schritte (`- [ ]`).

**Goal:** Bei `wrapper=fund` (Fonds/ETF) eine **Info-Schicht** zuschalten: TER (Kosten-Drag) + Tracking-Error (Abbildungstreue zum Benchmark), rein informativ (kein Richtungssignal).

**Architecture:** Reiner Tracking-Error-Helfer (`core/utils/fund_info.py`) + Domänenmodell `FundInfo` (ter/tracking_error/available). Neuer Port `FundInfoProvider` (Hexagonal) + UNAVAILABLE-Stub. `BottomUpOrchestrator._run_index` legt die Schicht bei `wrapper=FUND` über das Ergebnis. Verhaltens-erhaltend für alle anderen Wrapper.

**Tech Stack:** Python 3.12, pytest. Reine Funktionen ohne I/O in `core/`.

## Global Constraints

- Deutsch (Kommentare/Docstrings); Hexagonal; moderne Type-Hints; TDD (rot→grün); defensive Defaults (fehlt → UNAVAILABLE, nie Crash).
- Master-Design: `…/2026-06-21-anlageklassen-taxonomie-design.md` §6.6 + §13.2.
- Einheiten: TER + Tracking-Error als Dezimal p. a. (0.001 = 0,1 %). Tracking-Error = annualisierte Stdev der Renditedifferenz ETF−Benchmark.

---

### Task 1: Pure Math — Tracking-Error

**Files:**
- Create: `core/utils/fund_info.py`
- Test: `tests/core/utils/test_fund_info_math.py`

**Interfaces:**
- Produces: `tracking_error_ann(etf_returns: list[float], benchmark_returns: list[float], periods_per_year: int = 252) -> float | None`

**Begründung (§6.6):** Tracking-Error = `stdev(R_etf − R_index)` (Sample-Stdev der Differenzreihe), annualisiert mit `√periods_per_year`. Misst Abbildungstreue. Ungleiche/zu kurze Reihen oder unbekannter Benchmark → `None` (UNAVAILABLE), TER bleibt davon unberührt.

- [ ] **Step 1: Write the failing test**

```python
import math
import pytest
from core.utils.fund_info import tracking_error_ann


def test_perfect_tracking_is_zero():
    etf = [0.01, -0.02, 0.015, 0.0]
    assert tracking_error_ann(etf, etf) == 0.0


def test_tracking_error_annualises_diff_stdev():
    etf = [0.012, -0.018, 0.016, -0.009]
    bench = [0.010, -0.020, 0.015, -0.010]
    diffs = [e - b for e, b in zip(etf, bench)]
    mean = sum(diffs) / len(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / (len(diffs) - 1)
    expected = (var ** 0.5) * math.sqrt(252)
    assert tracking_error_ann(etf, bench) == pytest.approx(expected)


def test_guards_unequal_or_too_short():
    assert tracking_error_ann([0.01], [0.01]) is None          # < 2 Punkte
    assert tracking_error_ann([0.01, 0.02], [0.01]) is None     # ungleiche Länge
    assert tracking_error_ann([], []) is None
```

- [ ] **Step 2: Run test to verify it fails** — `python -m pytest tests/core/utils/test_fund_info_math.py -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

```python
"""Reine Fund-Info-Mathematik (TER ist Roh-Stammdatum; hier nur der Tracking-Error).
Keine I/O. §6.6 des Taxonomie-Designs. Einheiten: Dezimal p. a."""
import math


def tracking_error_ann(etf_returns: list[float], benchmark_returns: list[float],
                       periods_per_year: int = 252) -> float | None:
    """Annualisierte Stdev der Renditedifferenz ETF−Benchmark = stdev(R_etf − R_index)·√P."""
    if (len(etf_returns) != len(benchmark_returns)) or len(etf_returns) < 2:
        return None
    diffs = [e - b for e, b in zip(etf_returns, benchmark_returns)]
    mean = sum(diffs) / len(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / (len(diffs) - 1)
    return (var ** 0.5) * math.sqrt(periods_per_year)
```

- [ ] **Step 4: Run test to verify it passes** — PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(fund): reine Tracking-Error-Mathematik (annualisierte Diff-Stdev)"`

---

### Task 2: Domänenmodell `FundInfo` + Port `FundInfoProvider` + Stub

**Files:**
- Modify: `core/domain/models.py` (`@dataclass(frozen=True) FundInfo` + `unavailable()`)
- Create: `core/ports/fund_info.py`
- Create: `adapters/data/fund_info_stub.py`
- Test: `tests/adapters/test_fund_info_stub.py`

**Interfaces:**
- Produces: `FundInfo(ter, tracking_error, available)` mit `FundInfo.unavailable()`; `FundInfoProvider(ABC).get_fund_info(symbol) -> FundInfo | None`; `StubFundInfoProvider` → immer `None`.

**Begründung:** TER + Tracking-Error sind unabhängig verfügbar — TER kann vorliegen, während der Benchmark (und damit Tracking-Error) fehlt (§6.6). `available=True`, sobald **mindestens** TER vorliegt.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from core.domain.models import FundInfo
from core.ports.fund_info import FundInfoProvider
from adapters.data.fund_info_stub import StubFundInfoProvider


def test_unavailable_factory():
    fi = FundInfo.unavailable()
    assert fi.available is False
    assert fi.ter is None and fi.tracking_error is None


@pytest.mark.asyncio
async def test_stub_returns_none():
    provider = StubFundInfoProvider()
    assert isinstance(provider, FundInfoProvider)
    assert await provider.get_fund_info("XLE") is None
```

- [ ] **Step 2: Run test to verify it fails** — FAIL (`ImportError`).

- [ ] **Step 3: Write minimal implementation**

`models.py`:
```python
@dataclass(frozen=True)
class FundInfo:
    """Fonds/ETF-Info-Schicht (§6.6): TER-Kosten-Drag + Tracking-Error. Rein informativ."""
    ter: float | None
    tracking_error: float | None
    available: bool

    @classmethod
    def unavailable(cls) -> "FundInfo":
        return cls(None, None, False)
```
`core/ports/fund_info.py`:
```python
from abc import ABC, abstractmethod
from core.domain.models import FundInfo


class FundInfoProvider(ABC):
    """Port für ETF-/Fonds-Stammdaten (TER) + Benchmark-Renditen (Tracking-Error)."""

    @abstractmethod
    async def get_fund_info(self, symbol: str) -> FundInfo | None:
        """Liefert die Fund-Info oder None (UNAVAILABLE)."""
        ...
```
`adapters/data/fund_info_stub.py`:
```python
from core.domain.models import FundInfo
from core.ports.fund_info import FundInfoProvider


class StubFundInfoProvider(FundInfoProvider):
    """Platzhalter, bis eine echte ETF-Stammdaten-/Benchmark-Quelle angebunden ist."""

    async def get_fund_info(self, symbol: str) -> FundInfo | None:
        return None
```

- [ ] **Step 4: Run test to verify it passes** — PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(fund): FundInfo-Modell + FundInfoProvider-Port + UNAVAILABLE-Stub"`

---

### Task 3: `BottomUpResult.fund_info` + Overlay im Index-Pfad

**Files:**
- Modify: `core/domain/models.py` (`fund_info: FundInfo | None = None` an `BottomUpResult`)
- Modify: `orchestrators/bottom_up_orchestrator.py` (Konstruktor `fund_info_provider`; `_run_index` Overlay bei `wrapper=FUND`)
- Test: `tests/test_bottom_up_fund_overlay.py`

**Interfaces:**
- Consumes: `FundInfoProvider` (Task 2).
- Produces: `BottomUpResult.fund_info` ist bei `wrapper=FUND` ein `FundInfo`, sonst `None`.

**Begründung:** Info-Schicht nur für Fonds-Hülle (§6.6); fehlender Provider/Datenfehler → `unavailable()` (defensiv). Direkt-Indizes (`wrapper=SINGLE`) und alle anderen Wrapper unberührt.

- [ ] **Step 1: Write the failing test**

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock
from core.domain.models import FundInfo
from core.domain.taxonomy import Underlying, Wrapper
from core.ports.fund_info import FundInfoProvider
from orchestrators.bottom_up_orchestrator import BottomUpOrchestrator


class _FakeFund(FundInfoProvider):
    async def get_fund_info(self, symbol):
        return FundInfo(ter=0.001, tracking_error=0.02, available=True)


def _orch(fund_info_provider=None):
    orch = BottomUpOrchestrator(
        fundamentals_provider=MagicMock(), macro_provider=MagicMock(),
        market_provider=MagicMock(), llm=MagicMock(), bus=MagicMock(),
        fund_info_provider=fund_info_provider,
    )
    idx = MagicMock()
    orch.index_chief = MagicMock()
    orch.index_chief.run = AsyncMock(return_value=idx)
    orch.index_chief.default = MagicMock(return_value=idx)
    return orch


def test_fund_wrapper_attaches_info():
    res = asyncio.run(_orch(_FakeFund()).run("XLE", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND))
    assert res.fund_info is not None and res.fund_info.available is True


def test_index_single_has_no_fund_info():
    res = asyncio.run(_orch(_FakeFund()).run("^GSPC", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.SINGLE))
    assert res.fund_info is None


def test_fund_without_provider_is_unavailable():
    res = asyncio.run(_orch(None).run("XLE", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND))
    assert res.fund_info is not None and res.fund_info.available is False
```

- [ ] **Step 2: Run test to verify it fails** — FAIL (Konstruktor kennt `fund_info_provider` nicht).

- [ ] **Step 3: Write minimal implementation**

- `models.py`: an `BottomUpResult` trailing `fund_info: Optional["FundInfo"] = None`.
- `bottom_up_orchestrator.py`:
  - Importe: `from core.domain.models import BottomUpResult, FundInfo, RiskAffinity`; `from core.ports.fund_info import FundInfoProvider`.
  - Konstruktor: Param `fund_info_provider: "FundInfoProvider | None" = None` → `self.fund_info_provider`.
  - Helfer:
    ```python
    async def _fund_overlay(self, symbol: str, wrapper: Wrapper) -> "FundInfo | None":
        if wrapper != Wrapper.FUND:
            return None
        if self.fund_info_provider is None:
            return FundInfo.unavailable()
        try:
            info = await self.fund_info_provider.get_fund_info(symbol)
        except Exception:
            info = None
        return info if info is not None else FundInfo.unavailable()
    ```
  - `_run_index(self, ticker, wrapper=Wrapper.SINGLE)`: vor dem `return` `fund = await self._fund_overlay(ticker, wrapper)` und im `BottomUpResult(..., fund_info=fund)` setzen.

- [ ] **Step 4: Run test to verify it passes** — PASS; Regression `python -m pytest tests/test_bottom_up_dispatch.py -q`.

- [ ] **Step 5: Commit** — `git commit -m "feat(fund): Info-Overlay bei wrapper=FUND im Index-Pfad"`

---

### Task 4: Volle Suite + PR

- [ ] Volle Suite `python -m pytest -q` (erwartet: grün außer den 2 vorbestehenden `test_routes_cockpit.py`-Isolationsfehlern).
- [ ] `git push -u origin feat/taxonomie-phase2b-fund` + `gh pr create` (Body: was/warum/wie, Hinweis auf die 2 vorbestehenden Cockpit-Fehler + dass die echte ETF-/Benchmark-Quelle eine eigene Slice ist).

---

## Self-Review (gegen §6.6 + §13.2)

- **TER als Kosten-Drag, ausgewiesen, fehlt → UNAVAILABLE** → `FundInfo.ter` (Task 2), Provider/Stub. ✓
- **Tracking-Error = stdev(R_etf−R_index) annualisiert; Benchmark nötig; unbekannt → nur Tracking-Error UNAVAILABLE, TER bleibt** → Task 1 (`None` bei fehlenden Reihen) + `FundInfo` trennt beide Felder. ✓
- **Nur `wrapper=fund`; andere unberührt; defensiv** → Task 3. ✓
- **Bewusst NICHT in 2b:** echte ETF-Stammdaten-/Benchmark-Quelle (Stub bleibt; eigene Slice), Look-Through/Holdings (separater Impact-Punkt G).
