# Konflikt-UX (Inbox + Entscheidungs-Protokoll) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine persistente Konflikt-Inbox — Konflikte als offene Posten (Dedupe + Reopen), gespeist on-demand + proaktiv, mit CLI zum Listen/Entscheiden. Das Tool handelt nie, es protokolliert nur.

**Architecture:** `ConflictItem` (Domäne) + `ConflictStorePort` (ABC) + `SupabaseConflictStore` (Tabelle `conflicts`); reine `record_conflict`-Lebenszyklus-Logik; on-demand im `JudgmentOrchestrator`, proaktiv im `background_runner` (Voll-Reuse von `JudgmentOrchestrator.run` je Depot-Position), CLI `conflicts`/`resolve`.

**Tech Stack:** Python, pytest, psycopg (Supabase).

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-22-konflikt-ux-design.md`.
- TDD Pflicht (roter Test zuerst). DB/LLM in Tests **gemockt**. Deutsche Kommentare, Type Hints. **Jeder** Store-/DB-Pfad defensiv (`try/except`) — die Inbox ist nie kritisch.
- Worktree `.claude/worktrees/konflikt-ux`, Branch `feat/konflikt-ux`. PR-First — **nicht** mergen. Runner `python -m pytest -q`.
- Severity: `HOLD < EXIT < REVERSE`. Reopen nur bei **schärferem** Verdikt. Dedupe-Schlüssel: (ticker, direction). Tool **handelt nie** (nur protokollieren).

---

## Task 1: `ConflictItem`-Modell + Verdikt-Severity

**Files:** Modify `core/domain/models.py`; Test `tests/test_conflict_item_model.py`

**Interfaces:**
- Produces: `ConflictItem` (dataclass, Felder s. u.); `core/domain/conflict_inbox.py:_VERDICT_SEVERITY` (in Task 2).

- [ ] **Step 1: Failing test** — `tests/test_conflict_item_model.py`:
```python
from core.domain.models import ConflictItem

def test_conflict_item_defaults():
    c = ConflictItem(ticker="AAPL", direction="long", verdict="EXIT", reason="screent short")
    assert c.status == "open" and c.source == "on_demand"
    assert c.user_decision is None and c.id is None
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_conflict_item_model.py -q`.

- [ ] **Step 3: Implement** — `core/domain/models.py` (bei den anderen Dataclasses):
```python
@dataclass
class ConflictItem:
    ticker: str
    direction: str                         # gehaltene Position: "long" | "short"
    verdict: str                           # "HOLD" | "EXIT" | "REVERSE"
    reason: str
    status: str = "open"                   # "open" | "resolved"
    source: str = "on_demand"              # "on_demand" | "proactive"
    user_decision: Optional[str] = None    # "held" | "closed" | None
    id: Optional[int] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_conflict_item_model.py -q`.

- [ ] **Step 5: Commit** — `git add core/domain/models.py tests/test_conflict_item_model.py && git commit -m "feat(conflict): ConflictItem-Modell"`

---

## Task 2: `ConflictStorePort` + `record_conflict` (Lebenszyklus, pure)

**Files:** Create `core/ports/conflict_store.py`, `core/domain/conflict_inbox.py`; Test `tests/test_conflict_inbox.py`

**Interfaces:**
- Consumes: `ConflictItem` (Task 1).
- Produces: `ConflictStorePort(ABC)` mit `find_open(ticker, direction)`, `find_latest_resolved(ticker, direction)`, `save(item)`, `load_open()`, `resolve(conflict_id, user_decision)`; `record_conflict(store, ticker, direction, verdict, reason, source) -> ConflictItem | None`.

- [ ] **Step 1: Failing tests** — `tests/test_conflict_inbox.py`:
```python
from core.domain.models import ConflictItem
from core.domain.conflict_inbox import record_conflict


class _FakeStore:
    def __init__(self, open_item=None, resolved=None):
        self._open, self._resolved, self.saved = open_item, resolved, []
    def find_open(self, t, d): return self._open
    def find_latest_resolved(self, t, d): return self._resolved
    def save(self, item): self.saved.append(item)
    def load_open(self): return []
    def resolve(self, cid, dec): pass


