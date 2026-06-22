# SHORT+-Aktivierung Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die ungenutzte `ShortAction.SHORT_PLUS` aktivieren — in einen Gewinner-Short nachlegen, symmetrisch zu BUY+, mit Profit- (≥5 %) und Squeeze-Gate.

**Architecture:** Reine Signal-Logik in `core/domain/short_assessment.py` (Engine) + P&L-Beschaffung in der Judgment-Schicht über den injizierten `PortfolioPort` (DI-Kette Orchestrator→Chief→Agent). Engine bleibt pure function; I/O (Depot-Lookup) bleibt in der Agenten-Schicht (Hexagonal).

**Tech Stack:** Python, pytest.

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-21-short-plus-design.md`.
- TDD Pflicht (erst roter Test). Deutsche Code-Kommentare. Type Hints. LLM in Tests immer gemockt.
- Branch `feat/short-plus` (Worktree `.claude/worktrees/short-plus`). PR-First — **nicht** mergen.
- Runner: `python -m pytest -q`. SHORT+ nur Equity. Defensiv: fehlende Daten → `None` → HOLD (kein Crash).
- `_THRESHOLD = 0.50` (unverändert), `_SHORT_PLUS_MIN_PROFIT_PCT = 5.0`, SHORT+-Tranche `= _position_size_pct(conf) · 0.25`.

---

## Task 1: Engine — SHORT_PLUS-Aktion + Sizing

**Files:**
- Modify: `core/domain/short_assessment.py`
- Test: `tests/test_short_assessment_engine.py`

**Interfaces:**
- Produces: `derive_short_assessment(bottom_up, cockpit, current_position, top_down_available, bu_anomaly, td_anomaly, position_pnl_pct: float | None = None) -> ShortAssessment` (neuer letzter Parameter, default `None`).
- Consumes: bestehende `_position_size_pct` (aus `core.domain.recommendation`), `ShortAction.SHORT_PLUS`.

- [ ] **Step 1: Failing tests** — in `tests/test_short_assessment_engine.py` ergänzen (oben den Import erweitern):

```python
from core.domain.recommendation import _position_size_pct

_STRONG = dict(quality=NS(altman_z=1.0, interest_coverage=0.5, fcf_margin=-5.0,
                          debt_to_equity=2.0, current_ratio=0.8),
               earnings_trend=NS(estimate_revision="down", beat_rate=0.3))


def test_short_plus_when_winning_and_thesis_holds():
    a = _run(_bu(**_STRONG), pos=PositionState.SHORT, pnl=6.0)
    assert a.short_action == ShortAction.SHORT_PLUS
    assert a.suggested_size_pct == round(_position_size_pct(a.confidence) * 0.25, 1)
    assert a.stop_pct == 15.0


def test_short_plus_boundary_exactly_5pct():
    assert _run(_bu(**_STRONG), pos=PositionState.SHORT, pnl=5.0).short_action == ShortAction.SHORT_PLUS
    assert _run(_bu(**_STRONG), pos=PositionState.SHORT, pnl=4.9).short_action == ShortAction.HOLD


def test_short_plus_none_pnl_holds():
    assert _run(_bu(**_STRONG), pos=PositionState.SHORT, pnl=None).short_action == ShortAction.HOLD


def test_short_plus_blocked_by_high_squeeze():
    # squeeze "high" via short_float ≥ 20 (dtc < 8 → kein htb-Konfidenzabzug, conf bleibt ≥ 0.50)
    bu = _bu(**_STRONG, short_interest=NS(days_to_cover=3, short_float_pct=25.0))
    assert _run(bu, pos=PositionState.SHORT, pnl=8.0).short_action == ShortAction.HOLD


def test_short_plus_weak_thesis_still_covers():
    # conf < 0.50 → COVER, egal ob im Gewinn (pnl wird nur im "These gilt weiter"-Zweig geprüft)
    assert _run(_bu(), pos=PositionState.SHORT, pnl=20.0).short_action == ShortAction.COVER
```

Und den `_run`-Helfer um `pnl` erweitern (bestehende Aufrufe bleiben kompatibel, da `pnl` default `None`):

```python
def _run(bu, pos=PositionState.NONE, cockpit=None, td=True, bua=_NA, tda=_NA, pnl=None):
    return derive_short_assessment(bu, cockpit, pos, td, bua, tda, position_pnl_pct=pnl)
