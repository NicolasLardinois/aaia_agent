# Konflikt-Backtester Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Einen eigenen Konflikt-Backtester bauen, der die Verdikte des Konflikt-Agenten (`HOLD`/`EXIT`/`REVERSE` aus der `conflicts`-Tabelle) rückblickend gegen die Kursrealität der gehaltenen Position benotet — je Verdikt-Typ, nur messen.

**Architecture:** Reine Mathematik in `core/utils/conflict_backtest.py` (kein I/O), ein dünner `ConflictBacktesterAgent` (lädt Konflikte über den `ConflictStorePort`, benotet, speichert Report über `MemoryPort`), die Aggregation aus `core/utils/short_backtest.py` **wiederverwendet**. Eine kleine Port-Methode `load_for_backtest`; keine DB-Migration.

**Tech Stack:** Python 3.12, pytest, psycopg2 (Supabase), yfinance (nur im Default-Provider).

## Global Constraints

- **Sprache:** Code-Kommentare/Doc-Strings **Deutsch** (AGENTS.md §0).
- **Hexagonal:** Agent hängt nur an `ConflictStorePort` + `MemoryPort` + injizierten Callables; kein `adapters/`-Import. Reine Mathe in `core/utils/` ohne I/O.
- **TDD verpflichtend:** erst Test (Rot) → minimal → Grün → aufräumen.
- **Defensiv:** fehlende/unreife Daten → Eintrag überspringen, nie crashen.
- **Vorzeichen explizit, keine magischen Zahlen** ohne Begründung (AGENTS.md §3).
- **Benotung:** `r = held_return(direction, adj)` (long → `adj`, short → `−adj`). **HOLD** korrekt ⟺ `r > 0` (Auszahlung `r`); **EXIT** korrekt ⟺ `r < 0` (Auszahlung `−r`); **REVERSE** korrekt ⟺ `apply_costs(−r) > 0` (Auszahlung `apply_costs(−r)`).
- **Kein Borrow** (v1). **Markt-bereinigt** (Benchmark, Markt-Default `"USA"`).
- **Nur messen:** kein Zurückschreiben in `compute_confidence` / den Konflikt-Agenten.
- **Reuse, nicht duplizieren:** `aggregate_by_reason`/`payoff_warning` aus `core/utils/short_backtest.py` **unverändert** wiederverwenden (das gemergte Modul **nicht** anfassen).
- **`created_at`** kommt aus dem `ConflictStore` als **String** → im Backtester zu tz-aware `datetime` parsen.

---

## File Structure

- **Modify** `core/ports/conflict_store.py` — neue Methode `load_for_backtest(days)` (konkreter Default `[]`, damit bestehende Implementierungen nicht brechen).
- **Modify** `adapters/persistence/supabase_conflict_store.py` — `load_for_backtest` überschreiben (SELECT mit `created_at`-Filter; reuse `_SELECT_COLS`/`_row_to_item`).
- **Create** `core/utils/conflict_backtest.py` — reine Funktionen `held_return`, `grade_verdict` + `VALID_VERDICTS`.
- **Create** `agents/backtester/conflict_backtester_agent.py` — `ConflictBacktesterAgent` (dünn).
- **Modify** `agents/backtester_chief_agent.py` — optionalen `conflict_store` aufnehmen, Konflikt-Backtester bedingt mitstarten.
- **Modify** `orchestrators/judgment_orchestrator.py:30` + `background_runner.py:90` — `conflict_store` durchreichen.
- **Create** `tests/test_supabase_conflict_store_backtest.py` (oder Anhang an `tests/test_supabase_conflict_store.py`), `tests/utils/test_conflict_backtest.py`, `tests/agents/backtester/test_conflict_backtester_agent.py`.
- **Modify** `tests/test_backtester_chief.py` — Verdrahtungs-Test.
- **Modify** `docs/open_todos.md` — Befolgungsrate als Folge-Aufgabe.

**Keine DB-Migration** — die `conflicts`-Tabelle trägt schon alle nötigen Felder.

---

### Task 1: Port-Methode `load_for_backtest`

**Files:**
- Modify: `core/ports/conflict_store.py`
- Modify: `adapters/persistence/supabase_conflict_store.py`
- Test: `tests/test_supabase_conflict_store.py` (anhängen)

