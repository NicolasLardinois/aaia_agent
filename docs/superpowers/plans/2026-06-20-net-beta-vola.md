# Block F4a: `net_beta` (pro Region) + Portfolio-Vola — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** `net_beta` pro Region (beta-bereinigte, richtungs-bewusste Markt-Exposure als $-Hedge-Notional) im Monitor-Snapshot + den vorhandenen `returns_provider` produktiv verdrahten (Vola/MaxDD live).

**Architecture:** Erweiterung des `PortfolioMonitorAgent` (Beta via injiziertem `market_provider.get_info`); `returns_provider`-Factory aus `get_price_history`; Verdrahtung in `background_runner`.

**Tech Stack:** Python, pytest.

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-20-net-beta-vola-design.md`. Status/Roadmap: `docs/open_todos.md` (Logbuch).
- `net_beta` = `Σ(signed_value · β)` **pro Region** ($, FX-konvertiert, long +, short −); Beta via `market_provider.get_info(ticker)["beta"]`, fehlend/None/Provider-None → **1,0**, defensiv (kein Crash).
- Branch `feat/risk-net-beta-vola`. PR-First. TDD. Runner `python -m pytest -q`. Am Ende (Task 2) Gesamtsuite grün.

---

## Task 1: `net_beta` pro Region im Monitor

**Files:** Modify `agents/portfolio/portfolio_monitor_agent.py`; Test `tests/test_portfolio_monitor.py` (erweitern).

**ZUERST** `agents/portfolio/portfolio_monitor_agent.py` (`_evaluate_positions`, Konstruktor mit `market_provider`) lesen.

- [ ] **Step 1: Failing test** — in `tests/test_portfolio_monitor.py` ergänzen:
```python
def _market(betas):
    m = MagicMock()
    m.get_info.side_effect = lambda t: {"beta": betas.get(t)}
    return m


def _agent_mp(positions, betas):
    return PortfolioMonitorAgent(
        MagicMock(), portfolio_port=_port(positions),
        market_provider=_market(betas), fx_rate=lambda a, b: 1.0)


def test_net_beta_signed_and_beta_weighted():
    # SPY long β1 (Wert 100) + TSLA short β1.8 (Wert 100), beide USA → net_beta["USA"] ≈ -80
    positions = [_pos("SPY", "long", 100, 100, sector="Index"),
                 _pos("TSLA", "short", 100, 100, sector="Auto")]
    snap = _agent_mp(positions, {"SPY": 1.0, "TSLA": 1.8})._evaluate_positions(positions)
    assert round(snap["net_beta"]["USA"], 0) == -80


def test_net_beta_missing_beta_defaults_one():
    positions = [_pos("X", "long", 100, 100)]
    snap = _agent_mp(positions, {"X": None})._evaluate_positions(positions)
    assert snap["net_beta"]["USA"] == 100.0   # β=1.0


def test_net_beta_per_region_split():
    positions = [_pos("US1", "long", 100, 100), _pos("CH1", "long", 100, 100)]
    positions[1] = Position(ticker="CH1", shares=10, entry_price=10, direction="long",
                            current_price=10, sector="Pharma", asset_class="equity", country="CH")
    snap = _agent_mp(positions, {"US1": 1.0, "CH1": 1.0})._evaluate_positions(positions)
    assert set(snap["net_beta"].keys()) == {"USA", "CH"}
```
> Falls die `_pos`-Helper-Signatur (aus 3a-Tests) abweicht, an die reale anpassen; Default-`country` der Helper ist „USA".

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_portfolio_monitor.py -q`.

- [ ] **Step 3: Implement** — `agents/portfolio/portfolio_monitor_agent.py`:
  - Region-Helfer (Modulebene, bei den anderen Helfern):
    ```python
    _US = {"USA", "US", "United States"}
    _CH = {"CH", "CHE", "Schweiz", "Switzerland"}
    _EUROZONE = {"DE","FR","IT","ES","NL","AT","BE","PT","FI","IE","GR","SK","SI","EE","LV","LT","LU","MT","CY",
                 "Deutschland","Frankreich","Eurozone"}

    def _region_of(country: str) -> str:
        c = (country or "").strip()
        if c in _US: return "USA"
        if c in _CH: return "CH"
        if c in _EUROZONE: return "Eurozone"
        return c or "Unbekannt"
    ```
  - Beta-Methode (in der Klasse, defensiv):
    ```python
    def _beta_for(self, ticker: str) -> float:
        if self.market_provider is None:
            return 1.0
        try:
            info = self.market_provider.get_info(ticker) or {}
            b = info.get("beta")
            return float(b) if b is not None else 1.0
        except Exception:
            return 1.0
    ```
  - In `_evaluate_positions` (nach `values`/long/short/gross, vor dem return-Dict):
    ```python
    net_beta: dict[str, float] = {}
    for p, val in zip(positions, values):
        signed = val if p.direction == "long" else -val
        region = _region_of(p.country)
        net_beta[region] = net_beta.get(region, 0.0) + signed * self._beta_for(p.ticker)
    net_beta = {r: round(v, 2) for r, v in net_beta.items()}
    net_beta_pct = {r: round(v / gross, 3) for r, v in net_beta.items()} if gross > 0 else {}
    ```
    Im Snapshot-Dict ergänzen: `"net_beta": net_beta, "net_beta_pct": net_beta_pct`. Im leeren-Portfolio-Zweig `"net_beta": {}, "net_beta_pct": {}` ergänzen.

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_portfolio_monitor.py -q`.

- [ ] **Step 5: Commit** — `git add agents/portfolio/portfolio_monitor_agent.py tests/test_portfolio_monitor.py && git commit -m "feat(portfolio): net_beta pro Region (Hedge-Notional) im Monitor-Snapshot"`

---

## Task 2: `returns_provider` verdrahten + Anzeige + Regression

**Files:** Modify `agents/portfolio/portfolio_monitor_agent.py` (Factory + Anzeige), `background_runner.py`; Test `tests/test_portfolio_monitor.py`.

- [ ] **Step 1: Failing test** — `make_returns_provider`:
```python
import pandas as pd
from agents.portfolio.portfolio_monitor_agent import make_returns_provider


