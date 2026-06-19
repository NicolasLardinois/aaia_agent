# Konflikt-Agent (Thesis-Reversal) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Ein LLM-gestützter `ConflictAgent`, der bei `DeepDiveResult.conflict` ein beratendes `ConflictResolution` (EXIT/HOLD/REVERSE + Begründung) liefert; bedingt im `judgment_orchestrator` verdrahtet, persistiert (Lern-Haken), angezeigt.

**Architecture:** Neuer Agent analog `JudgmentAgent` (LLM via `asyncio.to_thread(self.llm.complete, ...)`); bedingter Call im Orchestrator; LLM in Tests immer gemockt.

**Tech Stack:** Python, asyncio, dataclasses, pytest.

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-19-konflikt-agent-design.md`. Design: `docs/short.md` §18.
- **Beratend** — formale Aktionen bleiben unverändert.
- Agent läuft **nur bei `conflict`**. LLM in Tests **immer gemockt** (kein echter Call).
- Branch `feat/conflict-agent`. PR-First. Runner `python -m pytest -q`. Am Ende (Task 4) Gesamtsuite grün.

---

## Task 1: `ConflictResolution`-Modell + `DeepDiveResult`-Feld

**Files:** Modify `core/domain/models.py`; Test `tests/test_conflict_resolution_model.py` (Create).

- [ ] **Step 1: Failing test** — `tests/test_conflict_resolution_model.py`:
```python
import dataclasses
from core.domain.models import ConflictResolution, DeepDiveResult


def test_conflict_resolution_fields():
    cr = ConflictResolution(verdict="EXIT", reasoning="weil…")
    assert cr.verdict == "EXIT" and cr.reasoning == "weil…"


def test_deepdive_has_conflict_resolution_field():
    names = {f.name for f in dataclasses.fields(DeepDiveResult)}
    assert "conflict_resolution" in names
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_conflict_resolution_model.py -q`.

- [ ] **Step 3: Implement** — in `core/domain/models.py` (vor `DeepDiveResult`):
```python
@dataclass
class ConflictResolution:
    verdict: str       # "EXIT" | "HOLD" | "REVERSE"
    reasoning: str
```
und in `DeepDiveResult` als **letztes** Feld: `conflict_resolution: Optional["ConflictResolution"] = None`.

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_conflict_resolution_model.py -q`.

- [ ] **Step 5: Commit** — `git add core/domain/models.py tests/test_conflict_resolution_model.py && git commit -m "feat(conflict): ConflictResolution-Modell + DeepDiveResult.conflict_resolution"`

---

## Task 2: `ConflictAgent` (LLM)

**Files:** Create `agents/conflict/__init__.py` (leer), `agents/conflict/conflict_agent.py`; Test `tests/test_conflict_agent.py` (Create).

**Interfaces:** Produces `ConflictAgent(llm, bus)`, `async run(ticker, current_position, recommendation, short_assessment, conflict_reason, top_down_anomaly, bottom_up_anomaly, backtester_context) -> ConflictResolution`; `_parse_verdict(text) -> str`.

- [ ] **Step 1: Failing test** — `tests/test_conflict_agent.py`:
```python
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

from agents.conflict.conflict_agent import ConflictAgent, _parse_verdict


class _LLM:
    def __init__(self, resp): self.resp = resp; self.last_prompt = None
    def complete(self, prompt, system):
        self.last_prompt = prompt
        return self.resp


def _rec():
    return NS(action=NS(value="HOLD"), reasoning="Long-These intakt.")


def _sa():
    return NS(short_action=NS(value="NONE"), confidence=0.72, archetypes=["distress"],
              thesis_flags=["Altman-Z 1.2 (Konkurszone)"])


def _run(resp, bt=None):
    agent = ConflictAgent(_LLM(resp), MagicMock())
    from core.domain.models import PositionState, AnomalyReport
    return agent, asyncio.run(agent.run(
        ticker="X", current_position=PositionState.LONG, recommendation=_rec(),
        short_assessment=_sa(), conflict_reason="Long gehalten, screent als Short",
        top_down_anomaly=AnomalyReport.empty(), bottom_up_anomaly=AnomalyReport.empty(),
        backtester_context=bt))


def test_parses_verdict():
    assert _parse_verdict("VERDICT: EXIT\nGründe…") == "EXIT"
    assert _parse_verdict("verdict: reverse\n…") == "REVERSE"


def test_run_returns_resolution():
    _, cr = _run("VERDICT: EXIT\nDie These ist gekippt.")
    assert cr.verdict == "EXIT"
    assert "gekippt" in cr.reasoning


def test_parse_fallback_hold():
    _, cr = _run("Ich bin unsicher, keine klare Aussage.")
    assert cr.verdict == "HOLD"


def test_track_record_in_prompt():
    agent, _ = _run("VERDICT: HOLD\n…", bt={"hit_rate": 0.65})
    assert "65" in agent.llm.last_prompt or "0.65" in agent.llm.last_prompt
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_conflict_agent.py -q`.

