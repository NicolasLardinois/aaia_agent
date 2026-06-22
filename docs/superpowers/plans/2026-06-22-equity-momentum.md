# Equity-Momentum (long + short) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Equity-Momentum-Agent (RSI/MA/Cross/relative Stärke vs. Heimatmarkt) bauen und sein Signal sekundär in die Long-Aggregation + als zwei Verstärker-Flags in die Short-Engine speisen.

**Architecture:** Neuer Bottom-up-Sub-Agent `EquityMomentumAgent` (spiegelt `IndexMomentumAgent`), Benchmark aus `get_info(ticker).country` (selbst-enthalten). Geteilte Pure-Helfer in `core/utils/momentum.py`. Long: Equity-Aggregat + Alignment (sekundär). Short: zwei Verstärker-Flags.

**Tech Stack:** Python, pytest, pandas.

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-22-equity-momentum-design.md`.
- TDD Pflicht (roter Test zuerst). Deutsche Kommentare, Type Hints. Defensive Aggregation (`default()` bei Fehler). Worktree `.claude/worktrees/momentum`, Branch `feat/equity-momentum`. PR-First — **nicht** mergen.
- Momentum **sekundär**: Equity-Chief `_W_MOMENTUM = 0.10`, Alignment-Gewicht `0.5`. Short-Flags **Verstärker** (`momentum_breakdown` 0.04, `relative_weakness` 0.03).
- Benchmark-Default `^GSPC`. RS-Vorzeichen: `rs = Titel-Return − Benchmark-Return` (rs<0 = schwächer). Runner `python -m pytest -q`.

---

## Task 1: Geteilte Momentum-Helfer (`core/utils/momentum.py`)

**Files:**
- Create: `core/utils/momentum.py`
- Test: `tests/utils/test_momentum.py`

**Interfaces:**
- Produces: `momentum_signal(ma50, ma200, rsi, *, overbought=70.0, oversold=30.0) -> Signal`; `detect_crossover(ma50_series, ma200_series, window=5) -> bool | None`.

- [ ] **Step 1: Failing tests** — `tests/utils/test_momentum.py`:
```python
import math
import pandas as pd
from core.domain.models import Signal
from core.utils.momentum import momentum_signal, detect_crossover


def test_momentum_signal_uptrend_bullish():
    assert momentum_signal(110.0, 100.0, 55.0) == Signal.BULLISH

def test_momentum_signal_uptrend_overbought_neutral():
    assert momentum_signal(110.0, 100.0, 75.0) == Signal.NEUTRAL

def test_momentum_signal_downtrend_bearish():
    assert momentum_signal(90.0, 100.0, 45.0) == Signal.BEARISH

def test_momentum_signal_downtrend_oversold_neutral():
    assert momentum_signal(90.0, 100.0, 25.0) == Signal.NEUTRAL

def test_momentum_signal_none_or_nan_neutral():
    assert momentum_signal(None, 100.0, 50.0) == Signal.NEUTRAL
    assert momentum_signal(float("nan"), 100.0, 50.0) == Signal.NEUTRAL

def test_detect_crossover_golden_and_death():
    golden = pd.Series([-2, -1, 1, 2]); base = pd.Series([0, 0, 0, 0])
    assert detect_crossover(pd.Series([8, 9, 11, 12]), pd.Series([10, 10, 10, 10])) is True
    assert detect_crossover(pd.Series([12, 11, 9, 8]), pd.Series([10, 10, 10, 10])) is False
    assert detect_crossover(pd.Series([11, 11, 11, 11]), pd.Series([10, 10, 10, 10])) is None
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/utils/test_momentum.py -q` (ModuleNotFound).

- [ ] **Step 3: Implement** — `core/utils/momentum.py`:
```python
import math
from core.domain.models import Signal


def momentum_signal(ma50, ma200, rsi, *, overbought: float = 70.0, oversold: float = 30.0) -> Signal:
    """Signal aus Trend-STATUS (ma50 vs ma200) + RSI-Extreme.
    Aufwärtstrend + nicht überkauft → BULLISH; Abwärtstrend + nicht überverkauft → BEARISH;
    Extreme/None/NaN → NEUTRAL. (Spiegelt die Index-Momentum-Logik.)"""
    if ma50 is None or ma200 is None:
        return Signal.NEUTRAL
    if math.isnan(ma50) or math.isnan(ma200):
        return Signal.NEUTRAL
    if ma50 > ma200:
        if rsi is not None and rsi > overbought:
            return Signal.NEUTRAL
        return Signal.BULLISH
    if rsi is not None and rsi < oversold:
        return Signal.NEUTRAL
    return Signal.BEARISH


