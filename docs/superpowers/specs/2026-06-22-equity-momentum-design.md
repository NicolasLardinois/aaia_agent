# Equity-Momentum (long + short) — Design

- **Datum:** 2026-06-22
- **Status:** Entwurf zur Review
- **Teil von:** Shorts-Programm — „Equity-Short fertig" (Baustein 2/4). Aktiviert die in `short.md §11` als *dormant* beschriebenen Momentum-Short-Flags und speist symmetrisch auch die Long-Seite.

## 1. Kontext & Ziel

Equity hat heute **keinen** Momentum-Agenten (nur der Index hat einen). `short.md §11` verlangt: Momentum kommt als **neuer Bottom-up-Sub-Agent** (`MomentumSnapshot`, analog Index) und speist **beide** Seiten — **Long** (Alignment/Aggregat) und **Short** (Verstärker-Flags). Begründung der Symmetrie: „nutzt Short Momentum, muss Long es auch."

**Ziel:** `EquityMomentumAgent` bauen (RSI/MA/Cross/relative Stärke), in den Equity-Bottom-Up verdrahten, und sein Signal **gewichtet-sekundär** in die Long-Aggregation + als **zwei Verstärker-Flags** in die Short-Engine geben.

## 2. Entscheidungen (Brainstorm 2026-06-22)

1. **Umfang:** beide Seiten (long + short).
2. **Short-Natur:** **Verstärker** (Bestätigung), kein eigener Kern-Archetyp — konsistent mit der Kern-These-Pflicht (`short.md §4`).
3. **RS-Benchmark:** **Heimatmarkt je Region** (USA→`^GSPC`, CH→`^SSMI`, Eurozone→`^STOXX50E`; Default `^GSPC`), **aus dem Ticker abgeleitet** via `get_info(ticker).country` — der Bottom-Up läuft in Modus 2 ohne Markt, Modus 3 nutzt den Cache, daher **keine** Markt-Durchreichung (§3.3).
4. **Momentum-Gewicht:** **leicht/sekundär** — Equity-Chief `_W_MOMENTUM = 0.10`, Alignment `0.5`. Bestätigt, dominiert nie die Fundamentaldaten.
5. **Short-Flags:** **zwei** Verstärker — `momentum_breakdown` (Trend bearish) + `relative_weakness` (rs < 0).
6. **Index-Momentum-Benchmark** (heute fix `URTH`) wird hier **nicht** angefasst → Folge-Aufgabe im Logbuch.

## 3. Komponenten

### 3.1 `MomentumSnapshot` (`core/domain/models.py`)
Neues Datenmodell, spiegelt `IndexMomentumSnapshot`:
```python
@dataclass
class MomentumSnapshot:
    rsi_14: Optional[float]
    ma50: Optional[float]
    ma200: Optional[float]
    golden_cross: Optional[bool]      # True=Golden, False=Death, None=kein Kreuz in 5T
    relative_strength: Optional[float] # Titel-Return − Heimatmarkt-Return (rs<0 = schwächer)
    signal: Signal
```
*(Eigenes Modell statt das Index-benannte wiederverwenden — semantische Klarheit; die Rechen-Helfer werden über `core.utils.scoring` geteilt.)*

### 3.2 `EquityMomentumAgent` (`agents/stock_deep_dive/equity/momentum_agent.py`)
Spiegelt `IndexMomentumAgent` (gleiche Mathematik), aber **Benchmark = Heimatmarkt, aus dem Ticker abgeleitet** (selbst-enthalten, keine Markt-Durchreichung):
- **Benchmark aus `country`** (Modul-Map `_BENCHMARK_BY_COUNTRY`): `country = (market_provider.get_info(ticker) or {}).get("country")`; `"United States"→"^GSPC"`, `"Switzerland"→"^SSMI"`, Eurozone-Länder (`"Germany"`, `"France"`, `"Italy"`, `"Spain"`, `"Netherlands"`, `"Austria"`, `"Belgium"`, `"Portugal"`, `"Finland"`, `"Ireland"`, `"Greece"`, …)→`"^STOXX50E"`; sonst/Fehler/kein `country` → Default `"^GSPC"`.
- `run(self, ticker: str) -> MomentumSnapshot`:
  - Benchmark via `country`-Map; `get_price_history(ticker, "2y")` **und** `get_price_history(benchmark, "2y")` parallel (`asyncio.to_thread` + `gather`, `return_exceptions=True`).
  - `rsi_14 = wilder_rsi(close, 14)`; `ma50/ma200` = rollende Mittel; `golden_cross = _detect_crossover(ma50_series, ma200_series)`; `relative_strength = ticker_ret − bench_ret` (Total Return über die Periode; benchmarkfehlend → `None`).
  - `signal = _signal(ma50, ma200, rsi)` — **identische Logik** wie Index: Aufwärtstrend (ma50>ma200) + nicht überkauft → BULLISH; Abwärtstrend + nicht überverkauft → BEARISH; Extreme/None → NEUTRAL.
  - `default()` → alle `None`, `signal=NEUTRAL` (defensiv; fehlende/teilweise Daten brechen die Analyse nie ab).