- [ ] **Step 3: Implement** — `agents/conflict/__init__.py` (leer) + `agents/conflict/conflict_agent.py`:
```python
import asyncio

from core.domain.models import ConflictResolution
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider

SYSTEM_PROMPT = """Du bist ein Risk-Reconciliation-Spezialist. Eine bestehende Position
widerspricht der aktuellen Analyse. Wäge nüchtern ab, ob die ursprüngliche These gekippt ist.
Antworte in der ERSTEN Zeile mit GENAU einem von: `VERDICT: EXIT`, `VERDICT: HOLD`, `VERDICT: REVERSE`.
Danach eine kurze, klare Begründung (max. 5 Sätze).
EXIT = Ausstieg empfohlen (SELL bei Long / COVER bei Short); HOLD = These hält trotz Gegenwind;
REVERSE = Ausstieg + Gegenposition (aggressiv)."""

_VALID = {"EXIT", "HOLD", "REVERSE"}


def _parse_verdict(text: str) -> str:
    for line in (text or "").splitlines():
        s = line.strip().upper()
        if s.startswith("VERDICT:"):
            tok = s.split(":", 1)[1].strip().split()[0] if len(s.split(":", 1)) > 1 else ""
            if tok in _VALID:
                return tok
    up = (text or "").upper()
    for v in ("EXIT", "REVERSE", "HOLD"):
        if v in up:
            return v
    return "HOLD"


class ConflictAgent:
    def __init__(self, llm: LLMProvider, bus: EventBus):
        self.llm = llm
        self.bus = bus

    async def run(self, ticker, current_position, recommendation, short_assessment,
                  conflict_reason, top_down_anomaly, bottom_up_anomaly, backtester_context):
        track = ""
        if backtester_context:
            hr = backtester_context.get("hit_rate")
            if hr is not None:
                track = f"\nSYSTEM-TRACK-RECORD (Kontext): historische Treffsicherheit {hr:.0%}"

        long_line = f"LONG-LESART: {recommendation.action.value} — {recommendation.reasoning}"
        if short_assessment:
            sa = short_assessment
            short_line = (f"SHORT-LESART: {sa.short_action.value}, Konfidenz {sa.confidence:.0%}, "
                          f"Typ {', '.join(sa.archetypes) or 'n/v'}; "
                          f"Gründe: {'; '.join(sa.thesis_flags) or 'n/v'}")
        else:
            short_line = "SHORT-LESART: n/v"

        prompt = f"""Titel: {ticker} | Gehaltene Position: {current_position.value}
KONFLIKT: {conflict_reason}

{long_line}
{short_line}

ANOMALIEN:
{top_down_anomaly.summary}
{bottom_up_anomaly.summary}{track}

Hat sich die gehaltene These wirklich gedreht? Verdikt + Begründung."""

        text = await asyncio.to_thread(self.llm.complete, prompt, SYSTEM_PROMPT)
        return ConflictResolution(verdict=_parse_verdict(text), reasoning=text)
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_conflict_agent.py -q` (4 passed).

- [ ] **Step 5: Commit** — `git add agents/conflict/ tests/test_conflict_agent.py && git commit -m "feat(conflict): ConflictAgent (LLM, Verdikt-Parsing, Fallback HOLD)"`

---

## Task 3: Orchestrierung (bedingter Call)

**Files:** Modify `orchestrators/judgment_orchestrator.py`; Test `tests/test_judgment_orchestrator_conflict.py` (Create).