def detect_crossover(ma50_series, ma200_series, window: int = 5) -> bool | None:
    """True = Golden Cross, False = Death Cross, None = kein Kreuz im Fenster."""
    try:
        diff   = ma50_series - ma200_series
        recent = diff.iloc[-(window + 1):]
        if len(recent) < 2:
            return None
        was_above = recent.iloc[0] > 0
        is_above  = recent.iloc[-1] > 0
        if not was_above and is_above:
            return True
        if was_above and not is_above:
            return False
        return None
    except Exception:
        return None
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/utils/test_momentum.py -q`.

- [ ] **Step 5: Commit** — `git add core/utils/momentum.py tests/utils/test_momentum.py && git commit -m "feat(momentum): geteilte Pure-Helfer momentum_signal + detect_crossover"`

---

## Task 2: `MomentumSnapshot` + Event + `EquityMomentumAgent`

**Files:**
- Modify: `core/domain/models.py` (MomentumSnapshot), `core/domain/events.py` (EquityMomentumReady)
- Create: `agents/stock_deep_dive/equity/momentum_agent.py`
- Test: `tests/agents/stock_deep_dive/equity/test_momentum_agent.py`

**Interfaces:**
- Consumes: `momentum_signal`, `detect_crossover` (Task 1); `core.utils.scoring.wilder_rsi`.
- Produces: `MomentumSnapshot(rsi_14, ma50, ma200, golden_cross, relative_strength, signal)`; `EquityMomentumAgent(market, bus)` mit `async run(ticker) -> MomentumSnapshot` und `default()`; `_benchmark_for(country) -> str`.

**ZUERST LESEN:** `agents/stock_deep_dive/index/index_momentum_agent.py` (Vorlage) + `core/domain/events.py` (Event-Muster `IndexMomentumReady`).

- [ ] **Step 1: Failing tests** — `tests/agents/stock_deep_dive/equity/test_momentum_agent.py`:
```python
import asyncio
import pandas as pd
from unittest.mock import MagicMock
from core.domain.models import Signal, MomentumSnapshot
from agents.stock_deep_dive.equity.momentum_agent import EquityMomentumAgent, _benchmark_for


def _series(vals): return pd.DataFrame({"Close": vals})


def _market(country, ticker_prices, bench_prices):
    m = MagicMock()
    m.get_info.return_value = {"country": country}
    def _hist(sym, period):
        return _series(bench_prices) if sym.startswith("^") else _series(ticker_prices)
    m.get_price_history.side_effect = _hist
    return m


def test_benchmark_map():
    assert _benchmark_for("United States") == "^GSPC"
    assert _benchmark_for("Switzerland") == "^SSMI"
    assert _benchmark_for("Germany") == "^STOXX50E"
    assert _benchmark_for("Brazil") == "^GSPC"      # Default
    assert _benchmark_for(None) == "^GSPC"


def test_relative_strength_and_signal():
    # Titel +20 %, Benchmark +10 % → rs ≈ +0.10 ; Aufwärtstrend → BULLISH
    up = [100.0] * 200 + [120.0] * 60
    bench = [100.0] * 200 + [110.0] * 60
    snap = asyncio.run(EquityMomentumAgent(_market("United States", up, bench), MagicMock()).run("AAPL"))
    assert snap.relative_strength is not None and round(snap.relative_strength, 2) == 0.10
    assert snap.signal in (Signal.BULLISH, Signal.NEUTRAL)


def test_default_on_price_error():
    m = MagicMock()
    m.get_info.return_value = {"country": "United States"}
    m.get_price_history.side_effect = Exception("net")
    snap = asyncio.run(EquityMomentumAgent(m, MagicMock()).run("AAPL"))
    assert snap.signal == Signal.NEUTRAL and snap.ma50 is None
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/agents/stock_deep_dive/equity/test_momentum_agent.py -q`.

- [ ] **Step 3: Implement**
  - `core/domain/models.py` — neues Modell (bei den anderen Snapshots):
```python
@dataclass
class MomentumSnapshot:
    rsi_14: Optional[float]
    ma50: Optional[float]
    ma200: Optional[float]
    golden_cross: Optional[bool]
    relative_strength: Optional[float]   # Titel-Return − Heimatmarkt-Return (rs<0 = schwächer)
    signal: Signal
