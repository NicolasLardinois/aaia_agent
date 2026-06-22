# ShortThesisAgent (LLM-Short-These + XAI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein LLM-Agent, der aus dem `ShortAssessment` zwei Texte erzeugt — `short_thesis` (angezeigt) + `short_xai` (persistiert) — symmetrisch zur Long-Seite.

**Architecture:** Separater Agent `ShortThesisAgent` (Muster `ConflictAgent`), vom `JudgmentOrchestrator` immer (null-sicher) aufgerufen; zwei sequenzielle LLM-Calls (These → XAI nutzt die These); defensiv `("", "")`. `short_xai` wird in `analysis_memory` persistiert (wie `xai_explanation`).

**Tech Stack:** Python, pytest, asyncio.

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-22-short-thesis-agent-design.md`.
- TDD Pflicht (roter Test zuerst). **LLM in allen Tests gemockt** (kein echter API-Call). Deutsche Kommentare/Prompts, Type Hints. Defensiv: jeder Fehlerpfad → `("", "")`/leer, nie Crash.
- Worktree `.claude/worktrees/short-thesis`, Branch `feat/short-thesis-agent`. PR-First — **nicht** mergen. Runner `python -m pytest -q`.
- „Immer" erzeugen (kein Thesen-Gating); `short_assessment is None` ist nur Null-Schutz. Long-Seite **nicht** anfassen.

---

## Task 1: `DeepDiveResult`-Felder + `ShortThesisReady`-Event

**Files:**
- Modify: `core/domain/models.py` (DeepDiveResult), `core/domain/events.py`
- Test: `tests/test_models.py` (oder vorhandene Modell-Testdatei; `grep -rl "DeepDiveResult(" tests/`)

**Interfaces:**
- Produces: `DeepDiveResult.short_thesis: str = ""`, `DeepDiveResult.short_xai: str = ""`; Event `ShortThesisReady`.

- [ ] **Step 1: Failing test**
```python
def test_deepdive_has_short_thesis_fields():
    from core.domain.events import ShortThesisReady
    # DeepDiveResult mit Minimalfeldern bauen (wie in Nachbartests) — Defaults greifen:
    # r = DeepDiveResult(ticker="X", asset_class="equity", market="USA",
    #                    top_down_context="", top_down_available=True, judgment="",
    #                    alignment="mixed", recommendation=<irgendeine InvestmentRecommendation>)
    assert r.short_thesis == "" and r.short_xai == ""
    ev = ShortThesisReady(source="short_thesis_agent", payload={"ticker": "X"})
    assert ev.payload["ticker"] == "X"
```
> An die reale `DeepDiveResult`-Konstruktion der Testdatei anpassen (Pflichtfelder wie in den Nachbartests).

- [ ] **Step 2: Run → FAIL** — `python -m pytest <modell-testdatei> -q` (AttributeError / ImportError).

- [ ] **Step 3: Implement**
  - `core/domain/models.py` — `DeepDiveResult` um zwei **trailing**-Felder erweitern (nach `conflict_reason`/`conflict_resolution`, am Ende der Dataclass):
    ```python
        short_thesis: str = ""
        short_xai: str = ""
    ```
  - `core/domain/events.py` — `ShortThesisReady` **analog `ConflictResolutionReady`** (gleiche Basisklasse/Felder `source`, `payload`).

- [ ] **Step 4: Run → PASS** — `python -m pytest <modell-testdatei> -q`.

- [ ] **Step 5: Commit** — `git add core/domain/models.py core/domain/events.py tests/ && git commit -m "feat(short): DeepDiveResult.short_thesis/short_xai + ShortThesisReady-Event"`

---

## Task 2: `ShortThesisAgent`

**Files:**
- Create: `agents/short_thesis/short_thesis_agent.py`
- Test: `tests/agents/short_thesis/test_short_thesis_agent.py`

**Interfaces:**
- Consumes: `ShortThesisReady` (Task 1).
- Produces: `ShortThesisAgent(llm, bus)` mit `async run(ticker, short_assessment, asset_class) -> tuple[str, str]`.

**ZUERST LESEN:** `agents/conflict/conflict_agent.py` (Muster: Prompt-Bau, `asyncio.to_thread(self.llm.complete, prompt, SYSTEM_PROMPT)`, Event, return).

- [ ] **Step 1: Failing tests** — `tests/agents/short_thesis/test_short_thesis_agent.py`:
```python
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import MagicMock
from core.domain.models import ShortAction
from agents.short_thesis.short_thesis_agent import ShortThesisAgent


