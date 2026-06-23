# Short-Backtester (Shorts Block #4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Einen eigenen Short-Backtester bauen, der die Short-Entscheidungen (`short_action`) getrennt vom Long-Backtester benotet — mit gestaffelten Leih-Kosten, aufgeschlüsselt nach Short-Grund, Trefferquote neben Profit-Faktor inkl. Warn-Flag. Nur messen.

**Architecture:** Reine Backtest-Mathematik in `core/utils/short_backtest.py` (kein I/O, voll testbar), ein dünner `ShortBacktesterAgent` (lädt Historie → reine Funktionen → speichert Report), plus eine kleine Persistenz-Erweiterung (`short_meta jsonb`), damit Short-Grund/Konfidenz/Borrow-Flag überhaupt aufgezeichnet werden.

**Tech Stack:** Python 3.12, pytest, psycopg2 (Supabase), yfinance (nur im Default-Provider).

## Global Constraints

- **Sprache:** Code-Kommentare und Doc-Strings auf **Deutsch** (AGENTS.md §0).
- **Hexagonal:** Agent hängt nur am `MemoryPort` + injizierten Provider-Callables; kein direkter Adapter-Import (AGENTS.md §1).
- **TDD verpflichtend:** erst Test (Rot) → minimal implementieren → Grün → aufräumen (AGENTS.md §4).
- **Defensiv:** fehlende Daten → Eintrag überspringen, nie crashen.
- **Vorzeichen explizit, keine magischen Zahlen** ohne begründeten Kommentar (AGENTS.md §3).
- **Nur messen:** kein Zurückschreiben in `compute_confidence`/Engine.
- **Borrow-Startwerte:** normal `0.01` (1 %/J), hard-to-borrow `0.08` (8 %/J), anteilig `· tage/365`.
- **Warn-Schwellen:** Trefferquote `≥ 0.55` **und** Profit-Faktor `< 1.0`.

---

## File Structure

- **Create** `core/utils/short_backtest.py` — reine Funktionen: `borrow_cost`, `grade_entry`, `grade_exit`, `payoff_warning`, `aggregate_by_reason` + Konstanten.
- **Create** `agents/backtester/short_backtester_agent.py` — `ShortBacktesterAgent` (dünn, orchestriert).
- **Modify** `adapters/memory/supabase_memory.py` — `_build_short_meta`-Helfer + `short_meta` in den `save_analysis`-INSERT.
- **Create** `tests/utils/test_short_backtest.py` — Tests der reinen Funktionen.
- **Create** `tests/agents/backtester/test_short_backtester_agent.py` — Test des Agenten mit Fake-Memory.
- **Modify** `tests/adapters/memory/test_supabase_memory.py` (falls vorhanden, sonst neu) — Test für `_build_short_meta`.
- **Modify** `docs/open_todos.md` — Folge-Blöcke (Konflikt-Backtester, Kalibrierung-Rückspeisung) erfassen.

**Migration (manueller Deploy-Schritt, VOR Merge):**
```sql
ALTER TABLE analysis_memory ADD COLUMN short_meta jsonb DEFAULT '{}'::jsonb;
```

---

### Task 1: Persistenz — `short_meta` aufzeichnen

**Files:**
- Modify: `adapters/memory/supabase_memory.py` (INSERT in `save_analysis`, ~`:167-204`)
- Test: `tests/adapters/memory/test_supabase_memory.py`

**Interfaces:**
- Produces: `_build_short_meta(short_assessment) -> dict` — modul-lokaler reiner Helfer; baut das jsonb-Dict. Liefert `{}` wenn `short_assessment is None`.

- [ ] **Step 1: Write the failing test**

In `tests/adapters/memory/test_supabase_memory.py` (neue Datei oder ans Ende anfügen):

```python
from types import SimpleNamespace
from adapters.memory.supabase_memory import _build_short_meta


def test_build_short_meta_full():
    sa = SimpleNamespace(
        archetypes=["distress", "valuation_extreme"],
        confidence=0.62,
        hard_to_borrow=True,
        squeeze_risk="elevated",
        borrow_rate_manual=0.05,
    )
    assert _build_short_meta(sa) == {
        "archetypes": ["distress", "valuation_extreme"],
        "confidence": 0.62,
        "hard_to_borrow": True,
        "squeeze_risk": "elevated",
        "borrow_rate_manual": 0.05,
    }


def test_build_short_meta_none_is_empty():
    assert _build_short_meta(None) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/adapters/memory/test_supabase_memory.py::test_build_short_meta_full -v`