def test_skip_when_open_exists():
    s = _FakeStore(open_item=ConflictItem("AAPL", "long", "EXIT", "x"))
    assert record_conflict(s, "AAPL", "long", "EXIT", "x", "on_demand") is None
    assert s.saved == []

def test_new_when_none():
    s = _FakeStore()
    item = record_conflict(s, "AAPL", "long", "HOLD", "x", "on_demand")
    assert item is not None and len(s.saved) == 1 and s.saved[0].status == "open"

def test_reopen_only_on_more_severe():
    s = _FakeStore(resolved=ConflictItem("AAPL", "long", "HOLD", "x", status="resolved"))
    assert record_conflict(s, "AAPL", "long", "EXIT", "y", "proactive") is not None   # HOLD→EXIT schärfer
    assert len(s.saved) == 1

def test_no_reopen_when_same_or_milder():
    s = _FakeStore(resolved=ConflictItem("AAPL", "long", "EXIT", "x", status="resolved"))
    assert record_conflict(s, "AAPL", "long", "HOLD", "y", "proactive") is None        # EXIT→HOLD milder
    assert s.saved == []
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_conflict_inbox.py -q`.

- [ ] **Step 3: Implement**
  - `core/ports/conflict_store.py`:
```python
from abc import ABC, abstractmethod
from core.domain.models import ConflictItem


class ConflictStorePort(ABC):
    @abstractmethod
    def find_open(self, ticker: str, direction: str) -> ConflictItem | None: ...
    @abstractmethod
    def find_latest_resolved(self, ticker: str, direction: str) -> ConflictItem | None: ...
    @abstractmethod
    def save(self, item: ConflictItem) -> None: ...
    @abstractmethod
    def load_open(self) -> list[ConflictItem]: ...
    @abstractmethod
    def resolve(self, conflict_id: int, user_decision: str) -> None: ...
```
  - `core/domain/conflict_inbox.py`:
```python
from core.domain.models import ConflictItem

_VERDICT_SEVERITY = {"HOLD": 0, "EXIT": 1, "REVERSE": 2}


def record_conflict(store, ticker, direction, verdict, reason, source) -> ConflictItem | None:
    """Lebenszyklus: Dedupe (offener existiert → skip), Reopen nur bei schärferem Verdikt.
    Reine Logik gegen den ConflictStorePort. Gibt den angelegten ConflictItem zurück oder None (skip)."""
    if store.find_open(ticker, direction) is not None:
        return None                                  # Dedupe: schon offen
    last = store.find_latest_resolved(ticker, direction)
    if last is not None:
        if _VERDICT_SEVERITY.get(verdict, 0) <= _VERDICT_SEVERITY.get(last.verdict, 0):
            return None                              # gleich/milder → erledigt lassen
    item = ConflictItem(ticker=ticker, direction=direction, verdict=verdict,
                        reason=reason, status="open", source=source)
    store.save(item)
    return item
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_conflict_inbox.py -q`.

- [ ] **Step 5: Commit** — `git add core/ports/conflict_store.py core/domain/conflict_inbox.py tests/test_conflict_inbox.py && git commit -m "feat(conflict): ConflictStorePort + record_conflict (Dedupe/Reopen)"`

---

## Task 3: `SupabaseConflictStore` + `conflicts`-Tabelle

**Files:** Create `adapters/persistence/supabase_conflict_store.py`; Modify `db/schema.sql`; Test `tests/test_supabase_conflict_store.py`

**ZUERST LESEN:** `adapters/memory/supabase_memory.py` (Verbindungs-/Cursor-Muster, `_connect`/psycopg, INSERT/SELECT, defensives `try/except`).

**Interfaces:**
- Consumes: `ConflictStorePort`, `ConflictItem`.
- Produces: `SupabaseConflictStore(ConflictStorePort)`.

- [ ] **Step 1: Failing tests** — `tests/test_supabase_conflict_store.py` (gemockter Cursor wie in `test_supabase_memory.py`): `save` führt ein `INSERT INTO conflicts` mit ticker/direction/verdict/status aus; `resolve` führt ein `UPDATE conflicts SET status='resolved', user_decision=%s` aus; `load_open` mappt Zeilen → `ConflictItem` mit `status="open"`. (An das reale Mock-Muster der Memory-Tests anlehnen.)

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_supabase_conflict_store.py -q`.