**Interfaces:**
- Produces: `ConflictStorePort.load_for_backtest(self, days: int = 180) -> list[ConflictItem]` — lädt alle Konflikte mit `created_at >= now()-days`. Default `[]`; `SupabaseConflictStore` überschreibt mit echter Query.

- [ ] **Step 1: Write the failing test**

Ans Ende von `tests/test_supabase_conflict_store.py` (nutzt die vorhandenen Helfer `_patch_store`):

```python
def test_load_for_backtest_selektiert_nach_created_at(monkeypatch):
    cur = MagicMock()
    cur.fetchall.return_value = [
        {"id": 1, "ticker": "AAPL", "direction": "long", "verdict": "EXIT",
         "reason": "r", "status": "resolved", "source": "on_demand",
         "user_decision": "closed",
         "created_at": datetime(2026, 6, 1, tzinfo=timezone.utc), "resolved_at": None},
    ]
    store, conn = _patch_store(monkeypatch, cur)
    items = store.load_for_backtest(180)
    assert len(items) == 1
    assert items[0].verdict == "EXIT"
    sql = cur.execute.call_args[0][0]
    assert "created_at >=" in sql


def test_port_default_load_for_backtest_leer():
    # Eine Implementierung, die die Methode NICHT überschreibt, liefert [].
    from core.ports.conflict_store import ConflictStorePort

    class _Stub(ConflictStorePort):
        def find_open(self, t, d): return None
        def find_latest_resolved(self, t, d): return None
        def save(self, item): ...
        def load_open(self): return []
        def resolve(self, cid, ud): ...

    assert _Stub().load_for_backtest(180) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_supabase_conflict_store.py -k "load_for_backtest or port_default" -v`
Expected: FAIL (`AttributeError: 'SupabaseConflictStore' object has no attribute 'load_for_backtest'`).

- [ ] **Step 3: Implement on the port (concrete default)**

In `core/ports/conflict_store.py`, als **nicht-abstrakte** Methode in der Klasse (nach `resolve`):

```python
    def load_for_backtest(self, days: int = 180) -> list[ConflictItem]:
        """Lädt Konflikte der letzten `days` Tage für den Konflikt-Backtester.

        Konkreter Default `[]` (nicht @abstractmethod): bestehende Implementierungen
        ohne Backtest-Bedarf brechen nicht; die echte Quelle (Supabase) überschreibt.
        """
        return []
```

- [ ] **Step 4: Implement on SupabaseConflictStore**

In `adapters/persistence/supabase_conflict_store.py`, neue Methode (nutzt `_SELECT_COLS`/`_row_to_item`):

```python
    def load_for_backtest(self, days: int = 180) -> list[ConflictItem]:
        """Lädt Konflikte mit created_at >= now()-days (für den Konflikt-Backtester)."""
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT {_SELECT_COLS}
                        FROM conflicts
                        WHERE created_at >= %s
                        ORDER BY created_at DESC
                        """,
                        (cutoff,),
                    )
                    return [_row_to_item(dict(r)) for r in cur.fetchall()]
        except Exception:
            _log.exception("load_for_backtest(%r) fehlgeschlagen", days)
            return []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_supabase_conflict_store.py -v`
Expected: PASS (bestehende + 2 neue).

- [ ] **Step 6: Commit**

```bash
git add core/ports/conflict_store.py adapters/persistence/supabase_conflict_store.py tests/test_supabase_conflict_store.py
git commit -m "feat(conflict-store): load_for_backtest (Konflikte fuer den Backtester laden)"
```

---

### Task 2: Reine Benotungs-Mathematik

**Files:**
- Create: `core/utils/conflict_backtest.py`
- Test: `tests/utils/test_conflict_backtest.py`

**Interfaces:**
- Consumes: `apply_costs` (aus `core.utils.performance_metrics`).
- Produces:
  - `VALID_VERDICTS = {"HOLD", "EXIT", "REVERSE"}`
  - `held_return(direction: str, adj_return: float) -> float`
  - `grade_verdict(verdict: str, r: float, cost_per_side: float = 0.0005) -> tuple[bool, float]`

