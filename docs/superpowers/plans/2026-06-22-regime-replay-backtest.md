# Regime-Replay-Backtest (Stufe 1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den Top-Down-Regime-Motor look-ahead-frei über die US-Historie (ab 1960, monatlich) durchspielen und seine Urteile gegen (A) den Forward-S&P-Return und (B) NBER-Rezessionsdaten messen — als reproduzierbaren Offline-Lauf mit datiertem Report.

**Architecture:** Ein neuer `HistoricalFredProvider(as_of)` erfüllt dasselbe `MacroDataProvider`-Port wie der Live-Adapter und liefert Point-in-Time-Daten (Vintage wo möglich). Eine Replay-Schleife führt je Stichtag die **echten** Sub-Signal-Agenten aus und ruft den (um eine injizierbare Trend-Historie erweiterten) `RegimeDetector` über eine geteilte `assemble_regime_inputs()`-Funktion — so validiert der Replay exakt die Produktionslogik. Ein reiner `RegimeEvaluator` bewertet die gesammelten Urteile.

**Tech Stack:** Python 3, `fredapi` (Vintage via `get_series_as_of_date`), `yfinance` (S&P `^GSPC`), `pandas`/`python-dateutil`, `pytest`. Bestehende Hexagonal-Architektur (Ports/Adapter), `core/utils/backtest.py` (Forward-Return, Wilson-CI).

## Global Constraints

- **Sprache:** Code-Kommentare und Doc-Strings auf **Deutsch** (Projektkonvention).
- **TDD verpflichtend:** Erst der fehlschlagende Test, dann Implementierung. Keine Ausnahme (AGENTS.md §4).
- **PR-First:** Alle Commits auf Branch `worktree-regime-replay-backtest`. **Nie** direkt auf `master`. Kein `--no-verify`.
- **Staging explizit:** Nur genannte Pfade stagen (`git add <pfad>`), **nie** `git add -A`.
- **Look-Ahead verboten:** Kein Datenwert mit Beobachtungs-/Kursdatum **nach** `as_of` darf je in eine Entscheidung oder einen Entry-Return einfließen.
- **Rückwärtskompatibel:** Eingriffe am Bestand (`detect`, `MacroChiefAgent`, `BuffettIndicatorAgent`) dürfen das Live-Verhalten per Default **nicht** ändern. Bestehende Tests bleiben grün.
- **Reine Funktionen ohne I/O** in `core/` (`regime_inputs.py`, `regime_eval.py`): keine Netz-/Datei-Zugriffe.
- **Region/Default:** USA-only, monatlich, Fenster 1960-01 → heute, Horizonte 3/6/12 Monate, Benchmark `^GSPC`, Wirtschafts-Label FRED `USREC`.

---

### Task 1: `RegimeDetector.detect()` — Trend-Historie injizierbar

**Files:**
- Modify: `core/domain/regime.py` (Methode `RegimeDetector.detect`, ~Zeile 142–175)
- Test: `tests/domain/test_regime.py`

**Interfaces:**
- Produces: `RegimeDetector.detect(state: dict, sub_signals: dict | None = None, history: list[tuple[str, float]] | None = None) -> tuple[MarketRegime, float, dict]`. Ist `history` gesetzt, wird die Datei `composite_history.json` **weder gelesen noch geschrieben**; der Trend wird aus `history` berechnet.

- [ ] **Step 1: Write the failing test**

```python
# tests/domain/test_regime.py  (ans Ende anfügen)
def test_detect_mit_injizierter_historie_ignoriert_datei(tmp_path, monkeypatch):
    """history-Parameter: kein Datei-Read/Write, Trend kommt aus der injizierten Reihe."""
    import core.domain.regime as regime_mod
    # Falls die Implementierung doch die Datei anfasst, soll der Test hart scheitern:
    def _boom(*a, **k):
        raise AssertionError("Datei-I/O trotz injizierter history")
    monkeypatch.setattr(regime_mod, "_load_history", _boom)
    monkeypatch.setattr(regime_mod, "_save_history", _boom)

    det = regime_mod.RegimeDetector()
    state = {"gdp_growth": 3.5, "unemployment": 3.5, "inflation": 2.0}
    # steigende Composite-Historie → Aufwärtstrend
    hist = [("2020-01-01", -0.2), ("2020-02-01", 0.0), ("2020-03-01", 0.2)]
    regime, confidence, evidence = det.detect(state, sub_signals=None, history=hist)

    assert regime is not None
    assert 0.0 <= confidence <= 1.0
    assert "gdp_growth" in evidence
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/domain/test_regime.py::test_detect_mit_injizierter_historie_ignoriert_datei -v`
Expected: FAIL — `detect()` kennt das `history`-Argument noch nicht (`TypeError: detect() got an unexpected keyword argument 'history'`).

- [ ] **Step 3: Implement minimal change**

In `core/domain/regime.py`, Methode `detect` so anpassen, dass bei gesetztem `history` keine Datei berührt wird:

```python
    def detect(self, state: dict, sub_signals: Optional[dict] = None,
               history: Optional[list] = None) -> tuple[MarketRegime, float, dict]:
        """Returns: (regime, confidence, evidence_per_indicator)
        sub_signals: optionale {key: ±1.0}-Werte (money_supply, credit, labor, buffett)
        mit kleinen Gewichten; fließen in weighted_sum/weight_total ein.
        history: optionale datierte Composite-Reihe [(iso_date, value), ...]. Ist sie
        gesetzt, wird die Cache-Datei WEDER gelesen NOCH geschrieben (Backtest/Replay) —
        der Trend kommt allein aus dieser Reihe.
        """
        evidence = {}
        weighted_sum = 0.0
        weight_total = 0.0

        for key, value in state.items():
            score = _score_indicator(key, value)
            w = INDICATOR_WEIGHTS.get(key, 0.0)
            evidence[key] = round(score, 3)
            weighted_sum += score * w
            weight_total += w

        _SUB_WEIGHT = 0.03
        if sub_signals:
            for sub_key, sub_val in sub_signals.items():
                if sub_val is not None and isinstance(sub_val, (int, float)):
                    evidence[sub_key] = round(sub_val, 3)
                    weighted_sum += sub_val * _SUB_WEIGHT
                    weight_total += _SUB_WEIGHT

        composite = weighted_sum / weight_total if weight_total > 0 else 0.0

        if history is None:
            # Live-Pfad: datei-basierte Historie (unverändertes Verhalten)
            loaded = _load_history()
            trend = _trend(loaded, composite)
            _save_history(loaded, composite)
        else:
            # Backtest/Replay-Pfad: rein aus der injizierten Reihe, kein Datei-I/O
            trend = _trend(history, composite)

        regime     = _regime_from(composite, trend)
        confidence = round(min(1.0, abs(composite) * 1.5 + 0.3), 3)
        return regime, confidence, evidence
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/domain/test_regime.py -v`
Expected: PASS (neuer Test + alle bestehenden Regime-Tests grün — Default-Pfad unverändert).

- [ ] **Step 5: Commit**

```bash
git add core/domain/regime.py tests/domain/test_regime.py
git commit -m "feat(regime): detect() akzeptiert injizierbare Trend-Historie (Backtest-fähig)"
```

---

### Task 2: Geteilte `assemble_regime_inputs()` + `MacroChiefAgent`-Umbau