def _sa():
    return NS(short_action=ShortAction.SHORT, confidence=0.62, archetypes=["distress"],
              thesis_flags=["Altman-Z 0.9 (Konkurszone)"], regime_effect="tailwind",
              squeeze_risk="low", hard_to_borrow=False, suggested_size_pct=3.0, stop_pct=15.0)


def test_returns_thesis_and_xai():
    llm = MagicMock(); llm.complete.side_effect = ["THESE-TEXT", "XAI-TEXT"]
    thesis, xai = asyncio.run(ShortThesisAgent(llm, MagicMock()).run("AAPL", _sa(), "equity"))
    assert thesis == "THESE-TEXT" and xai == "XAI-TEXT"
    assert llm.complete.call_count == 2
    assert "THESE-TEXT" in llm.complete.call_args_list[1][0][0]   # XAI-Prompt enthält die These


def test_none_assessment_returns_empty():
    llm = MagicMock()
    assert asyncio.run(ShortThesisAgent(llm, MagicMock()).run("AAPL", None, "equity")) == ("", "")
    llm.complete.assert_not_called()


def test_llm_error_returns_empty():
    llm = MagicMock(); llm.complete.side_effect = Exception("boom")
    assert asyncio.run(ShortThesisAgent(llm, MagicMock()).run("AAPL", _sa(), "equity")) == ("", "")
```
*(Lege fehlende `__init__.py` in den neuen Ordnern an, falls das Projekt das so macht — prüfe Nachbarn.)*

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/agents/short_thesis/test_short_thesis_agent.py -q`.

- [ ] **Step 3: Implement** — `agents/short_thesis/short_thesis_agent.py`:
```python
import asyncio

from core.domain.events import ShortThesisReady
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider

SHORT_SYSTEM_PROMPT = """Du bist ein erfahrener Leerverkaufs-Analyst (Short-Seller).
Formuliere aus den strukturierten Engine-Befunden eine klare, nüchterne Short-These (max. 6 Sätze).
Erkläre die deterministischen Befunde — erfinde nichts dazu. Liegt keine belastbare Kern-These vor,
sag klar, dass und warum kein überzeugendes Short-Setup besteht."""

SHORT_XAI_SYSTEM_PROMPT = """Du bist ein Finanzanalyst und erklärst eine Short-Einschätzung nachvollziehbar.
Erkläre ausführlich, warum die Engine zu dieser Short-Aktion und Konfidenz kommt — anhand der genannten
Flags/Archetypen/Regime/Squeeze. Bleib bei den gelieferten Fakten."""


def _assessment_block(sa) -> str:
    return (
        f"Short-Aktion: {sa.short_action.value} | Konfidenz: {sa.confidence:.0%}\n"
        f"Archetypen: {', '.join(sa.archetypes) or 'keine'}\n"
        f"Befunde (Flags): {'; '.join(sa.thesis_flags) or 'keine'}\n"
        f"Regime-Effekt: {sa.regime_effect} | Squeeze-Risiko: {sa.squeeze_risk} | "
        f"Hard-to-borrow: {sa.hard_to_borrow}\n"
        f"Größe: {sa.suggested_size_pct}% | Stop: {sa.stop_pct}%"
    )


class ShortThesisAgent:
    """Erzeugt aus dem deterministischen ShortAssessment eine Fließtext-These + XAI.
    Spiegelt die Long-Seite (judgment + xai_explanation); erklärt die Engine, erfindet nichts."""

    def __init__(self, llm: LLMProvider, bus: EventBus):
        self.llm = llm
        self.bus = bus

    async def run(self, ticker: str, short_assessment, asset_class: str) -> tuple[str, str]:
        if short_assessment is None:
            return "", ""
        try:
            block = _assessment_block(short_assessment)
            thesis_prompt = (f"Titel: {ticker} | Anlageklasse: {asset_class}\n\n"
                             f"ENGINE-BEFUNDE (Short):\n{block}\n\nFormuliere die Short-These.")
            thesis = await asyncio.to_thread(self.llm.complete, thesis_prompt, SHORT_SYSTEM_PROMPT)

            xai_prompt = (f"Titel: {ticker} | Short-Aktion: {short_assessment.short_action.value} | "
                          f"Konfidenz: {short_assessment.confidence:.0%}\n\n"
                          f"ENGINE-BEFUNDE (Short):\n{block}\n\n"
                          f"SHORT-THESE DES ANALYSTEN:\n{thesis}\n\n"
                          f"Erkläre ausführlich, warum diese Short-Einschätzung getroffen wurde.")
            xai = await asyncio.to_thread(self.llm.complete, xai_prompt, SHORT_XAI_SYSTEM_PROMPT)

            self.bus.publish(ShortThesisReady(source="short_thesis_agent",
                                              payload={"ticker": ticker}))
            return thesis, xai
        except Exception:
            return "", ""
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/agents/short_thesis/test_short_thesis_agent.py -q`.