- [ ] **Step 1: Failing test** — `tests/test_judgment_orchestrator_conflict.py`:
```python
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

from orchestrators.judgment_orchestrator import JudgmentOrchestrator
from core.domain.models import (
    DeepDiveResult, InvestmentRecommendation, Recommendation, AnomalyReport,
    ConflictResolution, PositionState,
)


def _result(conflict):
    rec = InvestmentRecommendation(action=Recommendation.HOLD, short_type=None,
                                   short_warning=None, confidence=0.6, reasoning="x")
    return DeepDiveResult(
        ticker="X", asset_class="equity", market="USA", top_down_context="",
        top_down_available=True, judgment="", alignment="mixed", recommendation=rec,
        conflict=conflict, conflict_reason=("Konflikt" if conflict else ""))


def _orch(result):
    o = JudgmentOrchestrator.__new__(JudgmentOrchestrator)
    o.memory = MagicMock()
    o.memory.load_history.return_value = []
    o.memory.load_global_history.return_value = []
    o.anomaly_chief = MagicMock()
    o.anomaly_chief.run.return_value = (AnomalyReport.empty(), AnomalyReport.empty())
    o.backtester_chief = MagicMock()
    o.backtester_chief.load_context.return_value = {}
    o.judgment_chief = MagicMock()
    o.judgment_chief.run = AsyncMock(return_value=result)
    o.conflict_agent = MagicMock()
    o.conflict_agent.run = AsyncMock(return_value=ConflictResolution(verdict="EXIT", reasoning="r"))
    return o


def _bottom_up():
    return NS(ticker="X", asset_class="equity")


def test_conflict_triggers_agent():
    res = _result(conflict=True)
    o = _orch(res)
    out = asyncio.run(o.run(cockpit=None, bottom_up=_bottom_up(), market="USA",
                            current_position=PositionState.LONG))
    o.conflict_agent.run.assert_awaited_once()
    assert out.conflict_resolution.verdict == "EXIT"


def test_no_conflict_skips_agent():
    res = _result(conflict=False)
    o = _orch(res)
    out = asyncio.run(o.run(cockpit=None, bottom_up=_bottom_up(), market="USA",
                            current_position=PositionState.NONE))
    o.conflict_agent.run.assert_not_awaited()
    assert out.conflict_resolution is None
```
> Hinweis: Falls `JudgmentOrchestrator.run` `cockpit=None` → `top_down_available=False` macht und früher zurückkehrt, ist das ok — die Tests setzen `conflict` direkt am gemockten judgment_chief-Result und prüfen nur die Konflikt-Verzweigung. Bei Abweichung den Mock an die reale `run`-Struktur anpassen.

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_judgment_orchestrator_conflict.py -q`.

- [ ] **Step 3: Implement** — `orchestrators/judgment_orchestrator.py`:
  - Import: `from agents.conflict.conflict_agent import ConflictAgent`.
  - `__init__`: `self.conflict_agent = ConflictAgent(llm, bus)`.
  - In `run()` **nach** `result.top_down_anomaly = td_anomaly` / `result.bottom_up_anomaly = bu_anomaly` und **vor** `self.memory.save_analysis(...)` einfügen:
    ```python
    if result.conflict:
        try:
            result.conflict_resolution = await self.conflict_agent.run(
                ticker=bottom_up.ticker, current_position=current_position,
                recommendation=result.recommendation, short_assessment=result.short_assessment,
                conflict_reason=result.conflict_reason,
                top_down_anomaly=td_anomaly, bottom_up_anomaly=bu_anomaly,
                backtester_context=backtester_context)
        except Exception:
            result.conflict_resolution = None
    ```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_judgment_orchestrator_conflict.py -q`.

- [ ] **Step 5: Commit** — `git add orchestrators/judgment_orchestrator.py tests/test_judgment_orchestrator_conflict.py && git commit -m "feat(conflict): bedingte Orchestrierung im judgment_orchestrator"`

---

## Task 4: Persistenz-Haken + Anzeige + Gesamt-Regression

**Files:** Modify Memory-Adapter(s) (`adapters/memory/*.py`), `app/main.py`; ggf. Tests.

- [ ] **Step 1: Persistenz-Haken** — `grep -rn "def save_analysis" adapters/memory/`. In jeder `save_analysis`-Implementierung, die einen Snapshot/`indicators`-Dict baut und speichert, den Verdikt ergänzen (vor dem Schreiben):
  ```python
  if getattr(result, "conflict_resolution", None):
      indicators["conflict_verdict"] = result.conflict_resolution.verdict
  ```
  (Variablenname an den jeweiligen Adapter anpassen — der Wert kommt in denselben Snapshot wie `pe_ratio`/`short_float_pct`.) Das ist der **Vorwärts-Haken**; die Auswertung gegen Forward-Returns ist Block #4.

- [ ] **Step 2: Anzeige** — `app/main.py`, nach der bestehenden Konflikt-Ausgabe:
  ```python
      if result.conflict_resolution:
          cr = result.conflict_resolution
          print(f"🔀 KONFLIKT-URTEIL: {cr.verdict}\n{cr.reasoning}")
  ```

- [ ] **Step 3: Bestehende Tests prüfen** — `grep -rn "save_analysis\|conflict" tests/`; falls ein Memory- oder Orchestrator-Test durch das neue Snapshot-Feld bricht, fachlich korrekt anpassen (nicht verbiegen).

- [ ] **Step 4: Gesamt-Regression** — `python -m pytest -q` → **0 failed** (~3 Min). Bei Fehlern: superpowers:systematic-debugging.

- [ ] **Step 5: Commit** — `git add adapters/ app/ tests/ && git commit -m "feat(conflict): Persistenz-Haken (conflict_verdict) + Anzeige + Regression gruen"`

---

## Abdeckung (Spec → Task)
| Spec-Element | Task |
|---|---|
| `ConflictResolution` + `DeepDiveResult`-Feld | 1 |
| `ConflictAgent` (LLM, Verdikt, Fallback, backtester_context-Konsum) | 2 |
| Bedingte Orchestrierung (nur bei conflict) | 3 |
| Persistenz-Haken + Anzeige | 4 |
| Lern-Haken (Persistenz + Track-Record im Prompt) | 2 + 4 |
| Beratend (Aktionen unverändert) | by design (kein Override) |

## Self-Review (durchgeführt)
- **Spec-Abdeckung:** alle Komponenten je Task. ✅
- **Platzhalter:** ConflictAgent + Parsing vollständig; Orchestrator-Test mockt die Kette; Persistenz-Task per Grep an reale Adapter angepasst. ✅
- **Typ-Konsistenz:** `ConflictAgent.run`-Signatur identisch Task 2 (Def) / Task 3 (Aufruf); `ConflictResolution(verdict, reasoning)` einheitlich. ✅
- **LLM in Tests gemockt** (Fake-`complete`). ✅