**Files:**
- Create: `core/domain/regime_inputs.py`
- Modify: `agents/market_cockpit/macro_chief_agent.py` (Zeilen 69–93)
- Test: `tests/domain/test_regime_inputs.py`

**Interfaces:**
- Consumes: `core.domain.models.Signal`.
- Produces: `assemble_regime_inputs(economic_state: dict, usa_10y3m: float | None, eu_spreads: dict, ch_spreads: dict, sub_signal_map: dict[str, "Signal"]) -> tuple[dict, dict]`. Liefert `(state, sub_signals)` identisch zur bisherigen Inline-Montage in `MacroChiefAgent`. `sub_signal_map`-Keys: `"money_supply" | "credit" | "labor" | "buffett"`, Werte sind `Signal`-Enums.

- [ ] **Step 1: Write the failing test**

```python
# tests/domain/test_regime_inputs.py
from core.domain.models import Signal
from core.domain.regime_inputs import assemble_regime_inputs


def test_state_anreicherung_und_subsignal_scores():
    econ = {"gdp_growth": 2.0, "inflation": 2.1, "yield_curve": 0.5}
    state, subs = assemble_regime_inputs(
        economic_state=econ,
        usa_10y3m=0.8,
        eu_spreads={},
        ch_spreads={},
        sub_signal_map={
            "money_supply": Signal.NEUTRAL,
            "credit":       Signal.BULLISH,
            "labor":        Signal.BEARISH,
            "buffett":      Signal.NEUTRAL,
        },
    )
    # Anreicherung: USA 10y-3m landet unter dem Gewichts-Key des Detektors
    assert state["yield_curve_10y3m_usa"] == 0.8
    # Ursprüngliche econ-Keys bleiben erhalten
    assert state["gdp_growth"] == 2.0
    # Signal → ±1.0-Score
    assert subs == {"money_supply": 0.0, "credit": 1.0, "labor": -1.0, "buffett": 0.0}


def test_fehlende_spreads_werden_uebersprungen():
    state, subs = assemble_regime_inputs({"gdp_growth": 1.0}, None, {}, {}, {})
    assert "yield_curve_10y3m_usa" not in state   # None → kein Key
    assert subs == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/domain/test_regime_inputs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.domain.regime_inputs'`.

- [ ] **Step 3: Implement the module**

```python
# core/domain/regime_inputs.py
"""Reine Montage der Regime-Eingaben (state + sub_signals) aus den Roh-Ergebnissen.
Geteilt von MacroChiefAgent (Live) und dem Regime-Replay — eine Quelle, kein Drift."""
from core.domain.models import Signal


def _sig_score(sig) -> float | None:
    """Signal → ±1.0-Score fürs Regime (None = unbekannt → ignoriert)."""
    if sig == Signal.BULLISH:  return  1.0
    if sig == Signal.BEARISH:  return -1.0
    if sig == Signal.NEUTRAL:  return  0.0
    return None


def assemble_regime_inputs(
    economic_state: dict,
    usa_10y3m: float | None,
    eu_spreads: dict,
    ch_spreads: dict,
    sub_signal_map: dict,
) -> tuple[dict, dict]:
    """Baut (state, sub_signals) exakt wie der bisherige Inline-Code im MacroChiefAgent.

    - economic_state: Ergebnis von get_economic_state() (wird kopiert, nicht mutiert).
    - usa_10y3m: USA-Zinskurve 10y-3m (Gewicht 0,17). None → kein Key.
    - eu_spreads/ch_spreads: dicts mit Keys "10y2y"/"10y3m" (heute meist leer → übersprungen).
    - sub_signal_map: {"money_supply"|"credit"|"labor"|"buffett": Signal}.
    """
    state = dict(economic_state)

    def _add(key, val):
        if isinstance(val, (int, float)):
            state[key] = val

    _add("yield_curve_10y3m_usa", usa_10y3m)
    _add("yield_curve_10y2y_eu",  eu_spreads.get("10y2y"))
    _add("yield_curve_10y3m_eu",  eu_spreads.get("10y3m"))
    _add("yield_curve_10y3m_ch",  ch_spreads.get("10y3m"))

    sub_signals = {}
    for key, sig in sub_signal_map.items():
        score = _sig_score(sig)
        if score is not None:
            sub_signals[key] = score
    return state, sub_signals
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/domain/test_regime_inputs.py -v`
Expected: PASS.

- [ ] **Step 5: Refactor `MacroChiefAgent` to use the shared function**

In `agents/market_cockpit/macro_chief_agent.py` die Inline-Montage (Zeilen 69–93) ersetzen. Neuer Block ab nach der `_safe(...)`-Entpackung (`usa_spreads`, `eu_spreads`, `ch_spreads` bleiben wie gehabt):

```python
        from core.domain.regime_inputs import assemble_regime_inputs

        state, sub_signals = assemble_regime_inputs(
            economic_state=state,
            usa_10y3m=usa_spreads.get("10y3m"),
            eu_spreads=eu_spreads,
            ch_spreads=ch_spreads,
            sub_signal_map={
                "money_supply": money_supply.usa.signal,
                "credit":       credit.usa.signal,
                "labor":        labor_income.usa.signal,
                "buffett":      buffett_indicator.signal,
            },
        )

        regime, confidence, _ = self._detector.detect(state, sub_signals=sub_signals)
```

Den ersetzten Inline-Code (`_add(...)`-Block, lokale `_sig_score`-Definition, `sub_signals = {...}`) entfernen.

- [ ] **Step 6: Run the macro-chief tests to verify no regression**

Run: `python -m pytest tests/agents/market_cockpit/test_macro_chief.py -v`
Expected: PASS (Regime unverändert — nur die Input-Montage wurde ausgelagert).

- [ ] **Step 7: Commit**

```bash
git add core/domain/regime_inputs.py tests/domain/test_regime_inputs.py agents/market_cockpit/macro_chief_agent.py
git commit -m "refactor(macro): Regime-Input-Montage in geteilte assemble_regime_inputs()"
```

---

### Task 3: `BuffettIndicatorAgent` — Weltbank-Fetch injizierbar

**Files:**
- Modify: `agents/market_cockpit/macro/buffett_indicator_agent.py` (`__init__` + `run`)
- Test: `tests/agents/market_cockpit/macro/test_buffett_indicator_agent.py`

**Interfaces:**
- Produces: `BuffettIndicatorAgent(macro, bus, wb_fetch=_fetch_world_bank)`. `wb_fetch` ist ein parameterloser Callable, der `{ISO3: (ratio, year, history)}` liefert; Default unverändert. `run()` nutzt `self._wb_fetch` statt der Modulfunktion.

- [ ] **Step 1: Write the failing test**