- [ ] **Step 5: Commit** — `git add agents/short_thesis/ tests/agents/short_thesis/ && git commit -m "feat(short): ShortThesisAgent (These + XAI aus dem ShortAssessment)"`

---

## Task 3: Orchestrator-Verdrahtung (immer, null-sicher)

**Files:**
- Modify: `orchestrators/judgment_orchestrator.py`
- Test: `tests/test_judgment_orchestrator_conflict.py` (gleiche Datei wie die ConflictAgent-Orchestrator-Tests; sonst `grep -rl "JudgmentOrchestrator(" tests/`)

**Interfaces:**
- Consumes: `ShortThesisAgent` (Task 2), `DeepDiveResult.short_thesis/short_xai` (Task 1).

- [ ] **Step 1: Failing test**
```python
def test_orchestrator_fills_short_thesis(monkeypatch):
    # Orchestrator wie in den Nachbartests bauen (gemockte llm/bus/memory).
    orch = ...
    async def _fake_run(ticker, sa, ac): return ("T", "X")
    orch.short_thesis_agent.run = _fake_run
    # run(...) mit Cockpit/BottomUp wie in den Nachbartests; result muss gefüllt sein:
    result = asyncio.run(orch.run(...))
    assert result.short_thesis == "T" and result.short_xai == "X"
```
> An die reale Orchestrator-Test-Fixture anpassen (gleiche Mocks/Aufrufe wie die ConflictAgent-Tests in der Datei). Ziel: nach `run()` sind `result.short_thesis/short_xai` aus dem (gemockten) Agenten gefüllt.

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_judgment_orchestrator_conflict.py -q`.

- [ ] **Step 3: Implement** — `orchestrators/judgment_orchestrator.py`:
  - Import: `from agents.short_thesis.short_thesis_agent import ShortThesisAgent`.
  - `__init__`: `self.short_thesis_agent = ShortThesisAgent(llm, bus)`.
  - In `run()` **nach** dem `if result.conflict:`-Block und **vor** `self.memory.save_analysis(...)`:
    ```python
            if result.short_assessment is not None:
                try:
                    result.short_thesis, result.short_xai = await self.short_thesis_agent.run(
                        bottom_up.ticker, result.short_assessment, result.asset_class)
                except Exception:
                    result.short_thesis, result.short_xai = "", ""
    ```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_judgment_orchestrator_conflict.py -q`.

- [ ] **Step 5: Commit** — `git add orchestrators/judgment_orchestrator.py tests/ && git commit -m "feat(short): ShortThesisAgent im JudgmentOrchestrator verdrahtet (immer, null-sicher)"`

---

## Task 4: Anzeige + Persistenz (short_xai) + Regression