- [ ] **Step 3: Implement**
  - `adapters/persistence/supabase_conflict_store.py` — `SupabaseConflictStore(ConflictStorePort)` nach dem `SupabaseMemory`-Muster (gleiche Verbindung/`_connect`; **jede** Methode in `try/except` defensiv, bei Fehler `None`/`[]`/no-op):
    - `find_open(t,d)`: `SELECT … WHERE ticker=%s AND direction=%s AND status='open' ORDER BY id DESC LIMIT 1` → `ConflictItem` oder None.
    - `find_latest_resolved(t,d)`: `… AND status='resolved' ORDER BY resolved_at DESC LIMIT 1`.
    - `save(item)`: `INSERT INTO conflicts (ticker, direction, verdict, reason, status, source, created_at) VALUES (%s,…, now())`.
    - `load_open()`: `SELECT … WHERE status='open' ORDER BY id` → `list[ConflictItem]`.
    - `resolve(id, dec)`: `UPDATE conflicts SET status='resolved', user_decision=%s, resolved_at=now() WHERE id=%s`.
  - `db/schema.sql` — Tabelle `conflicts` ergänzen:
```sql
CREATE TABLE IF NOT EXISTS conflicts (
    id            bigserial PRIMARY KEY,
    ticker        text NOT NULL,
    direction     text NOT NULL,           -- "long" | "short"
    verdict       text NOT NULL,           -- "HOLD" | "EXIT" | "REVERSE"
    reason        text,
    status        text NOT NULL DEFAULT 'open',   -- "open" | "resolved"
    source        text NOT NULL DEFAULT 'on_demand',
    user_decision text,                     -- "held" | "closed" | NULL
    created_at    timestamptz DEFAULT now(),
    resolved_at   timestamptz
);
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_supabase_conflict_store.py -q`.

- [ ] **Step 5: Commit** — `git add adapters/persistence/supabase_conflict_store.py db/schema.sql tests/test_supabase_conflict_store.py && git commit -m "feat(conflict): SupabaseConflictStore + conflicts-Tabelle"`

> **⚠️ Deploy:** vor Merge/Deploy einmalig auf Supabase die `CREATE TABLE conflicts (...)` (s. `db/schema.sql`) ausführen.

---

## Task 4: On-demand — Orchestrator nimmt Konflikte auf

**Files:** Modify `orchestrators/judgment_orchestrator.py`, `app/main.py` (Store injizieren); Test `tests/test_judgment_orchestrator_conflict.py`

- [ ] **Step 1: Failing test** — im Orchestrator-Test: mit gemocktem `conflict_store` + einem `result.conflict=True` + `result.conflict_resolution` (verdict) ruft `run(...)` `record_conflict` so, dass `store.save` einen offenen Posten erhält; ohne Konflikt → kein `save`; Store-Exception → kein Crash. (An die Fixture der Datei anlehnen; `orch.conflict_store` setzen.)

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_judgment_orchestrator_conflict.py -q`.

- [ ] **Step 3: Implement**
  - `orchestrators/judgment_orchestrator.py`:
    - Import `from core.domain.conflict_inbox import record_conflict`.
    - `__init__(..., conflict_store=None)` → `self.conflict_store = conflict_store`.
    - In `run()`, im `if result.conflict:`-Block (nach dem ConflictAgent), defensiv:
```python
                if self.conflict_store is not None and result.conflict_resolution is not None:
                    try:
                        record_conflict(self.conflict_store, bottom_up.ticker,
                                        current_position.value,
                                        result.conflict_resolution.verdict,
                                        result.conflict_resolution.reasoning, "on_demand")
                    except Exception:
                        pass