```python
# tests/agents/market_cockpit/macro/test_buffett_indicator_agent.py  (anfügen)
import asyncio
from agents.market_cockpit.macro.buffett_indicator_agent import BuffettIndicatorAgent
from core.domain.models import Signal


class _FakeBus:
    def publish(self, event): pass


class _FakeMacro:
    def get_buffett_data(self):
        # Wilshire/GDP → Ratio 150 %
        return {"market_cap_bn": 30000.0, "gdp_bn": 20000.0}
    def get_buffett_history(self, years=10):
        # genug Historie für z-Score (>= 8), Mittel ~100 → 150 ist deutlich darüber
        return [90.0, 95.0, 100.0, 105.0, 110.0, 98.0, 102.0, 99.0, 101.0]


def test_wb_fetch_injizierbar_kein_netz():
    """Injizierter No-Op-WB-Fetch → kein Netz; USA-Signal entsteht aus FRED-Daten."""
    called = {"n": 0}
    def _noop_wb():
        called["n"] += 1
        return {}
    agent = BuffettIndicatorAgent(_FakeMacro(), _FakeBus(), wb_fetch=_noop_wb)
    result = asyncio.run(agent.run())
    assert called["n"] == 1                       # der injizierte Fetch wurde benutzt
    assert "USA" in result.countries             # USA aus FRED trotz leerer Weltbank
    assert result.signal in (Signal.BULLISH, Signal.BEARISH, Signal.NEUTRAL)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agents/market_cockpit/macro/test_buffett_indicator_agent.py::test_wb_fetch_injizierbar_kein_netz -v`
Expected: FAIL — `__init__()` kennt `wb_fetch` noch nicht (`TypeError`).

- [ ] **Step 3: Implement the injection**

In `agents/market_cockpit/macro/buffett_indicator_agent.py`:

`__init__` ersetzen:

```python
    def __init__(self, macro: MacroDataProvider, bus: EventBus, wb_fetch=_fetch_world_bank):
        self.macro = macro
        self.bus   = bus
        self._wb_fetch = wb_fetch   # injizierbar: erlaubt netzfreien Replay/Backtest
```

In `run()` den `asyncio.gather`-Aufruf von `_fetch_world_bank` auf `self._wb_fetch` umstellen:

```python
        fred_data, wb_data, fred_history = await asyncio.gather(
            asyncio.to_thread(self.macro.get_buffett_data),
            asyncio.to_thread(self._wb_fetch),
            asyncio.to_thread(self.macro.get_buffett_history, 10),
            return_exceptions=True,
        )
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/agents/market_cockpit/macro/test_buffett_indicator_agent.py -v`
Expected: PASS (neuer Test + bestehende grün; Default `wb_fetch` unverändert).

- [ ] **Step 5: Commit**

```bash
git add agents/market_cockpit/macro/buffett_indicator_agent.py tests/agents/market_cockpit/macro/test_buffett_indicator_agent.py
git commit -m "feat(buffett): injizierbarer Weltbank-Fetch (netzfreier Backtest)"
```

---

### Task 4: `HistoricalFredProvider(as_of)` — Point-in-Time-Adapter

**Files:**
- Create: `adapters/data/historical_fred.py`
- Test: `tests/adapters/test_historical_fred.py`

**Interfaces:**
- Consumes: `core.ports.data_provider.MacroDataProvider`, `adapters.data.fred_api.SERIES`/`EXTENDED_SERIES` (Serien-Mappings wiederverwenden).
- Produces: `HistoricalFredProvider(api_key: str, as_of: date, _series_loader=None)`. `_series_loader(fred, series_id, as_of) -> pandas.Series` ist für Tests injizierbar (Default ruft FRED). Methoden: `get_economic_state()`, `get_extended_state()`, `get_yield_spreads()`, `get_buffett_data()`, `get_buffett_history(years=10)`. Attribut `self.quality: str` ∈ {`"vintage"`, `"revised"`} (gesetzt nach dem ersten Kern-Abruf).

- [ ] **Step 1: Write the failing test**

```python
# tests/adapters/test_historical_fred.py
from datetime import date
import pandas as pd
from adapters.data.historical_fred import HistoricalFredProvider


def _fake_loader(series_map):
    """Baut einen _series_loader, der pro series_id eine feste Reihe liefert,
    bereits auf <= as_of geschnitten (simuliert den Point-in-Time-Schnitt)."""
    def _loader(fred, series_id, as_of):
        idx, vals = series_map[series_id]
        s = pd.Series(vals, index=pd.to_datetime(idx))
        return s[s.index <= pd.Timestamp(as_of)]
    return _loader


def test_get_economic_state_nutzt_nur_werte_bis_as_of():
    # CPI mit YoY-Sprung NACH dem Stichtag, der nicht sichtbar sein darf
    series = {
        "CPIAUCSL": (["2019-01-01", "2020-01-01", "2021-01-01"], [100.0, 102.0, 130.0]),
        "UNRATE":   (["2019-12-01", "2020-12-01"], [3.5, 6.7]),
        "FEDFUNDS": (["2020-01-01"], [1.5]),
        "T10Y2Y":   (["2020-01-01"], [0.3]),
        "GDP":      (["2018-01-01", "2019-01-01", "2020-01-01"], [100.0, 102.0, 104.0]),
        "UMCSENT":  (["2020-01-01"], [99.0]),
        "INDPRO":   (["2019-01-01", "2020-01-01"], [100.0, 101.0]),
    }
    prov = HistoricalFredProvider("KEY", date(2020, 6, 1), _series_loader=_fake_loader(series))
    state = prov.get_economic_state()
    # unemployment = letzter Wert <= as_of = 3.5 (der 6.7-Wert von 12/2020 ist Zukunft)
    assert state["unemployment"] == 3.5
    # inflation = YoY 2020 vs 2019 = (102-100)/100 = 2.0 % (der 130-Wert ist Zukunft)
    assert round(state["inflation"], 1) == 2.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/adapters/test_historical_fred.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'adapters.data.historical_fred'`.

- [ ] **Step 3: Implement the adapter**