Expected: FAIL mit `ImportError: cannot import name '_build_short_meta'`.

- [ ] **Step 3: Write minimal implementation**

In `adapters/memory/supabase_memory.py`, auf Modulebene (nahe den anderen Helfern):

```python
def _build_short_meta(short_assessment) -> dict:
    """Short-Metadaten für die Persistenz (jsonb): Grund/Konfidenz/Borrow-Flag.

    Wird vom Short-Backtester gelesen (Aufschlüsselung nach Grund + gestaffelte
    Leih-Kosten). Defensiv: ohne Assessment → leeres Dict.
    """
    if short_assessment is None:
        return {}
    return {
        "archetypes": short_assessment.archetypes,
        "confidence": short_assessment.confidence,
        "hard_to_borrow": short_assessment.hard_to_borrow,
        "squeeze_risk": short_assessment.squeeze_risk,
        "borrow_rate_manual": short_assessment.borrow_rate_manual,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/adapters/memory/test_supabase_memory.py -v`
Expected: PASS (beide Tests).

- [ ] **Step 5: Wire `short_meta` into the INSERT**

In `save_analysis`: die Spalte in die Spaltenliste (`INSERT INTO analysis_memory (...)`) **nach** `short_xai` aufnehmen, ein zusätzliches `%s` in `VALUES`, und in der Werte-Tupel-Reihenfolge ergänzen:

```python
# Spaltenliste: ..., short_xai, short_meta, price_at_analysis, ...
# VALUES: eine zusätzliche %s ergänzen
# Werte-Tupel, an gleicher Position:
json.dumps(_build_short_meta(result.short_assessment)),
```

(`json` ist in der Datei bereits importiert — vgl. `json.dumps(indicators)`.)

- [ ] **Step 6: Commit**

```bash
git add adapters/memory/supabase_memory.py tests/adapters/memory/test_supabase_memory.py
git commit -m "feat(memory): short_meta (Grund/Konfidenz/Borrow-Flag) persistieren fuer Short-Backtest"
```

---

### Task 2: Borrow-Modell (reine Funktion)

**Files:**
- Create: `core/utils/short_backtest.py`
- Test: `tests/utils/test_short_backtest.py`

**Interfaces:**
- Produces: `borrow_cost(hold_days: int, hard_to_borrow: bool, manual_rate: float | None = None) -> float` — anteilige Leih-Miete (Dezimal, ≥ 0). Konstanten `BORROW_RATE_NORMAL = 0.01`, `BORROW_RATE_HTB = 0.08`.

- [ ] **Step 1: Write the failing test**

In `tests/utils/test_short_backtest.py`:

```python
from core.utils.short_backtest import borrow_cost, BORROW_RATE_NORMAL, BORROW_RATE_HTB


def test_borrow_normal_prorated():
    # 1 %/Jahr über 365 Tage = 1 %
    assert borrow_cost(365, hard_to_borrow=False) == BORROW_RATE_NORMAL


def test_borrow_htb_higher():
    assert borrow_cost(365, hard_to_borrow=True) == BORROW_RATE_HTB


def test_borrow_manual_overrides():
    assert borrow_cost(365, hard_to_borrow=True, manual_rate=0.20) == 0.20


def test_borrow_zero_days():
    assert borrow_cost(0, hard_to_borrow=True) == 0.0


def test_borrow_prorated_half_year():
    assert borrow_cost(182, hard_to_borrow=False) == BORROW_RATE_NORMAL * (182 / 365.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/utils/test_short_backtest.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'core.utils.short_backtest'`.

- [ ] **Step 3: Write minimal implementation**

In `core/utils/short_backtest.py`:

```python
"""Reine Backtest-Mathematik für die Short-Entscheidungen (Shorts Block #4).

Kein I/O. Bewertet die Short-Calls (short_action) getrennt vom Long-Backtester:
gestaffelte Leih-Kosten, Einstieg-/Ausstieg-Benotung, Aufschlüsselung nach Grund,
Trefferquote vs. Profit-Faktor + Warn-Flag.
"""
from core.utils.backtest import MIN_SAMPLE, hit_rate_ci
from core.utils.performance_metrics import apply_costs, max_drawdown, profit_factor

# Leih-Miete p. a. (Dezimal) — begründete Startwerte (AGENTS.md §3):
# normal: breit verfügbare Titel ("general collateral") real ~0,3–1 %/Jahr.
BORROW_RATE_NORMAL: float = 0.01
# hard-to-borrow: real oft 5–20 %+/Jahr; 8 % als konservativer Mittelwert.
BORROW_RATE_HTB: float = 0.08


def borrow_cost(hold_days: int, hard_to_borrow: bool, manual_rate: float | None = None) -> float:
    """Anteilige Leih-Miete eines Shorts über die Haltedauer (Dezimal, ≥ 0).

    Manueller Satz schlägt den Proxy; sonst Staffel nach hard_to_borrow.
    """
    if hold_days <= 0:
        return 0.0
    if manual_rate is not None:
        rate = manual_rate
    elif hard_to_borrow:
        rate = BORROW_RATE_HTB
    else:
        rate = BORROW_RATE_NORMAL
    return rate * (hold_days / 365.0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/utils/test_short_backtest.py -v`
Expected: PASS (5 Tests).

- [ ] **Step 5: Commit**

```bash
git add core/utils/short_backtest.py tests/utils/test_short_backtest.py
git commit -m "feat(short-backtest): gestaffelte Borrow-Kosten (pure function)"
```

---

### Task 3: Benotung Einstieg + Ausstieg (reine Funktionen)

**Files:**
- Modify: `core/utils/short_backtest.py`
- Test: `tests/utils/test_short_backtest.py`

**Interfaces:**
- Consumes: `apply_costs` (aus `core.utils.performance_metrics`, bereits importiert in Task 2).
- Produces:
  - `grade_entry(adj_return: float, borrow: float, cost_per_side: float = 0.0005) -> tuple[bool, float]` → `(correct, short_payoff)`.
  - `grade_exit(post_adj_return: float) -> tuple[bool, float]` → `(correct, payoff)`.

- [ ] **Step 1: Write the failing test**

Ans Ende von `tests/utils/test_short_backtest.py`:

```python
from core.utils.short_backtest import grade_entry, grade_exit


def test_grade_entry_correct_when_stock_fell():
    # Aktie fiel 10 % (adj=-0.10); Short-Ertrag = +0.10 - Kosten - Borrow > 0
    correct, payoff = grade_entry(-0.10, borrow=0.0, cost_per_side=0.0)
    assert correct is True
    assert payoff == 0.10


def test_grade_entry_borrow_can_flip_to_wrong():
    # Aktie fiel nur 0,5 % (adj=-0.005), aber Borrow 1 % frisst den Gewinn
    correct, payoff = grade_entry(-0.005, borrow=0.01, cost_per_side=0.0)
    assert correct is False
    assert payoff < 0


def test_grade_entry_break_even_is_not_correct():
    # Short-Ertrag exakt 0 → nicht korrekt (strikt > 0)
    correct, payoff = grade_entry(0.0, borrow=0.0, cost_per_side=0.0)
    assert correct is False
    assert payoff == 0.0


def test_grade_exit_correct_when_stock_rose_after_cover():
    # Nach dem Cover stieg die Aktie 8 % → Ausstieg vermied Verlust → korrekt
    correct, payoff = grade_exit(0.08)
    assert correct is True
    assert payoff == 0.08


def test_grade_exit_wrong_when_stock_kept_falling():
    correct, payoff = grade_exit(-0.04)
    assert correct is False
    assert payoff == -0.04
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/utils/test_short_backtest.py -k "grade" -v`
Expected: FAIL mit `ImportError: cannot import name 'grade_entry'`.

- [ ] **Step 3: Write minimal implementation**

Ans Ende von `core/utils/short_backtest.py`:

```python
def grade_entry(adj_return: float, borrow: float, cost_per_side: float = 0.0005) -> tuple[bool, float]:
    """SHORT/SHORT_PLUS: korrekt, wenn die Aktie netto FIEL.

    short_payoff = -(marktbereinigter Return) - Transaktionskosten - Leih-Miete.
    Fällt die Aktie (adj < 0), ist -adj > 0 → Gewinn, minus Kosten/Borrow.
    """
    short_payoff = apply_costs(-adj_return, cost_per_side) - borrow
    return (short_payoff > 0, short_payoff)


def grade_exit(post_adj_return: float) -> tuple[bool, float]:
    """COVER: korrekt, wenn die Aktie NACH dem Cover STIEG (Verlust vermieden).

    payoff = vermiedener Verlust = marktbereinigter Return nach dem Cover.
    Keine Leih-Miete (Position ist flach), kein Round-Trip-Kostenabzug
    (kontrafaktische Mess-Größe, kein realisierter Trade).
    """
    return (post_adj_return > 0, post_adj_return)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/utils/test_short_backtest.py -v`
