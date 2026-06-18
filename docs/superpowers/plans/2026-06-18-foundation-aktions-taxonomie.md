# Foundation-Block: Aktions-Taxonomie (long + short) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Long-Empfehlung auf eine saubere Aktions-Taxonomie (BUY/BUY+/HOLD/SELL/NONE) umstellen, den naiven SHORT entfernen, `current_position` (none/long/short) einführen und die leere Short-Aktions-Hülle (`ShortAction`) anlegen.

**Architecture:** Reine Domänenfunktionen (`derive_recommendation`, neuer Short-Platzhalter) über vorhandene Snapshots; Enums in `core/domain/models.py`; Verdrahtung durch die Judgment-Kette (orchestrator → chief → agent) + CLI/Anzeige. Kein LLM, keine neue Datenquelle.

**Tech Stack:** Python, dataclasses/Enum, pytest.

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-18-foundation-aktions-taxonomie-design.md`.
- **`derive_recommendation` gibt nie SHORT aus** (Member bleibt im Enum für Altreferenzen).
- **HOLD nur bei gehaltener Long-Position; NONE nur bei nicht-gehaltener.**
- **Defer-Symmetrie:** `current_position == SHORT` → Long-Linse NONE; `== LONG` → Short-Platzhalter NONE.
- Branch `feat/shorts-foundation`. Runner: `python -m pytest -q`. Zwischen Tasks darf die Gesamtsuite kurz rot sein (Signatur-Umstellung); **am Ende (Task 4) grün**.

---

## Task 1: Enums (Recommendation +NONE/+BUY+, ShortAction, PositionState)

**Files:**
- Modify: `core/domain/models.py` (Enum-Block ~Zeile 26–35)
- Test: `tests/test_action_enums.py` (Create)

**Interfaces:**
- Produces: `Recommendation.BUY_PLUS` (`"BUY+"`), `Recommendation.NONE` (`"NONE"`); `class ShortAction(str, Enum)` {SHORT, SHORT_PLUS, HOLD, COVER, NONE}; `class PositionState(str, Enum)` {NONE="none", LONG="long", SHORT="short"}.

- [ ] **Step 1: Failing test** — `tests/test_action_enums.py`:
```python
from core.domain.models import Recommendation, ShortAction, PositionState


def test_recommendation_has_new_members():
    assert Recommendation.BUY_PLUS.value == "BUY+"
    assert Recommendation.NONE.value == "NONE"
    assert Recommendation.SHORT.value == "SHORT"  # transitional, bleibt


def test_short_action_members():
    assert {a.value for a in ShortAction} == {"SHORT", "SHORT+", "HOLD", "COVER", "NONE"}


def test_position_state_members():
    assert PositionState.NONE.value == "none"
    assert PositionState.LONG.value == "long"
    assert PositionState.SHORT.value == "short"
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_action_enums.py -q` (ImportError/AttributeError erwartet).

- [ ] **Step 3: Implement** — in `core/domain/models.py` den Enum-Block erweitern:
```python
class Recommendation(str, Enum):
    BUY      = "BUY"
    BUY_PLUS = "BUY+"
    HOLD     = "HOLD"
    SELL     = "SELL"
    NONE     = "NONE"
    SHORT    = "SHORT"   # transitional: nicht mehr von derive_recommendation ausgegeben


class ShortAction(str, Enum):
    SHORT      = "SHORT"
    SHORT_PLUS = "SHORT+"
    HOLD       = "HOLD"
    COVER      = "COVER"
    NONE       = "NONE"


class PositionState(str, Enum):
    NONE  = "none"
    LONG  = "long"
    SHORT = "short"
```
(`ShortType` unverändert lassen.)

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_action_enums.py -q` (3 passed).

- [ ] **Step 5: Commit** — `git add core/domain/models.py tests/test_action_enums.py && git commit -m "feat(taxonomy): Enums Recommendation+NONE/+BUY+, ShortAction, PositionState"`

---

## Task 2: `derive_recommendation` — neue Long-Matrix