```

- [ ] **Step 2: Run → FAIL**

Run: `python -m pytest tests/test_short_assessment_engine.py -q`
Expected: FAIL (`derive_short_assessment() got an unexpected keyword argument 'position_pnl_pct'` bzw. SHORT_PLUS wird nicht erzeugt).

- [ ] **Step 3: Implement** — in `core/domain/short_assessment.py`:

Konstante neben `_THRESHOLD`:
```python
_SHORT_PLUS_MIN_PROFIT_PCT = 5.0   # SHORT+ nur in einen klaren Gewinner-Short (Kurs ~5 %+ unter Einstand)
```

`_action` erweitern (Profit-/Squeeze-Gates nur im "These gilt weiter"-Zweig):
```python
def _action(pos, confidence, pnl_pct=None, squeeze="low") -> ShortAction:
    if pos == PositionState.LONG:
        return ShortAction.NONE
    if pos == PositionState.SHORT:
        if confidence < _THRESHOLD:
            return ShortAction.COVER          # These gebrochen
        # These gilt weiter — nur in einen Gewinner nachlegen, nie in einen Squeeze:
        if pnl_pct is not None and pnl_pct >= _SHORT_PLUS_MIN_PROFIT_PCT and squeeze != "high":
            return ShortAction.SHORT_PLUS
        return ShortAction.HOLD
    return ShortAction.SHORT if confidence >= _THRESHOLD else ShortAction.NONE
```

Signatur + Durchreichen + Sizing in `derive_short_assessment` (nur die `_action`-Zeile und der Sizing-Block ändern sich; der Fallback-`_action(current_position, conf)` ohne Kern-These bleibt unverändert — Default `pnl_pct=None` → dort weiter COVER/HOLD wie bisher):
```python
def derive_short_assessment(bottom_up, cockpit, current_position,
                            top_down_available, bu_anomaly, td_anomaly,
                            position_pnl_pct=None) -> ShortAssessment:
    ...
    action = _action(current_position, conf, position_pnl_pct, squeeze)
    size = None
    if action == ShortAction.SHORT:
        size = round(_position_size_pct(conf) * 0.5, 1)
        if squeeze == "high":
            size = round(size * 0.5, 1)
    elif action == ShortAction.SHORT_PLUS:
        size = round(_position_size_pct(conf) * 0.25, 1)   # konservativer Top-up (halbe Erst-Tranche)
    stop = 10.0 if squeeze == "high" else 15.0
    return _mk(asset_class, action, conf, archetypes, details, regime, squeeze, htb, size, stop)
```

- [ ] **Step 4: Run → PASS**

Run: `python -m pytest tests/test_short_assessment_engine.py -q`
Expected: PASS (neue + alle bestehenden Engine-Tests grün; `test_short_held_strong_holds_weak_covers` bleibt grün, da ohne `pnl` → `None` → HOLD).

- [ ] **Step 5: Commit**

```bash
git add core/domain/short_assessment.py tests/test_short_assessment_engine.py
git commit -m "feat(short): SHORT_PLUS-Aktion (Profit+Squeeze-Gate) + konservatives Sizing"
```

---

## Task 2: Judgment-Agent — P&L-Helfer + Port-DI

**Files:**
- Modify: `agents/judgment/judgment_agent.py`
- Test: `tests/test_chief_agents_judgment.py`

**Interfaces:**
- Produces: Modul-Funktion `_short_position_pnl_pct(port, ticker, position, bottom_up) -> float | None`; `JudgmentAgent.__init__(self, llm, bus, portfolio_port=None)` mit Attribut `self.portfolio_port`.
- Consumes: `core.domain.portfolio.PortfolioError`, `core.ports.portfolio_port.PortfolioPort`, `derive_short_assessment(..., position_pnl_pct=...)` (Task 1).

- [ ] **Step 1: Failing tests** — in `tests/test_chief_agents_judgment.py` ergänzen:

```python
from types import SimpleNamespace as NS
from core.domain.models import PositionState
from core.domain.portfolio import PortfolioError
from agents.judgment.judgment_agent import _short_position_pnl_pct


def _port(positions):
    return NS(get_positions=lambda: positions)


def _bu_price(cur):
    return NS(valuation_range=NS(current_price=cur))


def test_pnl_short_in_profit():
    port = _port([NS(ticker="AAPL", direction="short", entry_price=100.0)])
    assert _short_position_pnl_pct(port, "AAPL", PositionState.SHORT, _bu_price(90.0)) == 10.0