```
  - `app/main.py` (`run_judgment`): `SupabaseConflictStore` instanziieren und an den Orchestrator geben (`conflict_store=SupabaseConflictStore()`).

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_judgment_orchestrator_conflict.py -q`.

- [ ] **Step 5: Commit** — `git add orchestrators/judgment_orchestrator.py app/main.py tests/ && git commit -m "feat(conflict): on-demand Aufnahme im JudgmentOrchestrator"`

---

## Task 5: CLI — `conflicts` + `resolve`

**Files:** Modify `app/main.py`; Test `tests/test_cli_conflicts.py` (oder vorhandene CLI-Testdatei)

- [ ] **Step 1: Failing test** — eine Funktion `run_conflicts(store)` (listet) und `run_resolve(store, conflict_id, decision)` (protokolliert): mit gemocktem Store gibt `run_conflicts` die offenen aus; `run_resolve(store, 3, "held")` ruft `store.resolve(3, "held")`; ungültige Entscheidung (`"foo"`) ruft **nicht** `resolve`.

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_cli_conflicts.py -q`.

- [ ] **Step 3: Implement** — `app/main.py`:
  - `run_conflicts(store)`: `items = store.load_open()`; je Item `print(f"#{c.id}  {c.ticker} ({c.direction})  {c.verdict} — {c.reason}")`; leer → Hinweis „keine offenen Konflikte".
  - `run_resolve(store, conflict_id, decision)`: `if decision not in ("held", "closed"): print("Nutzung: resolve <id> <held|closed>"); return`; `store.resolve(int(conflict_id), decision)`; `print("✓ protokolliert (kein Trade ausgeführt).")`.
  - Doku-String + `main()`-Dispatch ergänzen: `elif args[0] == "conflicts": run_conflicts(SupabaseConflictStore())` und `elif args[0] == "resolve" and len(args) >= 3: run_resolve(SupabaseConflictStore(), args[1], args[2])`.

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_cli_conflicts.py -q`.

- [ ] **Step 5: Commit** — `git add app/main.py tests/test_cli_conflicts.py && git commit -m "feat(conflict): CLI conflicts/resolve (protokolliert, kein Trade)"`

---

## Task 6: Proaktiv — Depot-Scan + Regression

**Files:** Modify `background_runner.py`; Create `agents/conflict/portfolio_conflict_scan.py`; Modify `docs/open_todos.md`; Test `tests/test_portfolio_conflict_scan.py`

**Interfaces:**
- Consumes: `record_conflict` (Task 2), `PortfolioPort`, `ConflictStorePort`, ein „judgment-runner" (Callable `ticker, current_position -> result|None`).

- [ ] **Step 1: Failing test** — `tests/test_portfolio_conflict_scan.py`: `scan_portfolio_conflicts(positions, judge_fn, store)` ruft `judge_fn` je Position; bei `result.conflict=True` (+ conflict_resolution) → `record_conflict` (store.save); bei `result is None` (keine gecachte Analyse) → übersprungen; `judge_fn`-Exception → übersprungen, kein Crash.
```python
from types import SimpleNamespace as NS
from agents.conflict.portfolio_conflict_scan import scan_portfolio_conflicts

class _Store:
    def __init__(self): self.saved=[]
    def find_open(self,t,d): return None
    def find_latest_resolved(self,t,d): return None
    def save(self,i): self.saved.append(i)

def test_scan_records_only_conflicts():
    pos = [NS(ticker="AAPL", direction="long"), NS(ticker="MSFT", direction="long")]
    def judge_fn(ticker, direction):
        if ticker == "AAPL":
            return NS(conflict=True, conflict_resolution=NS(verdict="EXIT", reasoning="r"))
        return NS(conflict=False, conflict_resolution=None)
    store = _Store()
    scan_portfolio_conflicts(pos, judge_fn, store)
    assert [i.ticker for i in store.saved] == ["AAPL"]
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_portfolio_conflict_scan.py -q`.