- [ ] **Step 1: Write the failing test**

In `tests/utils/test_conflict_backtest.py`:

```python
from core.utils.conflict_backtest import VALID_VERDICTS, grade_verdict, held_return


def test_held_return_long_is_raw():
    assert held_return("long", -0.10) == -0.10


def test_held_return_short_is_flipped():
    # Short gewinnt, wenn der Kurs fällt: adj=-0.10 → r=+0.10
    assert held_return("short", -0.10) == 0.10


def test_hold_correct_when_position_gained():
    correct, payoff = grade_verdict("HOLD", 0.08)
    assert correct is True and payoff == 0.08


def test_hold_wrong_at_zero():
    correct, _ = grade_verdict("HOLD", 0.0)   # strikt > 0
    assert correct is False


def test_exit_correct_when_position_would_have_lost():
    correct, payoff = grade_verdict("EXIT", -0.05)
    assert correct is True and payoff == 0.05   # vermiedener Verlust


def test_exit_wrong_at_zero():
    correct, _ = grade_verdict("EXIT", 0.0)     # strikt < 0
    assert correct is False


def test_reverse_needs_to_clear_costs():
    # -r muss nach Round-Trip-Kosten (2*cost_per_side) im Plus sein
    correct, payoff = grade_verdict("REVERSE", -0.10, cost_per_side=0.0005)
    assert correct is True
    assert payoff == -0.10 - 2 * 0.0005          # apply_costs(0.10) ... s.u.


def test_reverse_wrong_when_reversal_too_small_after_costs():
    # -r = 0.0005 < Kosten 0.001 → Gegenposition zahlt nicht → falsch
    correct, payoff = grade_verdict("REVERSE", -0.0005, cost_per_side=0.0005)
    assert correct is False
    assert payoff < 0


def test_valid_verdicts_set():
    assert VALID_VERDICTS == {"HOLD", "EXIT", "REVERSE"}
```

> Hinweis zur REVERSE-Auszahlung: `apply_costs(x, c) = x - 2*c`. Für `r=-0.10`:
> `apply_costs(-r=0.10, 0.0005) = 0.10 - 0.001 = 0.099`. Der Test oben prüft genau diese Form
> (`-r - 2*cost_per_side` mit `-r = -(-0.10) = 0.10`); ggf. als `0.10 - 2*0.0005` schreiben.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/utils/test_conflict_backtest.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'core.utils.conflict_backtest'`).

- [ ] **Step 3: Write minimal implementation**

In `core/utils/conflict_backtest.py`:

```python
"""Reine Benotungs-Mathematik für die Konflikt-Verdikte (Konflikt-Backtester).

Kein I/O. Benotet die Verdikte des Konflikt-Agenten (HOLD/EXIT/REVERSE) gegen die
Kursrealität der gehaltenen Position. Aggregation/Kennzahlen kommen wiederverwendet
aus core/utils/short_backtest.py (per-Verdikt-Buckets).
"""
from core.utils.performance_metrics import apply_costs

VALID_VERDICTS = {"HOLD", "EXIT", "REVERSE"}


def held_return(direction: str, adj_return: float) -> float:
    """Markt-bereinigtes Forward-Ergebnis der GEHALTENEN Position.

    long  → adj_return (Kursverlauf);
    short → −adj_return (ein Short gewinnt, wenn der Kurs fällt).
    direction ist per DB-Constraint immer 'long' oder 'short'.
    """
    return adj_return if direction == "long" else -adj_return


def grade_verdict(verdict: str, r: float, cost_per_side: float = 0.0005) -> tuple[bool, float]:
    """Benotet ein Verdikt gegen r (Ergebnis der gehaltenen Position) → (korrekt, Auszahlung).

    HOLD    korrekt ⟺ r > 0 (These hielt);            Auszahlung r.
    EXIT    korrekt ⟺ r < 0 (Verlust vermieden);      Auszahlung −r.
    REVERSE korrekt ⟺ Gegenposition zahlt NACH Kosten; Auszahlung apply_costs(−r)
            (strengere Latte: nicht nur „raus wäre gut", die Umkehr muss real lohnen).
    """
    if verdict == "HOLD":
        return (r > 0, r)
    if verdict == "EXIT":
        return (r < 0, -r)
    # REVERSE
    payoff = apply_costs(-r, cost_per_side)
    return (payoff > 0, payoff)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/utils/test_conflict_backtest.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/utils/conflict_backtest.py tests/utils/test_conflict_backtest.py