**Files:**
- Modify: `app/main.py` (Anzeige), `adapters/memory/supabase_memory.py` (INSERT), `db/schema.sql` (Spalte)
- Test: `tests/test_supabase_memory.py` (oder vorhandene save_analysis-Testdatei; `grep -rl "save_analysis" tests/`)

- [ ] **Step 1: Failing test** — save_analysis übergibt `short_xai` an den INSERT:
```python
def test_save_analysis_persists_short_xai():
    # save_analysis mit gemocktem DB-Connect/Cursor (wie die bestehenden Tests dort);
    # result.short_xai = "SX". Nach save_analysis muss "SX" in den INSERT-Parametern stehen.
    ...
    assert "SX" in _executed_params(cur)   # an die reale Mock-Assertion der Datei anpassen
```
> An die bestehenden `save_analysis`-Tests anlehnen (die mocken `psycopg`/Cursor und prüfen die Parameter). Falls keine solche Testdatei existiert, diesen Test weglassen und die Persistenz über die **Regression** + manuelles Code-Review absichern (im Report vermerken).

- [ ] **Step 2: Run → FAIL** (falls Test vorhanden).

- [ ] **Step 3: Implement**
  - `app/main.py` — nach `print(f"\nURTEIL:\n{result.judgment}")`:
    ```python
        if result.short_thesis:
            print(f"\nSHORT-THESE:\n{result.short_thesis}")
    ```
  - `adapters/memory/supabase_memory.py` — im `INSERT INTO analysis_memory`:
    - in die **Spaltenliste** nach `xai_explanation` ein `short_xai` ergänzen,
    - **ein** zusätzliches `%s` in die `VALUES (...)`-Klausel,
    - in das **Werte-Tupel** nach `result.xai_explanation` ein `result.short_xai` ergänzen.
    (Alle drei müssen ausgerichtet bleiben — Spaltenzahl == Platzhalterzahl == Tupellänge.)
  - `db/schema.sql` — `analysis_memory` um `short_xai text` ergänzen (autoritatives Schema synchron halten).

- [ ] **Step 4: Run → PASS** (gezielter Test, falls vorhanden).

- [ ] **Step 5: Gesamt-Regression** — `python -m pytest -q` → **0 failed** (~3 Min). Bei Fehlern: Ursache beheben (superpowers:systematic-debugging).

- [ ] **Step 6: Commit** — `git add app/main.py adapters/memory/supabase_memory.py db/schema.sql tests/ && git commit -m "feat(short): SHORT-THESE-Anzeige + short_xai persistiert (Spalte) + Regression gruen"`

> **⚠️ Deploy-Schritt (manuell, vor Merge/Deploy):** einmalig auf Supabase `ALTER TABLE analysis_memory ADD COLUMN short_xai text;` ausführen, sonst schlägt jeder `save_analysis`-INSERT fehl.

---

## Abdeckung (Spec → Task)
| Spec-Element | Task |
|---|---|
| `DeepDiveResult.short_thesis/short_xai` + Event | 1 |
| `ShortThesisAgent` (2 LLM-Calls, XAI nutzt These, defensiv) | 2 |
| Orchestrator ruft immer (null-sicher), füllt Felder | 3 |
| CLI zeigt SHORT-THESE | 4 |
| short_xai persistiert (Spalte + Migration + schema.sql) | 4 |
| Regression | 4 |

## Self-Review (durchgeführt)
- **Spec-Abdeckung:** alle Akzeptanzkriterien (§7) auf Tasks abgebildet (Agent T2, Felder T1, Orchestrator T3, Anzeige+Persistenz T4). ✅
- **Platzhalter:** Agent/Event/Wiring vollständig codiert. Drei Stellen bewusst an reale Test-Fixtures angepasst (Modell-, Orchestrator-, save_analysis-Testdatei) — Pfade per `grep`; Verhalten eindeutig. ✅
- **Typ-Konsistenz:** `run(ticker, short_assessment, asset_class) -> tuple[str,str]` (T2) == Aufruf in T3; `short_thesis`/`short_xai` (T1) gelesen in T3/T4; `ShortThesisReady` (T1) genutzt in T2. ✅