**Files:**
- Modify: `core/domain/recommendation.py` (`derive_recommendation`, ~Zeile 99–184)
- Test: `tests/test_recommendation_taxonomy.py` (Create)
- Modify (Altlasten): bestehende Tests, die `derive_recommendation(..., in_portfolio=...)` aufrufen — anpassen (siehe Step 5).

**Interfaces:**
- Consumes: `PositionState`, `Recommendation`, `Signal`, `_position_size_pct` (bereits im Modul).
- Produces: `derive_recommendation(alignment, signal, asset_class, current_position: PositionState, market, cockpit, top_down_available, confidence) -> InvestmentRecommendation`. Signatur **ohne** `in_portfolio`, `days_to_cover`, `short_float_pct`.

- [ ] **Step 1: Failing test** — `tests/test_recommendation_taxonomy.py`:
```python
from core.domain.models import Recommendation, PositionState, Signal
from core.domain.recommendation import derive_recommendation


def _rec(signal, pos, conf=0.7, alignment="mixed"):
    return derive_recommendation(
        alignment=alignment, signal=signal, asset_class="equity",
        current_position=pos, market="USA", cockpit=None,
        top_down_available=True, confidence=conf,
    ).action


def test_not_held_bullish_is_buy():
    assert _rec(Signal.BULLISH, PositionState.NONE) == Recommendation.BUY


def test_not_held_bearish_is_none():
    assert _rec(Signal.BEARISH, PositionState.NONE) == Recommendation.NONE


def test_not_held_neutral_is_none():
    assert _rec(Signal.NEUTRAL, PositionState.NONE) == Recommendation.NONE


def test_long_bullish_is_buy_plus():
    assert _rec(Signal.BULLISH, PositionState.LONG) == Recommendation.BUY_PLUS


def test_long_neutral_is_hold():
    assert _rec(Signal.NEUTRAL, PositionState.LONG) == Recommendation.HOLD


def test_long_bearish_is_sell():
    assert _rec(Signal.BEARISH, PositionState.LONG) == Recommendation.SELL


def test_short_position_long_lens_defers_to_none():
    for sig in (Signal.BULLISH, Signal.BEARISH, Signal.NEUTRAL):
        assert _rec(sig, PositionState.SHORT) == Recommendation.NONE


def test_low_confidence_held_is_hold_not_held_is_none():
    assert _rec(Signal.BULLISH, PositionState.LONG, conf=0.4) == Recommendation.HOLD
    assert _rec(Signal.BULLISH, PositionState.NONE, conf=0.4) == Recommendation.NONE


def test_never_emits_short():
    actions = {_rec(s, p) for s in (Signal.BULLISH, Signal.BEARISH, Signal.NEUTRAL)
               for p in PositionState}
    assert Recommendation.SHORT not in actions
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_recommendation_taxonomy.py -q`.