def test_pnl_none_when_not_short():
    port = _port([NS(ticker="AAPL", direction="short", entry_price=100.0)])
    assert _short_position_pnl_pct(port, "AAPL", PositionState.NONE, _bu_price(90.0)) is None


def test_pnl_none_when_no_port():
    assert _short_position_pnl_pct(None, "AAPL", PositionState.SHORT, _bu_price(90.0)) is None


def test_pnl_none_when_ticker_absent():
    port = _port([NS(ticker="MSFT", direction="short", entry_price=100.0)])
    assert _short_position_pnl_pct(port, "AAPL", PositionState.SHORT, _bu_price(90.0)) is None


def test_pnl_none_when_no_current_price():
    port = _port([NS(ticker="AAPL", direction="short", entry_price=100.0)])
    assert _short_position_pnl_pct(port, "AAPL", PositionState.SHORT, NS(valuation_range=None)) is None


def test_pnl_none_on_portfolio_error():
    def _raise():
        raise PortfolioError("bad")
    assert _short_position_pnl_pct(NS(get_positions=_raise), "AAPL", PositionState.SHORT, _bu_price(90.0)) is None
```

- [ ] **Step 2: Run → FAIL**

Run: `python -m pytest tests/test_chief_agents_judgment.py -q`
Expected: FAIL (`ImportError: cannot import name '_short_position_pnl_pct'`).

- [ ] **Step 3: Implement** — in `agents/judgment/judgment_agent.py`:

Importe ergänzen (zu den bestehenden `core.domain`-Importen):
```python
from core.domain.portfolio import PortfolioError
from core.ports.portfolio_port import PortfolioPort
```

Modul-Funktion (oberhalb der Klasse `JudgmentAgent`):
```python
def _short_position_pnl_pct(port, ticker: str, position: PositionState, bottom_up) -> float | None:
    """P&L-% einer gehaltenen Short-Position (Gewinn, wenn der Kurs unter den Einstand fällt).
    Defensiv: fehlt Port/Position/Einstand/Kurs oder wirft das Depot → None (→ kein SHORT+)."""
    if position != PositionState.SHORT or port is None:
        return None
    vr = getattr(bottom_up, "valuation_range", None)
    cur = getattr(vr, "current_price", None) if vr else None
    if cur is None:
        return None
    try:
        for p in port.get_positions():
            if p.ticker == ticker and p.direction == "short" and p.entry_price > 0:
                return (p.entry_price - cur) / p.entry_price * 100
    except PortfolioError:
        return None
    return None
```

Konstruktor um den Port erweitern:
```python
    def __init__(self, llm: LLMProvider, bus: EventBus, portfolio_port: PortfolioPort | None = None):
        self.llm = llm
        self.bus = bus
        self.portfolio_port = portfolio_port
```

In `run(...)` den `derive_short_assessment`-Aufruf (heute Z. 177-179) ersetzen:
```python
        position_pnl_pct = _short_position_pnl_pct(
            self.portfolio_port, ticker, current_position, bottom_up)
        short_assessment = derive_short_assessment(
            bottom_up, cockpit, current_position, top_down_available,
            bottom_up_anomaly, top_down_anomaly, position_pnl_pct=position_pnl_pct)
```

- [ ] **Step 4: Run → PASS**

Run: `python -m pytest tests/test_chief_agents_judgment.py -q`
Expected: PASS (neue + bestehende Tests grün).

- [ ] **Step 5: Commit**

```bash
git add agents/judgment/judgment_agent.py tests/test_chief_agents_judgment.py
git commit -m "feat(short): Short-P&L aus dem Depot (PortfolioPort) in der Judgment-Schicht"
```

---

## Task 3: Port-Verdrahtung (Chief→Orchestrator→app/main) + Regression

**Files:**
- Modify: `agents/judgment_chief_agent.py`, `orchestrators/judgment_orchestrator.py`, `app/main.py`
- Test: `tests/test_chief_agents_judgment.py`

**Interfaces:**
- Consumes: `JudgmentAgent(llm, bus, portfolio_port)` (Task 2).
- Produces: `JudgmentChiefAgent.__init__(self, llm, bus, portfolio_port=None)`, `JudgmentOrchestrator.__init__(self, llm, bus, memory, portfolio_port=None)`; `app/main.py` injiziert `JsonPortfolioProvider()`.

- [ ] **Step 1: Failing tests** — in `tests/test_chief_agents_judgment.py` ergänzen:

```python
def test_portfolio_port_wired_chief_to_agent():
    from agents.judgment_chief_agent import JudgmentChiefAgent
    sentinel = object()
    chief = JudgmentChiefAgent(NS(), NS(), portfolio_port=sentinel)
    assert chief.judgment_agent.portfolio_port is sentinel


