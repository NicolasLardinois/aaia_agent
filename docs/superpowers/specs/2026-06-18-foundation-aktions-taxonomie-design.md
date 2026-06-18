# Foundation-Block: Aktions-Taxonomie (long + short) — Design

**Datum:** 2026-06-18
**Status:** Genehmigt (Design)
**Teil von:** Shorts-Programm (siehe `docs/open_todos.md` §9). Dies ist der **Foundation-Block**, der **vor** der Short-Thesis-Engine (Block 1) gebaut wird.

## Kontext & Ziel

Heute gibt `derive_recommendation` (`core/domain/recommendation.py`) auf der Long-Seite **BUY / SELL / HOLD / SHORT** aus, gesteuert durch einen **bool `in_portfolio`**. Zwei Schwächen:
1. **HOLD ist überladen** — es heißt sowohl „bin investiert, halte" als auch „bin nicht investiert, kein klares Signal". Das sind verschiedene Lagen.
2. **Der SHORT-Zweig ist naiv** („bearish + nicht im Depot + full_analysis → SHORT") — die echte Short-Logik kommt in Block 1.

**Ziel:** Eine **einheitliche Positions-Aktions-Taxonomie** für beide Linsen einführen, die Long-Seite sauber darauf umstellen und die **leere Short-Aktions-Hülle** anlegen (von Block 1 später gefüllt).

### Die Taxonomie (Ziel-Zustand)

| Lage | Long-Linse | Short-Linse |
|---|---|---|
| nicht gehalten + klares Einstiegssignal | **BUY** | SHORT |
| nicht gehalten + **kein** belastbares Urteil | **NONE** | NONE |
| gehalten + Signal gilt weiter/verstärkt | **BUY+** | SHORT+ |
| gehalten + Lage unklar | **HOLD** | HOLD |
| gehalten + These gekippt | **SELL** | COVER |

**HOLD vs NONE:** HOLD setzt eine bestehende Position voraus; NONE = nicht investiert + kein belastbares Urteil.

## Scope

**Im Foundation-Block:**
- Neue Position-Repräsentation `current_position` (none/long/short) statt bool `in_portfolio`.
- `Recommendation`-Enum um **NONE** und **BUY+** erweitern; `derive_recommendation` auf die Long-Matrix (BUY/BUY+/HOLD/SELL/NONE) umstellen; **SHORT-Zweig entfernen**.
- Neues `ShortAction`-Enum (SHORT/SHORT+/HOLD/COVER/NONE) + **positionsbasierte Platzhalter-Ableitung** (noch keine Thesis-Logik).
- `short_action`-Feld auf `DeepDiveResult`; Verdrahtung in `judgment_agent`; Serialisierung in `result_cache`; Anzeige/CLI in `app/main.py`.
- Tests: volle Long-Matrix + Short-Platzhalter + Regression.

**Außerhalb (spätere Blöcke):**
- Die Short-Thesis-Engine (`derive_short_assessment`, Note/Archetyp/Flags/Risiko) — **Block 1**.
- Echtes Ableiten von `current_position` aus dem Depot inkl. Richtung — **PM-Ausbau / Block #3**.
- „Verstärkt"-Erkennung via Memory-Historie (v1: „gilt weiter" genügt für „+").

### ⚠️ Bewusste Verhaltensänderung (vom User bestätigt)
Der naive SHORT entfällt aus `derive_recommendation`. „nicht-long + bearish" → **Long-Seite NONE**. Der echte SHORT kommt erst in Block 1. **Zwischen** Foundation und Block 1 erzeugt das Tool für Short-Fälle **kein** Short-Signal (Short-Aktion bleibt NONE/HOLD-Platzhalter). Akzeptiert.

## Komponenten / Änderungen

### 1. `core/domain/models.py` — Enums

```python
class Recommendation(str, Enum):
    BUY      = "BUY"
    BUY_PLUS = "BUY+"     # NEU: gehaltene Long-Position aufstocken
    HOLD     = "HOLD"
    SELL     = "SELL"
    NONE     = "NONE"     # NEU: nicht investiert + kein belastbares Urteil
    SHORT    = "SHORT"    # TRANSITIONAL: bleibt als Member (Referenzen im Code), wird
                          # von derive_recommendation NICHT mehr ausgegeben; Cleanup in Block 1.

class ShortAction(str, Enum):   # NEU
    SHORT      = "SHORT"
    SHORT_PLUS = "SHORT+"
    HOLD       = "HOLD"
    COVER      = "COVER"
    NONE       = "NONE"

class PositionState(str, Enum):  # NEU
    NONE  = "none"
    LONG  = "long"
    SHORT = "short"
```
- `Recommendation.SHORT`-Member **bleibt** (vermeidet Brüche bei bestehenden String-Vergleichen, z. B. `portfolio_monitor_agent` `last_rec in ("SELL","SHORT")` und Backtester). Wird in Block 1 entfernt, wenn `ShortAction` die Shorts vollständig übernimmt.

### 2. `core/domain/recommendation.py` — `derive_recommendation` (Long-Matrix)

Signaturänderung: `in_portfolio: bool` → `current_position: PositionState`. Die nur vom entfernten SHORT-Zweig genutzten Parameter `days_to_cover` und `short_float_pct` **entfallen**. (`market`, `top_down_available`, `cockpit` bleiben in der Signatur — für die Long-Matrix ungenutzt, aber für das Block-1-Short-Gate beibehalten.)

Neue Logik:
```python
# Titel wird als Short gehalten → die Long-Linse deferiert (kein "BUY, obwohl short").
# Reversal/Reconciliation (short→long) erst mit Short-Engine + PM (Block 1 / #3).
if current_position == PositionState.SHORT:
    return InvestmentRecommendation(
        Recommendation.NONE, None, None, confidence,
        "Titel als Short gehalten — Long-Seite deferiert (Short-Linse/PM zuständig).")

is_long = current_position == PositionState.LONG
bearish = signal == Signal.BEARISH or alignment == "aligned_bearish"
bullish = signal == Signal.BULLISH or alignment == "aligned_bullish"

# Uneindeutig/anomal → keine Aktion (positionsabhängig)
if confidence < 0.50:
    action = Recommendation.HOLD if is_long else Recommendation.NONE
    reasoning = ("Stark widersprüchliche/anomale Signale — Cash bevorzugen."
                 if confidence < 0.35 else
                 "Signallage zu widersprüchlich — Abwarten.")
    return InvestmentRecommendation(action, None, None, confidence, reasoning)

# Konfident:
if is_long:
    if bearish:  action = Recommendation.SELL       # These gekippt → raus
    elif bullish: action = Recommendation.BUY_PLUS  # gilt weiter → aufstocken
    else:        action = Recommendation.HOLD        # neutral → halten
else:  # current_position == NONE → Long-Linse: "nicht investiert"
    if bullish:  action = Recommendation.BUY         # Einstieg
    else:        action = Recommendation.NONE         # kein Long-Setup
```
`short_type`/`short_warning` der `InvestmentRecommendation` sind auf der Long-Seite jetzt **immer `None`** (Felder bleiben am Modell; Relocation in Block 1).

### 3. Short-Aktions-Platzhalter

Kleine reine Funktion (in `core/domain/recommendation.py` oder `core/domain/short_action.py`):
```python
def derive_short_action_placeholder(current_position: PositionState) -> ShortAction:
    """Platzhalter bis zur Short-Thesis-Engine (Block 1).
    Nur positionsbasiert: short gehalten → HOLD; sonst → NONE."""
    return ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE
```

### 4. `core/domain/models.py` — `DeepDiveResult`
Neues Feld `short_action: ShortAction` (Default `ShortAction.NONE`). Auch in `JudgmentChiefAgent.default(...)` gesetzt.

### 5. `agents/judgment/judgment_agent.py` — Verdrahtung
- Parameter `in_portfolio: bool` → `current_position: PositionState` (durchgereicht an `derive_recommendation`).
- `short_action = derive_short_action_placeholder(current_position)`; in `DeepDiveResult(...)` setzen.

### 6. `orchestrators/judgment_orchestrator.py`
`in_portfolio: bool = False` → `current_position: PositionState = PositionState.NONE` durchreichen.

### 7. `adapters/cache/result_cache.py`
`short_action` mit serialisieren/deserialisieren (str-Enum: `.value` / `ShortAction(...)`). Neue `Recommendation`-Werte (`BUY+`, `NONE`) sind String-basiert — keine Sonderbehandlung.

### 8. `app/main.py`
- CLI: `--portfolio` (bool) → `--position long|short` (Default → `PositionState.NONE`).
- Ausgabe: **Long-Aktion und Short-Aktion** beide anzeigen (`result.recommendation.action.value` + `result.short_action.value`).

## Datenfluss
```
CLI/Aufrufer → current_position (none/long/short)
  → judgment_orchestrator → judgment_agent.run(current_position)
      ├─ derive_recommendation(..., current_position) → Long-Aktion (BUY/BUY+/HOLD/SELL/NONE)
      └─ derive_short_action_placeholder(current_position) → Short-Aktion (NONE/HOLD)
  → DeepDiveResult(recommendation, short_action) → cache/Anzeige
```

## Fehlerbehandlung
- Niedrige/anomale Konfidenz → positionsabhängig **HOLD** (gehalten) bzw. **NONE** (nicht gehalten), kein Crash.
- Unbekannter/fehlender `current_position` → Default `PositionState.NONE`.

## Tests (`tests/`)
- **Long-Matrix** (`test_recommendation_taxonomy.py`, neu): je Kombination aus `current_position ∈ {none,long,short}` × Signal {bullish,bearish,neutral} × Konfidenz {<0.35, <0.50, ≥0.50} → erwartete Aktion. Insbesondere:
  - long + bullish + konfident → **BUY+**; long + neutral → **HOLD**; long + bearish → **SELL**.
  - none + bullish → **BUY**; none + bearish/neutral → **NONE**.
  - short (egal welches Signal) → **NONE** (Long-Linse deferiert).
  - konfident<0.50: long → **HOLD**, none → **NONE** (short bereits oben → NONE).
- **Short-Platzhalter**: short → **HOLD**, none/long → **NONE**.
- **Regression**: bestehende Tests (`test_domain_extensions.py`, `test_confidence.py`) auf `current_position` umstellen; SHORT-Erwartungen entfernen/auf NONE anpassen. Gesamtsuite **0 failed**.

## Akzeptanzkriterien
1. `derive_recommendation` liefert genau eine von **BUY/BUY+/HOLD/SELL/NONE**; **nie SHORT**.
2. HOLD nur bei gehaltener Long-Position; NONE nur bei nicht-gehaltener.
3. BUY+ bei gehaltener Long-Position mit weiterhin bullischem, konfidentem Signal.
4. `ShortAction`-Enum + `DeepDiveResult.short_action` existieren; Platzhalter liefert NONE/HOLD korrekt.
5. `current_position` ersetzt `in_portfolio` durchgängig (Agent, Orchestrator, CLI, Tests).
6. Serialisierung (`result_cache`) und Anzeige (`app/main.py`) zeigen beide Aktionen; Round-Trip korrekt.
7. Gesamte Testsuite grün (0 failed).