def test_make_returns_provider_from_price_history():
    mp = MagicMock()
    mp.get_price_history.return_value = pd.DataFrame({"Close": [100.0, 110.0, 99.0]})
    rp = make_returns_provider(mp)
    rets = rp("X")
    assert len(rets) == 2 and abs(rets[0] - 0.10) < 1e-9


def test_make_returns_provider_error_empty():
    mp = MagicMock()
    mp.get_price_history.side_effect = Exception("net")
    assert make_returns_provider(mp)("X") == []
```

- [ ] **Step 2: Run → FAIL** — `python -m pytest tests/test_portfolio_monitor.py -k returns_provider -q`.

- [ ] **Step 3: Implement**
  - `agents/portfolio/portfolio_monitor_agent.py` — Factory (Modulebene):
    ```python
    def make_returns_provider(market_provider):
        """Callable ticker -> Renditereihe aus get_price_history (Close → pct_change). Fehler → []."""
        def _provider(ticker: str) -> list:
            try:
                hist = market_provider.get_price_history(ticker, "1y")
                close = hist["Close"].dropna()
                return close.pct_change().dropna().tolist()
            except Exception:
                return []
        return _provider
    ```
  - **Anzeige** in `run()`: nach der Netto/Brutto-Zeile je Region `net_beta` ausgeben, z. B.:
    ```python
    for region, v in (snapshot.get("net_beta") or {}).items():
        pct = (snapshot.get("net_beta_pct") or {}).get(region)
        suffix = f" ({pct:+.0%} Brutto)" if pct is not None else ""
        print(f"  net-β {region}: ${v:,.0f}{suffix}")
    ```
  - **`background_runner.py`:** den Yahoo-Markt-Provider (Klasse in `adapters/data/yahoo_finance.py`) instanziieren und an den Monitor geben:
    ```python
    from adapters.data.yahoo_finance import <YahooProviderKlasse>
    from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent, make_returns_provider
    from adapters.persistence.json_portfolio import JsonPortfolioProvider
    ...
    market = <YahooProviderKlasse>()
    PortfolioMonitorAgent(memory, portfolio_port=JsonPortfolioProvider(),
                          market_provider=market,
                          returns_provider=make_returns_provider(market))
    ```
    (Exakten Klassennamen aus `adapters/data/yahoo_finance.py` übernehmen.)

- [ ] **Step 4: Run → PASS** — `python -m pytest tests/test_portfolio_monitor.py -q`.

- [ ] **Step 5: Gesamt-Regression** — `python -m pytest -q` → **0 failed** (~3 Min). Bei Fehlern: superpowers:systematic-debugging.

- [ ] **Step 6: Commit** — `git add agents/portfolio/portfolio_monitor_agent.py background_runner.py tests/test_portfolio_monitor.py && git commit -m "feat(portfolio): returns_provider verdrahtet (Vola live) + net_beta-Anzeige + Regression gruen (F4a)"`

---

## Abdeckung (Spec → Task)
| Spec-Element | Task |
|---|---|
| `net_beta` pro Region (Beta via get_info, Default 1,0, signiert, FX) | 1 |
| `returns_provider` produktiv (Vola/MaxDD live) | 2 |
| Anzeige `net_beta` je Region | 2 |
| Regression | 2 |

## Self-Review (durchgeführt)
- **Spec-Abdeckung:** net_beta (Task 1), returns_provider + Anzeige (Task 2). ✅
- **Platzhalter:** Code vollständig; einzige offene Stelle = exakter Yahoo-Klassenname (Implementer liest `adapters/data/yahoo_finance.py`). ✅
- **Typ-Konsistenz:** `_beta_for -> float`; `net_beta: dict[str,float]`; `make_returns_provider` → Callable. Bestehende Tests ohne `market_provider` → Beta 1,0 (kein Bruch). ✅