```
  - `core/domain/events.py` — `EquityMomentumReady` analog `IndexMomentumReady` (gleiches Muster: `source`, `payload`).
  - `agents/stock_deep_dive/equity/momentum_agent.py`:
```python
import asyncio
import math

from core.domain.events import EquityMomentumReady
from core.domain.models import MomentumSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.scoring import wilder_rsi
from core.utils.momentum import momentum_signal, detect_crossover

_HISTORY_PERIOD = "2y"
_BENCHMARK_BY_COUNTRY = {
    "United States": "^GSPC", "Switzerland": "^SSMI",
    "Germany": "^STOXX50E", "France": "^STOXX50E", "Italy": "^STOXX50E",
    "Spain": "^STOXX50E", "Netherlands": "^STOXX50E", "Austria": "^STOXX50E",
    "Belgium": "^STOXX50E", "Portugal": "^STOXX50E", "Finland": "^STOXX50E",
    "Ireland": "^STOXX50E", "Greece": "^STOXX50E",
}
_DEFAULT_BENCHMARK = "^GSPC"
_DEFAULT = MomentumSnapshot(rsi_14=None, ma50=None, ma200=None,
                            golden_cross=None, relative_strength=None, signal=Signal.NEUTRAL)


def _benchmark_for(country: str | None) -> str:
    return _BENCHMARK_BY_COUNTRY.get(country or "", _DEFAULT_BENCHMARK)


class EquityMomentumAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> MomentumSnapshot:
        def _ready():
            self.bus.publish(EquityMomentumReady(source="equity_momentum_agent",
                                                 payload={"ticker": ticker}))
        try:
            info = await asyncio.to_thread(self.market.get_info, ticker)
        except Exception:
            info = None
        benchmark = _benchmark_for((info or {}).get("country"))
        try:
            hist, bench = await asyncio.gather(
                asyncio.to_thread(self.market.get_price_history, ticker, _HISTORY_PERIOD),
                asyncio.to_thread(self.market.get_price_history, benchmark, _HISTORY_PERIOD),
                return_exceptions=True,
            )
            if isinstance(hist, Exception):
                _ready(); return _DEFAULT
            close   = hist["Close"]
            ma50_s  = close.rolling(50).mean()
            ma200_s = close.rolling(200).mean()
            _m50, _m200 = float(ma50_s.iloc[-1]), float(ma200_s.iloc[-1])
            ma50  = None if math.isnan(_m50)  else round(_m50, 2)
            ma200 = None if math.isnan(_m200) else round(_m200, 2)
            rsi    = wilder_rsi(close)
            golden = detect_crossover(ma50_s, ma200_s)
            rs = None
            if not isinstance(bench, Exception):
                bc = bench["Close"]
                t_ret = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
                b_ret = (bc.iloc[-1] - bc.iloc[0]) / bc.iloc[0]
                rs = round(float(t_ret - b_ret), 4)
            _ready()
            return MomentumSnapshot(rsi_14=rsi, ma50=ma50, ma200=ma200,
                                    golden_cross=golden, relative_strength=rs,
                                    signal=momentum_signal(ma50, ma200, rsi))
        except Exception:
            _ready(); return _DEFAULT

    @staticmethod
    def default() -> MomentumSnapshot:
        return _DEFAULT
```

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/agents/stock_deep_dive/equity/test_momentum_agent.py -q`.

- [ ] **Step 5: Commit** — `git add core/domain/models.py core/domain/events.py agents/stock_deep_dive/equity/momentum_agent.py tests/agents/stock_deep_dive/equity/test_momentum_agent.py && git commit -m "feat(momentum): MomentumSnapshot + EquityMomentumAgent (Benchmark aus country)"`

---

## Task 3: In Equity-Chief + Bottom-Up verdrahten (verhaltens-erhaltend)

**Files:**
- Modify: `core/domain/models.py` (`EquityChiefResult.momentum`, `BottomUpResult.momentum`), `agents/stock_deep_dive/equity_chief_agent.py`, `orchestrators/bottom_up_orchestrator.py`
- Test: `tests/test_chief_agents.py` (oder bestehende Equity-Chief-Testdatei — vorher `grep -rl "EquityChiefAgent" tests/`)