Expected: PASS (alle Tests).

- [ ] **Step 5: Commit**

```bash
git add core/utils/short_backtest.py tests/utils/test_short_backtest.py
git commit -m "feat(short-backtest): Einstieg-/Ausstieg-Benotung (pure functions)"
```

---

### Task 4: Aggregation nach Grund + Warn-Flag (reine Funktionen)

**Files:**
- Modify: `core/utils/short_backtest.py`
- Test: `tests/utils/test_short_backtest.py`

**Interfaces:**
- Consumes: `MIN_SAMPLE`, `hit_rate_ci`, `profit_factor`, `max_drawdown` (bereits importiert in Task 2).
- Produces:
  - `payoff_warning(hit_rate: float | None, pf: float) -> bool`. Konstanten `PAYOFF_WARN_HIT_RATE = 0.55`, `PAYOFF_WARN_PROFIT_FACTOR = 1.0`.
  - `aggregate_by_reason(graded: list[dict]) -> dict[str, dict]` — `graded`-Elemente: `{"archetypes": list[str], "correct": bool, "payoff": float}`. Bucket-Werte: `{"n", "hit_rate", "ci_low", "ci_high", "mean_payoff", "profit_factor", "max_drawdown", "warning"}`.

- [ ] **Step 1: Write the failing test**

Ans Ende von `tests/utils/test_short_backtest.py`:

```python
from core.utils.short_backtest import aggregate_by_reason, payoff_warning


def test_payoff_warning_high_hitrate_but_losing():
    assert payoff_warning(0.55, 0.9) is True      # exakt an der Schwelle, PF < 1


def test_payoff_warning_off_when_profitable():
    assert payoff_warning(0.80, 1.0) is False      # PF == 1.0 → keine Warnung


def test_payoff_warning_off_when_hitrate_unknown():
    assert payoff_warning(None, 0.1) is False      # n < MIN_SAMPLE → keine Warnung


def test_aggregate_splits_by_archetype_and_counts_each():
    graded = [
        {"archetypes": ["distress", "valuation_extreme"], "correct": True, "payoff": 0.05},
        {"archetypes": ["distress"], "correct": False, "payoff": -0.03},
    ]
    out = aggregate_by_reason(graded)
    assert out["distress"]["n"] == 2
    assert out["valuation_extreme"]["n"] == 1


def test_aggregate_empty_archetypes_bucket():
    out = aggregate_by_reason([{"archetypes": [], "correct": True, "payoff": 0.02}])
    assert "(ohne Grund)" in out
    assert out["(ohne Grund)"]["n"] == 1


def test_aggregate_below_min_sample_hides_hitrate():
    out = aggregate_by_reason([{"archetypes": ["x"], "correct": True, "payoff": 0.02}])
    assert out["x"]["hit_rate"] is None        # n=1 < MIN_SAMPLE
    assert out["x"]["mean_payoff"] == 0.02
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/utils/test_short_backtest.py -k "aggregate or warning" -v`
Expected: FAIL mit `ImportError: cannot import name 'aggregate_by_reason'`.

- [ ] **Step 3: Write minimal implementation**

Ans Ende von `core/utils/short_backtest.py`:

```python
PAYOFF_WARN_HIT_RATE: float = 0.55       # "oft recht"
PAYOFF_WARN_PROFIT_FACTOR: float = 1.0   # aber unterm Strich Verlust
_NO_REASON = "(ohne Grund)"


def payoff_warning(hit_rate: float | None, pf: float) -> bool:
    """True, wenn oft recht (≥ 55 %) ABER Profit-Faktor < 1 (Squeeze-Asymmetrie)."""
    if hit_rate is None:
        return False
    return hit_rate >= PAYOFF_WARN_HIT_RATE and pf < PAYOFF_WARN_PROFIT_FACTOR


def aggregate_by_reason(graded: list[dict]) -> dict[str, dict]:
    """Je Short-Grund (Archetyp) ein Bucket mit Kennzahlen.

    Ein Eintrag mit mehreren Archetypen zählt in JEDEN zugehörigen Bucket;
    leere Archetypen → Bucket "(ohne Grund)". Trefferquote erst ab MIN_SAMPLE.
    """
    buckets: dict[str, list[dict]] = {}
    for g in graded:
        for reason in (g.get("archetypes") or [_NO_REASON]):
            buckets.setdefault(reason, []).append(g)

    out: dict[str, dict] = {}
    for reason, items in buckets.items():
        n = len(items)
        payoffs = [it["payoff"] for it in items]
        correct = sum(1 for it in items if it["correct"])
        if n >= MIN_SAMPLE:
            hit = round(correct / n, 3)
            lo, hi = hit_rate_ci(correct, n)
        else:
            hit, lo, hi = None, None, None
        pf = profit_factor(payoffs)   # kann float("inf") sein (keine Verluste)
        out[reason] = {
            "n": n,
            "hit_rate": hit,
            "ci_low": lo,
            "ci_high": hi,
            "mean_payoff": round(sum(payoffs) / n, 4) if n else 0.0,
            "profit_factor": None if pf == float("inf") else round(pf, 3),
            "max_drawdown": round(max_drawdown(payoffs), 3),
            "warning": payoff_warning(hit, pf),
        }
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/utils/test_short_backtest.py -v`
Expected: PASS (alle Tests).

- [ ] **Step 5: Commit**

```bash
git add core/utils/short_backtest.py tests/utils/test_short_backtest.py
git commit -m "feat(short-backtest): Aggregation nach Grund + Trefferquote-vs-Payoff-Warnung"
```

---

### Task 5: `ShortBacktesterAgent` (dünn, orchestriert)

**Files:**
- Create: `agents/backtester/short_backtester_agent.py`
- Test: `tests/agents/backtester/test_short_backtester_agent.py`

**Interfaces:**
- Consumes: `MemoryPort.load_global_history(days) -> list[dict]`, `MemoryPort.save_backtester_report(dict)`; `borrow_cost`, `grade_entry`, `grade_exit`, `aggregate_by_reason` (Tasks 2–4); `forward_return`, `market_adjusted_return`, `HORIZONS_DAYS` (`core.utils.backtest`); Default-Provider `_default_price_on_horizon`, `_default_benchmark_return` (`agents.backtester.bottom_up_backtester_agent`).
- Produces: `ShortBacktesterAgent(memory, price_on_horizon=..., benchmark_return=..., cost_per_side=0.0005)` mit `async def run() -> None`.

- [ ] **Step 1: Write the failing test**

In `tests/agents/backtester/test_short_backtester_agent.py`:

```python
import asyncio
from datetime import datetime, timedelta, timezone

from agents.backtester.short_backtester_agent import ShortBacktesterAgent


class _FakeMemory:
    def __init__(self, rows):
        self._rows = rows
        self.reports = []

    def load_global_history(self, days=180):
        return self._rows

    def save_backtester_report(self, report):
        self.reports.append(report)


def _row(action, price, days_ago, meta, ticker="AAA"):
    return {
        "ticker": ticker,
        "short_action": action,
        "price_at_analysis": price,
        "market": "USA",
        "timestamp": datetime.now(timezone.utc) - timedelta(days=days_ago),
        "short_meta": meta,
    }


def test_short_entry_that_fell_is_graded_correct():
    rows = [_row("SHORT", 100.0, days_ago=40, meta={"archetypes": ["distress"]})]
    mem = _FakeMemory(rows)
    agent = ShortBacktesterAgent(
        mem,
        price_on_horizon=lambda t, d, h: 90.0,      # Aktie fiel 100 → 90
        benchmark_return=lambda m, d, h: 0.0,        # kein Markt-Drift
    )
    asyncio.run(agent.run())
    entry_reports = [r for r in mem.reports
                     if r["original_recommendation"] == "entry:distress"]
    assert len(entry_reports) == 1
    assert entry_reports[0]["return_pct"] > 0       # Short verdiente


def test_missing_forward_price_is_skipped_not_crash():
    rows = [_row("SHORT", 100.0, days_ago=40, meta={"archetypes": ["distress"]})]
    mem = _FakeMemory(rows)
    agent = ShortBacktesterAgent(
        mem,
        price_on_horizon=lambda t, d, h: None,       # kein Folgekurs
        benchmark_return=lambda m, d, h: 0.0,
    )
    asyncio.run(agent.run())                          # darf nicht crashen
    assert all(r["original_recommendation"] != "entry:distress" for r in mem.reports)


def test_hold_and_none_are_ignored():
    rows = [
        _row("HOLD", 100.0, days_ago=40, meta={"archetypes": ["x"]}),
        _row("NONE", 100.0, days_ago=40, meta={"archetypes": ["x"]}),
    ]
    mem = _FakeMemory(rows)
    agent = ShortBacktesterAgent(mem, price_on_horizon=lambda t, d, h: 90.0,
                                 benchmark_return=lambda m, d, h: 0.0)
    asyncio.run(agent.run())
    assert mem.reports == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agents/backtester/test_short_backtester_agent.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'agents.backtester.short_backtester_agent'`.