```python
# adapters/data/historical_fred.py
from datetime import date, datetime

import numpy as np
import pandas as pd
from fredapi import Fred

from core.ports.data_provider import MacroDataProvider
from adapters.data.fred_api import SERIES, EXTENDED_SERIES


def _default_series_loader(fred: Fred, series_id: str, as_of: date) -> pd.Series:
    """Point-in-Time-Serie: bevorzugt Vintage (Stand wie am `as_of` veröffentlicht),
    sonst Rückfall auf die revidierte Serie, in beiden Fällen auf Datum <= as_of geschnitten.
    Setzt das Attribut NICHT — die Qualität ermittelt der Aufrufer über _loaded_vintage."""
    ts = pd.Timestamp(as_of)
    try:
        # get_series_as_of_date liefert die zum Stichtag bekannten Releases
        df = fred.get_series_as_of_date(series_id, as_of)
        # Normalisieren auf observation_date -> letzter bekannter value je Datum
        df = df[["date", "value"]].copy()
        df["date"] = pd.to_datetime(df["date"])
        s = df.dropna().groupby("date")["value"].last()
        s = s[s.index <= ts].astype(float)
        if not s.empty:
            return s
    except Exception:
        pass
    # Fallback: revidierte Serie, auf <= as_of geschnitten
    s = fred.get_series(series_id)
    s.index = pd.to_datetime(s.index)
    return s[s.index <= ts].astype(float)


class HistoricalFredProvider(MacroDataProvider):
    """Wie FredDataProvider, aber Point-in-Time zum Stichtag `as_of`. Nutzt dieselben
    Serien-Mappings/Transformationen, damit der Regime-Input identisch zum Live-Pfad ist."""

    def __init__(self, api_key: str, as_of: date, _series_loader=None):
        self.as_of = as_of
        self.quality = "unbekannt"
        self._fred = Fred(api_key=api_key) if _series_loader is None else None
        self._load = _series_loader or _default_series_loader

    def _series(self, series_id: str) -> pd.Series:
        return self._load(self._fred, series_id, self.as_of)

    def _state_from(self, mapping: dict) -> dict:
        state = {}
        for key, (fred_id, transform) in mapping.items():
            try:
                data = self._series(fred_id)
                value = float(transform(data))
                state[key] = round(value, 3) if not np.isnan(value) else None
            except Exception:
                state[key] = None
        return state

    def get_economic_state(self) -> dict:
        state = self._state_from(SERIES)
        # Qualitäts-Flag grob über die Kern-Reihe CPIAUCSL bestimmen
        try:
            self.quality = "vintage" if self._has_vintage("CPIAUCSL") else "revised"
        except Exception:
            self.quality = "revised"
        return state

    def get_extended_state(self) -> dict:
        state = self._state_from(EXTENDED_SERIES)
        nom = state.get("nominal_wage_growth")
        try:
            cpi = self._series("CPIAUCSL")
            inf_val = float(cpi.pct_change(12).dropna().iloc[-1] * 100)
            inf = round(inf_val, 3) if not np.isnan(inf_val) else None
        except Exception:
            inf = None
        if nom is not None and inf is not None:
            state["real_wage_growth"] = round(nom - inf, 3)
        return state

    def get_yield_spreads(self) -> dict:
        result = {"10y2y": None, "10y3m": None}
        for key, fred_id in (("10y2y", "T10Y2Y"), ("10y3m", "T10Y3M")):
            try:
                s = self._series(fred_id)
                result[key] = round(float(s.dropna().iloc[-1]), 3)
            except Exception:
                pass
        return result

    def get_buffett_data(self) -> dict:
        try:
            market_cap = float(self._series("WILL5000INDFC").dropna().iloc[-1])
            gdp        = float(self._series("GDP").dropna().iloc[-1])
            return {"market_cap_bn": market_cap, "gdp_bn": gdp}
        except Exception:
            return {"market_cap_bn": None, "gdp_bn": None}

    def get_buffett_history(self, years: int = 10) -> list:
        try:
            wilshire = self._series("WILL5000INDFC").resample("Q").last().dropna()
            gdp      = self._series("GDP").resample("Q").last().dropna()
            aligned  = wilshire.align(gdp, join="inner")
            ratios   = (aligned[0] / aligned[1] * 100).dropna()
            cutoff   = pd.Timestamp(self.as_of) - pd.DateOffset(years=years)
            ratios   = ratios[ratios.index >= cutoff]
            return [round(float(r), 1) for r in ratios]
        except Exception:
            return []

    def _has_vintage(self, series_id: str) -> bool:
        """True, wenn FRED für series_id einen echten Vintage-Stand zum as_of liefert."""
        if self._fred is None:
            return False
        try:
            df = self._fred.get_series_as_of_date(series_id, self.as_of)
            return df is not None and len(df) > 0
        except Exception:
            return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/adapters/test_historical_fred.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/data/historical_fred.py tests/adapters/test_historical_fred.py
git commit -m "feat(adapter): HistoricalFredProvider (Point-in-Time, Vintage mit Revised-Fallback)"
```

---

### Task 5: `RegimeEvaluator` (A) — Markt-Wahrheit (Forward-S&P)

**Files:**
- Create: `core/utils/regime_eval.py`
- Test: `tests/core/utils/test_regime_eval_market.py`

**Interfaces:**
- Consumes: `core.utils.backtest.forward_return`, `is_correct`, `hit_rate_ci`; `core.domain.models.MarketRegime`.
- Produces:
  - `regime_direction(regime: MarketRegime) -> str` → `"bullish"` | `"bearish"`.
  - `evaluate_market(judgments: list[dict], sp_price_on, horizons_months: tuple[int, ...] = (3, 6, 12)) -> dict`. `judgments`: Liste von `{"as_of": date, "regime": MarketRegime, ...}`. `sp_price_on(d: date) -> float | None`. Rückgabe pro Horizont: `{"n", "hit_rate", "ci_low", "ci_high", "by_regime": {regime_name: {"n", "hit_rate"}}}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/utils/test_regime_eval_market.py
from datetime import date
from dateutil.relativedelta import relativedelta
from core.domain.models import MarketRegime
from core.utils.regime_eval import regime_direction, evaluate_market


def test_regime_direction_mapping():
    assert regime_direction(MarketRegime.BOOM) == "bullish"
    assert regime_direction(MarketRegime.EXPANSION) == "bullish"
    assert regime_direction(MarketRegime.RECOVERY) == "bullish"
    assert regime_direction(MarketRegime.SLOWDOWN) == "bearish"
    assert regime_direction(MarketRegime.RECESSION) == "bearish"
    assert regime_direction(MarketRegime.DEPRESSION) == "bearish"


def test_evaluate_market_trefferquote():
    # Zwei bullische Urteile; Preis steigt nach 3M in einem Fall, fällt im anderen.
    j = [
        {"as_of": date(2000, 1, 1), "regime": MarketRegime.EXPANSION},
        {"as_of": date(2001, 1, 1), "regime": MarketRegime.EXPANSION},
    ]
    prices = {
        date(2000, 1, 1): 100.0, date(2000, 4, 1): 110.0,   # +10 % → korrekt (bullish)
        date(2001, 1, 1): 100.0, date(2001, 4, 1):  90.0,   # -10 % → falsch
    }
    def sp_price_on(d): return prices.get(d)
    report = evaluate_market(j, sp_price_on, horizons_months=(3,))
    h3 = report[3]
    assert h3["n"] == 2
    assert h3["hit_rate"] == 0.5
    assert h3["by_regime"]["Aufschwung"]["n"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/utils/test_regime_eval_market.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.utils.regime_eval'`.

- [ ] **Step 3: Implement the module**

```python
# core/utils/regime_eval.py
"""Reine Bewertung von Regime-Urteilen: (A) Markt-Wahrheit (Forward-S&P) und
(B) Wirtschafts-Wahrheit (NBER). Kein I/O — Kursabruf/USREC werden injiziert."""
from datetime import date

from dateutil.relativedelta import relativedelta

from core.domain.models import MarketRegime
from core.utils.backtest import forward_return, is_correct, hit_rate_ci

_BULLISH = {MarketRegime.BOOM, MarketRegime.EXPANSION, MarketRegime.RECOVERY}
RISK_OFF = {MarketRegime.SLOWDOWN, MarketRegime.RECESSION, MarketRegime.DEPRESSION}


def regime_direction(regime: MarketRegime) -> str:
    """Regime → erwartete Marktrichtung. Wachstums-/Erholungsphasen bullish, Schwächephasen bearish."""
    return "bullish" if regime in _BULLISH else "bearish"


def evaluate_market(judgments: list, sp_price_on, horizons_months: tuple = (3, 6, 12)) -> dict:
    """Pro Horizont (Monate): Hit-Rate + Wilson-CI, gesamt und je Regime.
    sp_price_on(d: date) -> float | None liefert den S&P-Schlusskurs am/nach d."""
    report = {}
    for h in horizons_months:
        correct = 0
        total = 0
        by_regime: dict[str, dict] = {}
        for j in judgments:
            as_of = j["as_of"]
            regime = j["regime"]
            entry_px = sp_price_on(as_of)
            fwd_px = sp_price_on(as_of + relativedelta(months=h))
            ret = forward_return(entry_px, fwd_px)
            if ret is None:
                continue
            direction = regime_direction(regime)
            ok = is_correct(direction, ret)
            total += 1
            correct += 1 if ok else 0
            rk = regime.value
            b = by_regime.setdefault(rk, {"n": 0, "correct": 0})
            b["n"] += 1
            b["correct"] += 1 if ok else 0
        lo, hi = hit_rate_ci(correct, total)
        report[h] = {
            "n": total,
            "hit_rate": round(correct / total, 3) if total else None,
            "ci_low": lo,
            "ci_high": hi,
            "by_regime": {
                k: {"n": v["n"], "hit_rate": round(v["correct"] / v["n"], 3) if v["n"] else None}
                for k, v in by_regime.items()
            },
        }
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/utils/test_regime_eval_market.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/utils/regime_eval.py tests/core/utils/test_regime_eval_market.py
git commit -m "feat(eval): RegimeEvaluator (A) Markt-Wahrheit (Forward-S&P + Wilson-CI je Regime)"
```