**Interfaces:**
- Consumes: `EquityMomentumAgent` (Task 2).
- Produces: `EquityChiefResult.momentum: Optional[MomentumSnapshot]`, `BottomUpResult.momentum: Optional[MomentumSnapshot]` (beide default `None`).

- [ ] **Step 1: Failing test** — in der Equity-Chief-Testdatei:
```python
def test_equity_chief_populates_momentum():
    # nutzt die vorhandene Equity-Chief-Test-Konstruktion (Provider/LLM/Bus gemockt);
    # nach run(ticker) muss result.momentum ein MomentumSnapshot sein.
    ...  # an die bestehende Testfixture anpassen
    result = asyncio.run(chief.run("AAPL"))
    from core.domain.models import MomentumSnapshot
    assert isinstance(result.momentum, MomentumSnapshot)
```
> Hinweis: An die reale Fixture der Datei anpassen (gleiche Mock-Provider wie die übrigen Equity-Chief-Tests). Ziel: `EquityChiefResult.momentum` ist befüllt.

- [ ] **Step 2: Run → FAIL** — `python -m pytest <equity-chief-testdatei> -q` (AttributeError `momentum`).

- [ ] **Step 3: Implement**
  - `core/domain/models.py`: `EquityChiefResult` um `momentum: Optional["MomentumSnapshot"] = None` (trailing, default) erweitern; `BottomUpResult` um `momentum: Optional["MomentumSnapshot"] = None` (trailing, default) erweitern.
  - `agents/stock_deep_dive/equity_chief_agent.py`:
    - Import `from agents.stock_deep_dive.equity.momentum_agent import EquityMomentumAgent`.
    - `__init__`: `self.momentum_agent = EquityMomentumAgent(market, bus)`.
    - `run()`: in `asyncio.gather(...)` als **8.** Aufruf `self.momentum_agent.run(ticker)` ergänzen; nach den `_safe(...)`-Zeilen: `momentum = _safe(results[7], EquityMomentumAgent.default())`; im `return EquityChiefResult(...)` `momentum=momentum` ergänzen. **`_aggregate_signal` NICHT ändern** (Momentum noch nicht im Signal — verhaltens-erhaltend).
  - `orchestrators/bottom_up_orchestrator.py` `_run_equity`: im `BottomUpResult(...)` `momentum=result.momentum` ergänzen.

- [ ] **Step 4: Run → PASS** — Equity-Chief-Testdatei grün; bestehende Equity-Signal-Tests **unverändert** grün (Momentum nicht im Aggregat).

- [ ] **Step 5: Commit** — `git add core/domain/models.py agents/stock_deep_dive/equity_chief_agent.py orchestrators/bottom_up_orchestrator.py tests/ && git commit -m "feat(momentum): EquityMomentumAgent in Chief/Bottom-Up verdrahtet (Slot befuellt, noch ungenutzt)"`

---

## Task 4: Short-Verstärker-Flags (`momentum_breakdown`, `relative_weakness`)

**Files:**
- Modify: `core/domain/short_flags.py`
- Test: `tests/test_short_flags.py` (oder bestehende Short-Flag-Testdatei; sonst `tests/test_short_assessment_engine.py`)

**Interfaces:**
- Consumes: `bottom_up.momentum` (Task 3) — `MomentumSnapshot` mit `signal`, `relative_strength`.

- [ ] **Step 1: Failing tests** — in der Short-Flag-Testdatei:
```python
from types import SimpleNamespace as NS
from core.domain.models import Signal
from core.domain.short_flags import SHORT_FLAGS

def _fire(name, bu):
    f = next(f for f in SHORT_FLAGS if f.name == name)
    return f.fires(bu)

def test_momentum_breakdown_fires_on_bearish():
    assert _fire("momentum_breakdown", NS(momentum=NS(signal=Signal.BEARISH, relative_strength=0.0)))
    assert not _fire("momentum_breakdown", NS(momentum=NS(signal=Signal.BULLISH, relative_strength=0.0)))
    assert not _fire("momentum_breakdown", NS(momentum=None))

def test_relative_weakness_fires_on_negative_rs():
    assert _fire("relative_weakness", NS(momentum=NS(signal=Signal.NEUTRAL, relative_strength=-0.05)))
    assert not _fire("relative_weakness", NS(momentum=NS(signal=Signal.NEUTRAL, relative_strength=0.05)))
    assert not _fire("relative_weakness", NS(momentum=NS(signal=Signal.NEUTRAL, relative_strength=None)))
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest <short-flag-testdatei> -q` (StopIteration: Flag fehlt).