- [ ] **Step 3: Implement** — `core/domain/recommendation.py`: oben `PositionState` importieren (z. B. `from core.domain.models import ..., PositionState`). `derive_recommendation` **vollständig ersetzen**:
```python
def derive_recommendation(
    alignment: str,
    signal: Signal,
    asset_class: str,
    current_position: PositionState,
    market: str,
    cockpit: Optional[CockpitResult],
    top_down_available: bool,
    confidence: float,
) -> InvestmentRecommendation:
    # Titel als Short gehalten → Long-Linse deferiert (kein "BUY, obwohl short").
    if current_position == PositionState.SHORT:
        return InvestmentRecommendation(
            action=Recommendation.NONE, short_type=None, short_warning=None,
            confidence=confidence,
            reasoning="Titel als Short gehalten — Long-Seite deferiert (Short-Linse/PM zuständig).",
        )

    is_long = current_position == PositionState.LONG
    bearish = signal == Signal.BEARISH or alignment == "aligned_bearish"
    bullish = signal == Signal.BULLISH or alignment == "aligned_bullish"

    # Uneindeutig/anomal → keine Aktion (positionsabhängig)
    if confidence < 0.50:
        action = Recommendation.HOLD if is_long else Recommendation.NONE
        reasoning = ("Stark widersprüchliche/anomale Signale — Cash bevorzugen, kein neues Kapital."
                     if confidence < 0.35 else
                     "Signallage zu widersprüchlich — Abwarten empfohlen.")
        return InvestmentRecommendation(action, None, None, confidence, reasoning)

    if is_long:
        if bearish:
            action = Recommendation.SELL
            reasoning = "Bearish bei bestehender Long-Position — Verkauf empfohlen."
        elif bullish:
            size = _position_size_pct(confidence)
            action = Recommendation.BUY_PLUS
            reasoning = (f"Bullish bei bestehender Long-Position — Aufstocken. "
                         f"Zusätzliche Tranche ~{size:.1f}% des Risikobudgets (konfidenz-skaliert).")
        else:
            action = Recommendation.HOLD
            reasoning = "Kein klares Signal — Position halten."
    else:  # PositionState.NONE
        if bullish:
            size = _position_size_pct(confidence)
            action = Recommendation.BUY
            reasoning = (f"Bullish ohne bestehende Position — Kauf empfohlen. "
                         f"Empfohlene Positionsgröße: {size:.1f}% des Risikobudgets (konfidenz-skaliert).")
        else:
            action = Recommendation.NONE
            reasoning = "Kein Long-Setup (kein bullisches Signal)."

    return InvestmentRecommendation(action, None, None, confidence, reasoning)
```
> Der alte SHORT-Zweig + die Parameter `days_to_cover`/`short_float_pct` entfallen. `_short_type`, `SHORT_WARNINGS`, `_DTC_SQUEEZE_THRESHOLD`, `FULL_ANALYSIS_MARKETS` im Modul **belassen** (Wiederverwendung in Block 1). `market`/`cockpit`/`top_down_available` bleiben in der Signatur (ungenutzt, fürs Block-1-Short-Gate).

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_recommendation_taxonomy.py -q`.

- [ ] **Step 5: Altlasten-Tests anpassen** — bestehende Aufrufe von `derive_recommendation` finden und auf die neue Signatur umstellen (`in_portfolio=True` → `current_position=PositionState.LONG`, `in_portfolio=False` → `PositionState.NONE`; SHORT-Erwartungen → NONE):
```bash
grep -rn "derive_recommendation\|in_portfolio" tests/test_domain_extensions.py tests/test_confidence.py
```
Betroffene Asserts entsprechend der neuen Matrix korrigieren. Danach: `python -m pytest tests/test_domain_extensions.py tests/test_confidence.py tests/test_recommendation_taxonomy.py -q` → grün. *(Integration/judgment-Tests bleiben evtl. rot bis Task 3 — ok.)*

- [ ] **Step 6: Commit** — `git add core/domain/recommendation.py tests/ && git commit -m "feat(taxonomy): derive_recommendation Long-Matrix (BUY/BUY+/HOLD/SELL/NONE), SHORT entfernt, current_position"`

---

## Task 3: Short-Aktions-Platzhalter + `DeepDiveResult.short_action` + Verdrahtung

**Files:**
- Modify: `core/domain/recommendation.py` (Platzhalter-Funktion)
- Modify: `core/domain/models.py` (`DeepDiveResult` Feld)
- Modify: `agents/judgment/judgment_agent.py`, `agents/judgment_chief_agent.py`, `orchestrators/judgment_orchestrator.py` (Verdrahtung `in_portfolio` → `current_position`, `short_action` setzen)
- Test: `tests/test_short_action_placeholder.py` (Create); bestehende judgment-Tests anpassen.

**Interfaces:**
- Produces: `derive_short_action_placeholder(current_position: PositionState) -> ShortAction`; `DeepDiveResult.short_action: ShortAction` (Default `ShortAction.NONE`).
- Consumes (Verdrahtung): `JudgmentAgent.run(..., current_position: PositionState, ...)`, `JudgmentChiefAgent.run(..., current_position, ...)`, `JudgmentOrchestrator.run(..., current_position: PositionState = PositionState.NONE, ...)`.

- [ ] **Step 1: Failing test** — `tests/test_short_action_placeholder.py`:
```python
from core.domain.models import ShortAction, PositionState
from core.domain.recommendation import derive_short_action_placeholder


