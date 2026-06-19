# Konflikt-Agent (Thesis-Reversal) — Design

**Datum:** 2026-06-19
**Status:** Genehmigt (Design)
**Teil von:** Shorts-Programm (`docs/short.md` §18). Baut auf **1b** (`DeepDiveResult.conflict`/`conflict_reason`).

## Kontext & Ziel

1b erkennt **Konflikte** bidirektional (`conflict`-Flag): Titel **long** gehalten, screent aber als **Short** — oder umgekehrt. Ziel: ein **spezialisierter, LLM-gestützter Agent**, der bei einem Konflikt abwägt „Hat sich die gehaltene These wirklich gedreht?" und ein **beratendes** Reconciliation-Urteil liefert. Plus die **Haken der Lern-Schleife** (Persistenz + Backtester-Kontext), damit der Agent später kalibriert werden kann.

## Scope

**Im Block:**
- `ConflictResolution`-Modell + `DeepDiveResult.conflict_resolution`.
- `ConflictAgent` (LLM-gestützt) — Verdikt (`EXIT`/`HOLD`/`REVERSE`) + Begründung.
- **Bedingte** Orchestrierung im `judgment_orchestrator` (nur bei `conflict`).
- **Lern-Haken:** `conflict_resolution` wird mit der Analyse persistiert; der Agent **konsumiert `backtester_context`** (Track-Record im Prompt).
- Anzeige in `app/main.py`. Tests (LLM gemockt, TDD).

**Außerhalb (spätere Blöcke):**
- **Verdikt-Auswertung gegen Forward-Returns + Kalibrierungs-Befüllung** → **Block #4** (Backtest).
- **Handlungsverändernd** (Aktionen überschreiben) — bewusst **nicht** (beratend).
- PM-P&L-gestützte Verfeinerung (Block #3).

## Komponenten

### 1. `core/domain/models.py` — `ConflictResolution`
```python
@dataclass
class ConflictResolution:
    verdict: str       # "EXIT" | "HOLD" | "REVERSE"
    reasoning: str
```
`DeepDiveResult` als **letztes** Feld: `conflict_resolution: Optional["ConflictResolution"] = None`.

### 2. `agents/conflict/conflict_agent.py` (neu) — `ConflictAgent`
```python
class ConflictAgent:
    def __init__(self, llm: LLMProvider, bus: EventBus): ...
    async def run(self, ticker, current_position, recommendation, short_assessment,
                  conflict_reason, top_down_anomaly, bottom_up_anomaly,
                  backtester_context) -> ConflictResolution
```
- Baut einen Prompt aus **beiden Linsen**: Long-Empfehlung (`recommendation.action` + `reasoning`) **und** Short-Assessment (`short_action`/`confidence`/`archetypes`/`thesis_flags`), dem `conflict_reason`, den Anomalie-Summaries und — **falls vorhanden** — dem **eigenen Track-Record** aus `backtester_context` („deine EXIT-Calls lagen historisch zu X % richtig").
- System-Prompt: Rolle = Risk-Reconciliation-Spezialist; Aufgabe = abwägen, ob die gehaltene These gekippt ist; **Antwort beginnt mit `VERDICT: EXIT|HOLD|REVERSE`**, danach Begründung.
- Call: `await asyncio.to_thread(self.llm.complete, prompt, SYSTEM_PROMPT)`.
- **Verdikt-Parsing** (`_parse_verdict`): erste `VERDICT:`-Zeile → Token; akzeptiert nur EXIT/HOLD/REVERSE; **Fallback `HOLD`** wenn kein gültiges Token. `reasoning` = voller LLM-Text.
- Gibt `ConflictResolution(verdict, reasoning)` zurück; publiziert optional ein `*Ready`-Event (Konsistenz).

### 3. `orchestrators/judgment_orchestrator.py` — bedingter Schritt
- `__init__`: `self.conflict_agent = ConflictAgent(llm, bus)`.
- In `run()` **nach** dem `judgment_chief.run(...)` (das `result` inkl. `conflict` liefert) und **vor** `memory.save_analysis(...)`:
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
  (`current_position`, `td_anomaly`, `bu_anomaly`, `backtester_context` sind in `run()` vorhanden.) Läuft **nur** bei Konflikt → sonst null Kosten.

### 4. Persistenz (Lern-Haken)
`memory.save_analysis(result, cockpit, price=None)` wird bereits aufgerufen; `conflict_resolution` hängt am `result`. **Sicherstellen, dass die Memory-Serialisierung das Feld mitspeichert** (Adapter prüfen; falls die Persistenz selektiv ist, `verdict`/`reasoning` ergänzen). So kann **Block #4** die Verdikte später gegen Forward-Returns auswerten.

### 5. Anzeige (`app/main.py`)
Bei vorhandener `result.conflict_resolution`:
```python
    cr = result.conflict_resolution
    print(f"🔀 KONFLIKT-URTEIL: {cr.verdict}\n{cr.reasoning}")
```

## Datenfluss
`judgment_chief.run()` → `result` (mit `conflict`) → **wenn `conflict`**: `conflict_agent.run(beide Linsen + Anomalien + backtester_context)` → `ConflictResolution` ans `result` → `memory.save_analysis` (persistiert) → Anzeige.

## Fehlerbehandlung
- Agent-Call in `try/except` im Orchestrator → bei Fehler `conflict_resolution = None` (Konflikt-Flag + Grund werden trotzdem gezeigt).
- Parse-Fehler im Verdikt → `HOLD` + Roh-Text als `reasoning`.
- Kein Konflikt → Agent läuft nicht (keine LLM-Kosten).

## Tests (`tests/` — TDD, LLM IMMER gemockt)
- **ConflictAgent** (`test_conflict_agent.py`): Fake-LLM `.complete` → `"VERDICT: EXIT\nBegründung…"` ⇒ `verdict=="EXIT"`, `reasoning` enthält Text. Fake-LLM ohne `VERDICT:` ⇒ Fallback `HOLD`, `reasoning` = Roh-Text. Track-Record aus `backtester_context` taucht im übergebenen Prompt auf (Prompt-Assertion via Mock-`call_args`).
- **Orchestrierung** (`test_judgment_orchestrator_conflict.py` o. bestehende erweitern): `result.conflict=True` ⇒ `conflict_agent.run` aufgerufen, `result.conflict_resolution` gesetzt; `result.conflict=False` ⇒ Agent **nicht** aufgerufen, `conflict_resolution is None`.
- **Persistenz:** `conflict_resolution` übersteht den Memory-Round-Trip (falls Serialisierung selektiv: Feld-Test).
- **Regression:** Gesamtsuite grün.

## Akzeptanzkriterien
1. `ConflictResolution` + `DeepDiveResult.conflict_resolution` existieren.
2. `ConflictAgent` liefert ein gültiges Verdikt (EXIT/HOLD/REVERSE) + Begründung; Parse-Fehler → HOLD-Fallback; LLM in Tests gemockt.
3. Orchestrator ruft den Agenten **nur bei `conflict`** und hängt das Ergebnis ans `result`.
4. `conflict_resolution` wird mit der Analyse persistiert (Lern-Haken); der Agent konsumiert `backtester_context`.
5. Beratend — die formalen Aktionen bleiben unverändert.
6. Anzeige zeigt Verdikt + Begründung.
7. Gesamtsuite grün (0 failed).