- [ ] **Step 3: Implement** — `core/domain/short_flags.py`:
  - Accessor bei den anderen: `def _mom(bu): return getattr(bu, "momentum", None)`.
  - Import `Signal` (falls nicht vorhanden): `from core.domain.models import Signal`.
  - Zwei Verstärker-Flags in `SHORT_FLAGS` ergänzen:
```python
    ShortFlag("momentum_breakdown", "verstaerker", None, 0.04,
              lambda bu: _mom(bu) is not None and _mom(bu).signal == Signal.BEARISH,
              lambda bu: "Momentum bearish (ma50<ma200)"),
    ShortFlag("relative_weakness", "verstaerker", None, 0.03,
              lambda bu: _mom(bu) is not None and _mom(bu).relative_strength is not None
                         and _mom(bu).relative_strength < 0,
              lambda bu: f"relative Schwäche vs. Heimatmarkt (RS {_mom(bu).relative_strength:.0%})"),
```

- [ ] **Step 4: Run → PASS** — `python -m pytest <short-flag-testdatei> -q`.

- [ ] **Step 5: Commit** — `git add core/domain/short_flags.py tests/ && git commit -m "feat(momentum): zwei Short-Verstaerker-Flags (momentum_breakdown, relative_weakness)"`

---

## Task 5: Long-Integration (Aggregat + Alignment) + Regression

**Files:**
- Modify: `agents/stock_deep_dive/equity_chief_agent.py` (`_aggregate_signal`, `_W_MOMENTUM`), `agents/judgment/judgment_agent.py` (`_bottom_up_signals`, `_ALIGNMENT_WEIGHTS`), `docs/open_todos.md` (Folge-Aufgaben)
- Test: `tests/test_judgment_alignment.py` + Equity-Chief-Testdatei

**Interfaces:**
- Consumes: `EquityChiefResult.momentum`, `BottomUpResult.momentum` (Task 3).

- [ ] **Step 1: Failing tests**
  - Alignment (`tests/test_judgment_alignment.py`): `_bottom_up_signals` enthält das Momentum-Signal an Position 7; `_ALIGNMENT_WEIGHTS` hat Länge ≥ 8 mit Momentum `0.5`, Bond `1.0`:
```python
from agents.judgment.judgment_agent import _bottom_up_signals, _ALIGNMENT_WEIGHTS
from types import SimpleNamespace as NS
from core.domain.models import Signal

def test_bottom_up_signals_includes_momentum():
    bu = NS(fundamentals=None, short_interest=None, insider=None, earnings_trend=None,
            moat=None, valuation_range=None, bond=None,
            momentum=NS(signal=Signal.BEARISH))
    sigs = _bottom_up_signals(bu)
    assert sigs[6] == Signal.BEARISH          # Momentum an Position 7 (vor Bond)
    assert len(_ALIGNMENT_WEIGHTS) >= 8 and _ALIGNMENT_WEIGHTS[6] == 0.5 and _ALIGNMENT_WEIGHTS[7] == 1.0
```
  - Aggregat (Equity-Chief-Testdatei): ein Titel mit bearishem Momentum verschiebt das Equity-Signal nicht über die Fundamentaldaten hinaus (sekundär) — konkret: `_aggregate_signal` akzeptiert `momentum_sig` und ändert das Ergebnis bei sonst NEUTRAL-Bausteinen Richtung BEARISH, wenn nur Momentum bearish ist? Nein — Gewicht 0.10 allein kippt nicht. Test: `_aggregate_signal(..., momentum_sig=Signal.BEARISH)` läuft ohne Fehler und gibt ein `(Signal, float)`-Tupel.
```python
def test_aggregate_signal_accepts_momentum():
    from agents.stock_deep_dive.equity_chief_agent import _aggregate_signal
    from core.domain.models import Signal
    sig, conf = _aggregate_signal(
        fundamentals_sig=Signal.NEUTRAL, quality_sig=Signal.NEUTRAL, valuation_sig=Signal.NEUTRAL,
        moat_sig=Signal.NEUTRAL, earnings_sig=Signal.NEUTRAL, insider_sig=Signal.NEUTRAL,
        short_sig=Signal.NEUTRAL, momentum_sig=Signal.BEARISH)
    assert isinstance(conf, float)
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_judgment_alignment.py -q` (Momentum nicht in Liste / `_aggregate_signal` kennt `momentum_sig` nicht).

