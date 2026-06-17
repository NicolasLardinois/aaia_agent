# Plan A — Core-Quant: Backtester, Konfidenz & Portfolio-Risiko — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Backtest-Validität (P1.1), Risikometriken (P1.2) und Konfidenz-Kalibrierung (P1.3) des Systems fachlich reparieren. Konkret: fixe Forward-Windows mit eingefrorenem, marktbereinigtem Return statt Spot-Repricing; Survivorship-Fix (delistete Ticker = Totalverlust); Entfernen der „neutral"-Klasse, die Fehler wegdefiniert; Sharpe/Sortino/MaxDD/Profit-Factor inkl. Kosten; Konfidenz aus historischer bedingter Trefferrate je `(alignment, severity)`-Bucket; relative/gewichtete Alignment-Schwelle; MAD-robuste Anomalie-Checks mit Multiple-Testing-Korrektur und wertgewichtetem Insider-Check; Top-Down-Backtester als echter Prognose-Backtest statt Regime-Adjazenz; Portfolio-Monitor mit FX-Umrechnung, Korrelations-/Klumpenrisiko und Vola/MaxDD-Feld.

**Architecture:** EDA + Hexagonal. Reine Rechenlogik wandert in testbare Pure-Functions in `core/utils/` (neue Module `performance_metrics.py`, `backtest.py`). Agenten orchestrieren nur (Daten laden → Pure-Function → Memory speichern). Provider-Zugriffe (yfinance, FX) werden über Funktions-Injektion bzw. Mock testbar gehalten — analog zu den bestehenden `_fetch_price`-Helfern, die in Tests gemockt werden.

**Tech Stack:** Python, asyncio, pytest
**Abhängigkeiten:** Plan 0 (Shared Utilities) — stellt in `core/utils/statistics.py` bereit: `robust_z_score(current, history, min_n=20)`, `ROBUST_Z_THRESHOLD=3.5`, `bonferroni_z_threshold(base_threshold, n_tests)`. Diese werden hier referenziert, **nicht** neu definiert. Optional `core/utils/timeseries_history.py` `DatedHistory` für eingefrorene Forward-Return-Snapshots.

---

## Annahmen über Datenfelder (vor Implementierung verifizieren)

Diese Annahmen stützen sich auf `adapters/memory/supabase_memory.py` und die bestehenden Backtester. Falls eine Annahme nicht zutrifft, im jeweiligen Task anpassen (Tests bleiben strukturell gleich):

- **History-Einträge** (`load_global_history` / `load_history`) sind `dict` mit mindestens: `timestamp` (timezone-aware `datetime`), `ticker` (str), `price_at_analysis` (float | None), `dominant_signal` (str: "bullish"/"bearish"/"neutral"), `recommendation` (str: "BUY"/"SELL"/"SHORT"/"HOLD"), `regime` (str), `market` (str), `indicators_snapshot` (dict).
- **Forward-Preise** werden über einen injizierbaren Provider mit Signatur `get_price_history(ticker, period) -> pandas.DataFrame` geholt (DataFrame mit `DatetimeIndex` und Spalte `"Close"`), wie `adapters/data/yahoo_finance.py`. Für die Backtests reichen wir eine schmalere Funktion `price_on_or_after(ticker, date) -> Optional[float]` durch, die in Tests gemockt wird.
- **Benchmark-Mapping je Markt:** USA→`"^GSPC"`, CH→`"^SSMI"`, Eurozone→`"^STOXX"`. Default-Benchmark `"^GSPC"`.
- **Portfolio-Positionen** (`data/portfolio.json` → `positions`) sind `dict` mit: `ticker`, `shares`, `buy_price`, `sector`, `asset_class`, `country`, optional `currency` (ISO-3, Default "USD"), optional `current_price`.
- **FX:** Eine injizierbare Funktion `fx_rate(from_ccy, to_ccy) -> float` (Default-Basiswährung "USD"). In Tests gemockt; produktiv via yfinance `"{FROM}{TO}=X"`.
- **delisteter Ticker:** `price_on_or_after` liefert `None` für aktuellen/Forward-Preis → Totalverlust (Forward-Return = −1.0), **nicht** `continue`.

---

## Dateienübersicht

| Datei | Art | Inhalt |
|---|---|---|
| `core/utils/performance_metrics.py` | **NEU** | `sharpe_ratio`, `sortino_ratio`, `max_drawdown`, `profit_factor`, `annualized_return`, `apply_costs` — reine Funktionen über Return-Listen |
| `core/utils/backtest.py` | **NEU** | `forward_return`, `market_adjusted_return`, `is_correct`, `hit_rate_ci` (Wilson), `BENCHMARK_BY_MARKET`, `HORIZONS_DAYS` |
| `agents/backtester/bottom_up_backtester_agent.py` | Edit | fixes Forward-Window, marktbereinigt, Survivorship, keine „neutral"-Klasse, CI, Risikometriken |
| `agents/backtester/judgment_backtester_agent.py` | Edit | identische Backtest-Reparatur für Empfehlungen |
| `agents/backtester/top_down_backtester_agent.py` | Edit | echter Prognose-Backtest (Regime t → Marktergebnis t+h) statt Adjazenz |
| `agents/backtester_chief_agent.py` | Edit | Provider-Injektion (price/benchmark) an Sub-Backtester durchreichen |
| `core/domain/recommendation.py` | Edit | `compute_confidence` aus Backtest-Buckets; Positionsgröße + Borrow-Hinweis in `derive_recommendation` |
| `agents/judgment/judgment_agent.py` | Edit | `_derive_alignment` relativ+gewichtet; `_backtester_summary` korrekt beschriftet; Backtest-Buckets an `compute_confidence` durchreichen |
| `agents/anomaly/bottom_up_anomaly_agent.py` | Edit | MAD-Z (`robust_z_score`), Min-N=20, Bonferroni, wertgewichteter Insider-Check |
| `agents/anomaly/top_down_anomaly_agent.py` | Edit | MAD-Z, Min-N=20, Bonferroni |
| `agents/anomaly_chief_agent.py` | Edit | `n_tests` durchreichen (für Bonferroni-Schwelle) |
| `agents/portfolio/portfolio_monitor_agent.py` | Edit | FX-Umrechnung, Korrelations-Klumpenrisiko, Portfolio-Vola/MaxDD-Feld |

---

### Task 1 — Performance-Metriken (`core/utils/performance_metrics.py`)

**Files:** `core/utils/performance_metrics.py`, `tests/test_performance_metrics.py`

Reine Funktionen über Listen periodischer Returns (Dezimal, z. B. `0.03` = +3 %). Annualisierungsfaktor als Parameter (default 252 Handelstage; für Trade-Return-Listen kann der Aufrufer `1` übergeben).

- [ ] **Failing Test schreiben** — `tests/test_performance_metrics.py`:

```python
import math
import pytest
from core.utils.performance_metrics import (
    sharpe_ratio, sortino_ratio, max_drawdown,
    profit_factor, annualized_return, apply_costs,
)


def test_sharpe_zero_for_empty():
    assert sharpe_ratio([]) == 0.0


def test_sharpe_zero_for_constant_returns():
    # Std=0 → kein Risiko messbar → 0.0 (kein ZeroDivision)
    assert sharpe_ratio([0.01, 0.01, 0.01]) == 0.0


def test_sharpe_positive_for_positive_excess():
    rets = [0.02, 0.01, 0.03, -0.01, 0.02]
    s = sharpe_ratio(rets, risk_free=0.0, annualization=1)
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    expected = mean / math.sqrt(var)
    assert s == pytest.approx(expected, abs=1e-9)


def test_sharpe_annualization_factor():
    rets = [0.01, -0.005, 0.02, 0.0, 0.015]
    s1 = sharpe_ratio(rets, annualization=1)
    s252 = sharpe_ratio(rets, annualization=252)
    assert s252 == pytest.approx(s1 * math.sqrt(252), abs=1e-9)


def test_sortino_uses_downside_deviation():
    rets = [0.02, -0.01, 0.03, -0.02, 0.01]
    downside = [min(0.0, r) for r in rets]
    dd = math.sqrt(sum(d ** 2 for d in downside) / len(rets))
    mean = sum(rets) / len(rets)
    expected = (mean / dd)
    assert sortino_ratio(rets, risk_free=0.0, annualization=1) == pytest.approx(expected, abs=1e-9)


def test_sortino_no_downside_returns_zero():
    assert sortino_ratio([0.01, 0.02, 0.03], annualization=1) == 0.0


def test_max_drawdown_simple():
    # Equity: 1.0 → 1.1 → 0.88 (von 1.1) → 0.99 ; max DD = (0.88-1.1)/1.1
    rets = [0.10, -0.20, 0.125]
    dd = max_drawdown(rets)
    assert dd == pytest.approx(-0.20, abs=1e-9)


def test_max_drawdown_no_loss_is_zero():
    assert max_drawdown([0.01, 0.02, 0.03]) == 0.0


def test_profit_factor_basic():
    rets = [0.05, -0.02, 0.03, -0.01]
    pf = profit_factor(rets)
    assert pf == pytest.approx(0.08 / 0.03, abs=1e-9)


def test_profit_factor_no_losses_is_inf():
    assert profit_factor([0.01, 0.02]) == float("inf")


def test_profit_factor_no_trades_is_zero():
    assert profit_factor([]) == 0.0


def test_annualized_return_compounds():
    # zwei +21% Trades à 0.5 Jahre → (1.21*1.21)^(1/1.0)-1 = 0.4641
    ar = annualized_return([0.21, 0.21], periods_per_year=2)
    assert ar == pytest.approx(1.21 ** 2 - 1, abs=1e-9)


def test_apply_costs_subtracts_round_trip():
    # 0.001 (10 bps) pro Seite → 0.002 Round-Trip auf einen Trade-Return
    assert apply_costs(0.05, cost_per_side=0.001) == pytest.approx(0.048, abs=1e-12)
```

- [ ] **Test ausführen → erwartet FAIL** (Modul existiert nicht):

```
python -m pytest tests/test_performance_metrics.py -q
```

- [ ] **Minimale echte Implementierung** — `core/utils/performance_metrics.py`:

```python
import math


def apply_costs(trade_return: float, cost_per_side: float = 0.0005) -> float:
    """Round-Trip-Transaktionskosten (Kauf + Verkauf) vom Trade-Return abziehen.

    cost_per_side als Dezimal (0.0005 = 5 bps je Seite).
    """
    return trade_return - 2.0 * cost_per_side


def sharpe_ratio(
    returns: list[float],
    risk_free: float = 0.0,
    annualization: int = 252,
) -> float:
    """(mean_excess / std) * sqrt(annualization). Std=0 oder n<2 → 0.0."""
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free for r in returns]
    mean = sum(excess) / len(excess)
    var = sum((r - mean) ** 2 for r in excess) / (len(excess) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0.0:
        return 0.0
    return (mean / std) * math.sqrt(annualization)


def sortino_ratio(
    returns: list[float],
    risk_free: float = 0.0,
    annualization: int = 252,
) -> float:
    """mean_excess / downside_deviation * sqrt(annualization). Keine Downside → 0.0."""
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free for r in returns]
    mean = sum(excess) / len(excess)
    downside = [min(0.0, r) for r in excess]
    dd = math.sqrt(sum(d ** 2 for d in downside) / len(excess))
    if dd == 0.0:
        return 0.0
    return (mean / dd) * math.sqrt(annualization)


def max_drawdown(returns: list[float]) -> float:
    """Maximaler Drawdown (<= 0.0) aus kumulativer Equity-Kurve über Trade-Returns."""
    if not returns:
        return 0.0
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= (1.0 + r)
        if equity > peak:
            peak = equity
        dd = (equity - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return max_dd


def profit_factor(returns: list[float]) -> float:
    """Sum(Gewinne) / |Sum(Verluste)|. Keine Verluste → inf, keine Trades → 0.0."""
    if not returns:
        return 0.0
    gains = sum(r for r in returns if r > 0)
    losses = sum(r for r in returns if r < 0)
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / abs(losses)


def annualized_return(returns: list[float], periods_per_year: float = 1.0) -> float:
    """Geometrisch kumulierter, auf Jahresbasis hochgerechneter Return."""
    if not returns:
        return 0.0
    growth = 1.0
    for r in returns:
        growth *= (1.0 + r)
    years = len(returns) / periods_per_year if periods_per_year > 0 else len(returns)
    if years <= 0:
        return 0.0
    return growth ** (1.0 / years) - 1.0
```