git commit -m "feat(conflict-backtest): Verdikt-Benotung (held_return + grade_verdict, pure)"
```

---

### Task 3: `ConflictBacktesterAgent` (dünn)

**Files:**
- Create: `agents/backtester/conflict_backtester_agent.py`
- Test: `tests/agents/backtester/test_conflict_backtester_agent.py`

**Interfaces:**
- Consumes: `ConflictStorePort.load_for_backtest` (Task 1), `held_return`/`grade_verdict`/`VALID_VERDICTS` (Task 2), `aggregate_by_reason` (`core.utils.short_backtest`), `HORIZONS_DAYS`/`forward_return`/`market_adjusted_return` (`core.utils.backtest`), Default-Provider aus `bottom_up_backtester_agent`, `MemoryPort.save_backtester_report`.
- Produces: `ConflictBacktesterAgent(store, memory, price_on_horizon=..., benchmark_return=..., cost_per_side=0.0005)` mit `async def run() -> None`.

- [ ] **Step 1: Write the failing test**

In `tests/agents/backtester/test_conflict_backtester_agent.py`:

```python
import asyncio
from datetime import datetime, timedelta, timezone

from agents.backtester.conflict_backtester_agent import ConflictBacktesterAgent


class _Item:
    def __init__(self, ticker, direction, verdict, created_at):
        self.ticker, self.direction, self.verdict, self.created_at = (
            ticker, direction, verdict, created_at)


class _FakeStore:
    def __init__(self, items): self._items = items
    def load_for_backtest(self, days=180): return self._items


class _FakeMemory:
    def __init__(self): self.reports = []
    def save_backtester_report(self, report): self.reports.append(report)


def _created(days_ago):
    return str(datetime.now(timezone.utc) - timedelta(days=days_ago))


def test_exit_on_long_that_fell_is_correct_and_reported():
    store = _FakeStore([_Item("AAA", "long", "EXIT", _created(40))])
    mem = _FakeMemory()
    agent = ConflictBacktesterAgent(
        store, mem,
        price_on_horizon=lambda t, d, h: 100.0 if h == 0 else 90.0,  # fiel 100→90
        benchmark_return=lambda m, d, h: 0.0,
    )
    asyncio.run(agent.run())
    exit_rows = [r for r in mem.reports if r["original_recommendation"] == "EXIT"]
    assert len(exit_rows) == 1
    assert exit_rows[0]["return_pct"] > 0           # EXIT richtig → positive Auszahlung


def test_missing_price_is_skipped_not_crash():
    store = _FakeStore([_Item("AAA", "long", "HOLD", _created(40))])
    mem = _FakeMemory()
    agent = ConflictBacktesterAgent(
        store, mem,
        price_on_horizon=lambda t, d, h: None,
        benchmark_return=lambda m, d, h: 0.0,
    )
    asyncio.run(agent.run())
    assert mem.reports == []


def test_unknown_verdict_and_unripe_are_skipped():
    store = _FakeStore([
        _Item("AAA", "long", "WEITER", _created(40)),   # unbekanntes Verdikt
        _Item("BBB", "long", "HOLD", _created(5)),        # zu jung (< 30d Horizont)
    ])
    mem = _FakeMemory()
    agent = ConflictBacktesterAgent(
        store, mem, price_on_horizon=lambda t, d, h: 100.0 if h == 0 else 90.0,
        benchmark_return=lambda m, d, h: 0.0)
    asyncio.run(agent.run())
    assert mem.reports == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agents/backtester/test_conflict_backtester_agent.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'agents.backtester.conflict_backtester_agent'`).

- [ ] **Step 3: Write minimal implementation**

In `agents/backtester/conflict_backtester_agent.py`:

```python
"""ConflictBacktesterAgent — benotet die Konflikt-Verdikte (HOLD/EXIT/REVERSE).

Geschwister zum Short-/Judgment-Backtester, anderes Prüf-Subjekt: hier zählt das
Verdikt des Konflikt-Agenten gegen die Kursrealität der gehaltenen Position. Lädt aus
dem ConflictStore, benotet, aggregiert je Verdikt-Typ. Nur messen, kein Zurückschreiben.
"""
from datetime import datetime, timezone
from typing import Callable, Optional