- Reine Helfer (`_signal`, `_detect_crossover`) als pure functions; gemeinsame Mathematik mit dem Index-Agenten via `core.utils.scoring` (kein Duplikat — wo der Index schon `wilder_rsi` nutzt, nutzt Equity es auch).

### 3.3 Markt-Quelle (selbst-enthalten — keine Verdrahtung)
**Befund:** Der Bottom-Up läuft in **Modus 2** (`bottomup`, **ohne** Markt-Arg); **Modus 3** lädt den Bottom-Up aus dem **Cache** (`cache.load_bottom_up`). Eine „Markt-Durchreichung" erreicht den Agenten daher nicht. → Der Agent leitet den Markt **selbst aus dem Ticker** ab (`get_info(ticker).country`, §3.2). **Keine** Signatur-Änderung an `bottom_up_orchestrator.run` / `equity_chief.run`, **keine** CLI-Änderung. (`EquityMomentumAgent` bekommt im Chief-`__init__` den vorhandenen `market`-Provider — wie `valuation_range_agent`.)

### 3.4 Long-Integration
- **`EquityChiefResult.momentum`** + **`BottomUpResult.momentum`** Slots (`models.py`).
- `equity_chief_agent.py`: `EquityMomentumAgent` in `__init__` + `asyncio.gather`; `_safe(...)`-Default; `momentum` in `EquityChiefResult`; `_aggregate_signal(..., momentum_sig)` um `_W_MOMENTUM = 0.10` erweitern (`weighted_signal` normalisiert über die verfügbaren Gewichte).
- `agents/judgment/judgment_agent.py`:
  - `_bottom_up_signals(bottom_up)` hängt `momentum.signal` **nach** den Equity-Signalen, **vor** Bond an → Liste `[fu, si, ins, et, mo, vr, momentum, bond]`.
  - `_ALIGNMENT_WEIGHTS` **explizit** auf 8 Einträge: `[1.0, 0.5, 0.5, 1.0, 0.75, 1.5, 0.5, 1.0]` (Momentum `0.5`; Bond bleibt `1.0` — sein heutiger gepaddeter Wert, **verhaltens-erhaltend**).
  - `_run_equity`/`BottomUpResult`-Bau: `momentum=result.momentum` befüllen.

### 3.5 Short-Integration (`core/domain/short_flags.py`)
Accessor `def _mom(bu): return getattr(bu, "momentum", None)` + zwei **Verstärker**-Flags (`kind="verstaerker"`, `archetype=None`):
- **`momentum_breakdown`** (weight `0.04`): feuert, wenn `_mom(bu)` vorhanden und `_mom(bu).signal == Signal.BEARISH` (Abwärtstrend ohne Überverkauft-Dämpfung). Detail: „Momentum bearish (ma50<ma200)".
- **`relative_weakness`** (weight `0.03`): feuert, wenn `_mom(bu).relative_strength is not None and < 0` (schwächer als der Heimatmarkt). Detail: „relative Schwäche vs. Heimatmarkt (RS {rs:.0%})".

*(Beide lesen nur `bottom_up.momentum`; ist das Feld `None` — z. B. Nicht-Equity oder Default — feuern sie nicht. `derive_short_assessment` iteriert `SHORT_FLAGS` bereits defensiv.)*

## 4. Datenfluss