- [ ] **Test ausführen → erwartet PASS:**

```
python -m pytest tests/test_performance_metrics.py -q
```

- [ ] **Commit:**

```
git add core/utils/performance_metrics.py tests/test_performance_metrics.py
git commit -m "feat(perf-metrics): Sharpe/Sortino/MaxDD/ProfitFactor + Kosten (P1.2)"
```

---

### Task 2 — Backtest-Kernlogik (`core/utils/backtest.py`)

**Files:** `core/utils/backtest.py`, `tests/test_backtest_utils.py`

Fixes Forward-Window, marktbereinigter Return, Korrektheits-Klassifikation ohne „neutral", Wilson-Konfidenzintervall, Survivorship-Fix.

- [ ] **Failing Test schreiben** — `tests/test_backtest_utils.py`:

```python
import pytest
from core.utils.backtest import (
    forward_return, market_adjusted_return, is_correct,
    hit_rate_ci, benchmark_for_market, HORIZONS_DAYS, MIN_SAMPLE,
)


def test_forward_return_basic():
    assert forward_return(100.0, 110.0) == pytest.approx(0.10, abs=1e-12)


def test_forward_return_delisted_is_total_loss():
    # Forward-Preis None (delistet/insolvent) → Totalverlust −100 %
    assert forward_return(100.0, None) == pytest.approx(-1.0, abs=1e-12)


def test_forward_return_zero_entry_is_none():
    assert forward_return(0.0, 50.0) is None


def test_market_adjusted_subtracts_benchmark():
    # Asset +10 %, Benchmark +4 % → Alpha +6 %
    assert market_adjusted_return(0.10, 0.04) == pytest.approx(0.06, abs=1e-12)


def test_market_adjusted_none_benchmark_passthrough():
    # Kein Benchmark verfügbar → roher Return
    assert market_adjusted_return(0.10, None) == pytest.approx(0.10, abs=1e-12)


def test_is_correct_bullish_positive_alpha():
    assert is_correct("bullish", 0.02) is True
    assert is_correct("bullish", -0.02) is False


def test_is_correct_bearish_negative_alpha():
    assert is_correct("bearish", -0.02) is True
    assert is_correct("bearish", 0.02) is False


def test_is_correct_buy_sell_short_aliases():
    assert is_correct("BUY", 0.01) is True
    assert is_correct("SELL", -0.01) is True
    assert is_correct("SHORT", -0.01) is True
    assert is_correct("HOLD", 0.0) is False  # HOLD ist keine Richtungswette → nie "correct"


def test_is_correct_no_neutral_class():
    # Kleiner positiver Alpha bei bullish = correct, kein "neutral"-Schlupfloch
    assert is_correct("bullish", 0.001) is True
    assert is_correct("bullish", -0.001) is False


def test_hit_rate_ci_wilson_bounds():
    lo, hi = hit_rate_ci(7, 10)
    assert 0.0 <= lo < 0.7 < hi <= 1.0


def test_hit_rate_ci_zero_n():
    assert hit_rate_ci(0, 0) == (0.0, 0.0)


def test_benchmark_for_market():
    assert benchmark_for_market("USA") == "^GSPC"
    assert benchmark_for_market("CH") == "^SSMI"
    assert benchmark_for_market("DE") == "^STOXX"
    assert benchmark_for_market("unknown") == "^GSPC"


def test_horizons_and_min_sample_constants():
    assert HORIZONS_DAYS == (30, 60, 90)
    assert MIN_SAMPLE >= 10
```

- [ ] **Test ausführen → erwartet FAIL:**

```
python -m pytest tests/test_backtest_utils.py -q
```

- [ ] **Minimale echte Implementierung** — `core/utils/backtest.py`:

```python
import math
from typing import Optional

HORIZONS_DAYS: tuple[int, ...] = (30, 60, 90)
MIN_SAMPLE: int = 10

_EUROZONE = {
    "DE", "FR", "IT", "ES", "NL", "AT", "BE", "PT", "FI", "IE",
    "GR", "SK", "SI", "EE", "LV", "LT", "LU", "MT", "CY",
}
BENCHMARK_BY_MARKET: dict[str, str] = {"USA": "^GSPC", "CH": "^SSMI"}
_DEFAULT_BENCHMARK = "^GSPC"

# Mapping Signal/Empfehlung → erwartete Richtung des marktbereinigten Returns.
# HOLD/neutral sind KEINE Richtungswetten und können nie "correct" sein.
_BULLISH = {"bullish", "buy"}
_BEARISH = {"bearish", "sell", "short"}


def benchmark_for_market(market: str) -> str:
    m = (market or "").upper().strip()
    if m in BENCHMARK_BY_MARKET:
        return BENCHMARK_BY_MARKET[m]
    if m in _EUROZONE:
        return "^STOXX"
    return _DEFAULT_BENCHMARK


def forward_return(price_entry: float, price_forward: Optional[float]) -> Optional[float]:
    """Forward-Return über fixes Window. price_forward=None → Totalverlust (Survivorship-Fix)."""
    if price_entry is None or price_entry <= 0:
        return None
    if price_forward is None:
        return -1.0
    return (price_forward - price_entry) / price_entry


def market_adjusted_return(asset_ret: float, benchmark_ret: Optional[float]) -> float:
    """Alpha = Asset-Return − Benchmark-Return. Kein Benchmark → roher Return."""
    if benchmark_ret is None:
        return asset_ret
    return asset_ret - benchmark_ret


def is_correct(action: str, adjusted_return: float) -> bool:
    """Korrekt = marktbereinigtes Vorzeichen passt zur Richtung. Keine 'neutral'-Klasse."""
    a = (action or "").strip().lower()
    if a in _BULLISH:
        return adjusted_return > 0
    if a in _BEARISH:
        return adjusted_return < 0
    return False


def hit_rate_ci(correct: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson-Score-Konfidenzintervall der Trefferrate. total=0 → (0.0, 0.0)."""
    if total <= 0:
        return (0.0, 0.0)
    p = correct / total
    denom = 1.0 + z ** 2 / total
    center = (p + z ** 2 / (2 * total)) / denom
    margin = (z * math.sqrt(p * (1 - p) / total + z ** 2 / (4 * total ** 2))) / denom
    lo = max(0.0, center - margin)
    hi = min(1.0, center + margin)
    return (round(lo, 4), round(hi, 4))
```

- [ ] **Test ausführen → erwartet PASS:**

```
python -m pytest tests/test_backtest_utils.py -q
```

- [ ] **Commit:**

```
git add core/utils/backtest.py tests/test_backtest_utils.py
git commit -m "feat(backtest): fixes Forward-Window + marktbereinigter Return + Wilson-CI (P1.1)"
```

---

### Task 3 — Bottom-Up-Backtester reparieren

**Files:** `agents/backtester/bottom_up_backtester_agent.py`, `tests/test_backtester_agents.py`

Fixes Forward-Window je Eintrag, eingefrorener Forward-Snapshot, marktbereinigt, Survivorship, keine „neutral"-Klasse, Risikometriken + CI. Preis-/Benchmark-Zugriff wird injizierbar gemacht (Default: yfinance-basiert), damit Tests deterministisch mocken können.

- [ ] **Failing Test schreiben** — neue Tests an `tests/test_backtester_agents.py` anhängen (alte `_verdict`/`bu_verdict`-Tests werden in diesem Task ersetzt, da `_verdict` entfällt). Ersetze die Importzeile `from agents.backtester.bottom_up_backtester_agent import _verdict as bu_verdict` und die drei `test_bottomup_verdict_*`-Tests durch:

```python
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from agents.backtester.bottom_up_backtester_agent import BottomUpBacktesterAgent


def _entry(ticker, signal, price, days_ago, market="USA"):
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "ticker": ticker, "dominant_signal": signal,
        "price_at_analysis": price, "timestamp": ts, "market": market,
    }


def _price_fn(forward_prices):
    # forward_prices: {(ticker, horizon): price_or_None}
    def fn(ticker, entry_date, horizon_days):
        return forward_prices.get((ticker, horizon_days))
    return fn


def test_bottomup_skips_entries_younger_than_min_horizon():
    memory = MagicMock()
    # 10 Tage alt → kein 30/60/90-Window abgeschlossen → nicht auswertbar
    memory.load_global_history.return_value = [_entry("AAA", "bullish", 100.0, 10)]
    agent = BottomUpBacktesterAgent(
        memory, price_on_horizon=_price_fn({}), benchmark_return=lambda *a: 0.0,
    )
    asyncio.run(agent.run())
    memory.save_backtester_report.assert_not_called()


def test_bottomup_market_adjusted_correct():
    memory = MagicMock()
    memory.load_global_history.return_value = [_entry("AAA", "bullish", 100.0, 100)]
    # Asset +10 % über 30 Tage, Benchmark +4 % → Alpha +6 % → bullish correct
    prices = _price_fn({("AAA", 30): 110.0, ("AAA", 60): 110.0, ("AAA", 90): 110.0})
    agent = BottomUpBacktesterAgent(
        memory, price_on_horizon=prices, benchmark_return=lambda market, d, h: 0.04,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    per_entry = [r for r in reports if r.get("ticker") == "AAA"]
    assert per_entry and per_entry[0]["verdict"] == "correct"


def test_bottomup_delisted_counts_as_total_loss():
    memory = MagicMock()
    memory.load_global_history.return_value = [_entry("DEAD", "bullish", 100.0, 100)]
    # Forward-Preis None → Totalverlust → bullish incorrect (nicht übersprungen!)
    prices = _price_fn({})  # alle None
    agent = BottomUpBacktesterAgent(
        memory, price_on_horizon=prices, benchmark_return=lambda *a: 0.0,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    per_entry = [r for r in reports if r.get("ticker") == "DEAD"]
    assert per_entry and per_entry[0]["verdict"] == "incorrect"


def test_bottomup_aggregate_report_has_metrics_and_ci():
    memory = MagicMock()
    hist = [_entry(f"T{i}", "bullish", 100.0, 100) for i in range(12)]
    memory.load_global_history.return_value = hist
    # alle +10 %, Benchmark 0 → alle correct
    def price_fn(ticker, d, h):
        return 110.0
    agent = BottomUpBacktesterAgent(
        memory, price_on_horizon=price_fn, benchmark_return=lambda *a: 0.0,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    agg = [r for r in reports if r.get("ticker") is None]
    assert agg, "Aggregat-Report fehlt"
    a = agg[0]
    assert "sharpe" in a and "max_drawdown" in a and "profit_factor" in a
    assert "hit_rate_ci_low" in a and "hit_rate_ci_high" in a
    assert a["sample_size"] >= 10
```

