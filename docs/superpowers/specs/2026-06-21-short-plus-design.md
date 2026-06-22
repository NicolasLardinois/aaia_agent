# SHORT+-Aktivierung — Design

- **Datum:** 2026-06-21
- **Status:** Entwurf zur Review
- **Teil von:** Shorts-Programm (Equity-Short fertigstellen). Aktiviert die heute ungenutzte `ShortAction.SHORT_PLUS`. Symmetrisch zu **BUY+** der Long-Seite, mit zwei bewusst asymmetrischen Short-Gates (Gewinn + Squeeze).

## 1. Kontext & Ziel

Die Short-Engine (`core/domain/short_assessment.py`) gibt im `pos == SHORT`-Zweig heute nur **HOLD** (conf ≥ 0,50) oder **COVER** (conf < 0,50) aus — `ShortAction.SHORT_PLUS` existiert als Enum, wird aber **nie** erzeugt. Die Long-Seite (`derive_recommendation`) kennt dagegen **BUY+**: hält man long und das Signal ist *jetzt* bullish (gleiche 0,50-Schwelle wie BUY), wird aufgestockt — **ohne** Profit-Check (Long-Verlust ist nach unten begrenzt).

**Ziel:** SHORT+ symmetrisch ergänzen — *„Short-These gilt weiter"* → Nachlegen —, aber mit den zwei Gates, die Shorts brauchen (Short-Verlust ist **unbegrenzt** + Squeeze-Gefahr): **nur in einen Gewinner-Short** (≥ 5 % im Plus) und **nie in ein hohes Squeeze-Risiko**.

## 2. Verhalten (Engine)

`pos == SHORT`-Zweig:

| Bedingung | Aktion |
|---|---|
| `conf < 0,50` | **COVER** (These gebrochen — unverändert) |
| `conf ≥ 0,50` **und** `pnl_pct ≥ 5` **und** `squeeze ≠ "high"` | **SHORT_PLUS** |
| `conf ≥ 0,50` sonst (pnl < 5 / pnl `None` / squeeze hoch) | **HOLD** |