- [ ] **Step 3: Implement**
  - `agents/conflict/portfolio_conflict_scan.py`:
```python
from core.domain.conflict_inbox import record_conflict


def scan_portfolio_conflicts(positions, judge_fn, store) -> None:
    """Je gehaltener Position eine Analyse (judge_fn) laufen lassen; bei Konflikt protokollieren.
    judge_fn(ticker, direction) -> result mit .conflict/.conflict_resolution, oder None (keine Daten).
    Vollständig defensiv: ein Fehler je Position überspringt nur diese."""
    for p in positions:
        try:
            result = judge_fn(p.ticker, p.direction)
            if result is not None and getattr(result, "conflict", False) and result.conflict_resolution:
                record_conflict(store, p.ticker, p.direction,
                                result.conflict_resolution.verdict,
                                result.conflict_resolution.reasoning, "proactive")
        except Exception:
            continue
```
  - `background_runner.py`: einen `judge_fn` bauen, der je Position die gecachte `cockpit`+`bottom_up` lädt (`ResultCache`) und `JudgmentOrchestrator.run(...)` aufruft (Voll-Reuse; `current_position` aus `p.direction`); fehlt der Bottom-Up-Cache → `None`. `SupabaseConflictStore` + `JsonPortfolioProvider` instanziieren; `scan_portfolio_conflicts(port.get_positions(), judge_fn, store)` als neuen Schritt in der Agentenliste ergänzen (in `try/except` wie die übrigen Runner-Schritte).
    > Hinweis (Kosten): Voll-Reuse läuft die volle `judge`-Analyse je Position. Bei kleinem Depot trivial. **Folge-Aufgabe** (Logbuch): „LLM-nur-bei-Konflikt"-Optimierung via `skip_prose`-Flag durch den Judgment-Pfad.
  - `docs/open_todos.md`: Folge-Aufgabe „Konflikt-Scan: skip_prose-Optimierung (LLM nur bei echtem Konflikt)" ergänzen.

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_portfolio_conflict_scan.py -q`.

- [ ] **Step 5: Gesamt-Regression** — `python -m pytest -q` → **0 failed** (~3 Min). Bei Fehlern: superpowers:systematic-debugging.

- [ ] **Step 6: Commit** — `git add agents/conflict/portfolio_conflict_scan.py background_runner.py docs/open_todos.md tests/test_portfolio_conflict_scan.py && git commit -m "feat(conflict): proaktiver Depot-Scan im background_runner + Regression gruen"`

---

## Abdeckung (Spec → Task)
| Spec-Element | Task |
|---|---|
| `ConflictItem` | 1 |
| `ConflictStorePort` + `record_conflict` (Dedupe/Reopen) | 2 |
| `SupabaseConflictStore` + `conflicts`-Tabelle + Migration | 3 |
| On-demand (Orchestrator) | 4 |
| CLI `conflicts`/`resolve` | 5 |
| Proaktiv (Depot-Scan) | 6 |
| Regression + Folge-Aufgabe | 6 |

## Self-Review (durchgeführt)
- **Spec-Abdeckung:** alle Akzeptanzkriterien (§8) auf Tasks abgebildet; **Abweichung** dokumentiert: P3 nutzt Voll-Reuse statt deterministische Probe (Kosten trivial; skip_prose als Folge-Aufgabe). ✅
- **Platzhalter:** Kern-Logik (`ConflictItem`, `record_conflict`, Port, Scan) vollständig codiert; Adapter/CLI/Orchestrator-Tests an reale Fixtures angelehnt (Pfade per `grep`/Vorlage `SupabaseMemory`). ✅
- **Typ-Konsistenz:** `ConflictStorePort`-Methoden (Task 2) == genutzt in Task 3/4/5/6; `record_conflict(store, ticker, direction, verdict, reason, source)` (Task 2) == Aufrufe in Task 4/6; `_VERDICT_SEVERITY` HOLD<EXIT<REVERSE durchgängig. ✅