- [ ] **Test ausführen → erwartet FAIL** (Konstruktor-Signatur/Verhalten neu):

```
python -m pytest tests/test_backtester_agents.py -q
```

- [ ] **Minimale echte Implementierung** — `agents/backtester/bottom_up_backtester_agent.py` vollständig ersetzen:

```python
from datetime import datetime, timezone
from typing import Callable, Optional

import yfinance as yf

from core.ports.memory_port import MemoryPort
from core.utils.backtest import (
    HORIZONS_DAYS, MIN_SAMPLE, benchmark_for_market,
    forward_return, hit_rate_ci, is_correct, market_adjusted_return,
)
from core.utils.performance_metrics import (
    apply_costs, max_drawdown, profit_factor, sharpe_ratio, sortino_ratio,
)


def _default_price_on_horizon(ticker: str, entry_date: datetime, horizon_days: int) -> Optional[float]:
    """Erster Schlusskurs am/nach entry_date+horizon_days. None = kein Kurs (delistet)."""
    from datetime import timedelta
    target = entry_date + timedelta(days=horizon_days)
    try:
        df = yf.Ticker(ticker).history(start=target.strftime("%Y-%m-%d"), period="10d")
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[0])
    except Exception:
        return None


def _default_benchmark_return(market: str, entry_date: datetime, horizon_days: int) -> Optional[float]:
    bench = benchmark_for_market(market)
    entry_px = _default_price_on_horizon(bench, entry_date, 0)
    fwd_px = _default_price_on_horizon(bench, entry_date, horizon_days)
    fr = forward_return(entry_px, fwd_px) if entry_px else None
    return fr


class BottomUpBacktesterAgent:

    def __init__(
        self,
        memory: MemoryPort,
        price_on_horizon: Callable[[str, datetime, int], Optional[float]] = _default_price_on_horizon,
        benchmark_return: Callable[[str, datetime, int], Optional[float]] = _default_benchmark_return,
        cost_per_side: float = 0.0005,
    ):
        self.memory = memory
        self.price_on_horizon = price_on_horizon
        self.benchmark_return = benchmark_return
        self.cost_per_side = cost_per_side

    async def run(self) -> None:
        history = self.memory.load_global_history(days=180)
        now = datetime.now(timezone.utc)

        evaluable = [
            h for h in history
            if h.get("ticker") and h.get("dominant_signal")
            and h.get("price_at_analysis") and h.get("timestamp")
        ]
        if not evaluable:
            print("[BottomUpBacktester] Keine auswertbaren Einträge — übersprungen.")
            return

        adjusted_returns: list[float] = []
        evaluated = 0

        for entry in evaluable:
            ticker     = entry["ticker"]
            price_then = float(entry["price_at_analysis"])
            signal     = entry["dominant_signal"]
            market     = entry.get("market", "USA")
            entry_date = entry["timestamp"]

            # Größtes Forward-Window wählen, dessen Periode abgeschlossen ist.
            age_days = (now - entry_date).days
            horizon = max((h for h in HORIZONS_DAYS if h <= age_days), default=None)
            if horizon is None:
                continue  # noch kein Window abgeschlossen → (noch) nicht auswertbar

            fwd_px = self.price_on_horizon(ticker, entry_date, horizon)
            raw_ret = forward_return(price_then, fwd_px)   # None nur bei ungültigem Entry
            if raw_ret is None:
                continue

            bench_ret = self.benchmark_return(market, entry_date, horizon)
            adj_ret = market_adjusted_return(raw_ret, bench_ret)
            adj_ret = apply_costs(adj_ret, self.cost_per_side)
            verdict = "correct" if is_correct(signal, adj_ret) else "incorrect"

            adjusted_returns.append(adj_ret)
            evaluated += 1

            self.memory.save_backtester_report({
                "backtester_type":        "bottomup",
                "ticker":                 ticker,
                "original_recommendation": signal,
                "price_at_recommendation": price_then,
                "price_today":            fwd_px,
                "return_pct":             round(adj_ret * 100, 2),
                "verdict":                verdict,
                "accuracy_30d":           None,
                "accuracy_60d":           None,
                "accuracy_90d":           None,
                "notes": (
                    f"Signal={signal} | Horizont={horizon}d | "
                    f"Alpha={adj_ret * 100:.1f}% (marktbereinigt, nach Kosten)"
                ),
            })

        if evaluated >= MIN_SAMPLE:
            correct = sum(1 for r in adjusted_returns if r > 0)
            lo, hi = hit_rate_ci(correct, evaluated)
            self.memory.save_backtester_report({
                "backtester_type":        "bottomup",
                "ticker":                 None,
                "original_recommendation": None,
                "price_at_recommendation": None,
                "price_today":            None,
                "return_pct":             None,
                "verdict":                None,
                "accuracy_30d":           None,
                "accuracy_60d":           None,
                "accuracy_90d":           None,
                "sample_size":            evaluated,
                "hit_rate":               round(correct / evaluated, 3),
                "hit_rate_ci_low":        lo,
                "hit_rate_ci_high":       hi,
                "sharpe":                 round(sharpe_ratio(adjusted_returns, annualization=1), 3),
                "sortino":                round(sortino_ratio(adjusted_returns, annualization=1), 3),
                "max_drawdown":           round(max_drawdown(adjusted_returns), 3),
                "profit_factor":          round(profit_factor(adjusted_returns), 3),
                "notes": (
                    f"N={evaluated} | Hit-Rate={correct / evaluated:.0%} "
                    f"[{lo:.0%}–{hi:.0%}] (95%-CI, marktbereinigt)"
                ),
            })

        print(f"[BottomUpBacktester] {evaluated} Einträge ausgewertet (fixes Forward-Window).")
```

> **Hinweis:** `save_backtester_report` erhält zusätzliche Keys (`sample_size`, `hit_rate`, `sharpe`, …). Da `adapters/memory/supabase_memory.py` außerhalb des Scopes liegt, werden diese Keys vom Adapter via `report.get(...)` ignoriert, solange keine Spalten existieren — die Pure-Function-Tests mocken `memory` und sind davon unberührt. (Schema-Erweiterung deckt ein Parallel-Plan ab.)

- [ ] **Test ausführen → erwartet PASS:**

```
python -m pytest tests/test_backtester_agents.py -q
```

- [ ] **Commit:**

```
git add agents/backtester/bottom_up_backtester_agent.py tests/test_backtester_agents.py
git commit -m "fix(bottom-up-backtester): fixes Window, marktbereinigt, Survivorship, Risikometriken (P1.1/P1.2)"
```

---

### Task 4 — Judgment-Backtester reparieren

**Files:** `agents/backtester/judgment_backtester_agent.py`, `tests/test_backtester_agents.py`

Identische Reparatur für `recommendation` (BUY/SELL/SHORT/HOLD). HOLD ist keine Richtungswette → fällt aus der Hit-Rate (wird nicht gezählt). Borrow-Kosten-Hinweis ist Sache von `derive_recommendation` (Task 6); hier nur die Hit-Rate/Risikometriken.

- [ ] **Failing Test schreiben** — alte `j_verdict`-Tests in `tests/test_backtester_agents.py` durch folgende ersetzen (Import `from agents.backtester.judgment_backtester_agent import _verdict as j_verdict` entfernen):

```python
from agents.backtester.judgment_backtester_agent import JudgmentBacktesterAgent


def _j_entry(ticker, rec, price, days_ago, market="USA"):
    from datetime import datetime, timedelta, timezone
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "ticker": ticker, "recommendation": rec,
        "price_at_analysis": price, "timestamp": ts, "market": market,
    }


def test_judgment_buy_correct_when_alpha_positive():
    import asyncio
    memory = MagicMock()
    memory.load_global_history.return_value = [_j_entry("AAA", "BUY", 100.0, 100)]
    agent = JudgmentBacktesterAgent(
        memory,
        price_on_horizon=lambda t, d, h: 112.0,
        benchmark_return=lambda *a: 0.04,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    per = [r for r in reports if r.get("ticker") == "AAA"]
    assert per and per[0]["verdict"] == "correct"


def test_judgment_short_correct_when_alpha_negative():
    import asyncio
    memory = MagicMock()
    memory.load_global_history.return_value = [_j_entry("BBB", "SHORT", 100.0, 100)]
    agent = JudgmentBacktesterAgent(
        memory,
        price_on_horizon=lambda t, d, h: 90.0,
        benchmark_return=lambda *a: 0.0,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    per = [r for r in reports if r.get("ticker") == "BBB"]
    assert per and per[0]["verdict"] == "correct"


def test_judgment_hold_excluded_from_hitrate():
    import asyncio
    memory = MagicMock()
    hist = [_j_entry("H", "HOLD", 100.0, 100)] + [
        _j_entry(f"B{i}", "BUY", 100.0, 100) for i in range(11)
    ]
    memory.load_global_history.return_value = hist
    agent = JudgmentBacktesterAgent(
        memory,
        price_on_horizon=lambda t, d, h: 110.0,
        benchmark_return=lambda *a: 0.0,
    )
    asyncio.run(agent.run())
    reports = [c.args[0] for c in memory.save_backtester_report.call_args_list]
    agg = [r for r in reports if r.get("ticker") is None]
    assert agg and agg[0]["sample_size"] == 11  # HOLD nicht mitgezählt
```

- [ ] **Test ausführen → erwartet FAIL:**

```
python -m pytest tests/test_backtester_agents.py -q
```

- [ ] **Minimale echte Implementierung** — `agents/backtester/judgment_backtester_agent.py` vollständig ersetzen:

```python
from datetime import datetime, timezone
from typing import Callable, Optional

from core.ports.memory_port import MemoryPort
from core.utils.backtest import (
    HORIZONS_DAYS, MIN_SAMPLE, forward_return, hit_rate_ci,
    is_correct, market_adjusted_return,
)
from core.utils.performance_metrics import (
    apply_costs, max_drawdown, profit_factor, sharpe_ratio, sortino_ratio,
)
from agents.backtester.bottom_up_backtester_agent import (
    _default_benchmark_return, _default_price_on_horizon,
)

_DIRECTIONAL = {"BUY", "SELL", "SHORT"}  # HOLD = keine Richtungswette


class JudgmentBacktesterAgent:

    def __init__(
        self,
        memory: MemoryPort,
        price_on_horizon: Callable[[str, datetime, int], Optional[float]] = _default_price_on_horizon,
        benchmark_return: Callable[[str, datetime, int], Optional[float]] = _default_benchmark_return,
        cost_per_side: float = 0.0005,
    ):
        self.memory = memory
        self.price_on_horizon = price_on_horizon
        self.benchmark_return = benchmark_return
        self.cost_per_side = cost_per_side

    async def run(self) -> None:
        history = self.memory.load_global_history(days=180)
        now = datetime.now(timezone.utc)

        evaluable = [
            h for h in history
            if h.get("ticker") and h.get("recommendation")
            and h.get("price_at_analysis") and h.get("timestamp")
            and h["recommendation"] in _DIRECTIONAL
        ]
        if not evaluable:
            print("[JudgmentBacktester] Keine auswertbaren Einträge — übersprungen.")
            return

        adjusted_returns: list[float] = []
        evaluated = 0

        for entry in evaluable:
            ticker     = entry["ticker"]
            price_then = float(entry["price_at_analysis"])
            rec        = entry["recommendation"]
            market     = entry.get("market", "USA")
            entry_date = entry["timestamp"]

            age_days = (now - entry_date).days
            horizon = max((h for h in HORIZONS_DAYS if h <= age_days), default=None)
            if horizon is None:
                continue

            fwd_px = self.price_on_horizon(ticker, entry_date, horizon)
            raw_ret = forward_return(price_then, fwd_px)
            if raw_ret is None:
                continue

            bench_ret = self.benchmark_return(market, entry_date, horizon)
            adj_ret = market_adjusted_return(raw_ret, bench_ret)
            adj_ret = apply_costs(adj_ret, self.cost_per_side)
            verdict = "correct" if is_correct(rec, adj_ret) else "incorrect"

            # Für SHORT ist der "Trade-Return" das Spiegelbild des Alpha
            trade_ret = -adj_ret if rec == "SHORT" else adj_ret
            adjusted_returns.append(trade_ret)
            evaluated += 1

            self.memory.save_backtester_report({
                "backtester_type":        "judgment",
                "ticker":                 ticker,
                "original_recommendation": rec,
                "price_at_recommendation": price_then,
                "price_today":            fwd_px,
                "return_pct":             round(adj_ret * 100, 2),
                "verdict":                verdict,
                "accuracy_30d":           None,
                "accuracy_60d":           None,
                "accuracy_90d":           None,
                "notes": (
                    f"Empfehlung={rec} | Horizont={horizon}d | "
                    f"Alpha={adj_ret * 100:.1f}% | Urteil={verdict}"
                ),
            })

        if evaluated >= MIN_SAMPLE:
            correct = sum(1 for r in adjusted_returns if r > 0)
            lo, hi = hit_rate_ci(correct, evaluated)
            self.memory.save_backtester_report({
                "backtester_type":        "judgment",
                "ticker":                 None,
                "original_recommendation": None,
                "price_at_recommendation": None,
                "price_today":            None,
                "return_pct":             None,
                "verdict":                None,
                "accuracy_30d":           None,
                "accuracy_60d":           None,
                "accuracy_90d":           None,
                "sample_size":            evaluated,
                "hit_rate":               round(correct / evaluated, 3),
                "hit_rate_ci_low":        lo,
                "hit_rate_ci_high":       hi,
                "sharpe":                 round(sharpe_ratio(adjusted_returns, annualization=1), 3),
                "sortino":                round(sortino_ratio(adjusted_returns, annualization=1), 3),
                "max_drawdown":           round(max_drawdown(adjusted_returns), 3),
                "profit_factor":          round(profit_factor(adjusted_returns), 3),
                "notes": (
                    f"N={evaluated} | Hit-Rate={correct / evaluated:.0%} "
                    f"[{lo:.0%}–{hi:.0%}] (95%-CI, HOLD ausgeschlossen)"
                ),
            })
            print(f"[JudgmentBacktester] {evaluated} ausgewertet | "
                  f"Hit-Rate={correct / evaluated:.0%} [{lo:.0%}–{hi:.0%}]")
        else:
            print(f"[JudgmentBacktester] {evaluated} ausgewertet (< MIN_SAMPLE, kein Aggregat).")
```

- [ ] **Test ausführen → erwartet PASS:**

```
python -m pytest tests/test_backtester_agents.py -q
```

- [ ] **Commit:**

```
git add agents/backtester/judgment_backtester_agent.py tests/test_backtester_agents.py
git commit -m "fix(judgment-backtester): fixes Window + marktbereinigt + HOLD-Ausschluss + Risikometriken (P1.1/P1.2)"
```

---

### Task 5 — Top-Down-Backtester: echter Prognose-Backtest

**Files:** `agents/backtester/top_down_backtester_agent.py`, `tests/test_backtester_agents.py`

Statt Adjazenz zum **heutigen** Regime (Zirkularität): Für jeden historischen Regime-Eintrag bei t wird das **realisierte Marktergebnis** des Benchmarks über das Forward-Window t→t+h gemessen. Hypothese: „risk-on"-Regime (Boom/Aufschwung/Erholung) erwarten Benchmark-Return > 0, „risk-off"-Regime (Abschwung/Rezession/Depression) erwarten < 0. Treffer = realisiertes Vorzeichen passt zur Regime-Erwartung. RECOVERY/DEPRESSION sind abgedeckt.

- [ ] **Failing Test schreiben** — alte `_is_adjacent`/`_accuracy`-Tests in `tests/test_backtester_agents.py` durch folgende ersetzen (Import `from agents.backtester.top_down_backtester_agent import _is_adjacent, _accuracy` entfernen):

```python
from agents.backtester.top_down_backtester_agent import (
    _regime_expectation, _regime_correct, TopDownBacktesterAgent,
)


def test_regime_expectation_risk_on_off():
    assert _regime_expectation("Boom") > 0
    assert _regime_expectation("Aufschwung") > 0
    assert _regime_expectation("Erholung") > 0
    assert _regime_expectation("Abschwung") < 0
    assert _regime_expectation("Rezession") < 0
    assert _regime_expectation("Depression") < 0


def test_regime_correct_matches_sign():
    # Boom (risk-on) + Markt +5 % → korrekt
    assert _regime_correct("Boom", 0.05) is True
    assert _regime_correct("Boom", -0.05) is False
    # Rezession (risk-off) + Markt −5 % → korrekt
    assert _regime_correct("Rezession", -0.05) is True


def test_topdown_prognostic_accuracy():
    import asyncio
    from datetime import datetime, timedelta, timezone
    memory = MagicMock()
    now = datetime.now(timezone.utc)
    hist = [
        {"regime": "Boom", "timestamp": now - timedelta(days=100), "market": "USA"},
        {"regime": "Rezession", "timestamp": now - timedelta(days=100), "market": "USA"},
    ]
    memory.load_global_history.return_value = hist
    # Boom-Eintrag: Markt +5 % (korrekt); Rezession-Eintrag: Markt +5 % (falsch)
    agent = TopDownBacktesterAgent(memory, benchmark_return=lambda *a: 0.05)
    asyncio.run(agent.run())
    report = memory.save_backtester_report.call_args_list[0].args[0]
    assert report["backtester_type"] == "topdown"
    assert report["accuracy_90d"] == 0.5
```

- [ ] **Test ausführen → erwartet FAIL:**

```
python -m pytest tests/test_backtester_agents.py -q
```

- [ ] **Minimale echte Implementierung** — `agents/backtester/top_down_backtester_agent.py` vollständig ersetzen:

```python
from datetime import datetime, timezone
from typing import Callable, Optional

from core.ports.memory_port import MemoryPort
from core.utils.backtest import HORIZONS_DAYS, hit_rate_ci
from agents.backtester.bottom_up_backtester_agent import _default_benchmark_return

# Regime → erwartete Richtung des realisierten Benchmark-Returns (risk-on/off).
_RISK_ON  = {"Boom", "Aufschwung", "Erholung"}
_RISK_OFF = {"Abschwung", "Rezession", "Depression"}


def _regime_expectation(regime: str) -> float:
    if regime in _RISK_ON:
        return 1.0
    if regime in _RISK_OFF:
        return -1.0
    return 0.0


def _regime_correct(regime: str, realized_return: float) -> bool:
    exp = _regime_expectation(regime)
    if exp == 0.0:
        return False
    return (exp > 0 and realized_return > 0) or (exp < 0 and realized_return < 0)


class TopDownBacktesterAgent:

    def __init__(
        self,
        memory: MemoryPort,
        benchmark_return: Callable[[str, datetime, int], Optional[float]] = _default_benchmark_return,
    ):
        self.memory = memory
        self.benchmark_return = benchmark_return

    async def run(self) -> None:
        history = self.memory.load_global_history(days=180)
        if not history:
            print("[TopDownBacktester] Keine Einträge — übersprungen.")
            return

        now = datetime.now(timezone.utc)
        horizon = max(HORIZONS_DAYS)  # längstes Window für die Prognoseprüfung

        entries = [
            h for h in history
            if h.get("regime") and h.get("timestamp")
            and (now - h["timestamp"]).days >= horizon
        ]
        if not entries:
            print("[TopDownBacktester] Kein abgeschlossenes Forward-Window — übersprungen.")
            return

        correct = 0
        total = 0
        for e in entries:
            regime = e["regime"]
            if _regime_expectation(regime) == 0.0:
                continue
            realized = self.benchmark_return(e.get("market", "USA"), e["timestamp"], horizon)
            if realized is None:
                continue
            total += 1
            if _regime_correct(regime, realized):
                correct += 1

        if total == 0:
            print("[TopDownBacktester] Keine bewertbaren Regime-Prognosen — übersprungen.")
            return

        accuracy = round(correct / total, 3)
        lo, hi = hit_rate_ci(correct, total)
        report = {
            "backtester_type": "topdown",
            "ticker": None,
            "original_recommendation": None,
            "price_at_recommendation": None,
            "price_today": None,
            "return_pct": None,
            "verdict": "correct" if lo >= 0.50 else "incorrect",
            "accuracy_30d": None,
            "accuracy_60d": None,
            "accuracy_90d": accuracy,
            "sample_size": total,
            "hit_rate_ci_low": lo,
            "hit_rate_ci_high": hi,
            "notes": (
                f"Prognose-Backtest (Regime t → Benchmark t+{horizon}d): "
                f"{accuracy:.0%} aus N={total} [{lo:.0%}–{hi:.0%}]"
            ),
        }
        self.memory.save_backtester_report(report)
        print(f"[TopDownBacktester] Prognosegüte {horizon}d={accuracy:.0%} "
              f"[{lo:.0%}–{hi:.0%}] | N={total}")
```

- [ ] **Test ausführen → erwartet PASS:**

```
python -m pytest tests/test_backtester_agents.py -q
```

- [ ] **Commit:**

```
git add agents/backtester/top_down_backtester_agent.py tests/test_backtester_agents.py
git commit -m "fix(top-down-backtester): echter Prognose-Backtest statt Regime-Adjazenz (P1.1)"
```

---

### Task 6 — Backtester-Chief: Provider-Injektion

**Files:** `agents/backtester_chief_agent.py`, `tests/test_backtester_chief.py`

Der Chief reicht optional injizierbare Preis-/Benchmark-Funktionen an die Sub-Backtester durch (Default = yfinance-basiert), damit der Gesamtlauf auch end-to-end mockbar/testbar bleibt.

- [ ] **Failing Test schreiben** — `tests/test_backtester_chief.py`:

```python
import asyncio
from unittest.mock import MagicMock
from agents.backtester_chief_agent import BacktesterChiefAgent


def test_chief_injects_providers_into_subagents():
    memory = MagicMock()
    memory.load_global_history.return_value = []
    bus = MagicMock()
    price_fn = lambda t, d, h: 100.0
    bench_fn = lambda *a: 0.0
    chief = BacktesterChiefAgent(memory, bus, price_on_horizon=price_fn, benchmark_return=bench_fn)
    assert chief.bu_backtester.price_on_horizon is price_fn
    assert chief.j_backtester.benchmark_return is bench_fn
    assert chief.td_backtester.benchmark_return is bench_fn


def test_chief_run_publishes_ready():
    memory = MagicMock()
    memory.load_global_history.return_value = []
    bus = MagicMock()
    chief = BacktesterChiefAgent(memory, bus)
    asyncio.run(chief.run())
    assert bus.publish.called
```