```
bottom_up_orchestrator.run(ticker, asset_class, sector)        # Signaturen unverändert
      └─ _run_equity → equity_chief.run(ticker, sector)
            ├─ EquityMomentumAgent.run(ticker)  → (get_info.country → Benchmark) → MomentumSnapshot
            ├─ _aggregate_signal(..., momentum_sig @0.10) → EquityChiefResult.signal
            └─ EquityChiefResult.momentum
      → BottomUpResult.momentum
            ├─ LONG:  judgment _bottom_up_signals (+momentum.signal @0.5) → alignment/dominant → derive_recommendation
            └─ SHORT: short_flags momentum_breakdown / relative_weakness → derive_short_assessment (Konfidenz-Boost)
```

## 5. Fehlerbehandlung / Regression

- Kurs-/Benchmark-Quelle fehlt/teilweise → `EquityMomentumAgent.default()` (alle `None`, NEUTRAL). Keine Anomalie kippt die Analyse (defensive Aggregation, AGENTS.md §2).
- `relative_strength=None` (Benchmark fehlt) → `relative_weakness`-Flag feuert nicht.
- **Verhaltens-erhaltend für Bond/Nicht-Equity:** `bottom_up.momentum` ist dort `None` → Short-Flags inaktiv; Bond-Alignment-Gewicht unverändert `1.0`.
- **Long-Regression (P3):** Momentum verschiebt `_aggregate_signal` + Alignment bei Equity. Gewicht bewusst sekundär (0.10 / 0.5). Snapshot-/Regressionstests sichern, dass das Gesamtsignal nur dort kippt, wo Momentum eine echte Mehrheit verschiebt.

## 6. Phasen (je eigener PR-tauglicher Abschnitt, TDD)

- **P1 — Agent + Snapshot + Verdrahtung (verhaltens-erhaltend):** `MomentumSnapshot`, `EquityMomentumAgent` (Benchmark aus `get_info.country`), `EquityChiefResult.momentum` + `BottomUpResult.momentum` befüllt — **noch nicht konsumiert** (kein Aggregat-/Alignment-/Flag-Effekt). Bestehende Tests bleiben grün.
- **P2 — Short-Flags:** `momentum_breakdown` + `relative_weakness` in `short_flags.py`.
- **P3 — Long-Integration:** `_W_MOMENTUM` in `_aggregate_signal`, `_bottom_up_signals` + `_ALIGNMENT_WEIGHTS`. Gesamt-Regression.

## 7. Tests (TDD, AGENTS.md §4)

- **Agent:** RSI/MA50/MA200 aus einer bekannten Preisreihe; Golden/Death-Cross; `relative_strength = ticker_ret − bench_ret`; Benchmark-Map (USA/CH/Eurozone/Default); `_signal`-Grenzfälle (Up/Down/überkauft/überverkauft/None/NaN); `default()` bei Provider-Fehler.
- **Short-Flags:** `momentum_breakdown` feuert bei `signal==BEARISH`, nicht bei BULLISH/NEUTRAL/`momentum=None`; `relative_weakness` feuert bei `rs<0`, nicht bei `rs≥0`/`None`; Konfidenz-Boost in `derive_short_assessment` (Verstärker addiert sich).
- **Long:** `_bottom_up_signals` enthält `momentum.signal` an Position 7; `_ALIGNMENT_WEIGHTS`-Länge/Werte (Momentum 0.5, Bond 1.0); ein bearishes Momentum verschiebt Alignment/Aggregat erwartungsgemäß; **Bond-Pfad unverändert** (Regressionstest).
- **Regression:** Gesamtsuite grün (`python -m pytest -q`).

## 8. Akzeptanzkriterien

1. `EquityMomentumAgent` liefert `MomentumSnapshot` (RSI/MA/Cross/RS/Signal), Benchmark = Heimatmarkt, defensiv `default()`.
2. Der Agent leitet den Benchmark selbst aus `get_info(ticker).country` ab (kein Markt-Threading, keine Signatur-/CLI-Änderung); unbekannt/Fehler → Default `^GSPC`.
3. Long: Momentum-Signal fließt sekundär in Equity-Aggregat (`0.10`) **und** Alignment (`0.5`); Bond-Alignment unverändert.
4. Short: zwei Verstärker-Flags (`momentum_breakdown`, `relative_weakness`) boosten die Konfidenz, kippen nie allein die Richtung; bei `momentum=None` inaktiv.
5. Nicht-Equity/Bond verhaltens-erhaltend.
6. Gesamtsuite grün; Index-RS-Konsistenz als Logbuch-Folge-Aufgabe vermerkt.