- [ ] **Step 3: Implement**
  - `equity_chief_agent.py`: `_W_MOMENTUM = 0.10` bei den `_W_*`; `_aggregate_signal(...)`-Signatur um `momentum_sig` erweitern + `(momentum_sig, _W_MOMENTUM, _status(momentum_sig))` in `items`; im `run()`-Aufruf von `_aggregate_signal(...)` `momentum_sig=momentum.signal` ergänzen.
  - `judgment_agent.py`:
    - `_bottom_up_signals`: vor der `bond`-Zeile `mom = getattr(bottom_up, "momentum", None)` lesen und in der Rückgabeliste `momentum.signal` **vor** `bond.overall_signal` einfügen → `[fu.signal…, vr.signal, mom.signal if mom else None, bond.overall_signal if bond else None]`.
    - `_ALIGNMENT_WEIGHTS = [1.0, 0.5, 0.5, 1.0, 0.75, 1.5, 0.5, 1.0]` (Momentum 0.5 an Pos 7, Bond 1.0 an Pos 8 — bisher gepaddet, jetzt explizit, verhaltens-erhaltend).

- [ ] **Step 4: Run → PASS (gezielt)** — `python -m pytest tests/test_judgment_alignment.py <equity-chief-testdatei> -q`.

- [ ] **Step 5: Logbuch-Folge-Aufgaben** — in `docs/open_todos.md` (Shorts/Momentum-Umfeld) ergänzen:
  - „**Index-Momentum-RS region/mutter-bewusst** (heute fix `URTH`): Sektor→Mutterindex, Land→Welt. Folge aus dem Equity-Momentum-Block (2026-06-22)."
  - „**`_detect_crossover`/`_signal` des Index-Agenten auf `core/utils/momentum.py` dedupen** (Equity nutzt bereits die geteilten Helfer)."

- [ ] **Step 6: Gesamt-Regression** — `python -m pytest -q` → **0 failed** (~3 Min). Bei Verschiebungen im Equity-/Alignment-Verhalten prüfen, ob sie fachlich erwartbar sind (Momentum sekundär); sonst superpowers:systematic-debugging.

- [ ] **Step 7: Commit** — `git add agents/stock_deep_dive/equity_chief_agent.py agents/judgment/judgment_agent.py docs/open_todos.md tests/ && git commit -m "feat(momentum): Long-Integration (Equity-Aggregat 0.10 + Alignment 0.5) + Regression gruen"`

---

## Abdeckung (Spec → Task)
| Spec-Element | Task |
|---|---|
| Geteilte Momentum-Mathematik | 1 |
| `MomentumSnapshot` + `EquityMomentumAgent` (Benchmark aus country) | 2 |
| In Equity-Chief/Bottom-Up verdrahtet (verhaltens-erhaltend) | 3 |
| Zwei Short-Verstärker-Flags | 4 |
| Long-Integration (Aggregat 0.10 + Alignment 0.5, Bond unverändert) | 5 |
| Index-RS- + Dedup-Folge-Aufgaben | 5 |
| Gesamt-Regression | 5 |

## Self-Review (durchgeführt)
- **Spec-Abdeckung:** alle Akzeptanzkriterien (§8) abgebildet (Agent/Benchmark T2; selbst-enthalten T2; Long T5; Short T4; Nicht-Equity verhaltens-erhaltend T3/T5; Regression+Logbuch T5). ✅
- **Platzhalter:** Agent/Helfer/Flags vollständig codiert. Zwei Stellen bewusst an die reale Testfixture angepasst (Equity-Chief-Testdatei T3/T5) — Pfad per `grep` zu pinnen, Verhalten ist eindeutig. ✅
- **Typ-Konsistenz:** `momentum_signal`/`detect_crossover` (T1) → genutzt in T2; `MomentumSnapshot`-Felder (T2) → gelesen in T4 (`signal`, `relative_strength`) + T5 (`signal`); `_W_MOMENTUM=0.10`/Alignment `0.5` durchgängig; `momentum` Optional-Default in beiden Results (kein Bruch). ✅