from core.ports.conflict_store import ConflictStorePort
from core.ports.memory_port import MemoryPort
from core.utils.backtest import HORIZONS_DAYS, forward_return, market_adjusted_return
from core.utils.conflict_backtest import VALID_VERDICTS, grade_verdict, held_return
from core.utils.short_backtest import aggregate_by_reason
from agents.backtester.bottom_up_backtester_agent import (
    _default_benchmark_return, _default_price_on_horizon,
)


def _parse_dt(s) -> Optional[datetime]:
    """created_at kommt aus dem ConflictStore als String → tz-aware datetime."""
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(s))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


class ConflictBacktesterAgent:
    def __init__(
        self,
        store: ConflictStorePort,
        memory: MemoryPort,
        price_on_horizon: Callable[[str, datetime, int], Optional[float]] = _default_price_on_horizon,
        benchmark_return: Callable[[str, datetime, int], Optional[float]] = _default_benchmark_return,
        cost_per_side: float = 0.0005,
    ):
        self.store = store
        self.memory = memory
        self.price_on_horizon = price_on_horizon
        self.benchmark_return = benchmark_return
        self.cost_per_side = cost_per_side

    async def run(self) -> None:
        conflicts = self.store.load_for_backtest(180)
        now = datetime.now(timezone.utc)
        graded: list[dict] = []

        for c in conflicts:
            verdict = getattr(c, "verdict", None)
            ticker = getattr(c, "ticker", None)
            created = _parse_dt(getattr(c, "created_at", None))
            if verdict not in VALID_VERDICTS or not ticker or created is None:
                continue

            age_days = (now - created).days
            horizon = max((d for d in HORIZONS_DAYS if d <= age_days), default=None)
            if horizon is None:
                continue

            entry_px = self.price_on_horizon(ticker, created, 0)
            fwd_px = self.price_on_horizon(ticker, created, horizon)
            if entry_px is None or fwd_px is None:
                continue
            raw = forward_return(entry_px, fwd_px)
            if raw is None:
                continue

            bench = self.benchmark_return("USA", created, horizon)   # conflicts trägt kein market → USA
            adj = market_adjusted_return(raw, bench)
            r = held_return(getattr(c, "direction", "long"), adj)
            correct, payoff = grade_verdict(verdict, r, self.cost_per_side)
            graded.append({"archetypes": [verdict], "correct": correct, "payoff": payoff})

        for verdict, m in aggregate_by_reason(graded).items():
            self.memory.save_backtester_report({
                "backtester_type": "conflict",
                "ticker": None,
                "original_recommendation": verdict,
                "price_at_recommendation": None,
                "price_today": None,
                "return_pct": round(m["mean_payoff"] * 100, 2),
                "verdict": "WARN-payoff" if m["warning"] else None,
                "accuracy_30d": None, "accuracy_60d": None, "accuracy_90d": None,
                "notes": (f"N={m['n']} | Hit={m['hit_rate']} "
                          f"[{m['ci_low']}–{m['ci_high']}] | PF={m['profit_factor']} "
                          f"| MaxDD={m['max_drawdown']} | Warnung={m['warning']}"),
            })
        print(f"[ConflictBacktester] {len(graded)} Verdikte ausgewertet")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agents/backtester/test_conflict_backtester_agent.py -v`
Expected: PASS (3 Tests).

- [ ] **Step 5: Commit**

```bash
git add agents/backtester/conflict_backtester_agent.py tests/agents/backtester/test_conflict_backtester_agent.py
git commit -m "feat(conflict-backtest): ConflictBacktesterAgent (je Verdikt-Typ, nur messen)"
```

---

### Task 4: Verdrahtung in den BacktesterChiefAgent

**Files:**
- Modify: `agents/backtester_chief_agent.py`
- Modify: `orchestrators/judgment_orchestrator.py:30`
- Modify: `background_runner.py:90`
- Test: `tests/test_backtester_chief.py` (anhängen)

**Interfaces:**
- Consumes: `ConflictBacktesterAgent` (Task 3), `ConflictStorePort`.

- [ ] **Step 1: Write the failing test**

Ans Ende von `tests/test_backtester_chief.py` (Muster der bestehenden Tests dort spiegeln — `memory`/`bus`-Fakes):

```python
def test_conflict_store_wird_mitgestartet(monkeypatch):
    import asyncio
    from agents.backtester_chief_agent import BacktesterChiefAgent

    class _Store:
        def __init__(self): self.called = False
        def load_for_backtest(self, days=180):
            self.called = True
            return []

    memory = _FakeMemory()       # vorhandener Fake in dieser Testdatei
    bus = _FakeBus()             # vorhandener Fake in dieser Testdatei
    store = _Store()
    chief = BacktesterChiefAgent(memory, bus, conflict_store=store)
    asyncio.run(chief.run())
    assert store.called is True   # Konflikt-Backtester lief mit