def test_portfolio_port_wired_orchestrator_to_agent():
    from orchestrators.judgment_orchestrator import JudgmentOrchestrator
    sentinel = object()
    orch = JudgmentOrchestrator(NS(), NS(), NS(), portfolio_port=sentinel)
    assert orch.judgment_chief.judgment_agent.portfolio_port is sentinel
```

- [ ] **Step 2: Run → FAIL**

Run: `python -m pytest tests/test_chief_agents_judgment.py -k portfolio_port_wired -q`
Expected: FAIL (`JudgmentChiefAgent.__init__() got an unexpected keyword argument 'portfolio_port'`).

- [ ] **Step 3: Implement**

`agents/judgment_chief_agent.py` (Z. 9-11):
```python
    def __init__(self, llm: LLMProvider, bus: EventBus, portfolio_port=None):
        ...
        self.judgment_agent = JudgmentAgent(llm, bus, portfolio_port)
```
(Die übrigen `__init__`-Zeilen unverändert lassen; nur den Parameter ergänzen und an `JudgmentAgent` durchreichen.)

`orchestrators/judgment_orchestrator.py` (Z. 5-8):
```python
    def __init__(self, llm: LLMProvider, bus: EventBus, memory: MemoryPort, portfolio_port=None):
        ...
        self.judgment_chief   = JudgmentChiefAgent(llm, bus, portfolio_port)
```
(Nur Parameter + Durchreichen; restliche Konstruktor-Zeilen unverändert.)

`app/main.py` (Z. 140) — `JsonPortfolioProvider` injizieren. Import ist in 3a bereits vorhanden (sonst ergänzen: `from adapters.persistence.json_portfolio import JsonPortfolioProvider`):
```python
    orch   = JudgmentOrchestrator(llm, bus, memory, portfolio_port=JsonPortfolioProvider())
```

- [ ] **Step 4: Run → PASS (Verdrahtung)**

Run: `python -m pytest tests/test_chief_agents_judgment.py -k portfolio_port_wired -q`
Expected: PASS.

- [ ] **Step 5: Gesamt-Regression**

Run: `python -m pytest -q`
Expected: 0 failed (~3 Min). Bei Fehlern: superpowers:systematic-debugging — Ursache beheben.

- [ ] **Step 6: Commit**

```bash
git add agents/judgment_chief_agent.py orchestrators/judgment_orchestrator.py app/main.py tests/test_chief_agents_judgment.py
git commit -m "feat(short): PortfolioPort durch Judgment-Kette verdrahtet (SHORT+ produktiv) + Regression gruen"
```

---

## Abdeckung (Spec → Task)
| Spec-Element | Task |
|---|---|
| SHORT_PLUS-Verhalten (conf/pnl/squeeze-Gates) | 1 |
| Tranche `·0,25`, Stop 15 | 1 |
| `position_pnl_pct`-Param, verhaltens-erhaltender Default | 1 |
| P&L aus Depot (Port-Lookup + `valuation_range.current_price`, Short-invertiert) | 2 |
| Defensiv (kein Port/Einstand/Kurs/`PortfolioError` → None → HOLD) | 2 |
| Port-DI-Kette Orchestrator→Chief→Agent + Bau-Ort | 3 |
| Regression grün | 3 |

## Self-Review (durchgeführt)
- **Spec-Abdeckung:** alle Akzeptanzkriterien (§8) auf Tasks abgebildet (s. Tabelle). ✅
- **Platzhalter:** keine — vollständiger Code je Step; Pfade/Signaturen aus dem Code gepinnt (`app/main.py:140`, Chief/Orchestrator-Konstruktoren, `valuation_range.current_price`). ✅
- **Typ-Konsistenz:** `_short_position_pnl_pct(port, ticker, position, bottom_up) -> float | None` einheitlich in Task 2 (def) und Task 3-Tests; `position_pnl_pct`-Default `None` in Task 1 (def) und Task 2 (Aufruf); `portfolio_port`-Default `None` durch alle Konstruktoren (kein Bruch bestehender Bauten/Tests). ✅