- [ ] **Step 3: Write minimal implementation**

In `agents/backtester/short_backtester_agent.py`:

```python
"""ShortBacktesterAgent — benotet die Short-Entscheidungen (short_action) getrennt.

Geschwister zum JudgmentBacktesterAgent, anderes Prüf-Subjekt: hier zählt die
Trade-Entscheidung des Short-Motors (Einstieg SHORT/SHORT+, Ausstieg COVER) —
mit Leih-Kosten, aufgeschlüsselt nach Grund. Nur messen, kein Zurückschreiben.
"""
import json
from datetime import datetime, timezone
from typing import Callable, Optional

from core.ports.memory_port import MemoryPort
from core.utils.backtest import HORIZONS_DAYS, forward_return, market_adjusted_return
from core.utils.short_backtest import (
    aggregate_by_reason, borrow_cost, grade_entry, grade_exit,
)
from agents.backtester.bottom_up_backtester_agent import (
    _default_benchmark_return, _default_price_on_horizon,
)

_ENTRY_ACTIONS = {"SHORT", "SHORT+"}
_EXIT_ACTIONS = {"COVER"}


def _parse_meta(raw) -> dict:
    """short_meta kommt als dict (psycopg2-jsonb) oder str — defensiv beides."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}
    return {}


class ShortBacktesterAgent:
    def __init__(
        self,
        memory: MemoryPort,
        price_on_horizon: Callable[[str, datetime, int], Optional[float]] = _default_price_on_horizon,
        benchmark_return: Callable[[str, datetime, int], Optional[float]] = _default_benchmark_return,
        cost_per_side: float = 0.0005,
    ):
        self.memory = memory
        self.price_on_horizon = price_on_horizon
        self.benchmark_return = benchmark_return
        self.cost_per_side = cost_per_side

    async def run(self) -> None:
        history = self.memory.load_global_history(days=180)
        now = datetime.now(timezone.utc)
        entries: list[dict] = []
        exits: list[dict] = []

        for h in history:
            action = h.get("short_action")
            ticker = h.get("ticker")
            price_then = h.get("price_at_analysis")
            entry_date = h.get("timestamp")
            if not (ticker and price_then and entry_date
                    and action in (_ENTRY_ACTIONS | _EXIT_ACTIONS)):
                continue

            age_days = (now - entry_date).days
            horizon = max((d for d in HORIZONS_DAYS if d <= age_days), default=None)
            if horizon is None:
                continue

            fwd_px = self.price_on_horizon(ticker, entry_date, horizon)
            raw = forward_return(float(price_then), fwd_px)
            if raw is None:
                continue
            bench = self.benchmark_return(h.get("market", "USA"), entry_date, horizon)
            adj = market_adjusted_return(raw, bench)

            meta = _parse_meta(h.get("short_meta"))
            archetypes = meta.get("archetypes") or []

            if action in _ENTRY_ACTIONS:
                borrow = borrow_cost(horizon, bool(meta.get("hard_to_borrow")),
                                     meta.get("borrow_rate_manual"))
                correct, payoff = grade_entry(adj, borrow, self.cost_per_side)
                entries.append({"archetypes": archetypes, "correct": correct, "payoff": payoff})
            else:  # COVER
                correct, payoff = grade_exit(adj)
                exits.append({"archetypes": archetypes, "correct": correct, "payoff": payoff})

        self._save_section("entry", aggregate_by_reason(entries))
        self._save_section("exit", aggregate_by_reason(exits))
        print(f"[ShortBacktester] Einstiege: {len(entries)} | Ausstiege: {len(exits)}")

    def _save_section(self, section: str, buckets: dict) -> None:
        for reason, m in buckets.items():
            self.memory.save_backtester_report({
                "backtester_type": "short",
                "ticker": None,
                "original_recommendation": f"{section}:{reason}",
                "price_at_recommendation": None,
                "price_today": None,
                "return_pct": round(m["mean_payoff"] * 100, 2),
                "verdict": "WARN-payoff" if m["warning"] else None,
                "accuracy_30d": None, "accuracy_60d": None, "accuracy_90d": None,
                "notes": (f"N={m['n']} | Hit={m['hit_rate']} "
                          f"[{m['ci_low']}–{m['ci_high']}] | PF={m['profit_factor']} "
                          f"| MaxDD={m['max_drawdown']} | Warnung={m['warning']}"),
            })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agents/backtester/test_short_backtester_agent.py -v`