---

### Task 6: `RegimeEvaluator` (B) — Wirtschafts-Wahrheit (NBER)

**Files:**
- Modify: `core/utils/regime_eval.py` (Funktion `evaluate_nber` ergänzen)
- Test: `tests/core/utils/test_regime_eval_nber.py`

**Interfaces:**
- Produces: `evaluate_nber(judgments: list, usrec_by_month: dict[str, int]) -> dict`. `usrec_by_month`-Keys: `"YYYY-MM"`, Werte `0|1` (1 = NBER-Rezessionsmonat). Rückgabe: `{"precision", "recall", "tp", "fp", "tn", "fn", "n", "mean_lead_months", "episodes": [...]}`. `mean_lead_months` > 0 = das System schaltet **vor** dem Rezessionsbeginn auf risk-off (antizipierend).

- [ ] **Step 1: Write the failing test**

```python
# tests/core/utils/test_regime_eval_nber.py
from datetime import date
from core.domain.models import MarketRegime
from core.utils.regime_eval import evaluate_nber


def _j(y, m, regime):
    return {"as_of": date(y, m, 1), "regime": regime}


def test_konfusion_und_vorlauf():
    # NBER-Rezession: 2001-04 .. 2001-06 (drei Monate = 1)
    usrec = {
        "2001-01": 0, "2001-02": 0, "2001-03": 0,
        "2001-04": 1, "2001-05": 1, "2001-06": 1, "2001-07": 0,
    }
    # System schaltet bereits 2001-02 auf risk-off (SLOWDOWN) → 2 Monate Vorlauf
    judgments = [
        _j(2001, 1, MarketRegime.EXPANSION),   # risk-on, kein NBER → TN
        _j(2001, 2, MarketRegime.SLOWDOWN),    # risk-off, kein NBER (Vorlauf!) → FP
        _j(2001, 3, MarketRegime.SLOWDOWN),    # risk-off, kein NBER → FP
        _j(2001, 4, MarketRegime.RECESSION),   # risk-off, NBER → TP
        _j(2001, 5, MarketRegime.RECESSION),   # risk-off, NBER → TP
        _j(2001, 6, MarketRegime.EXPANSION),   # risk-on, NBER → FN
        _j(2001, 7, MarketRegime.EXPANSION),   # risk-on, kein NBER → TN
    ]
    r = evaluate_nber(judgments, usrec)
    assert (r["tp"], r["fp"], r["tn"], r["fn"]) == (2, 2, 2, 1)
    assert round(r["precision"], 3) == 0.5    # 2 / (2+2)
    assert round(r["recall"], 3) == round(2/3, 3)
    # Erster risk-off (2001-02) vs. NBER-Start (2001-04) → +2 Monate Vorlauf
    assert r["mean_lead_months"] == 2.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/utils/test_regime_eval_nber.py -v`
Expected: FAIL — `ImportError: cannot import name 'evaluate_nber'`.

- [ ] **Step 3: Implement the function (append to `core/utils/regime_eval.py`)**

```python
def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _nber_episodes(usrec_by_month: dict) -> list:
    """Zusammenhängende Rezessions-Episoden als Liste von (start_key, end_key)."""
    months = sorted(k for k, v in usrec_by_month.items() if v == 1)
    episodes = []
    start = prev = None
    for k in months:
        if start is None:
            start = prev = k
            continue
        y, m = int(prev[:4]), int(prev[5:7])
        nxt = f"{y + (m // 12):04d}-{(m % 12) + 1:02d}"
        if k == nxt:
            prev = k
        else:
            episodes.append((start, prev))
            start = prev = k
    if start is not None:
        episodes.append((start, prev))
    return episodes


def _key_diff_months(a: str, b: str) -> int:
    """a - b in Monaten (a, b im Format YYYY-MM)."""
    ay, am = int(a[:4]), int(a[5:7])
    by, bm = int(b[:4]), int(b[5:7])
    return (ay - by) * 12 + (am - bm)


def evaluate_nber(judgments: list, usrec_by_month: dict) -> dict:
    """Konfusionsmatrix risk-off × NBER + mittlerer Vorlauf je Rezessions-Episode."""
    tp = fp = tn = fn = 0
    risk_off_keys = set()
    for j in judgments:
        key = _month_key(j["as_of"])
        actual = usrec_by_month.get(key)
        if actual is None:
            continue
        called = j["regime"] in RISK_OFF
        if called:
            risk_off_keys.add(key)
        if called and actual == 1:   tp += 1
        elif called and actual == 0: fp += 1
        elif not called and actual == 0: tn += 1
        else: fn += 1

    # Vorlauf: erster risk-off-Monat im Fenster [-12, +6] um den Episoden-Start
    leads = []
    for start, _end in _nber_episodes(usrec_by_month):
        # risk-off-Monate im Fenster [Start-12, Start+6]: k-start liegt in [-12, +6]
        window = [k for k in risk_off_keys if -12 <= _key_diff_months(k, start) <= 6]
        if window:
            first = min(window)
            leads.append(_key_diff_months(start, first))  # >0 = vor dem Start (antizipierend)

    precision = round(tp / (tp + fp), 3) if (tp + fp) else None
    recall    = round(tp / (tp + fn), 3) if (tp + fn) else None
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn, "n": tp + fp + tn + fn,
        "precision": precision, "recall": recall,
        "mean_lead_months": round(sum(leads) / len(leads), 1) if leads else None,
        "episodes": [{"start": s, "end": e} for s, e in _nber_episodes(usrec_by_month)],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/utils/test_regime_eval_nber.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/utils/regime_eval.py tests/core/utils/test_regime_eval_nber.py
git commit -m "feat(eval): RegimeEvaluator (B) NBER-Konfusion + Vorlauf je Rezessions-Episode"
```

---

### Task 7: `RegimeReplayHarness` — die Replay-Schleife + Treue-Äquivalenztest

**Files:**
- Create: `agents/backtester/regime_replay.py`
- Test: `tests/agents/backtester/test_regime_replay.py`