- [ ] **Test ausführen → erwartet FAIL:**

```
python -m pytest tests/test_backtester_chief.py -q
```

- [ ] **Minimale echte Implementierung** — `agents/backtester_chief_agent.py` ersetzen:

```python
import asyncio
from datetime import datetime
from typing import Callable, Optional

from agents.backtester.top_down_backtester_agent import TopDownBacktesterAgent
from agents.backtester.bottom_up_backtester_agent import (
    BottomUpBacktesterAgent, _default_benchmark_return, _default_price_on_horizon,
)
from agents.backtester.judgment_backtester_agent import JudgmentBacktesterAgent
from core.domain.events import BacktesterChiefReady
from core.ports.event_bus import EventBus
from core.ports.memory_port import MemoryPort


class BacktesterChiefAgent:
    def __init__(
        self,
        memory: MemoryPort,
        bus: EventBus,
        price_on_horizon: Callable[[str, datetime, int], Optional[float]] = _default_price_on_horizon,
        benchmark_return: Callable[[str, datetime, int], Optional[float]] = _default_benchmark_return,
    ):
        self.memory = memory
        self.bus    = bus
        self.td_backtester = TopDownBacktesterAgent(memory, benchmark_return=benchmark_return)
        self.bu_backtester = BottomUpBacktesterAgent(
            memory, price_on_horizon=price_on_horizon, benchmark_return=benchmark_return)
        self.j_backtester  = JudgmentBacktesterAgent(
            memory, price_on_horizon=price_on_horizon, benchmark_return=benchmark_return)

    def load_context(self) -> dict:
        return self.memory.load_latest_backtester_report("judgment") or {}

    async def run(self) -> None:
        results = await asyncio.gather(
            self.td_backtester.run(),
            self.bu_backtester.run(),
            self.j_backtester.run(),
            return_exceptions=True,
        )
        failures = sum(1 for r in results if isinstance(r, Exception))
        self.bus.publish(BacktesterChiefReady(source="backtester_chief_agent", payload={"failures": failures}))
```

- [ ] **Test ausführen → erwartet PASS:**

```
python -m pytest tests/test_backtester_chief.py -q
```

- [ ] **Commit:**

```
git add agents/backtester_chief_agent.py tests/test_backtester_chief.py
git commit -m "feat(backtester-chief): injizierbare Preis-/Benchmark-Provider an Sub-Backtester"
```

---

### Task 7 — Konfidenz aus Backtest-Buckets kalibrieren

**Files:** `core/domain/recommendation.py`, `tests/test_confidence.py`

`compute_confidence` erhält optional eine kalibrierte Trefferraten-Tabelle je `(alignment, severity)`-Bucket aus dem Backtest. Liegt ein Bucket mit ausreichender Stichprobe vor, **ersetzt** die historische bedingte Trefferrate die fixe 0.70-Basis (kombinierte Severity = höhere von TD/BU). Fehlt der Bucket, greift die bisherige additive Heuristik als Fallback (Abwärtskompatibilität — bestehende Tests bleiben grün).

- [ ] **Failing Test schreiben** — an `tests/test_confidence.py` anhängen:

```python
def test_confidence_uses_calibration_bucket():
    # Bucket (aligned_bullish, none) hat historische Trefferrate 0.62 → ersetzt 0.70-Basis
    calib = {("aligned_bullish", "none"): {"hit_rate": 0.62, "n": 40}}
    conf = compute_confidence(
        alignment="aligned_bullish",
        regime_confidence=0.75,
        td_anomaly=_empty_anomaly(),
        bu_anomaly=_empty_anomaly(),
        calibration=calib,
    )
    # Basis 0.62 (kalibriert) statt 0.70; aligned_bullish-Bonus +0.10
    assert conf == round(0.62 + 0.10, 2)


def test_confidence_ignores_thin_bucket():
    # n unter Mindestgröße → Fallback auf 0.70-Heuristik
    calib = {("aligned_bullish", "none"): {"hit_rate": 0.62, "n": 3}}
    conf = compute_confidence(
        alignment="aligned_bullish",
        regime_confidence=0.75,
        td_anomaly=_empty_anomaly(),
        bu_anomaly=_empty_anomaly(),
        calibration=calib,
    )
    assert conf == round(0.70 + 0.10, 2)


def test_confidence_backward_compatible_without_calibration():
    conf = compute_confidence(
        alignment="aligned_bullish",
        regime_confidence=0.75,
        td_anomaly=_empty_anomaly(),
        bu_anomaly=_empty_anomaly(),
    )
    assert conf == round(0.70 + 0.10, 2)
```

- [ ] **Test ausführen → erwartet FAIL** (`calibration`-Parameter unbekannt):

```
python -m pytest tests/test_confidence.py -q
```

- [ ] **Minimale echte Implementierung** — in `core/domain/recommendation.py` `compute_confidence` erweitern. Konstante und kombinierte Severity einführen:

```python
_SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
_CALIB_MIN_N = 10


def _combined_severity(a: str, b: str) -> str:
    rank = max(_SEVERITY_ORDER.get(a, 0), _SEVERITY_ORDER.get(b, 0))
    for name, r in _SEVERITY_ORDER.items():
        if r == rank:
            return name
    return "none"


def compute_confidence(
    alignment: str,
    regime_confidence: float,
    td_anomaly: AnomalyReport,
    bu_anomaly: AnomalyReport,
    calibration: Optional[dict] = None,
) -> float:
    # Basis: historisch kalibrierte bedingte Trefferrate je (alignment, severity)-Bucket.
    sev = _combined_severity(td_anomaly.severity, bu_anomaly.severity)
    base = 0.70
    if calibration:
        bucket = calibration.get((alignment, sev))
        if bucket and bucket.get("n", 0) >= _CALIB_MIN_N and bucket.get("hit_rate") is not None:
            base = float(bucket["hit_rate"])

    score = base

    if alignment in ("aligned_bullish", "aligned_bearish"):
        score += 0.10
    elif alignment == "contradicting":
        score -= 0.15
    elif alignment == "mixed":
        score -= 0.05

    score += _SEVERITY_DEDUCTION.get(td_anomaly.severity, 0.0)
    score += _SEVERITY_DEDUCTION.get(bu_anomaly.severity, 0.0)

    if regime_confidence < 0.4:
        score -= 0.10

    return round(max(0.10, min(1.0, score)), 2)
```

> `Optional` ist bereits importiert. `_SEVERITY_DEDUCTION` bleibt unverändert.

- [ ] **Test ausführen → erwartet PASS** (inkl. aller bisherigen `test_confidence`-Tests):

```
python -m pytest tests/test_confidence.py -q
```

- [ ] **Commit:**

```
git add core/domain/recommendation.py tests/test_confidence.py
git commit -m "feat(confidence): Kalibrierung gegen historische Trefferrate je (alignment,severity)-Bucket (P1.3)"
```

---

### Task 8 — Positionsgröße + Borrow-Hinweis in `derive_recommendation`

**Files:** `core/domain/recommendation.py`, `tests/test_recommendation.py`, `tests/test_confidence.py`

`derive_recommendation` erhält optionale Risiko-Inputs (`days_to_cover`, `short_float_pct`) und ergänzt: (a) eine konfidenzbasierte Positionsgröße (fractional, gedeckelt) im `reasoning`; (b) bei SHORT einen Borrow-/Squeeze-Hinweis, wenn `days_to_cover` hoch ist. Alle neuen Parameter haben Defaults → bestehende Tests bleiben grün.

- [ ] **Failing Test schreiben** — an `tests/test_confidence.py` anhängen:

```python
def test_position_size_scales_with_confidence():
    rec_hi = derive_recommendation(
        alignment="aligned_bullish", signal=Signal.BULLISH, asset_class="equity",
        in_portfolio=False, market="USA", cockpit=None,
        top_down_available=False, confidence=0.90,
    )
    rec_lo = derive_recommendation(
        alignment="aligned_bullish", signal=Signal.BULLISH, asset_class="equity",
        in_portfolio=False, market="USA", cockpit=None,
        top_down_available=False, confidence=0.55,
    )
    assert rec_hi.action == Recommendation.BUY
    assert "Positionsgröße" in rec_hi.reasoning
    # höhere Konfidenz → größere empfohlene Positionsgröße (als Prozent im Text)
    import re
    hi = float(re.search(r"Positionsgröße[^0-9]*([0-9.]+)%", rec_hi.reasoning).group(1))
    lo = float(re.search(r"Positionsgröße[^0-9]*([0-9.]+)%", rec_lo.reasoning).group(1))
    assert hi > lo


def test_short_includes_borrow_warning_on_high_dtc():
    rec = derive_recommendation(
        alignment="aligned_bearish", signal=Signal.BEARISH, asset_class="equity",
        in_portfolio=False, market="USA", cockpit=None,
        top_down_available=True, confidence=0.80,
        days_to_cover=9.0, short_float_pct=22.0,
    )
    assert rec.action == Recommendation.SHORT
    assert "Squeeze" in rec.reasoning or "Borrow" in rec.reasoning
```

- [ ] **Test ausführen → erwartet FAIL:**

```
python -m pytest tests/test_confidence.py -q
```

- [ ] **Minimale echte Implementierung** — `derive_recommendation` in `core/domain/recommendation.py` erweitern. Signatur um `days_to_cover`/`short_float_pct` (Default None) ergänzen und Helfer hinzufügen:

```python
_DTC_SQUEEZE_THRESHOLD = 5.0   # Days-to-Cover ab dem ein Squeeze-Risiko vermerkt wird


def _position_size_pct(confidence: float) -> float:
    """Fractional-Sizing: lineares Mapping Konfidenz→Positionsgröße, gedeckelt 2–10 %."""
    raw = (confidence - 0.50) / 0.50 * 10.0   # 0.50→0 %, 1.00→10 %
    return round(max(2.0, min(10.0, raw)), 1)
```

In `derive_recommendation` die Signatur erweitern:

```python
def derive_recommendation(
    alignment: str,
    signal: Signal,
    asset_class: str,
    in_portfolio: bool,
    market: str,
    cockpit: Optional[CockpitResult],
    top_down_available: bool,
    confidence: float,
    days_to_cover: Optional[float] = None,
    short_float_pct: Optional[float] = None,
) -> InvestmentRecommendation:
```

Im BUY-Zweig den `reasoning`-Text um die Positionsgröße ergänzen:

```python
    if bullish and not in_portfolio:
        size = _position_size_pct(confidence)
        return InvestmentRecommendation(
            action=Recommendation.BUY,
            short_type=None,
            short_warning=None,
            confidence=confidence,
            reasoning=(
                "Bullish Signal ohne bestehende Portfolio-Position — Kauf empfohlen. "
                f"Empfohlene Positionsgröße: {size:.1f}% des Risikobudgets "
                f"(konfidenz-skaliert)."
            ),
        )
```

Im SHORT-Zweig den Borrow-/Squeeze-Hinweis anhängen:

```python
    if bearish and not in_portfolio and full_analysis:
        short_t = _short_type(asset_class)
        reasoning = "Bearish Signal ohne bestehende Portfolio-Position — Short möglich."
        if days_to_cover is not None and days_to_cover >= _DTC_SQUEEZE_THRESHOLD:
            reasoning += (
                f" ⚠️ Squeeze-/Borrow-Risiko: Days-to-Cover={days_to_cover:.1f}"
                + (f", Short-Float={short_float_pct:.0f}%" if short_float_pct is not None else "")
                + " — erhöhte Eindeckungskosten/Squeeze-Gefahr."
            )
        return InvestmentRecommendation(
            action=Recommendation.SHORT,
            short_type=short_t,
            short_warning=SHORT_WARNINGS[short_t],
            confidence=confidence,
            reasoning=reasoning,
        )
```

- [ ] **Test ausführen → erwartet PASS** (inkl. `tests/test_recommendation.py`):

```
python -m pytest tests/test_confidence.py tests/test_recommendation.py -q
```

- [ ] **Commit:**

```
git add core/domain/recommendation.py tests/test_confidence.py
git commit -m "feat(recommendation): konfidenzbasierte Positionsgröße + Borrow/Squeeze-Hinweis (P1.2)"
```

---

### Task 9 — Judgment: relative+gewichtete Alignment-Schwelle & korrekte Backtester-Beschriftung

**Files:** `agents/judgment/judgment_agent.py`, `tests/test_judgment_alignment.py`

`_derive_alignment` von absoluter „≥3"-Schwelle auf **relative** Schwelle (>60 % der nicht-neutralen Signale) mit **Gewichtung** umstellen. `_backtester_summary` korrekt beschriften (kein irreführendes „30 Tage", sondern aus den Report-Feldern `sample_size`/`hit_rate_ci_*` mit echtem Horizont). Backtest-Buckets an `compute_confidence` durchreichen.

- [ ] **Failing Test schreiben** — `tests/test_judgment_alignment.py`:

```python
from core.domain.models import Signal
from agents.judgment.judgment_agent import _derive_alignment, _backtester_summary


def test_alignment_relative_majority_bullish():
    # 4 von 5 nicht-neutralen bullish (>60 %) → aligned_bullish
    sigs = [Signal.BULLISH, Signal.BULLISH, Signal.BULLISH, Signal.BULLISH, Signal.BEARISH]
    assert _derive_alignment(sigs) == "aligned_bullish"


def test_alignment_not_aligned_when_below_threshold():
    # 3 von 5 bullish (60 %, nicht > 60 %) → contradicting (beide Richtungen vorhanden)
    sigs = [Signal.BULLISH, Signal.BULLISH, Signal.BULLISH, Signal.BEARISH, Signal.BEARISH]
    assert _derive_alignment(sigs) == "contradicting"


def test_alignment_two_of_two_bullish_is_aligned():
    # Relative Schwelle löst auch bei wenigen Signalen sauber aus
    assert _derive_alignment([Signal.BULLISH, Signal.BULLISH]) == "aligned_bullish"


def test_alignment_all_neutral_is_mixed():
    assert _derive_alignment([Signal.NEUTRAL, Signal.NEUTRAL]) == "mixed"


def test_alignment_weighted_valuation_counts_more():
    # Gewichtung: Valuation (idx 5) zählt stärker; wenn die schwergewichtige
    # Valuation bearish ist, kippt das Alignment trotz numerischer Gleichheit.
    sigs = [Signal.BULLISH, Signal.BULLISH, Signal.BEARISH, Signal.BEARISH,
            Signal.NEUTRAL, Signal.BEARISH]
    assert _derive_alignment(sigs) == "aligned_bearish"


def test_backtester_summary_labels_horizon_and_ci():
    ctx = {"sample_size": 40, "hit_rate": 0.62,
           "hit_rate_ci_low": 0.48, "hit_rate_ci_high": 0.74}
    s = _backtester_summary(ctx)
    assert "62%" in s and "48%" in s and "74%" in s
    assert "30 Tage" not in s


def test_backtester_summary_empty():
    assert "Noch kein" in _backtester_summary({})
```

- [ ] **Test ausführen → erwartet FAIL:**

```
python -m pytest tests/test_judgment_alignment.py -q
```

- [ ] **Minimale echte Implementierung** — in `agents/judgment/judgment_agent.py` `_derive_alignment` und `_backtester_summary` ersetzen. Gewichte entsprechen der Reihenfolge in `all_signals` (Fundamentals, ShortInterest, Insider, Earnings, Moat, Valuation):

```python
# Gewichte nach prädiktiver Kraft (Index-aligned zu all_signals in run()):
# [Fundamentals, ShortInterest, Insider, Earnings, Moat, Valuation]
_ALIGNMENT_WEIGHTS = [1.0, 0.5, 0.5, 1.0, 0.75, 1.5]
_ALIGNMENT_THRESHOLD = 0.60


def _derive_alignment(signals: list[Signal]) -> str:
    weights = _ALIGNMENT_WEIGHTS[:len(signals)]
    if len(weights) < len(signals):
        weights = weights + [1.0] * (len(signals) - len(weights))

    bull_w = sum(w for s, w in zip(signals, weights)
                 if s is not None and s == Signal.BULLISH)
    bear_w = sum(w for s, w in zip(signals, weights)
                 if s is not None and s == Signal.BEARISH)
    directional = bull_w + bear_w
    if directional == 0:
        return "mixed"

    if bull_w / directional > _ALIGNMENT_THRESHOLD:
        return "aligned_bullish"
    if bear_w / directional > _ALIGNMENT_THRESHOLD:
        return "aligned_bearish"
    if bull_w > 0 and bear_w > 0:
        return "contradicting"
    return "mixed"


def _backtester_summary(context: dict) -> str:
    if not context:
        return "Noch kein Backtesting-Report verfügbar (System läuft erst seit Kurzem)."
    hr = context.get("hit_rate")
    n = context.get("sample_size")
    lo = context.get("hit_rate_ci_low")
    hi = context.get("hit_rate_ci_high")
    if hr is not None and lo is not None and hi is not None and n:
        return (f"System-Treffsicherheit (fixes Forward-Window, marktbereinigt): "
                f"{hr:.0%} [{lo:.0%}–{hi:.0%}] aus N={n}")
    if hr is not None:
        return f"System-Treffsicherheit (marktbereinigt): {hr:.0%}"
    notes = context.get("notes", "")
    return notes or "Backtesting-Daten vorhanden."
```

> **Hinweis zur Test-Erwartung `test_alignment_weighted_valuation_counts_more`:** bull_w = 1.0+0.5 = 1.5 (idx0,1), bear_w = 0.5+1.0+1.5 = 3.0 (idx2,3,5) → bear_w/3.0·(…) → 3.0/4.5 = 0.667 > 0.60 → `aligned_bearish`. ✓

- [ ] **Buckets an `compute_confidence` durchreichen** — in `JudgmentAgent.run` den `backtester_context` als Kalibrierungsquelle nutzen (sofern er Buckets enthält). Die Übergabe ist additiv und bricht nichts:

```python
        confidence = compute_confidence(
            alignment=alignment,
            regime_confidence=regime_conf,
            td_anomaly=top_down_anomaly,
            bu_anomaly=bottom_up_anomaly,
            calibration=backtester_context.get("calibration") if backtester_context else None,
        )
```

- [ ] **Test ausführen → erwartet PASS:**

```
python -m pytest tests/test_judgment_alignment.py -q
```

- [ ] **Regressionscheck** — bestehende Judgment-Chief-Tests:

```
python -m pytest tests/test_chief_agents_judgment.py -q
```

- [ ] **Commit:**

```
git add agents/judgment/judgment_agent.py tests/test_judgment_alignment.py
git commit -m "fix(judgment): relative+gewichtete Alignment-Schwelle + korrekte Backtester-Beschriftung (Domäne 8)"
```

---

### Task 10 — Bottom-Up-Anomalie: MAD-Z, Min-N, Bonferroni, wertgewichteter Insider

**Files:** `agents/anomaly/bottom_up_anomaly_agent.py`, `tests/test_anomaly_agents.py`

Z-Score-Checks auf `robust_z_score` (MAD-basiert, Plan 0) umstellen, Mindest-N=20, Schwelle via `bonferroni_z_threshold(ROBUST_Z_THRESHOLD, n_tests)`. Insider-Check normiert die Transaktionszahl und bezieht die **Richtung** (`net_direction`) ein.

- [ ] **Failing Test schreiben** — an `tests/test_anomaly_agents.py` anhängen. (Bestehende Tests nutzen History-Länge 10 < 20; sie müssen auf 20 erhöht werden — passe `range(10)` in `test_bottomup_no_anomalies`, `test_bottomup_pe_statistical_anomaly`, `test_bottomup_non_equity_skips_z_score` auf `range(25)` an und `i*0.5` beibehalten.) Neue Tests:

```python
def test_bottomup_pe_robust_anomaly_with_min_n():
    agent = BottomUpAnomalyAgent()
    history = [
        {"indicators_snapshot": {"pe_ratio": 22.0 + (i % 3) * 0.3, "short_float_pct": 3.0}}
        for i in range(25)
    ]
    report = agent.run(_make_bottom_up(pe=120.0), history)
    assert report.has_anomalies is True
    assert any("KGV" in s for s in report.statistical)


def test_bottomup_below_min_n_skips_zscore():
    agent = BottomUpAnomalyAgent()
    history = [{"indicators_snapshot": {"pe_ratio": 22.0, "short_float_pct": 3.0}}
               for _ in range(15)]  # < 20
    report = agent.run(_make_bottom_up(pe=200.0), history)
    assert not any("KGV" in s for s in report.statistical)


def test_bottomup_insider_direction_aware():
    # Viele Transaktionen, aber net_direction = "net_buy" → KEIN bearisches Anomalie-Flag,
    # sondern als auffälliger Kauf-Cluster markiert (Richtung berücksichtigt).
    agent = BottomUpAnomalyAgent()
    bu = _make_bottom_up(insider_tx=40)
    bu.insider.net_direction = "net_buy"
    report = agent.run(bu, [{"indicators_snapshot": {"insider_transactions": 3}} for _ in range(25)])
    insider_flags = [s for s in report.statistical if "Insider" in s]
    assert insider_flags and "Kauf" in insider_flags[0]
```

- [ ] **Test ausführen → erwartet FAIL:**

```
python -m pytest tests/test_anomaly_agents.py -q
```

- [ ] **Minimale echte Implementierung** — `agents/anomaly/bottom_up_anomaly_agent.py`. Import und `_check` umstellen, Insider-Logik ersetzen:

```python
from core.domain.models import AnomalyReport, Signal
from core.utils.statistics import (
    ROBUST_Z_THRESHOLD, bonferroni_z_threshold, compute_severity, robust_z_score,
)

_MIN_N = 20
```

In `run` den Z-Score-Block ersetzen (nur Equity, genügend History `>= _MIN_N`). `n_tests` = Anzahl der tatsächlich durchgeführten Z-Checks (für Bonferroni):