def test_ohne_conflict_store_kein_crash():
    import asyncio
    from agents.backtester_chief_agent import BacktesterChiefAgent
    chief = BacktesterChiefAgent(_FakeMemory(), _FakeBus())   # conflict_store default None
    asyncio.run(chief.run())     # darf nicht crashen
```

> Falls die vorhandenen Fakes in `test_backtester_chief.py` anders heißen, die dort
> bereits genutzten verwenden (Datei zuerst lesen); die Logik (Store wird aufgerufen /
> None ist sicher) bleibt gleich.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_backtester_chief.py -k "conflict_store or ohne_conflict" -v`
Expected: FAIL (`TypeError: __init__() got an unexpected keyword argument 'conflict_store'`).

- [ ] **Step 3: Modify the chief**

In `agents/backtester_chief_agent.py`: Import + optionaler Parameter + bedingter Sub-Agent + bedingter `gather`.

```python
# Imports oben ergänzen:
from typing import Callable, Optional
from agents.backtester.conflict_backtester_agent import ConflictBacktesterAgent
from core.ports.conflict_store import ConflictStorePort

# __init__-Signatur um conflict_store erweitern:
    def __init__(
        self,
        memory: MemoryPort,
        bus: EventBus,
        price_on_horizon: Callable[[str, datetime, int], Optional[float]] = _default_price_on_horizon,
        benchmark_return: Callable[[str, datetime, int], Optional[float]] = _default_benchmark_return,
        conflict_store: Optional[ConflictStorePort] = None,
    ):
        # ... bestehende Zuweisungen unverändert ...
        # Konflikt-Backtester nur, wenn ein Store vorliegt (defensiv: sonst übersprungen).
        self.conflict_backtester = (
            ConflictBacktesterAgent(conflict_store, memory,
                                    price_on_horizon=price_on_horizon,
                                    benchmark_return=benchmark_return)
            if conflict_store is not None else None
        )

# in run(): die Liste der Coroutinen bedingt um den Konflikt-Backtester ergänzen:
    async def run(self) -> None:
        tasks = [
            self.td_backtester.run(),
            self.bu_backtester.run(),
            self.j_backtester.run(),
            self.short_backtester.run(),
        ]
        if self.conflict_backtester is not None:
            tasks.append(self.conflict_backtester.run())
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failures = sum(1 for r in results if isinstance(r, Exception))
        self.bus.publish(BacktesterChiefReady(source="backtester_chief_agent", payload={"failures": failures}))
```

- [ ] **Step 4: Thread the store through the construction sites**

In `orchestrators/judgment_orchestrator.py:30` — der `conflict_store`-Parameter ist im `__init__` bereits vorhanden:

```python
        self.backtester_chief    = BacktesterChiefAgent(memory, bus, conflict_store=conflict_store)
```

In `background_runner.py` (`main()`, bei `backtester = BacktesterChiefAgent(memory, bus)` ~Zeile 90) — `SupabaseConflictStore` ist oben bereits importiert:

```python
    try:
        conflict_store = SupabaseConflictStore()
    except Exception:
        conflict_store = None
    backtester = BacktesterChiefAgent(memory, bus, conflict_store=conflict_store)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_backtester_chief.py -v`
Expected: PASS (bestehende + 2 neue).

- [ ] **Step 6: Commit**

```bash
git add agents/backtester_chief_agent.py orchestrators/judgment_orchestrator.py background_runner.py tests/test_backtester_chief.py
git commit -m "feat(conflict-backtest): ConflictBacktester in BacktesterChiefAgent verdrahtet"
```

---

### Task 5: Logbuch — Befolgungsrate als Folge-Aufgabe

**Files:**
- Modify: `docs/open_todos.md` (§9, beim Konflikt-Backtester-Eintrag)

**Interfaces:** keine (reine Doku).

- [ ] **Step 1: Folge-Aufgabe ergänzen**

In `docs/open_todos.md` §9, direkt **nach** dem Bullet „**Konflikt-Backtester (eigener Block)**" (noch **nicht** abhaken — das ist PR-Protokoll nach dem Merge) einfügen:

```markdown
- [ ] **Konflikt-Befolgungsrate (`verdict` vs. `user_decision`)** — verhaltensbezogenes Maß (folgte
  der Nutzer dem Rat?), getrennt von der Verdikt-Qualität. Liest `conflicts.user_decision`
  (held/closed) gegen `verdict` (HOLD/EXIT/REVERSE) — **keine** Kurse nötig. Eigener kleiner Block;
  baut auf der `load_for_backtest`-Lademethode auf. *(Aus dem Konflikt-Backtester-Faden, 2026-06-24.)*
```

- [ ] **Step 2: Commit**

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): Konflikt-Befolgungsrate als Folge-Aufgabe"
```

---

## Self-Review

**1. Spec coverage:**
- §2.1 Port-Erweiterung `load_for_backtest` → Task 1 ✅
- §2.2 reine Mathematik (`held_return`, `grade_verdict`) → Task 2 ✅
- §2.3 dünner Agent (reuse `aggregate_by_reason`, nur messen) → Task 3 ✅
- §2.4 Verdrahtung in `BacktesterChiefAgent` → Task 4 ✅
- §4 Benotungsregeln (HOLD r>0 / EXIT r<0 / REVERSE apply_costs(−r)>0; kein Borrow; markt-bereinigt; Markt-Default USA) → Task 2 (`grade_verdict`/`held_return`) + Task 3 (`market_adjusted_return`, `"USA"`) ✅
- §5 Datenladen + `created_at`-String-Parsing + Horizont/Reife → Task 1 (Query) + Task 3 (`_parse_dt`, Horizont-Filter, skip) ✅
- §6 Kennzahlen je Verdikt-Typ (reuse) + Report-Form → Task 3 ✅
- §7 Verdrahtung defensiv (fehlt Store → übersprungen) → Task 4 (Chief-`if`, Orchestrator/Runner) ✅
- §9 Fehlerpfade/Grenzfälle → Task 2 (REVERSE-Kostenschwelle, r=0) + Task 3 (skip-Tests) ✅
- §10 Logbuch Befolgungsrate → Task 5 ✅ (Abhaken = post-merge PR-Protokoll, nicht Plan-Task)
- Keine DB-Migration → korrekt, kein Task nötig ✅

**2. Placeholder scan:** kein TBD/TODO; jeder Code-Step zeigt vollständigen Code. Die zwei „Datei zuerst lesen, vorhandene Fakes nutzen"-Hinweise (Task 4 Test) sind bewusste Anpassungs-Hinweise an die existierende Testdatei, keine fehlenden Inhalte. ✅

**3. Type consistency:** `grade_verdict`/`held_return` liefern `(bool, float)`, in Task 3 als `(correct, payoff)` entpackt und in `{"archetypes":[verdict],"correct","payoff"}` gelegt → passt zum `graded`-Format, das `aggregate_by_reason` (aus short_backtest) erwartet. Bucket-Keys (`n/hit_rate/ci_low/ci_high/mean_payoff/profit_factor/max_drawdown/warning`) wie in Task 3 gelesen. `load_for_backtest(days)` Signatur in Task 1 = Aufruf in Task 3/Task 4. ✅