Expected: PASS (3 Tests).

- [ ] **Step 5: Run the focused suite**

Run: `python -m pytest tests/utils/test_short_backtest.py tests/agents/backtester/test_short_backtester_agent.py -q`
Expected: alle grün.

- [ ] **Step 6: Commit**

```bash
git add agents/backtester/short_backtester_agent.py tests/agents/backtester/test_short_backtester_agent.py
git commit -m "feat(short-backtest): ShortBacktesterAgent (Einstiege+Ausstiege, nur messen)"
```

---

### Task 6: Logbuch — Folge-Blöcke erfassen

**Files:**
- Modify: `docs/open_todos.md` (§9, beim Short-Backtest-/Block-#4-Eintrag)

**Interfaces:** keine (reine Doku).

- [ ] **Step 1: Folge-Aufgaben ergänzen**

Beim Block-#4-Eintrag in `docs/open_todos.md` §9 notieren (noch **nicht** abhaken — das ist Teil des PR-Protokolls nach dem Merge):

```markdown
- [ ] **Konflikt-Backtester (eigener Block)** — bewertet `conflict_resolution` (war der erkannte
  Konflikt richtig + gut aufgelöst?), nicht `short_action`. Anderes Prüf-Subjekt als der
  Short-Backtester. Speist später die Kalibrierung des Konflikt-Agenten.
- [ ] **Short-Konfidenz-Kalibrierung (Rückspeisung)** — die per-Grund-Buckets des Short-Backtesters
  in `compute_confidence` zurückführen (ändert lebendes Verhalten → eigener geprüfter Schritt,
  Disziplin wie Regime-Backtest ②: erst messen, dann anwenden).
```

- [ ] **Step 2: Commit**

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): Konflikt-Backtester + Short-Konfidenz-Kalibrierung als Folge-Bloecke"
```

---

## Self-Review

**1. Spec coverage:**
- §2.1 Persistenz `short_meta` → Task 1 ✅
- §2.2 reine Mathematik (borrow, grade, aggregate, warning) → Tasks 2–4 ✅
- §2.3 dünner Agent (nur messen) → Task 5 ✅
- §4 Borrow-Staffel + manuell + anteilig + keine Borrow auf Cover → Task 2 (`borrow_cost`) + Task 5 (Cover ruft kein `borrow_cost`) ✅
- §5 Benotungsregeln Einstieg/Ausstieg, Vorzeichen → Task 3 ✅
- §6 Aufschlüsselung nach Grund, Kennzahlen, Warn-Flag, MIN_SAMPLE, Buckets → Task 4 + Task 5 (`_save_section`) ✅
- §7 short_meta-Felder aus `short_assessment` → Task 1 (`_build_short_meta`) ✅
- §9 Fehlerpfade (überspringen statt Crash) + Grenzfälle → Task 5 (skip-Test) + Tasks 2–4 (Grenzfall-Tests) ✅
- §10 Logbuch Folge-Blöcke → Task 6 ✅
- Migration `ALTER TABLE` → File Structure + Task 1 (Deploy-Hinweis) ✅

**2. Placeholder scan:** keine TBD/TODO/„handle edge cases"; jeder Code-Step zeigt vollständigen Code. ✅

**3. Type consistency:** `aggregate_by_reason` liefert Buckets mit Keys `n/hit_rate/ci_low/ci_high/mean_payoff/profit_factor/max_drawdown/warning`; Task 5 `_save_section` liest exakt diese Keys. `grade_entry`/`grade_exit` liefern `(bool, float)`, in Task 5 als `(correct, payoff)` entpackt und in `{"correct","payoff","archetypes"}` gelegt — passt zum `graded`-Format, das `aggregate_by_reason` erwartet. ✅