- **Schwelle:** dieselbe `_THRESHOLD = 0,50` wie heute — **kein** separater höherer Schwellwert, **keine** gespeicherte Eröffnungs-Konfidenz (analog BUY+: „Einstiegssignal gilt weiter").
- **Profit-Gate:** `_SHORT_PLUS_MIN_PROFIT_PCT = 5.0` (Kurs ~5 %+ unter Einstand). Begründung: ein kleiner Gegen-Wackler kippt nicht sofort zum Nachlegen; „press clear winners, never average a losing short".
- **Squeeze-Gate:** `squeeze == "high"` schließt SHORT+ aus (nie in einen Squeeze nachlegen).
- **Tranche:** `suggested_size_pct = round(_position_size_pct(conf) · 0,25, 1)` — konservativer Top-up (halbe Erst-Short-Tranche; Risiko wächst beim Nachlegen überproportional).
- **Stop:** 15 % (Squeeze ist bei SHORT+ per Gate ausgeschlossen, daher nie der 10-%-Squeeze-Stop).
- **Nur Equity:** SHORT+ liegt im Equity-Pfad der Engine; Nicht-Equity bleibt beim heutigen Fallback.

## 3. P&L-Verdrahtung (Option B — Port in die Judgment-Schicht injiziert)

Die Engine bekommt einen neuen Parameter `position_pnl_pct: float | None = None`. Den **Wert** berechnet die **Judgment-Schicht**, die den `PortfolioPort` per DI bekommt:

- **`agents/judgment/judgment_agent.py`** — Konstruktor `__init__(self, llm, bus, portfolio_port: PortfolioPort | None = None)`. In `run(...)`, wenn `current_position == PositionState.SHORT` **und** Port vorhanden:
  - Einstand über den Port nachschlagen: `get_positions()` → Position mit `ticker == ... and direction == "short"` → `entry_price`.
  - Live-Kurs aus dem Bottom-Up: `bottom_up.valuation_range.current_price`.
  - `pnl_pct = (entry − cur) / entry · 100` (Short-Gewinn, wenn der Kurs fällt).
  - `position_pnl_pct` an `derive_short_assessment(...)` übergeben.
- **Defensiv:** kein Port / keine passende Position / kein Einstand / keine `valuation_range`/`current_price` / `PortfolioError` → `position_pnl_pct = None` → kein SHORT+ → HOLD. **Kein Crash, kein versehentliches Nachlegen.**

**Port-Verdrahtung (DI-Kette):**
`PortfolioPort` (Adapter `JsonPortfolioProvider`) → `JudgmentOrchestrator.__init__(..., portfolio_port=None)` → `JudgmentChiefAgent(llm, bus, portfolio_port)` → `JudgmentAgent(llm, bus, portfolio_port)`. Am Bau-Ort des Orchestrators (`app/main.py`/`background_runner.py`) `JsonPortfolioProvider()` mitgeben. **Default `None`** überall → bestehende Konstruktion/Tests brechen nicht (Port fehlt → kein SHORT+, HOLD).

> Hinweis: `current_position` bleibt wie in 3a (früh in `app/main.py` aus dem Depot abgeleitet, zustands-only). Der Port in der Judgment-Schicht dient **nur** dem späten, analyse-abhängigen Einstand-/P&L-Nachschlag (anderes Konzept, andere Phase) — daher der zusätzliche Port-Zugriff statt Durchreichen eines Roh-Floats.

## 4. Komponenten

| Datei | Änderung |
|---|---|
| `core/domain/short_assessment.py` | `_SHORT_PLUS_MIN_PROFIT_PCT = 5.0`; `_action(pos, confidence, pnl_pct=None, squeeze="low")` → SHORT_PLUS-Zweig; `derive_short_assessment(..., position_pnl_pct=None)` → an `_action` reichen + SHORT_PLUS-Sizing (`·0,25`). |
| `agents/judgment/judgment_agent.py` | Konstruktor `portfolio_port=None`; in `run()` `position_pnl_pct` für SHORT berechnen (Port-Lookup + `valuation_range.current_price`) und an die Engine geben. |
| `agents/judgment_chief_agent.py` | Konstruktor nimmt `portfolio_port=None`, reicht an `JudgmentAgent`. |
| `orchestrators/judgment_orchestrator.py` | Konstruktor nimmt `portfolio_port=None`, reicht an `JudgmentChiefAgent`. |
| Bau-Ort (`app/main.py` / `background_runner.py`) | `JsonPortfolioProvider()` an den Orchestrator geben. |

## 5. Datenfluss

```
Depot (portfolio.json) ──JsonPortfolioProvider──┐
                                                 ▼ (DI)
app/main.py: current_position (3a, früh)   JudgmentOrchestrator → ChiefAgent → JudgmentAgent
                                                                                    │
   bottom_up.valuation_range.current_price ─────────────────────────────────────────┤ pnl_pct = (entry−cur)/entry·100
                                                                                    ▼
                                              derive_short_assessment(..., position_pnl_pct)
                                                   └─ pos==SHORT & conf≥0,50 & pnl≥5 & squeeze≠high → SHORT_PLUS
```

## 6. Fehlerbehandlung

- Fehlende Position/Einstand/Kurs, kein Port, `PortfolioError` → `position_pnl_pct = None` → HOLD.
- `entry_price ≤ 0` → keine P&L-Rechnung (Division vermeiden) → `None` → HOLD.
- Bestehende Pfade (NONE/LONG, COVER, SHORT-Erstaufbau) **unverändert** (verhaltens-erhaltend ohne Port/pnl).

## 7. Tests (TDD)

**Engine (`tests/test_short_assessment_engine.py` o. ä.):**
- SHORT + `conf ≥ 0,50` + `pnl = 6` + squeeze `low` → **SHORT_PLUS**; `suggested_size_pct == round(_position_size_pct(conf)·0,25, 1)`; stop 15.
- Grenzfall `pnl == 5.0` → **SHORT_PLUS**; `pnl == 4.9` → **HOLD**.
- `pnl = None` → **HOLD**; `squeeze == "high"` (trotz pnl ≥ 5) → **HOLD**.
- `conf < 0,50` → **COVER** (unverändert, pnl ignoriert).
- NONE-Pfad (SHORT/NONE) und LONG-Pfad (NONE) **unverändert**.
- Bestehende SHORT-Tests (ohne `position_pnl_pct`) bleiben grün (Default `None` → HOLD wie bisher).

**Judgment (`tests/.../test_judgment_agent*.py`):**
- Short gehalten, Einstand 100, `valuation_range.current_price` 90 → `pnl_pct = 10` an die Engine (Short invertiert).
- Kein Port / Ticker nicht im Depot / `valuation_range = None` / `current_price = None` → `position_pnl_pct = None` übergeben (kein SHORT+).
- `PortfolioPort.get_positions()` wirft `PortfolioError` → defensiv `None` (kein Crash).
- LLM in allen Judgment-Tests gemockt.

**Regression:** Gesamtsuite grün (`python -m pytest -q`).

## 8. Akzeptanzkriterien

1. `pos == SHORT` + `conf ≥ 0,50` + `pnl ≥ 5` + `squeeze ≠ high` → **SHORT_PLUS**, sonst HOLD; `conf < 0,50` → COVER.
2. SHORT+-Tranche = `_position_size_pct(conf) · 0,25`.
3. `position_pnl_pct` kommt aus der Judgment-Schicht (Port-Lookup Einstand + `valuation_range.current_price`), Short-invertiert.
4. Vollständig defensiv: fehlende Daten/Port/`PortfolioError` → `None` → HOLD (kein Crash, kein Nachlegen).
5. Long/NONE/COVER/SHORT-Erstaufbau verhaltens-erhaltend; Port-Default `None` bricht bestehende Konstruktion/Tests nicht.
6. Gesamtsuite grün.