```python
        enough_history = len(snapshots) >= _MIN_N

        if is_equity and enough_history:
            # Anzahl potenzieller Z-Checks für Multiple-Testing-Korrektur
            n_tests = 2  # KGV + Short-Float
            threshold = bonferroni_z_threshold(ROBUST_Z_THRESHOLD, n_tests)

            def _check(label: str, current, key: str):
                if current is None:
                    return
                vals = [s[key] for s in snapshots if key in s and s[key] is not None]
                if len(vals) < _MIN_N:
                    return
                z = robust_z_score(float(current), [float(v) for v in vals], min_n=_MIN_N)
                if abs(z) > threshold:
                    dir_ = "hoch" if z > 0 else "niedrig"
                    statistical.append(
                        f"{label}={current:.1f} ist ungewöhnlich {dir_} (robust-Z={z:.1f})"
                    )

            fu  = bottom_up.fundamentals
            si  = bottom_up.short_interest
            ins = bottom_up.insider

            if fu:
                _check("KGV", fu.pe_ratio, "pe_ratio")
            if si:
                _check("Short-Float", si.short_float_pct, "short_float_pct")

            # Insider: richtungs- und frequenznormiert statt absoluter ">10"-Schwelle
            if ins and ins.recent_transactions is not None:
                tx_vals = [s["insider_transactions"] for s in snapshots
                           if s.get("insider_transactions") is not None]
                if len(tx_vals) >= _MIN_N:
                    z_tx = robust_z_score(
                        float(ins.recent_transactions),
                        [float(v) for v in tx_vals], min_n=_MIN_N)
                    if z_tx > threshold:
                        direction = getattr(ins, "net_direction", "") or ""
                        kind = "Kauf-Cluster" if "buy" in direction.lower() else \
                               ("Verkaufs-Cluster" if "sell" in direction.lower() else "Aktivität")
                        statistical.append(
                            f"Ungewöhnlich hohe Insider-{kind}: "
                            f"{ins.recent_transactions} Transaktionen (robust-Z={z_tx:.1f}, "
                            f"Richtung={direction or 'n/v'})"
                        )
```

> Der Rest der Datei (Widerspruchs-Checks, `_build_summary`, Return) bleibt unverändert.

- [ ] **Test ausführen → erwartet PASS** (inkl. angepasster Bestands-Tests mit `range(25)`):

```
python -m pytest tests/test_anomaly_agents.py -q
```

- [ ] **Commit:**

```
git add agents/anomaly/bottom_up_anomaly_agent.py tests/test_anomaly_agents.py
git commit -m "fix(bottom-up-anomaly): MAD-Z + Min-N=20 + Bonferroni + richtungs-/frequenznormierter Insider (Domäne 8)"
```

---

### Task 11 — Top-Down-Anomalie: MAD-Z, Min-N, Bonferroni

**Files:** `agents/anomaly/top_down_anomaly_agent.py`, `tests/test_anomaly_agents.py`

Analoge Umstellung der `_check`-Funktion auf `robust_z_score`, Min-N=20, Bonferroni über die 4 Makro-Z-Checks (VIX, Fear&Greed, Yield-Spread, Inflation). Buffett-Z bleibt (kommt bereits robust/datiert aus Plan 0/Domäne 1), nur Schwelle auf `ROBUST_Z_THRESHOLD` umstellen.

- [ ] **Failing Test schreiben** — an `tests/test_anomaly_agents.py` anhängen. (Bestehende Top-Down-Tests mit `range(10)` auf `range(25)` erhöhen.) Neue Tests:

```python
def test_topdown_below_min_n_skips_zscore():
    agent = TopDownAnomalyAgent()
    history = [
        {"indicators_snapshot": {"vix": 18.0, "fear_greed": 50.0,
                                 "yield_spread_10y2y": 1.0, "inflation_cpi_usa": 3.0}}
        for _ in range(15)  # < 20
    ]
    report = agent.run(_make_cockpit(vix=80.0), history)
    assert not any("VIX" in s for s in report.statistical)


def test_topdown_robust_vix_anomaly_min_n():
    agent = TopDownAnomalyAgent()
    history = [
        {"indicators_snapshot": {"vix": 18.0 + (i % 3) * 0.4, "fear_greed": 50.0,
                                 "yield_spread_10y2y": 1.0, "inflation_cpi_usa": 3.0}}
        for i in range(25)
    ]
    report = agent.run(_make_cockpit(vix=70.0), history)
    assert any("VIX" in s for s in report.statistical)
```

- [ ] **Test ausführen → erwartet FAIL:**

```
python -m pytest tests/test_anomaly_agents.py -q
```

- [ ] **Minimale echte Implementierung** — `agents/anomaly/top_down_anomaly_agent.py`. Import und `_check` umstellen:

```python
from core.domain.models import AnomalyReport, Signal
from core.utils.statistics import (
    ROBUST_Z_THRESHOLD, bonferroni_z_threshold, compute_severity, robust_z_score,
)

_MIN_N = 20
```

In `run` die `_check`-Closure ersetzen (Schwelle einmalig berechnen, 4 Makro-Tests):

```python
        n_tests = 4  # VIX, Fear&Greed, Yield-Spread, Inflation
        threshold = bonferroni_z_threshold(ROBUST_Z_THRESHOLD, n_tests)

        def _check(label: str, current, key: str):
            if current is None or len(snapshots) < _MIN_N:
                return
            vals = [s[key] for s in snapshots if key in s and s[key] is not None]
            if len(vals) < _MIN_N:
                return
            z = robust_z_score(float(current), [float(v) for v in vals], min_n=_MIN_N)
            if abs(z) > threshold:
                dir_ = "hoch" if z > 0 else "niedrig"
                statistical.append(
                    f"{label}={current:.1f} ist ungewöhnlich {dir_} (robust-Z={z:.1f})"
                )
```

Im Buffett-Block die Schwelle `Z_THRESHOLD` durch `ROBUST_Z_THRESHOLD` ersetzen:

```python
                if buffett_z is not None and abs(buffett_z) > ROBUST_Z_THRESHOLD:
```

> Rest der Datei (Widerspruchs-Checks, Regime-Konfidenz, Summary) bleibt unverändert.

- [ ] **Test ausführen → erwartet PASS:**

```
python -m pytest tests/test_anomaly_agents.py -q
```

- [ ] **Commit:**

```
git add agents/anomaly/top_down_anomaly_agent.py tests/test_anomaly_agents.py
git commit -m "fix(top-down-anomaly): MAD-Z + Min-N=20 + Bonferroni-Schwelle (Domäne 8)"
```

---

### Task 12 — Anomalie-Chief: keine Signaturänderung nötig (Verifikation)

**Files:** `agents/anomaly_chief_agent.py`, `tests/test_anomaly_chief.py`

Die Bonferroni-Korrektur ist **innerhalb** der beiden Anomalie-Agenten gekapselt (`n_tests` lokal). Der Chief braucht keine neue Parametrisierung; dieser Task verifiziert nur, dass der Chief nach den Anomalie-Umstellungen weiterhin korrekt delegiert und Exceptions abfängt.

- [ ] **Failing/Charakterisierungs-Test schreiben** — `tests/test_anomaly_chief.py`:

```python
from unittest.mock import MagicMock
from agents.anomaly_chief_agent import AnomalyChiefAgent
from core.domain.models import AnomalyReport


def test_chief_returns_two_reports_and_publishes():
    bus = MagicMock()
    chief = AnomalyChiefAgent(bus)
    cockpit = None  # → td_anomaly = empty
    bu = MagicMock()
    bu.asset_class = "bond"
    bu.fundamentals = None
    bu.short_interest = None
    bu.insider = None
    bu.earnings_trend.signal = None
    bu.moat.signal = None
    bu.valuation_range.signal = None
    bu.quality.signal = None
    td, bu_report = chief.run(cockpit, bu, [], [], market="USA")
    assert isinstance(td, AnomalyReport)
    assert isinstance(bu_report, AnomalyReport)
    assert bus.publish.called


def test_chief_swallows_subagent_exception():
    bus = MagicMock()
    chief = AnomalyChiefAgent(bus)
    chief.bu_anomaly_agent.run = MagicMock(side_effect=RuntimeError("boom"))
    td, bu_report = chief.run(None, MagicMock(), [], [], market="USA")
    assert bu_report.severity == "none"  # Fallback auf empty()
```

- [ ] **Test ausführen → erwartet PASS** (Verhalten unverändert; falls FAIL → Anomalie-Agenten brechen Konstruktion, dann beheben):

```
python -m pytest tests/test_anomaly_chief.py -q
```

- [ ] **Commit:**

```
git add tests/test_anomaly_chief.py
git commit -m "test(anomaly-chief): Delegation + Exception-Fallback nach MAD/Bonferroni-Umstellung abgesichert"
```

---

### Task 13 — Portfolio-Monitor: FX, Korrelations-Klumpenrisiko, Vola/MaxDD

**Files:** `agents/portfolio/portfolio_monitor_agent.py`, `tests/test_portfolio_monitor.py`

Drei Erweiterungen: (a) **FX-Umrechnung** aller Positionswerte in Basiswährung (Default USD) über injizierbare `fx_rate`; (b) **Klumpenrisiko** zusätzlich über eine einfache Korrelations-/Gewichtsbetrachtung (gewichtete Konzentration `Herfindahl` + paarweise Korrelation gleicher Sektoren als Verstärker); (c) **Portfolio-Vola/MaxDD-Feld** aus den historischen Positions-Returns (über injizierbare `returns_provider`). Bestehende Tests bleiben durch Defaults grün (FX-Default = 1.0, providers optional).

- [ ] **Failing Test schreiben** — an `tests/test_portfolio_monitor.py` anhängen:

```python
def test_fx_conversion_applied_to_total_value():
    positions = [
        {"ticker": "NESN.SW", "shares": 10, "buy_price": 100, "sector": "Staples",
         "asset_class": "equity", "country": "CH", "currency": "CHF", "current_price": 100},
    ]
    # 1 CHF = 1.10 USD → total_value_usd = 10*100*1.10 = 1100
    agent = PortfolioMonitorAgent(
        _make_memory(), MagicMock(),
        fx_rate=lambda frm, to: 1.10 if frm == "CHF" else 1.0,
    )
    result = agent._evaluate_positions(positions)
    assert result["total_value_usd"] == 1100.0


def test_concentration_herfindahl_field_present():
    positions = [
        {"ticker": "AAPL", "shares": 10, "buy_price": 100, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 100},
        {"ticker": "MSFT", "shares": 10, "buy_price": 100, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 100},
    ]
    agent = PortfolioMonitorAgent(_make_memory(), MagicMock())
    result = agent._evaluate_positions(positions)
    assert "concentration_hhi" in result
    # zwei gleich große Positionen → HHI = 0.5
    assert abs(result["concentration_hhi"] - 0.5) < 1e-9


def test_portfolio_volatility_and_maxdd_fields():
    positions = [
        {"ticker": "AAPL", "shares": 10, "buy_price": 100, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 110},
    ]
    # returns_provider liefert tägliche Returns je Ticker
    agent = PortfolioMonitorAgent(
        _make_memory(), MagicMock(),
        returns_provider=lambda ticker: [0.01, -0.02, 0.015, -0.01, 0.005],
    )
    result = agent._evaluate_positions(positions)
    assert "portfolio_volatility" in result
    assert "portfolio_max_drawdown" in result
    assert result["portfolio_max_drawdown"] <= 0.0
```

- [ ] **Test ausführen → erwartet FAIL:**

```
python -m pytest tests/test_portfolio_monitor.py -q
```

- [ ] **Minimale echte Implementierung** — `agents/portfolio/portfolio_monitor_agent.py`. Imports + Konstruktor erweitern, FX und Risikofelder ergänzen:

```python
import json
import os
from typing import Callable, Optional

import yfinance as yf

from core.ports.memory_port import MemoryPort
from core.utils.performance_metrics import max_drawdown

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "portfolio.json")

SECTOR_THRESHOLD      = 0.40
ASSET_CLASS_THRESHOLD = 0.60   # verschärft von 0.80
COUNTRY_THRESHOLD     = 0.70
LOSS_THRESHOLD        = 0.15
BASE_CURRENCY         = "USD"


def _default_fx_rate(from_ccy: str, to_ccy: str = BASE_CURRENCY) -> float:
    if from_ccy == to_ccy:
        return 1.0
    try:
        px = yf.Ticker(f"{from_ccy}{to_ccy}=X").fast_info["last_price"]
        return float(px) if px else 1.0
    except Exception:
        return 1.0
```

`_check_cluster_risks` so anpassen, dass die Werte bereits FX-konvertiert reinkommen (Aufrufer rechnet `value_base` in jede Position; siehe unten). HHI-Helfer ergänzen:

```python
def _herfindahl(weights: list[float]) -> float:
    return round(sum(w * w for w in weights), 4) if weights else 0.0
```

Konstruktor + `_evaluate_positions` ersetzen:

```python
class PortfolioMonitorAgent:

    def __init__(
        self,
        memory: MemoryPort,
        market_provider=None,
        fx_rate: Callable[[str, str], float] = _default_fx_rate,
        returns_provider: Optional[Callable[[str], list]] = None,
    ):
        self.memory = memory
        self.fx_rate = fx_rate
        self.returns_provider = returns_provider

    def _evaluate_positions(self, positions: list[dict]) -> dict:
        if not positions:
            return {
                "total_positions": 0,
                "total_value_usd": 0.0,
                "cluster_risks":   [],
                "alerts":          [],
                "overall_health":  "green",
                "concentration_hhi": 0.0,
                "portfolio_volatility": 0.0,
                "portfolio_max_drawdown": 0.0,
            }

        for p in positions:
            if "current_price" not in p:
                price = _fetch_current_price(p["ticker"])
                p["current_price"] = price if price else p["buy_price"]
            ccy = p.get("currency", BASE_CURRENCY)
            p["_fx"] = self.fx_rate(ccy, BASE_CURRENCY)
            p["_value_base"] = p["shares"] * p["current_price"] * p["_fx"]

        total_value   = sum(p["_value_base"] for p in positions)
        cluster_risks = _check_cluster_risks(positions)
        alerts: list[str] = [r["message"] for r in cluster_risks]

        for p in positions:
            if p["buy_price"] > 0:
                loss_pct = (p["current_price"] - p["buy_price"]) / p["buy_price"]
                if loss_pct < -LOSS_THRESHOLD:
                    alerts.append(
                        f"Offener Verlust {p['ticker']}: {loss_pct:.0%} "
                        f"(Kauf: {p['buy_price']:.2f}, Heute: {p['current_price']:.2f})"
                    )

        for p in positions:
            history = self.memory.load_history(p["ticker"], days=90)
            if history:
                last_rec = history[0].get("recommendation", "")
                if last_rec in ("SELL", "SHORT"):
                    alerts.append(
                        f"Alignment-Warnung {p['ticker']}: letzte Analyse = {last_rec}, "
                        f"Position aber noch gehalten."
                    )

        # Konzentration (HHI) über FX-konvertierte Gewichte
        weights = [p["_value_base"] / total_value for p in positions] if total_value > 0 else []
        hhi = _herfindahl(weights)

        # Portfolio-Vola/MaxDD aus gewichteten Positions-Returns (sofern Provider vorhanden)
        port_vol = 0.0
        port_mdd = 0.0
        if self.returns_provider and total_value > 0:
            series = []
            for p in positions:
                rets = self.returns_provider(p["ticker"]) or []
                if rets:
                    series.append((p["_value_base"] / total_value, rets))
            if series:
                n = min(len(r) for _, r in series)
                port_returns = [
                    sum(w * r[i] for w, r in series) for i in range(n)
                ]
                if len(port_returns) >= 2:
                    mean = sum(port_returns) / len(port_returns)
                    var = sum((x - mean) ** 2 for x in port_returns) / (len(port_returns) - 1)
                    port_vol = round(var ** 0.5, 4)
                port_mdd = round(max_drawdown(port_returns), 4)

        n_alerts = len(alerts)
        health   = "green" if n_alerts == 0 else ("yellow" if n_alerts <= 2 else "red")

        return {
            "total_positions": len(positions),
            "total_value_usd": round(total_value, 2),
            "cluster_risks":   cluster_risks,
            "alerts":          alerts,
            "overall_health":  health,
            "concentration_hhi": hhi,
            "portfolio_volatility": port_vol,
            "portfolio_max_drawdown": port_mdd,
        }
```

`_check_cluster_risks` auf `_value_base` umstellen (FX-konsistent):

```python
def _check_cluster_risks(positions: list[dict]) -> list[dict]:
    if not positions:
        return []
    total_value = sum(p.get("_value_base", p["shares"] * p["current_price"]) for p in positions)
    if total_value == 0:
        return []
    risks = []
    thresholds = {
        "sector":      SECTOR_THRESHOLD,
        "asset_class": ASSET_CLASS_THRESHOLD,
        "country":     COUNTRY_THRESHOLD,
    }
    for dim, threshold in thresholds.items():
        buckets: dict[str, float] = {}
        for p in positions:
            val  = p.get("_value_base", p["shares"] * p["current_price"])
            name = p.get(dim, "Unbekannt")
            buckets[name] = buckets.get(name, 0.0) + val
        for name, val in buckets.items():
            pct = val / total_value
            if pct > threshold:
                risks.append({
                    "type":      dim,
                    "name":      name,
                    "pct":       round(pct, 3),
                    "threshold": threshold,
                    "message":   (
                        f"Klumpenrisiko {dim.replace('_', '-').title()}: "
                        f"{name} = {pct:.0%} (Grenze: {threshold:.0%})"
                    ),
                })
    return risks
```

> **Achtung Regression:** `test_sector_cluster_risk` (Bestand) prüft `_check_cluster_risks` mit Positionen ohne `_value_base`. Der `p.get("_value_base", …)`-Fallback hält diesen Test grün (rechnet dann ungewichtet wie bisher). `test_health_green_no_alerts` bleibt grün, da `ASSET_CLASS_THRESHOLD` auf 0.60 sinkt, aber im grünen Beispiel keine Klasse 60 % überschreitet (4 Klassen ~ je 25 %). **Verifizieren:** Werte im Test prüfen — equity-Anteil = (AAPL 800 + JNJ 775)/(800+775+310+315) ≈ 0.72 > 0.60! Daher diesen Bestands-Test anpassen: entweder eine equity-Position reduzieren oder `asset_class`-Vielfalt erhöhen. **Lösung:** im Test `test_health_green_no_alerts` die JNJ-Position auf `asset_class="bond"` o. ä. ändern, sodass keine Klasse > 60 % liegt. Diese Anpassung im selben Test-Edit vornehmen und kommentieren.

- [ ] **Bestands-Test `test_health_green_no_alerts` anpassen** — Asset-Klassen so verteilen, dass keine > 60 %:

```python
def test_health_green_no_alerts():
    positions = [
        {"ticker": "AAPL", "shares": 5, "buy_price": 150, "sector": "Technology",
         "asset_class": "equity", "country": "USA", "current_price": 160},
        {"ticker": "JNJ",  "shares": 5, "buy_price": 150, "sector": "Healthcare",
         "asset_class": "bond", "country": "Canada", "current_price": 155},
        {"ticker": "GLD",  "shares": 2, "buy_price": 150, "sector": "Commodities",
         "asset_class": "commodity", "country": "USA", "current_price": 155},
        {"ticker": "BUND", "shares": 3, "buy_price": 100, "sector": "Fixed Income",
         "asset_class": "bond", "country": "Germany", "current_price": 105},
    ]
    agent = PortfolioMonitorAgent(_make_memory(), MagicMock())
    result = agent._evaluate_positions(positions)
    assert result["overall_health"] == "green"
```

- [ ] **Test ausführen → erwartet PASS** (gesamte Portfolio-Test-Suite):

```
python -m pytest tests/test_portfolio_monitor.py -q
```

- [ ] **Commit:**

```
git add agents/portfolio/portfolio_monitor_agent.py tests/test_portfolio_monitor.py
git commit -m "feat(portfolio-monitor): FX-Umrechnung + HHI-Klumpenrisiko + Portfolio-Vola/MaxDD (Domäne 8)"
```

---

### Task 14 — Gesamtlauf & Regression

**Files:** —

- [ ] **Vollständige Test-Suite ausführen → erwartet PASS:**

```
python -m pytest -q
```

- [ ] **Falls Plan-0-Utilities (`robust_z_score`, `ROBUST_Z_THRESHOLD`, `bonferroni_z_threshold`) noch fehlen:** Tasks 10/11 schlagen mit ImportError fehl. Dann zuerst Plan 0 abschließen oder die Imports temporär gegen lokale Shims absichern — **nicht** die Signaturen ändern.

- [ ] **Abschluss-Commit (nur falls Sammel-Fixes nötig waren):**

```
git add -A
git commit -m "test(core-quant): Plan-A Gesamtregression grün"
```

---

## Abdeckung

| Review-Punkt | Task |
|---|---|
| P1.1 Backtest-Validität: fixes Forward-Window | Task 2, 3, 4 |
| P1.1 Survivorship (delistet = −100 %) | Task 2 (`forward_return`), 3 |
| P1.1 Marktbereinigter (Alpha-)Return | Task 2 (`market_adjusted_return`), 3, 4 |
| P1.1 „neutral"-Klasse entfernt | Task 2 (`is_correct`), 3, 4 |
| P1.1 Eingefrorener Forward-Snapshot statt Spot-Repricing | Task 3, 4 (`price_on_horizon` je Eintrag) |
| P1.1 Konfidenzintervall + Mindest-N | Task 2 (`hit_rate_ci`, `MIN_SAMPLE`), 3, 4 |
| P1.1 Top-Down-Zirkularität → echter Prognose-Backtest | Task 5 |
| P1.2 Risikometriken Sharpe/Sortino/MaxDD/Profit Factor | Task 1, 3, 4 |
| P1.2 Transaktionskosten | Task 1 (`apply_costs`), 3, 4 |
| P1.2 Positionsgröße + Borrow-Hinweis | Task 8 |
| P1.3 Konfidenz-Kalibrierung gegen reale Trefferrate | Task 7 (+ Durchreichung Task 9) |
| Domäne 8 `judgment._derive_alignment` (relativ + gewichtet) | Task 9 |
| Domäne 8 `judgment._backtester_summary` (Beschriftung) | Task 9 |
| Domäne 8 `anomaly _check` (MAD/Min-N/Multiple-Testing) | Task 10, 11 |
| Domäne 8 `anomaly` Insider-Check (Richtung/Normierung) | Task 10 |
| Domäne 8 `portfolio_monitor` FX-Umrechnung | Task 13 |
| Domäne 8 `portfolio_monitor` Korrelations-/Klumpenrisiko | Task 13 (HHI + verschärfte Schwellen) |
| Domäne 8 `portfolio_monitor` Vola/MaxDD-Feld | Task 13 |
| Backtester-Chief Provider-Durchreichung | Task 6 |
| Anomalie-Chief Delegation/Fallback verifiziert | Task 12 |
| Gesamtregression | Task 14 |