**Interfaces:**
- Consumes: `assemble_regime_inputs` (Task 2), `RegimeDetector.detect(..., history=)` (Task 1), die vier Sub-Signal-Agenten, `BuffettIndicatorAgent(wb_fetch=)` (Task 3).
- Produces:
  - `replay_step(provider, bus, ecb, snb) -> dict` — ein Stichtag: führt die vier Agenten mit den **injizierten** ECB/SNB-Providern aus, baut Inputs, gibt `{"economic_state", "usa_10y3m", "sub_signal_map"}` zurück (ohne Detector, damit der Trend außerhalb verwaltet wird).
  - `run_replay(provider_factory, stichtage: list[date], bus=None, ecb_factory=_default_ecb, snb_factory=_default_snb) -> list[dict]` — iteriert die Stichtage, pflegt die Composite-Historie, liefert Urteile `[{"as_of", "regime", "confidence", "composite", "data_quality"}, ...]`. `provider_factory(as_of) -> MacroDataProvider`; `ecb_factory(as_of) -> EcbDataProvider`, `snb_factory(as_of) -> SnbDataProvider` (Default = Stubs → EU/CH leer, wie Produktion). **Region/Quelle steckbar** (Spec §4.4): kein hartes `EcbStubProvider()` im Schleifen-Code.

- [ ] **Step 1: Write the failing test**

```python
# tests/agents/backtester/test_regime_replay.py
from datetime import date
from core.domain.models import MarketRegime
from agents.backtester.regime_replay import run_replay


class _FakeProvider:
    """Liefert je Stichtag einen konstanten, klar bullischen Makro-Zustand."""
    def __init__(self, as_of): self.as_of = as_of; self.quality = "revised"
    def get_economic_state(self):
        return {"gdp_growth": 3.5, "unemployment": 3.5, "inflation": 2.0,
                "industrial_production": 4.0, "consumer_sentiment": 95.0,
                "fed_rate": 1.5, "yield_curve": 0.5}
    def get_extended_state(self):
        return {"credit_growth": 5.0, "nominal_wage_growth": 4.0, "real_wage_growth": 2.0,
                "money_velocity": 1.4, "m2_growth": 5.0}
    def get_yield_spreads(self): return {"10y2y": 0.5, "10y3m": 0.8}
    def get_buffett_data(self): return {"market_cap_bn": None, "gdp_bn": None}
    def get_buffett_history(self, years=10): return []


def test_run_replay_liefert_urteile_je_stichtag():
    stichtage = [date(2000, 1, 1), date(2000, 2, 1), date(2000, 3, 1)]
    urteile = run_replay(lambda d: _FakeProvider(d), stichtage)
    assert len(urteile) == 3
    assert all(isinstance(u["regime"], MarketRegime) for u in urteile)
    assert all(u["data_quality"] == "revised" for u in urteile)
    # klar bullischer Zustand → Wachstums-/Boom-Phase
    assert urteile[-1]["regime"] in {MarketRegime.EXPANSION, MarketRegime.BOOM, MarketRegime.RECOVERY}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agents/backtester/test_regime_replay.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.backtester.regime_replay'`.

- [ ] **Step 3: Implement the harness**

```python
# agents/backtester/regime_replay.py
"""Regime-Replay: spielt den Top-Down-Regime-Motor Point-in-Time über die Historie durch.
Führt die ECHTEN Sub-Signal-Agenten aus (Treue) und nutzt die geteilte Input-Montage."""
import asyncio
from datetime import date

from agents.market_cockpit.macro.money_supply_agent import MoneySupplyAgent
from agents.market_cockpit.macro.credit_agent import CreditAgent
from agents.market_cockpit.macro.labor_income_agent import LaborIncomeAgent
from agents.market_cockpit.macro.buffett_indicator_agent import BuffettIndicatorAgent
from adapters.data.ecb_snb_stub import EcbStubProvider, SnbStubProvider
from core.domain.regime import RegimeDetector
from core.domain.regime_inputs import assemble_regime_inputs


class _NullBus:
    def publish(self, event): pass


# Default-Quellen-Fabriken: Stubs (EU/CH leer, wie Produktion heute). Region/Quelle ist
# steckbar — ein HistoricalEcbProvider/-SnbProvider ist später ein reiner Drop-in (Spec §4.4).
def _default_ecb(as_of):
    return EcbStubProvider()


def _default_snb(as_of):
    return SnbStubProvider()


async def _sub_signals(provider, bus, ecb, snb) -> dict:
    """Führt die vier echten Sub-Signal-Agenten aus (netzfrei: injizierte ECB/SNB, No-Op-WB)."""
    money = MoneySupplyAgent(provider, ecb, snb, bus)
    credit = CreditAgent(provider, bus)
    labor = LaborIncomeAgent(provider, bus)
    buffett = BuffettIndicatorAgent(provider, bus, wb_fetch=lambda: {})
    m, c, l, b = await asyncio.gather(money.run(), credit.run(), labor.run(), buffett.run())
    return {
        "money_supply": m.usa.signal,
        "credit":       c.usa.signal,
        "labor":        l.usa.signal,
        "buffett":      b.signal,
    }


def replay_step(provider, bus, ecb, snb) -> dict:
    """Ein Stichtag: Roh-Zustand + Sub-Signale (ohne Detector — Trend wird außen verwaltet)."""
    economic_state = provider.get_economic_state()
    spreads = provider.get_yield_spreads()
    sub_map = asyncio.run(_sub_signals(provider, bus, ecb, snb))
    return {
        "economic_state": economic_state,
        "usa_10y3m": spreads.get("10y3m"),
        "sub_signal_map": sub_map,
    }


def run_replay(provider_factory, stichtage: list, bus=None,
               ecb_factory=_default_ecb, snb_factory=_default_snb) -> list:
    """Iteriert die Stichtage, pflegt die Composite-Historie, liefert Regime-Urteile.
    ecb_factory/snb_factory(as_of) sind steckbar (Default = Stubs)."""
    bus = bus or _NullBus()
    detector = RegimeDetector()
    history: list = []          # [(iso_date, composite), ...]
    urteile = []
    for as_of in stichtage:
        provider = provider_factory(as_of)
        raw = replay_step(provider, bus, ecb_factory(as_of), snb_factory(as_of))
        state, sub_signals = assemble_regime_inputs(
            raw["economic_state"], raw["usa_10y3m"], {}, {}, raw["sub_signal_map"],
        )
        regime, confidence, evidence = detector.detect(state, sub_signals, history=history)
        # Composite für den Trend des nächsten Stichtags rekonstruieren
        composite = _composite_from(evidence, sub_signals)
        history = history + [(as_of.isoformat(), composite)]
        urteile.append({
            "as_of": as_of,
            "regime": regime,
            "confidence": confidence,
            "composite": round(composite, 4),
            "data_quality": getattr(provider, "quality", "unbekannt"),
        })
    return urteile


def _composite_from(evidence: dict, sub_signals: dict) -> float:
    """Composite aus evidence (score je Indikator) + INDICATOR_WEIGHTS + Sub-Gewichten,
    identisch zur Berechnung in RegimeDetector.detect()."""
    from core.domain.regime import INDICATOR_WEIGHTS
    weighted_sum = 0.0
    weight_total = 0.0
    for key, score in evidence.items():
        if key in sub_signals:
            continue
        w = INDICATOR_WEIGHTS.get(key, 0.0)
        weighted_sum += score * w
        weight_total += w
    for key in sub_signals:
        weighted_sum += sub_signals[key] * 0.03
        weight_total += 0.03
    return weighted_sum / weight_total if weight_total > 0 else 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agents/backtester/test_regime_replay.py -v`