def test_short_position_holds():
    assert derive_short_action_placeholder(PositionState.SHORT) == ShortAction.HOLD


def test_long_defers_to_none():
    assert derive_short_action_placeholder(PositionState.LONG) == ShortAction.NONE


def test_flat_is_none():
    assert derive_short_action_placeholder(PositionState.NONE) == ShortAction.NONE
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_short_action_placeholder.py -q`.

- [ ] **Step 3a: Platzhalter** — in `core/domain/recommendation.py` ergänzen (ggf. `ShortAction` importieren):
```python
def derive_short_action_placeholder(current_position: PositionState) -> ShortAction:
    """Platzhalter bis zur Short-Thesis-Engine (Block 1).
    short gehalten → HOLD; sonst → NONE (bei LONG deferiert die Short-Linse —
    man shortet nicht, was man besitzt). Block 1 muss Defer-on-LONG beibehalten."""
    return ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE
```

- [ ] **Step 3b: Modell-Feld** — `core/domain/models.py`, `DeepDiveResult` als **letztes** Feld:
```python
    short_action: ShortAction = ShortAction.NONE
```

- [ ] **Step 3c: Verdrahtung** — `in_portfolio: bool` → `current_position: PositionState` durchreichen:
  - `orchestrators/judgment_orchestrator.py`: `run(..., in_portfolio: bool = False, ...)` → `current_position: PositionState = PositionState.NONE`; an `judgment_chief.run(...)` `current_position=current_position` übergeben (statt `in_portfolio=in_portfolio`).
  - `agents/judgment_chief_agent.py`: `run(..., in_portfolio, ...)` → `current_position: PositionState`; an `judgment_agent.run(...)` weiterreichen. Import `PositionState` ergänzen.
  - `agents/judgment/judgment_agent.py`: `run(..., in_portfolio, ...)` → `current_position: PositionState`; im `derive_recommendation(...)`-Aufruf `current_position=current_position` (statt `in_portfolio=...`); die jetzt entfallenen Args `days_to_cover`/`short_float_pct` aus dem Aufruf entfernen, falls vorhanden. Nach `recommendation = ...` ergänzen:
    ```python
    short_action = derive_short_action_placeholder(current_position)
    ```
    und im `DeepDiveResult(...)` `short_action=short_action` setzen. Import `derive_short_action_placeholder`, `PositionState` ergänzen.

- [ ] **Step 4: Run → PASS (Platzhalter)** — `python -m pytest tests/test_short_action_placeholder.py -q`.

- [ ] **Step 5: judgment-Tests anpassen** — Aufrufe der Judgment-Kette mit `in_portfolio=` auf `current_position=` umstellen:
```bash
grep -rn "in_portfolio" agents/ orchestrators/ tests/ app/
```
Test-Aufrufe (z. B. judgment-Agent/-Chief/-Orchestrator-Tests) anpassen; ein Test ergänzen, der prüft, dass `result.short_action` für `current_position=PositionState.SHORT` == `ShortAction.HOLD` und sonst `NONE` ist. Dann die betroffenen Test-Dateien laufen lassen → grün.

- [ ] **Step 6: Commit** — `git add core/ agents/ orchestrators/ tests/ && git commit -m "feat(taxonomy): Short-Aktions-Platzhalter + DeepDiveResult.short_action + Verdrahtung current_position"`

---

## Task 4: CLI/Anzeige + Cache-Verifikation + Gesamt-Regression

**Files:**
- Modify: `app/main.py` (CLI + Anzeige)
- Verify/Modify: `adapters/cache/result_cache.py` (nur falls DeepDiveResult/recommendation dort serialisiert wird)
- Modify: verbleibende Tests, die noch `in_portfolio` nutzen.

**Interfaces:**
- Consumes: `PositionState`, `derive_*`, `JudgmentOrchestrator.run(current_position=...)`.

- [ ] **Step 1: CLI/Anzeige** — `app/main.py`:
  - `run_judgment(ticker, market, in_portfolio=False)` → `current_position: PositionState = PositionState.NONE`; an `judgment_orchestrator.run(..., current_position=current_position)` übergeben. `PositionState` importieren.
  - Arg-Parsing: `in_portfolio = "--portfolio" in args` ersetzen durch:
    ```python
    current_position = PositionState.NONE
    if "--position" in args:
        val = args[args.index("--position") + 1].lower()
        current_position = {"long": PositionState.LONG, "short": PositionState.SHORT}.get(val, PositionState.NONE)
    ```
  - Anzeige: nach der EMPFEHLUNG-Zeile zusätzlich die Short-Aktion ausgeben:
    ```python
    print(f"SHORT-AKTION:   {result.short_action.value}")
    ```
  - Usage-Doc-String von `--portfolio` auf `--position long|short` aktualisieren.

- [ ] **Step 2: Cache-Verifikation** — prüfen, ob `DeepDiveResult`/die Empfehlung überhaupt gecacht wird:
```bash
grep -rn "DeepDiveResult\|recommendation\|short_action\|\.action" adapters/cache/result_cache.py
```
  - **Falls** dort (de)serialisiert: `short_action` ergänzen (`"short_action": r.short_action.value` bzw. `short_action=ShortAction(d.get("short_action","NONE"))`).
  - **Falls nicht** (result_cache persistiert nur BottomUp/Cockpit): keine Änderung — im Commit-Text vermerken.

- [ ] **Step 3: Restliche `in_portfolio`-Stellen** — finaler Sweep:
```bash
grep -rn "in_portfolio" .
```
Alle verbliebenen Vorkommen (Code + Tests) auf `current_position` umstellen. (Hinweis: `portfolio_monitor_agent`/Backtester vergleichen ggf. Strings „SELL"/„SHORT" aus der Memory-Historie — das bleibt unverändert; `Recommendation.SHORT` existiert weiterhin.)

- [ ] **Step 4: Gesamt-Regression** — `python -m pytest -q` → **0 failed**. Bei Fehlern: superpowers:systematic-debugging (Ursache beheben, nicht raten).

- [ ] **Step 5: Manuelle Sicht** (optional) — `python -m app.main judge AAPL USA --position long` → Ausgabe zeigt Long-Aktion **und** SHORT-AKTION; ohne Flag → NONE/HOLD korrekt.

- [ ] **Step 6: Commit** — `git add app/ adapters/ tests/ && git commit -m "feat(taxonomy): CLI --position + Short-Aktion-Anzeige + Regression grün (Foundation-Block)"`

---

## Abdeckung (Spec → Task)
| Spec-Element | Task |
|---|---|
| Enums (Recommendation +NONE/+BUY+, ShortAction, PositionState) | 1 |
| `derive_recommendation` Long-Matrix + SHORT entfernt + Defer-on-SHORT | 2 |
| Short-Aktions-Platzhalter (+ Defer-on-LONG) | 3 |
| `current_position` statt `in_portfolio` (Agent/Chief/Orchestrator/CLI) | 3, 4 |
| `DeepDiveResult.short_action` | 3 |
| Serialisierung (falls vorhanden) + Anzeige beider Aktionen | 4 |
| Tests: Long-Matrix + Platzhalter + Regression | 1–4 |
| Gesamtsuite grün | 4, Step 4 |

## Self-Review (durchgeführt)
- **Spec-Abdeckung:** alle Komponenten haben einen Task. ✅
- **Platzhalter-Scan:** keine TBD/TODO; Code vollständig; Cache-Schritt bewusst verifikations-basiert (result_cache persistiert die Empfehlung vermutlich nicht). ✅
- **Typ-Konsistenz:** `current_position: PositionState` durchgängig; `short_action: ShortAction`; `derive_short_action_placeholder`-Name in Task 3 definiert + in judgment_agent verwendet. ✅