Expected: PASS.

- [ ] **Step 5: Write the faithfulness equivalence test**

```python
# tests/agents/backtester/test_regime_replay_treue.py
import asyncio
from datetime import date

from agents.backtester.regime_replay import replay_step, _NullBus
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from adapters.data.ecb_snb_stub import EcbStubProvider, SnbStubProvider
from core.domain.regime import RegimeDetector
from core.domain.regime_inputs import assemble_regime_inputs


class _FakeProvider:
    def __init__(self, as_of=None): self.quality = "revised"
    def get_economic_state(self):
        return {"gdp_growth": 1.0, "unemployment": 5.5, "inflation": 3.5,
                "industrial_production": -1.0, "consumer_sentiment": 60.0,
                "fed_rate": 4.5, "yield_curve": -0.2}
    def get_extended_state(self):
        return {"credit_growth": 1.0, "nominal_wage_growth": 2.0, "real_wage_growth": -1.5,
                "money_velocity": 1.3, "m2_growth": 1.0}
    def get_yield_spreads(self): return {"10y2y": -0.2, "10y3m": -0.3}
    def get_buffett_data(self): return {"market_cap_bn": None, "gdp_bn": None}
    def get_buffett_history(self, years=10): return []


def test_replay_pfad_gleich_produktionspfad():
    """Gleiche Roh-Daten durch MacroChiefAgent (echt) und Replay → identisches Regime."""
    prov = _FakeProvider()
    bus = _NullBus()

    # Produktionspfad: echter MacroChiefAgent, aber Detector mit injizierter (leerer) Historie
    chief = MacroChiefAgent(prov, EcbStubProvider(), SnbStubProvider(), bus)
    # buffett-Agent im Chief netzfrei machen:
    chief.buffett_indicator_agent = type(chief.buffett_indicator_agent)(
        prov, bus, wb_fetch=lambda: {})
    prod_result = asyncio.run(chief.run())

    # Replay-Pfad (ECB/SNB-Stubs explizit injiziert — wie der Default in run_replay)
    raw = replay_step(prov, bus, EcbStubProvider(), SnbStubProvider())
    state, subs = assemble_regime_inputs(raw["economic_state"], raw["usa_10y3m"], {}, {}, raw["sub_signal_map"])
    replay_regime, _, _ = RegimeDetector().detect(state, subs, history=[])

    # Produktion nutzt im run() die Datei-Historie; für den Vergleich nur das Regime-Mapping
    # bei leerer Historie heranziehen → beide mit history=[] auf identischem state.
    assert replay_regime == prod_result.regime
```

*(Hinweis für den Implementierer: Falls `MacroChiefAgent.run()` über die Datei-Historie einen anderen Trend zieht als `history=[]`, im Test die Datei vorab leeren/`monkeypatch`en, sodass beide Pfade dieselbe (leere) Historie sehen. Ziel des Tests ist die Gleichheit der **Input-Montage + Regime-Ableitung**, nicht des Datei-Trends.)*

- [ ] **Step 6: Run the equivalence test**

Run: `python -m pytest tests/agents/backtester/test_regime_replay_treue.py -v`
Expected: PASS — Replay-Regime == Produktions-Regime.

- [ ] **Step 7: Commit**

```bash
git add agents/backtester/regime_replay.py tests/agents/backtester/test_regime_replay.py tests/agents/backtester/test_regime_replay_treue.py
git commit -m "feat(replay): Regime-Replay-Schleife (echte Sub-Agenten) + Treue-Aequivalenztest"
```

---

### Task 8: Report-Builder + CLI-Entrypoint `app/replay_regime.py`

**Files:**
- Modify: `core/utils/regime_eval.py` (Funktion `build_report_md` ergänzen)
- Create: `app/replay_regime.py`
- Test: `tests/core/utils/test_regime_report.py`

**Interfaces:**
- Consumes: `evaluate_market`, `evaluate_nber` (Tasks 5/6).
- Produces:
  - `build_report_md(market: dict, nber: dict, n_judgments: int, window: str, quality_counts: dict) -> str` — lesbare Markdown-Zusammenfassung.
  - `app/replay_regime.py`: CLI `python -m app.replay_regime [--start YYYY-MM] [--end YYYY-MM]` → schreibt `data/backtests/regime_replay_YYYYMMDD.json` + `.md`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/utils/test_regime_report.py
from core.utils.regime_eval import build_report_md


def test_build_report_md_enthaelt_kernzahlen():
    market = {3: {"n": 100, "hit_rate": 0.62, "ci_low": 0.52, "ci_high": 0.71,
                  "by_regime": {"Aufschwung": {"n": 40, "hit_rate": 0.70}}}}
    nber = {"tp": 20, "fp": 10, "tn": 60, "fn": 10, "n": 100,
            "precision": 0.667, "recall": 0.667, "mean_lead_months": 1.5,
            "episodes": [{"start": "2001-04", "end": "2001-06"}]}
    md = build_report_md(market, nber, n_judgments=120, window="1960-01..2026-06",
                         quality_counts={"vintage": 30, "revised": 90})
    assert "Hit-Rate" in md
    assert "62" in md                  # 0.62 → 62 %
    assert "Vorlauf" in md
    assert "1960-01..2026-06" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/utils/test_regime_report.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_report_md'`.

- [ ] **Step 3: Implement `build_report_md` (append to `core/utils/regime_eval.py`)**

```python
def build_report_md(market: dict, nber: dict, n_judgments: int, window: str,
                    quality_counts: dict) -> str:
    """Lesbare Markdown-Zusammenfassung des Replay-Reports."""
    lines = [
        f"# Regime-Replay-Report",
        f"",
        f"- Fenster: **{window}**",
        f"- Urteile gesamt: **{n_judgments}**",
        f"- Datenqualität: " + ", ".join(f"{k}={v}" for k, v in sorted(quality_counts.items())),
        f"",
        f"## (A) Markt-Wahrheit — Forward-S&P",
        f"",
        f"| Horizont | N | Hit-Rate | 95 %-CI |",
        f"|---|---|---|---|",
    ]
    for h in sorted(market):
        m = market[h]
        hr = f"{m['hit_rate']*100:.0f} %" if m["hit_rate"] is not None else "n/v"
        lines.append(f"| {h} M | {m['n']} | {hr} | {m['ci_low']*100:.0f}–{m['ci_high']*100:.0f} % |")
    lines += ["", "### Je Regime (kürzester Horizont)", ""]
    if market:
        h0 = sorted(market)[0]
        for rk, v in sorted(market[h0]["by_regime"].items()):
            hr = f"{v['hit_rate']*100:.0f} %" if v["hit_rate"] is not None else "n/v"
            lines.append(f"- **{rk}**: N={v['n']}, Hit-Rate={hr}")
    lead = nber.get("mean_lead_months")
    lead_str = f"{lead:+.1f} Monate" if lead is not None else "n/v"
    lines += [
        "", "## (B) Wirtschafts-Wahrheit — NBER", "",
        f"- Precision (risk-off | NBER): **{(nber['precision'] or 0)*100:.0f} %**",
        f"- Recall: **{(nber['recall'] or 0)*100:.0f} %**",
        f"- Mittlerer **Vorlauf** vor Rezessionsbeginn: **{lead_str}** (positiv = antizipierend)",
        f"- Konfusion: TP={nber['tp']} FP={nber['fp']} TN={nber['tn']} FN={nber['fn']}",
        f"- Rezessions-Episoden im Fenster: {len(nber.get('episodes', []))}",
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/utils/test_regime_report.py -v`
Expected: PASS.

- [ ] **Step 5: Implement the CLI entrypoint**

```python
# app/replay_regime.py
"""Regime-Replay-Backtest (Stufe 1).
Verwendung:
  python -m app.replay_regime [--start YYYY-MM] [--end YYYY-MM]
Schreibt data/backtests/regime_replay_YYYYMMDD.json + .md."""
import argparse
import json
import os
from collections import Counter
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
import yfinance as yf
from fredapi import Fred

from config.settings import FRED_API_KEY
from adapters.data.historical_fred import HistoricalFredProvider
from agents.backtester.regime_replay import run_replay
from core.utils.backtest import benchmark_for_market
from core.utils.regime_eval import evaluate_market, evaluate_nber, build_report_md

_HORIZONS = (3, 6, 12)
# v1-Entrypoint läuft USA. Region-Steckbarkeit liegt in der Library-API (run_replay nimmt
# ecb_factory/snb_factory; evaluate_market nimmt die Kursfunktion injiziert; Benchmark über
# benchmark_for_market). EU/CH-Entrypoint = Stufe ①b (Spec §4.4/§10).
_REGION = "USA"


def _monatsenden(start: date, end: date) -> list:
    out, cur = [], start
    while cur <= end:
        out.append(cur)
        cur = cur + relativedelta(months=1)
    return out


def _price_on(ticker: str, d: date):
    """Erster Benchmark-Schlusskurs am/nach d. None = kein Kurs."""
    try:
        df = yf.Ticker(ticker).history(start=d.strftime("%Y-%m-%d"), period="10d")
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[0])
    except Exception:
        return None


def _usrec_by_month(fred: Fred) -> dict:
    s = fred.get_series("USREC").dropna()
    return {f"{ts.year:04d}-{ts.month:02d}": int(v) for ts, v in s.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="1960-01")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m"))
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m").date().replace(day=1)
    end = datetime.strptime(args.end, "%Y-%m").date().replace(day=1)
    stichtage = _monatsenden(start, end)

    print(f"[RegimeReplay] {len(stichtage)} Stichtage {args.start}..{args.end} (Region {_REGION}) …")
    urteile = run_replay(lambda d: HistoricalFredProvider(FRED_API_KEY, d), stichtage)

    # (A) Markt-Wahrheit: Benchmark region-abhängig via benchmark_for_market (USA→^GSPC).
    benchmark = benchmark_for_market(_REGION)
    market = evaluate_market(urteile, lambda d: _price_on(benchmark, d), horizons_months=_HORIZONS)

    # (B) Wirtschafts-Wahrheit: NBER ist USA-only (Spec §4.4). Andere Regionen: kein Label (Stufe ①b).
    fred = Fred(api_key=FRED_API_KEY)
    nber = evaluate_nber(urteile, _usrec_by_month(fred))
    quality_counts = dict(Counter(u["data_quality"] for u in urteile))
    window = f"{args.start}..{args.end} ({_REGION})"
    md = build_report_md(market, nber, len(urteile), window, quality_counts)

    os.makedirs("data/backtests", exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    payload = {
        "window": window,
        "n_judgments": len(urteile),
        "quality_counts": quality_counts,
        "market": market,
        "nber": nber,
        "judgments": [
            {"as_of": u["as_of"].isoformat(), "regime": u["regime"].value,
             "confidence": u["confidence"], "composite": u["composite"],
             "data_quality": u["data_quality"]}
            for u in urteile
        ],
    }
    with open(f"data/backtests/regime_replay_{stamp}.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(f"data/backtests/regime_replay_{stamp}.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    print(f"\n[RegimeReplay] Report → data/backtests/regime_replay_{stamp}.(json|md)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the report test + smoke-check the entrypoint imports**

Run: `python -m pytest tests/core/utils/test_regime_report.py -v`
Expected: PASS.

Run: `python -c "import app.replay_regime"`
Expected: kein Fehler (Imports auflösbar). *(Kein echter Lauf — der zieht Netz/FRED-Key.)*

- [ ] **Step 7: Commit**

```bash
git add core/utils/regime_eval.py tests/core/utils/test_regime_report.py app/replay_regime.py
git commit -m "feat(replay): Report-Builder + CLI app.replay_regime (JSON + Markdown)"
```

---

## Abschluss: Gesamtsuite + Logbuch

- [ ] **Step 1: Gesamte Testsuite grün**

Run: `python -m pytest -q`
Expected: Alle Tests grün (bestehende + neue), keine Regression.

- [ ] **Step 2: Logbuch-Eintrag**

In `docs/open_todos.md` §5 unter „Regime-Backtester" abhaken bzw. ergänzen: Stufe 1 (Validierung) umgesetzt, mit Verweis auf Spec/Plan; Stufen ②③④ als offene Folge-Aufgaben notieren. Committen:

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): Regime-Replay Stufe 1 umgesetzt, Folge-Stufen notiert"
```

- [ ] **Step 3: Branch fertig — PR vorbereiten**

Verwende die Skill `superpowers:finishing-a-development-branch`. **Nicht** ohne ausdrückliches OK des Users mergen (AGENTS.md §5, PR-First).

---

## Self-Review (vom Planautor durchgeführt)

**Spec-Abdeckung:**
- §3.1 (A Markt) → Task 5. §3.2 (B NBER) → Task 6. §4.0 Treue → Tasks 2/3/7. §4.1 Provider → Task 4. §4.2 (detect-History, assemble, buffett) → Tasks 1/2/3. §4.3 Harness → Task 7. **§4.4 Region-/Quellen-Steckbarkeit → Task 7 (injizierte ecb/snb-Fabriken) + Task 8 (`benchmark_for_market`, NBER USA-only).** §5 Look-Ahead → Tasks 1/4 (Tests pinnen `<= as_of`). §6 Daten/Defaults → Task 8 (Horizonte/USREC/Benchmark). §7 Tests → in jeder Task + Treue-Test (Task 7). §8 Deliverable → Task 8.
- **Lücke bewusst akzeptiert:** Vintage-Datenqualität pro Reihe ist auf ein grobes Gesamt-Flag pro Stichtag vereinfacht (Spec §9 erlaubt das; pro-Reihe-Granularität ist YAGNI für v1).

**Platzhalter-Scan:** Kein TBD/TODO im ausführbaren Code. Der redundante `candidates`-Block in Task 6 ist explizit als „nur `window` behalten" markiert.

**Typ-Konsistenz:** Urteil-Dict-Keys (`as_of: date`, `regime: MarketRegime`, `confidence`, `composite`, `data_quality`) durchgängig in Tasks 5/6/7/8. `assemble_regime_inputs`-Signatur identisch in Tasks 2/7. `detect(state, sub_signals, history=)` identisch in Tasks 1/7. `sp_price_on(date)->float|None` identisch in Tasks 5/8.
