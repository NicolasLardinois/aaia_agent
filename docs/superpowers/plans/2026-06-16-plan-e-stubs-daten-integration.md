# Plan E — Stub-Implementierungen & Daten-Integration — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die elf reinen Stub-/Durchreiche-Agenten aus den Domänen 3/6/7 des Konzept-Reviews (`docs/finanz_konzept_review_2026-06-16.md`) durch echte quantitative Berechnungen ersetzen. Solange eine externe Datenquelle noch nicht verdrahtet ist, liefert der jeweilige Agent `SignalStatus.UNAVAILABLE` statt `NEUTRAL`, damit die Chief-Aggregation (Plan 0 `weighted_signal`) ihn korrekt aus der Gewichtung herausnimmt (Re-Normalisierung), statt das Composite Richtung Mitte zu ziehen (Review Teil B, Punkt 1.4).
**Architecture:** Event-Driven + Hexagonal. Agenten hängen ausschließlich an Ports (`MarketDataProvider`, `MacroDataProvider` und neue Ports). Neue externe Daten werden als **Port-Methode mit klarer Signatur** eingeführt und die Agenten-Logik gegen einen **injizierten Fake-Provider** getestet. Reine Rechen-/Signal-Logik wird als freie Modul-Funktion (`_signal`, `_breadth`, `_percentile`, …) testbar gehalten — analog zur bestehenden Vorlage `tests/agents/stock_deep_dive/index/test_index_momentum_agent.py`.
**Tech Stack:** Python, asyncio, pytest
**Abhängigkeiten:** Plan 0 (Shared Utilities); profitiert von Plan D1/D2-Chief-Aggregation.

Aus **Plan 0** werden die folgenden Bausteine **referenziert** (NICHT in diesem Plan neu definiert):
- `core/utils/relative.py` → `percentile_rank(value, history, winsorize=0.0) -> float` (echtes Rang-Perzentil 0–100; in `commodity_valuation_range`, `cross_metal`-Anker, COT-Index).
- `core/utils/statistics.py` → `robust_z_score(value, history) -> float` (Median/MAD-basiert; in `seasonality`-Robustheit; das Modul existiert bereits mit `z_score`/`compute_severity`, Plan 0 ergänzt `robust_z_score`).
- (Reale Preis-Deflation: **bewusst zurückgestellt.** Plan 0's `to_real(nominal_rate, inflation)` ist ein **skalarer** Fisher-Helfer für Renditen/Wachstumsraten in Prozentpunkten und kann **keine Preis-Reihe** deflationieren. `commodity_valuation_range` und `seasonality` arbeiten daher auf **nominalen** Preisen; der substanzielle P4.3-Fix ist das echte Rang-Perzentil via `percentile_rank`. Eine spätere reale Deflation erfordert eine an die Preisdaten ausgerichtete CPI-Index-Serie + einen eigenen Reihen-Helfer und ist ein klar abgegrenzter Folge-Task.)
- `core/domain/models.py` → `SignalStatus` (Enum `AVAILABLE | UNAVAILABLE`; Stub→UNAVAILABLE bis Daten vorhanden). Plan 0 fügt dieses Enum hinzu und ergänzt jeden Snapshot um ein Feld `status: SignalStatus = SignalStatus.AVAILABLE`.

> **Konvention dieses Plans für `status`:** Jeder hier berührte Snapshot trägt nach Plan 0 ein Feld `status`. Liefert ein Agent ein echtes, datenbasiertes Signal → `status = SignalStatus.AVAILABLE`. Fehlt die externe Datenquelle (Port-Methode liefert `None`/leer) → `signal = Signal.NEUTRAL` **und** `status = SignalStatus.UNAVAILABLE`. Die Chief-Aggregation (Plan 0 `weighted_signal`) ignoriert `UNAVAILABLE`-Einträge. Falls Plan 0 zum Implementierungszeitpunkt noch nicht gemerged ist: zuerst Plan 0 ausführen; dieser Plan setzt `SignalStatus` und die Utils als vorhanden voraus.

---

## Dateienübersicht

**Scope-Agenten (geändert):**
- `agents/stock_deep_dive/index/index_breadth_agent.py` — echte Breadth (% > MA200 der Konstituenten, A/D-Ratio, New-High/Low).
- `agents/stock_deep_dive/index/index_earnings_agent.py` — aggregierte (bottom-up) Index-EPS + echte Estimate-Revisions statt Fwd/Trailing-PE-Proxy.
- `agents/stock_deep_dive/index/index_price_agent.py` — Total- vs. Price-Return (P4.6), 52W-High/Low aus Historie statt `info`.
- `agents/stock_deep_dive/index/sector_composition_agent.py` — dynamische Top-10-Konzentration/HHI aus Indexgewichten.
- `agents/stock_deep_dive/commodity/cot_agent.py` — CFTC-COT-Index (Managed Money, 0–100 normalisiert).
- `agents/stock_deep_dive/commodity/seasonality_agent.py` — längere Historie, t-Test-Signifikanz, Median statt Mittel, reale Preise.
- `agents/stock_deep_dive/commodity/supply_demand_agent.py` — echte Lagerbalancen, einheitliche S2F-Definition.
- `agents/stock_deep_dive/commodity/commodity_valuation_range_agent.py` — echtes Perzentil (P4.3), reale Preise, Cost-Curve-Anker.
- `agents/stock_deep_dive/precious_metals/cross_metal_agent.py` — rollierende Perzentil-Anker, metallspezifische Richtung, Gold/Platin-Signal.
- `agents/stock_deep_dive/precious_metals/precious_metal_price_agent.py` — Performance/RSI/MA/Realzins-Korrelation aus geladener Historie.
- `agents/market_cockpit/sentiment/fear_greed_agent.py` — echte Datenquelle + symmetrische Extremzonen.

**Ports / Adapter (geändert/erweitert):**
- `core/ports/data_provider.py` — neue Port-Methoden (Signaturen siehe Tasks).
- `adapters/data/yahoo_finance.py` — Implementierung markt-naher neuer Methoden.
- `adapters/data/finnhub.py` / neue `adapters/data/cftc_cot.py`, `adapters/data/cnn_fear_greed.py` — externe Quellen.

**Tests (neu):**
- `tests/agents/stock_deep_dive/index/test_index_breadth_agent.py`
- `tests/agents/stock_deep_dive/index/test_index_earnings_agent.py`
- `tests/agents/stock_deep_dive/index/test_index_price_agent.py`
- `tests/agents/stock_deep_dive/index/test_sector_composition_agent.py`
- `tests/agents/stock_deep_dive/commodity/test_cot_agent.py`
- `tests/agents/stock_deep_dive/commodity/test_seasonality_agent.py`
- `tests/agents/stock_deep_dive/commodity/test_supply_demand_agent.py`
- `tests/agents/stock_deep_dive/commodity/test_commodity_valuation_range_agent.py`
- `tests/agents/stock_deep_dive/precious_metals/test_cross_metal_agent.py`
- `tests/agents/stock_deep_dive/precious_metals/test_precious_metal_price_agent.py`
- `tests/agents/market_cockpit/sentiment/test_fear_greed_agent.py`

**Neue Port-Methoden (Überblick — Details je Task):**
| Port | Methode | Rückgabe |
|---|---|---|
| `MarketDataProvider` | `get_index_constituents(index_ticker: str) -> list[str]` | Liste der Konstituenten-Ticker (leer = unbekannt) |
| `MarketDataProvider` | `get_constituent_histories(index_ticker, period="2y") -> dict[str, "pandas.Series"]` | {ticker: Close-Serie} der Konstituenten |
| `MarketDataProvider` | `get_index_holdings(index_ticker: str) -> list[dict]` | [{"name","weight_pct","sector"}], leer = unbekannt |
| `MarketDataProvider` | `get_index_fundamentals(index_ticker) -> dict` | {"eps_ttm","eps_fwd","eps_growth_1y","revenue_growth_1y","operating_margin","estimate_revision"} |
| `MarketDataProvider` | `get_total_return_history(ticker, period="5y") -> object` | DataFrame mit Total-Return-`Close` (Dividenden reinvestiert); `None` falls nur Price-Return |
| `COTProvider` (neu) | `get_cot_history(commodity: str, years: int = 3) -> list[dict]` | [{"date","managed_money_net","open_interest"}], älteste zuerst |
| `CommoditySupplyProvider` (neu) | `get_inventory_history(commodity, years=5) -> list[dict]` | [{"date","inventory"}] |
| `CommoditySupplyProvider` (neu) | `get_production_cost_curve(commodity) -> dict` | {"cost_p25","cost_p50","cost_p75","cost_p90"} oder leer |
| `MacroDataProvider` | `get_real_rate_history(years: int = 5) -> list[dict]` | [{"date","real_rate_10y"}] (10J-TIPS), älteste zuerst |
| `SentimentDataProvider` (neu) | `get_fear_greed() -> Optional[float]` | aktueller CNN-Fear&Greed-Wert 0–100 |

---

### Task 1 — `SignalStatus`-Helfer & Test-Fixtures (Vorbereitung)

**Files:** `tests/agents/stock_deep_dive/conftest.py` (neu), `tests/agents/market_cockpit/sentiment/__init__.py` (neu, falls fehlt)

Ziel: gemeinsame Helfer/Imports, damit alle folgenden Tasks gegen Fake-Provider testen können. Voraussetzung: Plan 0 hat `SignalStatus` und die Utils bereitgestellt.

- [ ] **Verifikation Plan-0-Voraussetzungen** — failing Test schreiben: `tests/agents/stock_deep_dive/test_plan0_contract.py`
  ```python
  from core.domain.models import SignalStatus
  from core.utils.relative import percentile_rank
  from core.utils.statistics import robust_z_score
  from core.utils.real_nominal import to_real


  def test_signal_status_enum_exists():
      assert SignalStatus.AVAILABLE.value == "available"
      assert SignalStatus.UNAVAILABLE.value == "unavailable"


  def test_percentile_rank_basic():
      # 60 ist größer als 5 von 10 Werten → 50. Perzentil
      hist = [10, 20, 30, 40, 50, 70, 80, 90, 100, 110]
      assert percentile_rank(60, hist) == 50.0


  def test_robust_z_score_uses_median():
      # Ausreißer 1000 darf den Z-Score des Werts 5 nicht aufblähen (MAD-basiert)
      hist = [1, 2, 3, 4, 5, 6, 7, 1000]
      assert abs(robust_z_score(5, hist)) < 1.0
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/test_plan0_contract.py` → schlägt fehl, falls Plan 0 nicht vorhanden. Ist das der Fall: **STOP, zuerst Plan 0 ausführen.**
- [ ] **conftest schreiben** — `tests/agents/stock_deep_dive/conftest.py`:
  ```python
  from unittest.mock import MagicMock

  import pandas as pd
  import pytest


  def make_close_series(values: list[float], start: str = "2021-01-04", freq: str = "B") -> pd.Series:
      idx = pd.date_range(start=start, periods=len(values), freq=freq)
      return pd.Series(values, index=idx, dtype=float, name="Close")


  def make_hist(values: list[float], **kw) -> pd.DataFrame:
      return pd.DataFrame({"Close": make_close_series(values, **kw)})


  @pytest.fixture
  def bus() -> MagicMock:
      return MagicMock()
  ```
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/test_plan0_contract.py`
- [ ] **Commit** — `test(plan-e): Plan-0-Vertrag + gemeinsame Test-Fixtures`

---

### Task 2 — `cross_metal_agent`: rollierende Perzentil-Anker, metallspezifische Richtung, Gold/Platin-Signal

**Files:** `agents/stock_deep_dive/precious_metals/cross_metal_agent.py`, `tests/agents/stock_deep_dive/precious_metals/test_cross_metal_agent.py`

Befund (Review D7): `GOLD_SILVER_AVG=68`/`GOLD_PLATINUM_AVG=1.0` sind veraltet/falsch; Fallback `gs_ratio or AVG` maskiert fehlende Daten als NEUTRAL; Richtung unklar; Gold/Platin nie in ein Signal überführt. Lösung: rollierende Perzentile (`percentile_rank` aus Plan 0) der Ratio-Historie statt fixer Anker; hoher GS-Ratio → **bullish Silber / bearish Gold** (metallspezifisch über den `metal`-Parameter); Gold/Platin analog; fehlende Daten → `SignalStatus.UNAVAILABLE`.

Benötigt Ratio-**Historie** statt nur Spot. Genutzt wird `get_price_history` (existiert) für `GC=F`, `SI=F`, `PL=F`; keine neue Port-Methode nötig.

- [ ] **failing Test** — `tests/agents/stock_deep_dive/precious_metals/test_cross_metal_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  from agents.stock_deep_dive.precious_metals.cross_metal_agent import (
      CrossMetalAgent, _ratio_signal,
  )
  from core.domain.models import Signal, SignalStatus


  def test_high_gs_percentile_is_bullish_for_silver():
      # GS-Ratio im 95. Perzentil → Silber relativ billig → bullish Silber
      assert _ratio_signal(pct=95.0, metal="silver", high_favours="second") == Signal.BULLISH


  def test_high_gs_percentile_is_bearish_for_gold():
      # selber Zustand, aber Metall = Gold → bearish Gold
      assert _ratio_signal(pct=95.0, metal="gold", high_favours="second") == Signal.BEARISH


  def test_low_gs_percentile_is_bearish_for_silver():
      assert _ratio_signal(pct=5.0, metal="silver", high_favours="second") == Signal.BEARISH


  def test_mid_percentile_is_neutral():
      assert _ratio_signal(pct=50.0, metal="silver", high_favours="second") == Signal.NEUTRAL


  def test_missing_data_is_unavailable():
      provider = MagicMock()
      provider.get_price_history.return_value = None
      agent = CrossMetalAgent(provider, MagicMock())
      result = asyncio.run(agent.run("gold"))
      assert result.status == SignalStatus.UNAVAILABLE
      assert result.signal == Signal.NEUTRAL


  def test_gold_platinum_signal_is_emitted_for_platinum():
      # hoher Gold/Platin-Quotient (95. Perzentil) → Platin relativ billig → bullish Platin
      import pandas as pd
      provider = MagicMock()

      def hist(ticker, period="2y"):
          # konstruiere Ratio-Historie so, dass aktueller Quotient extrem hoch ist
          if ticker == "GC=F":
              return pd.DataFrame({"Close": pd.Series([2000.0] * 250 + [4000.0])})
          if ticker == "SI=F":
              return pd.DataFrame({"Close": pd.Series([25.0] * 251)})
          if ticker == "PL=F":
              return pd.DataFrame({"Close": pd.Series([1000.0] * 251)})
          return None

      provider.get_price_history.side_effect = hist
      agent = CrossMetalAgent(provider, MagicMock())
      result = asyncio.run(agent.run("platinum"))
      assert result.status == SignalStatus.AVAILABLE
      assert result.signal == Signal.BULLISH
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/precious_metals/test_cross_metal_agent.py`
- [ ] **echte Implementierung** — `agents/stock_deep_dive/precious_metals/cross_metal_agent.py` vollständig ersetzen:
  ```python
  import asyncio

  from core.domain.events import CrossMetalReady
  from core.domain.models import CrossMetalSnapshot, Signal, SignalStatus
  from core.ports.data_provider import MarketDataProvider
  from core.ports.event_bus import EventBus
  from core.utils.relative import percentile_rank

  _DEFAULT = CrossMetalSnapshot(
      gold_silver_ratio=None, gold_platinum_ratio=None,
      signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
  )

  _HIGH_PCT = 80.0   # ab hier "Ratio hoch" (zweites Metall relativ billig)
  _LOW_PCT  = 20.0   # ab hier "Ratio niedrig" (erstes Metall relativ billig)


  def _ratio_signal(pct: float, metal: str, high_favours: str) -> Signal:
      """pct = rollierendes Perzentil des aktuellen Ratios (Erstmetall/Zweitmetall).

      high_favours = "second": hohes Ratio → das ZWEITE Metall ist relativ billig.
      Richtung ist metallspezifisch: für das billige Metall bullish, fürs teure bearish.
      """
      m = metal.lower()
      if pct >= _HIGH_PCT:
          cheap, expensive = ("second", "first") if high_favours == "second" else ("first", "second")
      elif pct <= _LOW_PCT:
          cheap, expensive = ("first", "second") if high_favours == "second" else ("second", "first")
      else:
          return Signal.NEUTRAL
      # Mapping Position → konkretes Metall je Ratio bestimmt der Aufrufer; hier generisch:
      role = _role_of_metal(m)
      if role == cheap:
          return Signal.BULLISH
      if role == expensive:
          return Signal.BEARISH
      return Signal.NEUTRAL


  def _role_of_metal(metal: str) -> str | None:
      """Erstmetall ist immer Gold; Zweitmetall ist Silber bzw. Platin."""
      if metal == "gold":
          return "first"
      if metal in ("silver", "platinum"):
          return "second"
      return None


  def _ratio_history(num: "object", den: "object") -> tuple[list[float], float | None]:
      import pandas as pd
      if num is None or den is None:
          return [], None
      n = num["Close"] if isinstance(num, pd.DataFrame) else num
      d = den["Close"] if isinstance(den, pd.DataFrame) else den
      aligned = (n.reset_index(drop=True) / d.reset_index(drop=True)).dropna()
      if len(aligned) < 30:
          return [], None
      hist = [round(float(x), 4) for x in aligned.iloc[:-1]]
      current = round(float(aligned.iloc[-1]), 4)
      return hist, current


  class CrossMetalAgent:
      def __init__(self, provider: MarketDataProvider, bus: EventBus):
          self.provider = provider
          self.bus = bus

      async def run(self, metal: str = "gold") -> CrossMetalSnapshot:
          gold, silver, platinum = await asyncio.gather(
              asyncio.to_thread(self.provider.get_price_history, "GC=F", "2y"),
              asyncio.to_thread(self.provider.get_price_history, "SI=F", "2y"),
              asyncio.to_thread(self.provider.get_price_history, "PL=F", "2y"),
              return_exceptions=True,
          )
          gold     = None if isinstance(gold, Exception) else gold
          silver   = None if isinstance(silver, Exception) else silver
          platinum = None if isinstance(platinum, Exception) else platinum

          gs_hist, gs_cur = _ratio_history(gold, silver)
          gp_hist, gp_cur = _ratio_history(gold, platinum)

          m = metal.lower()
          if m == "silver" and gs_cur is not None:
              pct = percentile_rank(gs_cur, gs_hist)
              signal, status = _ratio_signal(pct, m, "second"), SignalStatus.AVAILABLE
          elif m == "platinum" and gp_cur is not None:
              pct = percentile_rank(gp_cur, gp_hist)
              signal, status = _ratio_signal(pct, m, "second"), SignalStatus.AVAILABLE
          elif m == "gold" and gs_cur is not None:
              pct = percentile_rank(gs_cur, gs_hist)
              signal, status = _ratio_signal(pct, m, "second"), SignalStatus.AVAILABLE
          else:
              signal, status = Signal.NEUTRAL, SignalStatus.UNAVAILABLE

          result = CrossMetalSnapshot(
              gold_silver_ratio=gs_cur,
              gold_platinum_ratio=gp_cur,
              signal=signal,
              status=status,
          )
          self.bus.publish(CrossMetalReady(source="cross_metal_agent", payload={
              "gold_silver_ratio": gs_cur, "gold_platinum_ratio": gp_cur,
          }))
          return result

      @staticmethod
      def default() -> CrossMetalSnapshot:
          return _DEFAULT
  ```
  > **Self-Review:** `cross_metal` wird im PM-Pfad mit dem analysierten Metall aufgerufen — der Aufrufer (`precious_metals_chief`) muss `metal` weiterreichen; aktuell ruft er `run()` ohne Argument. Default `metal="gold"` hält Abwärtskompatibilität. In einer Folge-Aufgabe (Plan D2) den Metall-Parameter durchreichen.
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/precious_metals/test_cross_metal_agent.py`
- [ ] **Commit** — `feat(cross_metal): rollierende Perzentil-Anker + metallspezifische Richtung + Gold/Platin-Signal (Review D7)`

---

### Task 3 — `precious_metal_price_agent`: Performance/RSI/MA aus Historie + Realzins-Korrelation

**Files:** `agents/stock_deep_dive/precious_metals/precious_metal_price_agent.py`, `core/ports/data_provider.py`, `tests/agents/stock_deep_dive/precious_metals/test_precious_metal_price_agent.py`

Befund (Review D7): `performance={}`, `rsi/ma50/ma200/real_yield_correlation=None` — alles TODO, obwohl 5J-Historie geladen wird. Lösung: Performance (1W/1M/3M/1Y/5Y), Wilder-RSI, MA50/MA200, Signal aus Momentum **aus der geladenen Historie** berechnen; Realzins-Korrelation per Regression Goldpreis vs. 10J-Realzins. Letzteres braucht eine **datierte Realzins-Historie** → neue `MacroDataProvider.get_real_rate_history`. Fehlt sie, bleibt `real_yield_correlation=None`, aber Preis/RSI/MA bleiben AVAILABLE.

Neue Port-Methode:
```python
# core/ports/data_provider.py  (MacroDataProvider)
@abstractmethod
def get_real_rate_history(self, years: int = 5) -> list[dict]:
    """Datierte 10J-Realzins-Reihe (TIPS), älteste zuerst.
    Rückgabe: [{"date": "YYYY-MM-DD", "real_rate_10y": float}, ...]; leer = nicht verfügbar."""
    ...
```

- [ ] **failing Test** — `tests/agents/stock_deep_dive/precious_metals/test_precious_metal_price_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  import pandas as pd
  import pytest

  from agents.stock_deep_dive.precious_metals.precious_metal_price_agent import (
      PreciousMetalPriceAgent, _wilder_rsi, _performance, _price_signal,
  )
  from core.domain.models import Signal, SignalStatus


  def _series(values):
      idx = pd.date_range("2019-06-01", periods=len(values), freq="B")
      return pd.Series(values, index=idx, dtype=float)


  def test_wilder_rsi_all_gains_is_100():
      rsi = _wilder_rsi(_series([i for i in range(1, 60)]), period=14)
      assert rsi > 99.0


  def test_wilder_rsi_all_losses_is_low():
      rsi = _wilder_rsi(_series([60 - i for i in range(50)]), period=14)
      assert rsi < 1.0


  def test_performance_1m():
      s = _series([100.0] * 21 + [110.0])
      perf = _performance(s)
      assert perf["1m"] == pytest.approx(10.0, abs=0.5)


  def test_price_signal_uptrend_not_overbought_is_bullish():
      # Preis über MA200, RSI moderat → bullish
      assert _price_signal(price=2000, ma200=1800, rsi=55) == Signal.BULLISH


  def test_price_signal_below_ma200_is_bearish():
      assert _price_signal(price=1500, ma200=1800, rsi=45) == Signal.BEARISH


  def test_price_signal_overbought_is_neutral():
      assert _price_signal(price=2000, ma200=1800, rsi=82) == Signal.NEUTRAL


  def _make_agent(history, real_rate_hist=None):
      provider = MagicMock()
      provider.get_current_price.return_value = float(history[-1])
      provider.get_price_history.return_value = pd.DataFrame({"Close": _series(history)})
      provider.get_real_rate_history.return_value = real_rate_hist or []
      return PreciousMetalPriceAgent(provider, MagicMock())


  def test_run_fills_rsi_ma_performance():
      agent = _make_agent([float(1500 + i) for i in range(300)])
      result = asyncio.run(agent.run("gold"))
      assert result.rsi is not None
      assert result.ma50 is not None
      assert result.ma200 is not None
      assert "1m" in result.performance
      assert result.status == SignalStatus.AVAILABLE


  def test_real_yield_correlation_none_when_no_history():
      agent = _make_agent([float(1500 + i) for i in range(300)], real_rate_hist=[])
      result = asyncio.run(agent.run("gold"))
      assert result.real_yield_correlation is None
      # Preis/RSI/MA trotzdem vorhanden
      assert result.status == SignalStatus.AVAILABLE


  def test_negative_real_yield_correlation_when_inverse():
      # Goldpreis steigt, Realzins fällt → negative Korrelation
      n = 300
      prices = [float(1500 + i) for i in range(n)]
      dates = pd.date_range("2019-06-01", periods=n, freq="B")
      rr = [{"date": d.strftime("%Y-%m-%d"), "real_rate_10y": float(2.0 - i * 0.005)}
            for i, d in enumerate(dates)]
      agent = _make_agent(prices, real_rate_hist=rr)
      result = asyncio.run(agent.run("gold"))
      assert result.real_yield_correlation is not None
      assert result.real_yield_correlation < -0.5
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/precious_metals/test_precious_metal_price_agent.py`
- [ ] **Port-Methode ergänzen** — `core/ports/data_provider.py`: `get_real_rate_history` in `MacroDataProvider` (Signatur oben). In `adapters/data/fred_api.py` implementieren (FRED-Serie `DFII10` = 10J-TIPS-Realzins; datiert, monatlich resampled). Stub-Adapter (`ecb_snb_stub.py`) liefert `[]`.
- [ ] **echte Implementierung** — `agents/stock_deep_dive/precious_metals/precious_metal_price_agent.py` neu:
  ```python
  import asyncio

  from core.domain.events import PreciousMetalDataReady
  from core.domain.models import PreciousMetalSnapshot, Signal, SignalStatus
  from core.ports.data_provider import MacroDataProvider, MarketDataProvider
  from core.ports.event_bus import EventBus

  METAL_TICKERS = {"gold": "GC=F", "silver": "SI=F", "platinum": "PL=F", "palladium": "PA=F"}

  # S2F einheitlich definiert als: oberirdische Bestände / Jahresproduktion (Jahre).
  # Quelle/Definition siehe supply_demand_agent (systemweit konsistent, Review D7).
  STOCK_TO_FLOW = {"gold": 62.0, "silver": 22.0, "platinum": 0.4, "palladium": 0.5}

  _DEFAULT = PreciousMetalSnapshot(
      metal="unknown", price_usd=None, performance={}, rsi=None, ma50=None, ma200=None,
      stock_to_flow=None, real_yield_correlation=None,
      signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
  )

  _PERF_WINDOWS = {"1w": 5, "1m": 21, "3m": 63, "1y": 252, "5y": 252 * 5}


  def _wilder_rsi(close: "object", period: int = 14) -> float | None:
      delta = close.diff().dropna()
      if len(delta) < period:
          return None
      gain = delta.clip(lower=0.0)
      loss = (-delta).clip(lower=0.0)
      avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
      avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
      if avg_loss == 0:
          return 100.0
      rs = avg_gain / avg_loss
      return round(100 - 100 / (1 + rs), 2)


  def _performance(close: "object") -> dict[str, float]:
      out: dict[str, float] = {}
      now = float(close.iloc[-1])
      for label, n in _PERF_WINDOWS.items():
          if len(close) > n:
              past = float(close.iloc[-(n + 1)])
              if past != 0:
                  out[label] = round((now - past) / abs(past) * 100, 2)
      return out


  def _price_signal(price: float | None, ma200: float | None, rsi: float | None) -> Signal:
      if price is None or ma200 is None:
          return Signal.NEUTRAL
      if price > ma200 and (rsi is None or rsi < 70):
          return Signal.BULLISH
      if price < ma200:
          return Signal.BEARISH
      return Signal.NEUTRAL


  def _real_yield_correlation(close: "object", rr_history: list[dict]) -> float | None:
      import pandas as pd
      if not rr_history or len(rr_history) < 30:
          return None
      rr = pd.Series(
          {pd.Timestamp(r["date"]): float(r["real_rate_10y"]) for r in rr_history}
      ).sort_index()
      px = close.copy()
      px.index = pd.to_datetime(px.index).tz_localize(None)
      joined = pd.concat([px.rename("px"), rr.rename("rr")], axis=1).dropna()
      if len(joined) < 30:
          return None
      corr = joined["px"].pct_change().dropna().corr(joined["rr"].diff().dropna())
      return None if corr != corr else round(float(corr), 3)


  class PreciousMetalPriceAgent:
      def __init__(self, provider: MarketDataProvider, bus: EventBus, macro: MacroDataProvider | None = None):
          self.provider = provider
          self.bus = bus
          self.macro = macro

      async def run(self, metal: str) -> PreciousMetalSnapshot:
          ticker = METAL_TICKERS.get(metal.lower())
          if not ticker:
              return _DEFAULT

          price, hist = await asyncio.gather(
              asyncio.to_thread(self.provider.get_current_price, ticker),
              asyncio.to_thread(self.provider.get_price_history, ticker, "5y"),
              return_exceptions=True,
          )
          price = None if isinstance(price, Exception) else price
          hist  = None if isinstance(hist, Exception) else hist
          if hist is None or "Close" not in getattr(hist, "columns", []):
              return PreciousMetalSnapshot(
                  metal=metal, price_usd=price, performance={}, rsi=None, ma50=None, ma200=None,
                  stock_to_flow=STOCK_TO_FLOW.get(metal.lower()),
                  real_yield_correlation=None, signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
              )

          close = hist["Close"].dropna()
          rsi   = _wilder_rsi(close)
          ma50  = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else None
          ma200 = round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None
          perf  = _performance(close)
          ref_price = price if price is not None else float(close.iloc[-1])

          rr_corr = None
          if self.macro is not None:
              rr_hist = await asyncio.to_thread(self.macro.get_real_rate_history, 5)
              rr_corr = _real_yield_correlation(close, rr_hist)

          result = PreciousMetalSnapshot(
              metal=metal, price_usd=price, performance=perf, rsi=rsi, ma50=ma50, ma200=ma200,
              stock_to_flow=STOCK_TO_FLOW.get(metal.lower()),
              real_yield_correlation=rr_corr,
              signal=_price_signal(ref_price, ma200, rsi),
              status=SignalStatus.AVAILABLE,
          )
          self.bus.publish(PreciousMetalDataReady(source="precious_metal_price_agent", payload={
              "metal": metal, "price_usd": price,
          }))
          return result

      @staticmethod
      def default(metal: str = "gold") -> PreciousMetalSnapshot:
          return PreciousMetalSnapshot(
              metal=metal, price_usd=None, performance={}, rsi=None, ma50=None, ma200=None,
              stock_to_flow=STOCK_TO_FLOW.get(metal, None),
              real_yield_correlation=None, signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
          )
  ```
  > **Self-Review:** `macro` ist optional, damit der bestehende Konstruktor-Aufruf (`provider, bus`) nicht bricht. Der PM-Chief sollte den Macro-Provider injizieren (Plan D2). Ohne ihn bleibt nur `real_yield_correlation=None`; alle anderen Felder sind vorhanden → Status bleibt AVAILABLE (der zentrale Momentum-Output existiert).
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/precious_metals/test_precious_metal_price_agent.py`
- [ ] **Commit** — `feat(precious_metal_price): RSI/MA/Performance aus Historie + Realzins-Korrelation (Review D7); + MacroDataProvider.get_real_rate_history`

---

### Task 4 — `commodity_valuation_range_agent`: echtes Perzentil, reale Preise, Cost-Curve

**Files:** `agents/stock_deep_dive/commodity/commodity_valuation_range_agent.py`, `core/ports/data_provider.py`, `tests/agents/stock_deep_dive/commodity/test_commodity_valuation_range_agent.py`

Befund (Review D7 / Teil B 4.3): `_percentile` ist Min-Max-Spanne, kein Rang-Perzentil; nominal; `production_cost_low/high=None`. Lösung: `percentile_rank` (Plan 0, winsorisiert), reale Preise via `to_real` (Plan 0), Cost-Curve-Anker via neuem `CommoditySupplyProvider.get_production_cost_curve`.

Neuer Port (eigenes Modul, da nicht markt-/macro-spezifisch):
```python
# core/ports/data_provider.py
class CommoditySupplyProvider(ABC):
    @abstractmethod
    def get_inventory_history(self, commodity: str, years: int = 5) -> list[dict]:
        """[{"date": "YYYY-MM-DD", "inventory": float}], älteste zuerst; leer = nicht verfügbar."""
        ...

    @abstractmethod
    def get_production_cost_curve(self, commodity: str) -> dict:
        """{"cost_p25","cost_p50","cost_p75","cost_p90"} in Preiseinheit des Tickers; leer = nicht verfügbar."""
        ...
```

- [ ] **failing Test** — `tests/agents/stock_deep_dive/commodity/test_commodity_valuation_range_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  import pandas as pd

  from agents.stock_deep_dive.commodity.commodity_valuation_range_agent import (
      CommodityValuationRangeAgent, _position,
  )
  from core.domain.models import Signal, SignalStatus


  def test_position_cheap_below_p20():
      pos, sig = _position(15.0)
      assert pos == "cheap" and sig == Signal.BULLISH


  def test_position_expensive_above_p80():
      pos, sig = _position(88.0)
      assert pos == "expensive" and sig == Signal.BEARISH


  def test_outlier_spike_does_not_make_current_look_cheap():
      # Ein einzelner Spike (1000) darf den aktuellen Preis (50) nicht als billig ausweisen
      values = [40.0, 45.0, 50.0, 48.0, 52.0, 1000.0]
      hist = pd.DataFrame({"Close": pd.Series(values * 50)})  # current = 1000 am Ende? -> setze explizit
      hist = pd.DataFrame({"Close": pd.Series([40, 45, 50, 48, 52] * 50 + [50.0])})
      provider = MagicMock()
      provider.get_price_history.return_value = hist
      provider.get_inventory_history = MagicMock(return_value=[])
      supply = MagicMock()
      supply.get_production_cost_curve.return_value = {}
      agent = CommodityValuationRangeAgent(provider, MagicMock(), supply=supply)
      result = asyncio.run(agent.run("CL=F"))
      # echtes Rang-Perzentil: 50 liegt im mittleren Bereich, nicht "cheap"
      assert result.position != "cheap"


  def test_cost_curve_anchors_set_when_provider_returns_them():
      hist = pd.DataFrame({"Close": pd.Series([float(50 + i % 10) for i in range(300)])})
      provider = MagicMock()
      provider.get_price_history.return_value = hist
      supply = MagicMock()
      supply.get_production_cost_curve.return_value = {
          "cost_p25": 40.0, "cost_p50": 48.0, "cost_p75": 55.0, "cost_p90": 62.0,
      }
      agent = CommodityValuationRangeAgent(provider, MagicMock(), supply=supply)
      result = asyncio.run(agent.run("CL=F"))
      assert result.production_cost_low == 40.0
      assert result.production_cost_high == 62.0
      assert result.status == SignalStatus.AVAILABLE


  def test_no_history_is_unavailable():
      provider = MagicMock()
      provider.get_price_history.return_value = None
      agent = CommodityValuationRangeAgent(provider, MagicMock(), supply=MagicMock())
      result = asyncio.run(agent.run("CL=F"))
      assert result.status == SignalStatus.UNAVAILABLE
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/commodity/test_commodity_valuation_range_agent.py`
- [ ] **Port-Methode ergänzen** — `core/ports/data_provider.py`: `CommoditySupplyProvider` (oben). Konkreter Adapter (`adapters/data/commodity_supply.py`, Stub mit `return []`/`{}`) — wird später an EIA/USDA/LME verdrahtet.
- [ ] **echte Implementierung** — `agents/stock_deep_dive/commodity/commodity_valuation_range_agent.py` neu:
  ```python
  import asyncio

  from core.domain.events import CommodityValuationRangeReady
  from core.domain.models import CommodityValuationRangeSnapshot, Signal, SignalStatus
  from core.ports.data_provider import CommoditySupplyProvider, MarketDataProvider
  from core.ports.event_bus import EventBus
  from core.utils.relative import percentile_rank
  from core.utils.real_nominal import to_real

  _DEFAULT = CommodityValuationRangeSnapshot(
      current_price=None, price_low_5y=None, price_high_5y=None,
      percentile_5y=None, percentile_10y=None,
      production_cost_low=None, production_cost_high=None,
      position="fair", signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
  )


  def _position(pct: float) -> tuple[str, Signal]:
      if pct < 20:
          return "cheap", Signal.BULLISH
      if pct > 80:
          return "expensive", Signal.BEARISH
      return "fair", Signal.NEUTRAL


  def _percentile_of(close: "object") -> tuple[float, float, float, float]:
      current = float(close.iloc[-1])
      hist = [float(x) for x in close.iloc[:-1]]
      pct = percentile_rank(current, hist, winsorize=0.05)
      return current, pct, round(float(close.min()), 2), round(float(close.max()), 2)


  class CommodityValuationRangeAgent:
      def __init__(self, market: MarketDataProvider, bus: EventBus,
                   supply: CommoditySupplyProvider | None = None):
          self.market = market
          self.bus = bus
          self.supply = supply

      async def run(self, ticker: str) -> CommodityValuationRangeSnapshot:
          hist5y, hist10y = await asyncio.gather(
              asyncio.to_thread(self.market.get_price_history, ticker, "5y"),
              asyncio.to_thread(self.market.get_price_history, ticker, "10y"),
              return_exceptions=True,
          )
          if isinstance(hist5y, Exception) or hist5y is None or "Close" not in getattr(hist5y, "columns", []):
              return _DEFAULT

          close5 = hist5y["Close"].dropna()
          # Nominale Preise. Reale CPI-Deflation ist als Folge-Task ausgelagert (benötigt eine an die
          # Preisdaten ausgerichtete CPI-Index-Serie). Der P4.3-Kernfix ist das echte Rang-Perzentil unten.
          current, pct5y, low5y, high5y = _percentile_of(close5)

          pct10y = None
          if not isinstance(hist10y, Exception) and hist10y is not None and "Close" in getattr(hist10y, "columns", []):
              close10 = hist10y["Close"].dropna()  # nominal; reale Deflation = Folge-Task
              _, pct10y, _, _ = _percentile_of(close10)

          cost_low = cost_high = None
          if self.supply is not None:
              curve = await asyncio.to_thread(self.supply.get_production_cost_curve, ticker)
              if curve:
                  cost_low = curve.get("cost_p25")
                  cost_high = curve.get("cost_p90")

          pos, sig = _position(pct5y)
          result = CommodityValuationRangeSnapshot(
              current_price=round(current, 2),
              price_low_5y=low5y, price_high_5y=high5y,
              percentile_5y=round(pct5y, 1), percentile_10y=round(pct10y, 1) if pct10y is not None else None,
              production_cost_low=cost_low, production_cost_high=cost_high,
              position=pos, signal=sig, status=SignalStatus.AVAILABLE,
          )
          self.bus.publish(CommodityValuationRangeReady(
              source="commodity_valuation_range_agent", payload={"ticker": ticker},
          ))
          return result

      @staticmethod
      def default() -> CommodityValuationRangeSnapshot:
          return _DEFAULT
  ```
  > **Self-Review (aufgelöst):** Plan 0's `to_real(nominal_rate, inflation)` ist **skalar** (Renditen/Wachstum in Prozentpunkten) und kann **keine Preis-Reihe** deflationieren — daher arbeitet dieser Agent auf **nominalen** Preisen. Der P4.3-Kernfix (echtes Rang-Perzentil via `percentile_rank`) ist davon unberührt; der Wrapper-Test (`test_outlier_spike…`) prüft nur die Perzentil-Robustheit und bleibt grün. Reale CPI-Deflation ist ein klar abgegrenzter Folge-Task (separater Reihen-Helfer + an die Preisdaten ausgerichtete CPI-Index-Serie).
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/commodity/test_commodity_valuation_range_agent.py`
- [ ] **Commit** — `feat(commodity_valuation_range): echtes Perzentil + reale Preise + Cost-Curve-Anker (Review D7, P4.3); + CommoditySupplyProvider`

---

### Task 5 — `cot_agent`: CFTC-COT-Index (Managed Money, 0–100)

**Files:** `agents/stock_deep_dive/commodity/cot_agent.py`, `core/ports/data_provider.py`, `adapters/data/cftc_cot.py` (neu), `tests/agents/stock_deep_dive/commodity/test_cot_agent.py`

Befund (Review D7): reiner Stub; absolute asymmetrische Schwellen. Lösung: CFTC-Disaggregated-COT (Managed Money) anbinden; **COT-Index** (aktuelle Netto-Position normalisiert auf eigenes 1–3J-Min/Max via `percentile_rank`); konträr: Index ≥80 → bearish, ≤20 → bullish. Fehlt die Quelle → UNAVAILABLE.

Neuer Port:
```python
# core/ports/data_provider.py
class COTProvider(ABC):
    @abstractmethod
    def get_cot_history(self, commodity: str, years: int = 3) -> list[dict]:
        """[{"date","managed_money_net","open_interest"}], älteste zuerst; leer = nicht verfügbar."""
        ...
```

- [ ] **failing Test** — `tests/agents/stock_deep_dive/commodity/test_cot_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  from agents.stock_deep_dive.commodity.cot_agent import COTAgent, _cot_signal
  from core.domain.models import Signal, SignalStatus


  def test_index_high_is_contrarian_bearish():
      assert _cot_signal(cot_index=90.0) == Signal.BEARISH


  def test_index_low_is_contrarian_bullish():
      assert _cot_signal(cot_index=10.0) == Signal.BULLISH


  def test_index_mid_is_neutral():
      assert _cot_signal(cot_index=50.0) == Signal.NEUTRAL


  def _hist(nets):
      return [{"date": f"2024-{(i % 12) + 1:02d}-01", "managed_money_net": n, "open_interest": 1000}
              for i, n in enumerate(nets)]


  def test_run_computes_index_and_available():
      provider = MagicMock()
      # aktuelle Netto-Long am Maximum → COT-Index ~100 → bearish
      provider.get_cot_history.return_value = _hist([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 200])
      agent = COTAgent(provider, MagicMock())
      result = asyncio.run(agent.run("gold"))
      assert result.status == SignalStatus.AVAILABLE
      assert result.signal == Signal.BEARISH


  def test_run_unavailable_when_no_data():
      provider = MagicMock()
      provider.get_cot_history.return_value = []
      agent = COTAgent(provider, MagicMock())
      result = asyncio.run(agent.run("gold"))
      assert result.status == SignalStatus.UNAVAILABLE
      assert result.signal == Signal.NEUTRAL
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/commodity/test_cot_agent.py`
- [ ] **Port + Adapter** — `core/ports/data_provider.py`: `COTProvider` (oben). `adapters/data/cftc_cot.py` (neu): lädt CFTC-Disaggregated-Wochenreport (CSV, `https://www.cftc.gov/files/dea/history/...`), filtert auf den Commodity-Kontrakt, gibt `managed_money_net = MM_long − MM_short` je Woche zurück. Bei Netzfehler `return []`.
- [ ] **echte Implementierung** — `agents/stock_deep_dive/commodity/cot_agent.py` neu:
  ```python
  from core.domain.events import COTReady
  from core.domain.models import COTSnapshot, Signal, SignalStatus
  from core.ports.data_provider import COTProvider
  from core.ports.event_bus import EventBus
  from core.utils.relative import percentile_rank
  import asyncio

  _DEFAULT = COTSnapshot(
      net_speculative_long=None, net_speculative_pct_oi=None,
      signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
  )

  _HIGH = 80.0
  _LOW  = 20.0


  def _cot_signal(cot_index: float) -> Signal:
      # konträr: extreme Long-Positionierung der Spekulanten → bearish
      if cot_index >= _HIGH:
          return Signal.BEARISH
      if cot_index <= _LOW:
          return Signal.BULLISH
      return Signal.NEUTRAL


  class COTAgent:
      def __init__(self, provider: COTProvider, bus: EventBus):
          self.provider = provider
          self.bus = bus

      async def run(self, commodity: str) -> COTSnapshot:
          history = await asyncio.to_thread(self.provider.get_cot_history, commodity, 3)
          if not history or len(history) < 26:
              self.bus.publish(COTReady(source="cot_agent", payload={"commodity": commodity}))
              return _DEFAULT

          nets = [float(h["managed_money_net"]) for h in history]
          current = nets[-1]
          cot_index = percentile_rank(current, nets[:-1])
          last = history[-1]
          oi = float(last.get("open_interest") or 0)
          pct_oi = round(current / oi * 100, 2) if oi else None

          result = COTSnapshot(
              net_speculative_long=round(current, 1),
              net_speculative_pct_oi=pct_oi,
              signal=_cot_signal(cot_index),
              status=SignalStatus.AVAILABLE,
          )
          self.bus.publish(COTReady(source="cot_agent", payload={"commodity": commodity}))
          return result

      @staticmethod
      def default() -> COTSnapshot:
          return _DEFAULT
  ```
  > **Self-Review:** Konstruktor-Signatur ändert sich (`bus` → `provider, bus`). Der PM-Chief verdrahtet `cot_signal` aktuell hart als NEUTRAL (Review D7) — in Plan D2 den COTAgent korrekt verkabeln. Bis dahin nutzt der bestehende Aufruf den neuen Konstruktor; betroffene Aufrufstellen mit Grep prüfen und anpassen.
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/commodity/test_cot_agent.py`
- [ ] **Commit** — `feat(cot): CFTC-COT-Index (Managed Money, 0–100 konträr) statt Stub (Review D7); + COTProvider + cftc_cot-Adapter`

---

### Task 6 — `supply_demand_agent`: echte Lagerbalancen + einheitliche S2F-Definition

**Files:** `agents/stock_deep_dive/commodity/supply_demand_agent.py`, `tests/agents/stock_deep_dive/commodity/test_supply_demand_agent.py`

Befund (Review D7): `inventory_*`/`production_change_yoy=None` → Signal immer NEUTRAL; zwei inkonsistente S2F-Definitionen. Lösung: echte Lagerhistorie via `CommoditySupplyProvider.get_inventory_history` (aus Task 4) → `inventory_current`, `inventory_avg_5y`, `inventory_pct_vs_avg`; Signal aus Lager vs. 5J-Schnitt. S2F bleibt als **Kontext-Label** mit der **einheitlichen** Definition „oberirdische Bestände / Jahresproduktion" (konsistent mit `precious_metal_price`); die alten, falschen Industrie-S2F-Werte werden entfernt und durch `None` ersetzt, wo keine belastbare Definition existiert. Fehlt die Lagerquelle → UNAVAILABLE.

- [ ] **failing Test** — `tests/agents/stock_deep_dive/commodity/test_supply_demand_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  from agents.stock_deep_dive.commodity.supply_demand_agent import (
      SupplyDemandAgent, _signal, _inventory_stats,
  )
  from core.domain.models import Signal, SignalStatus


  def test_low_inventory_is_bullish():
      assert _signal(pct_vs_avg=-15.0) == Signal.BULLISH


  def test_high_inventory_is_bearish():
      assert _signal(pct_vs_avg=25.0) == Signal.BEARISH


  def test_normal_inventory_is_neutral():
      assert _signal(pct_vs_avg=5.0) == Signal.NEUTRAL


  def test_inventory_stats_computes_pct_vs_avg():
      hist = [{"date": f"2020-{(i % 12) + 1:02d}-01", "inventory": 100.0} for i in range(60)]
      hist.append({"date": "2025-01-01", "inventory": 80.0})
      cur, avg5, pct = _inventory_stats(hist)
      assert cur == 80.0
      assert pct < 0  # aktuell unter dem 5J-Schnitt


  def test_run_unavailable_without_inventory():
      supply = MagicMock()
      supply.get_inventory_history.return_value = []
      agent = SupplyDemandAgent(supply, MagicMock())
      result = asyncio.run(agent.run("CL=F"))
      assert result.status == SignalStatus.UNAVAILABLE
      assert result.signal == Signal.NEUTRAL


  def test_run_available_with_inventory():
      supply = MagicMock()
      hist = [{"date": f"2020-{(i % 12) + 1:02d}-01", "inventory": 100.0} for i in range(60)]
      hist.append({"date": "2025-01-01", "inventory": 70.0})
      supply.get_inventory_history.return_value = hist
      agent = SupplyDemandAgent(supply, MagicMock())
      result = asyncio.run(agent.run("CL=F"))
      assert result.status == SignalStatus.AVAILABLE
      assert result.signal == Signal.BULLISH
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/commodity/test_supply_demand_agent.py`
- [ ] **echte Implementierung** — `agents/stock_deep_dive/commodity/supply_demand_agent.py` neu:
  ```python
  import asyncio

  from core.domain.events import SupplyDemandReady
  from core.domain.models import SupplyDemandSnapshot, Signal, SignalStatus
  from core.ports.data_provider import CommoditySupplyProvider
  from core.ports.event_bus import EventBus

  _DEFAULT = SupplyDemandSnapshot(
      inventory_current=None, inventory_avg_5y=None, inventory_pct_vs_avg=None,
      production_change_yoy=None, stock_to_flow=None, stock_to_flow_signal=None,
      signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
  )

  # Einheitliche S2F-Definition: oberirdische Bestände / Jahresproduktion (Jahre).
  # Nur dort gesetzt, wo diese Definition belastbar ist (Edelmetalle). Industrie-/Energie-
  # Rohstoffe: kein vergleichbarer S2F → None (Lagerreichweite ist dort das relevante Maß).
  _STOCK_TO_FLOW: dict[str, float] = {
      "GC=F": 62.0, "SI=F": 22.0,   # Gold/Silber (konsistent mit precious_metal_price)
  }

  _SCARCE_THRESHOLD = 10.0


  def _stf_label(stf: float | None) -> str | None:
      if stf is None:
          return None
      return "scarce" if stf >= _SCARCE_THRESHOLD else "normal"


  def _inventory_stats(history: list[dict]) -> tuple[float | None, float | None, float | None]:
      if not history:
          return None, None, None
      vals = [float(h["inventory"]) for h in history if h.get("inventory") is not None]
      if len(vals) < 12:
          return None, None, None
      current = vals[-1]
      avg5 = sum(vals) / len(vals)
      pct = round((current - avg5) / avg5 * 100, 1) if avg5 else None
      return round(current, 1), round(avg5, 1), pct


  def _signal(pct_vs_avg: float | None) -> Signal:
      if pct_vs_avg is None:
          return Signal.NEUTRAL
      if pct_vs_avg < -10:
          return Signal.BULLISH
      if pct_vs_avg > 20:
          return Signal.BEARISH
      return Signal.NEUTRAL


  class SupplyDemandAgent:
      def __init__(self, supply: CommoditySupplyProvider, bus: EventBus):
          self.supply = supply
          self.bus = bus

      async def run(self, ticker: str) -> SupplyDemandSnapshot:
          history = await asyncio.to_thread(self.supply.get_inventory_history, ticker, 5)
          current, avg5, pct = _inventory_stats(history)
          stf = _STOCK_TO_FLOW.get(ticker)

          if pct is None:
              result = SupplyDemandSnapshot(
                  inventory_current=None, inventory_avg_5y=None, inventory_pct_vs_avg=None,
                  production_change_yoy=None, stock_to_flow=stf, stock_to_flow_signal=_stf_label(stf),
                  signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
              )
          else:
              result = SupplyDemandSnapshot(
                  inventory_current=current, inventory_avg_5y=avg5, inventory_pct_vs_avg=pct,
                  production_change_yoy=None, stock_to_flow=stf, stock_to_flow_signal=_stf_label(stf),
                  signal=_signal(pct), status=SignalStatus.AVAILABLE,
              )
          self.bus.publish(SupplyDemandReady(source="supply_demand_agent", payload={"ticker": ticker}))
          return result

      @staticmethod
      def default() -> SupplyDemandSnapshot:
          return _DEFAULT
  ```
  > **Self-Review:** Konstruktor wechselt von `bus` zu `supply, bus`. `production_change_yoy` bleibt vorerst `None` (Produktions-API noch nicht angebunden) — beeinflusst das Signal nicht, das nur auf Lagerbalance beruht; mit Lager-Daten ist der Agent AVAILABLE. Aufrufstellen per Grep anpassen.
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/commodity/test_supply_demand_agent.py`
- [ ] **Commit** — `feat(supply_demand): echte Lagerbalancen + einheitliche S2F-Definition (Review D7)`

---

### Task 7 — `seasonality_agent`: längere Historie, t-Test-Signifikanz, Median, real

**Files:** `agents/stock_deep_dive/commodity/seasonality_agent.py`, `tests/agents/stock_deep_dive/commodity/test_seasonality_agent.py`

Befund (Review D7): 10J → ≤10 Beobachtungen/Monat, Mindestfilter `<3` zu lax, kein Signifikanztest; arithmetisches Mittel; nominal. Lösung: 20J-Historie laden; **Median** statt Mittel; **t-Test gegen 0** (nur signifikante Monatsbias als Signal, sonst NEUTRAL); höhere Mindest-N (≥15); reale Preise via `to_real`. Saisonalität bleibt ein klein gewichteter Tilt (Status AVAILABLE nur bei signifikantem Befund **und** ausreichender N; sonst NEUTRAL/AVAILABLE — die Datenlage ist da, das Signal ist nur „kein Bias").

- [ ] **failing Test** — `tests/agents/stock_deep_dive/commodity/test_seasonality_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  import pandas as pd

  from agents.stock_deep_dive.commodity.seasonality_agent import (
      SeasonalityAgent, _signal, _significant,
  )
  from core.domain.models import Signal, SignalStatus


  def test_significant_positive_bias_is_bullish():
      # klar positiver, signifikanter Monatsbias
      returns = [3.0, 3.2, 2.8, 3.1, 2.9, 3.0, 3.3, 2.7, 3.0, 3.1, 2.8, 3.2, 3.0, 2.9, 3.1, 3.0]
      assert _signal(returns) == Signal.BULLISH


  def test_insignificant_bias_is_neutral():
      # hohe Streuung, Median nahe 0 → nicht signifikant → NEUTRAL
      returns = [10.0, -9.0, 8.0, -11.0, 9.0, -8.0, 7.0, -10.0, 6.0, -7.0, 5.0, -6.0, 4.0, -5.0, 3.0, -4.0]
      assert _signal(returns) == Signal.NEUTRAL


  def test_too_few_observations_is_neutral():
      assert _signal([3.0, 3.1, 2.9]) == Signal.NEUTRAL


  def test_significance_helper():
      assert _significant([3.0] * 16) is True
      assert _significant([0.1, -0.1] * 8) is False


  def test_run_unavailable_when_history_short():
      provider = MagicMock()
      provider.get_price_history.return_value = pd.DataFrame(
          {"Close": pd.Series([100.0, 101.0, 102.0])}
      )
      agent = SeasonalityAgent(provider, MagicMock())
      result = asyncio.run(agent.run("ZW=F"))
      assert result.status == SignalStatus.UNAVAILABLE
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/commodity/test_seasonality_agent.py`
- [ ] **echte Implementierung** — `agents/stock_deep_dive/commodity/seasonality_agent.py` neu:
  ```python
  import asyncio
  import statistics as _stats
  from datetime import datetime

  from core.domain.events import SeasonalityReady
  from core.domain.models import SeasonalitySnapshot, Signal, SignalStatus
  from core.ports.data_provider import MarketDataProvider
  from core.ports.event_bus import EventBus
  from core.utils.real_nominal import to_real

  _DEFAULT = SeasonalitySnapshot(
      current_month_bias="neutral", avg_return_this_month=None, positive_years_pct=None,
      signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
  )

  _MIN_N = 15          # mind. 15 Jahresbeobachtungen für den Monat
  _T_CRITICAL = 2.0    # ~95 % zweiseitig bei df>30; konservativ


  def _t_stat(returns: list[float]) -> float:
      n = len(returns)
      if n < 2:
          return 0.0
      mean = _stats.fmean(returns)
      sd = _stats.pstdev(returns)
      if sd == 0:
          return 0.0
      return mean / (sd / (n ** 0.5))


  def _significant(returns: list[float]) -> bool:
      return len(returns) >= _MIN_N and abs(_t_stat(returns)) >= _T_CRITICAL


  def _signal(returns: list[float]) -> Signal:
      if not _significant(returns):
          return Signal.NEUTRAL
      median = _stats.median(returns)
      if median > 0:
          return Signal.BULLISH
      if median < 0:
          return Signal.BEARISH
      return Signal.NEUTRAL


  def _bias(median: float | None) -> str:
      if median is None:
          return "neutral"
      return "bullish" if median > 1.0 else ("bearish" if median < -1.0 else "neutral")


  class SeasonalityAgent:
      def __init__(self, market: MarketDataProvider, bus: EventBus):
          self.market = market
          self.bus = bus

      async def run(self, ticker: str) -> SeasonalitySnapshot:
          hist = await asyncio.to_thread(self.market.get_price_history, ticker, "20y")
          if hist is None or "Close" not in getattr(hist, "columns", []):
              self.bus.publish(SeasonalityReady(source="seasonality_agent", payload={"ticker": ticker}))
              return _DEFAULT

          close = hist["Close"].dropna()  # nominal; reale CPI-Deflation als Folge-Task
          monthly = close.resample("ME").last()
          monthly_returns = monthly.pct_change().dropna() * 100
          current_month = datetime.utcnow().month
          same_month = monthly_returns[monthly_returns.index.month == current_month]
          returns = [float(x) for x in same_month]

          if len(returns) < _MIN_N:
              self.bus.publish(SeasonalityReady(source="seasonality_agent", payload={"ticker": ticker}))
              return _DEFAULT

          median = round(_stats.median(returns), 2)
          pos_pct = round(sum(1 for r in returns if r > 0) / len(returns) * 100, 1)
          result = SeasonalitySnapshot(
              current_month_bias=_bias(median),
              avg_return_this_month=median,   # Median statt arithm. Mittel
              positive_years_pct=pos_pct,
              signal=_signal(returns),
              status=SignalStatus.AVAILABLE,
          )
          self.bus.publish(SeasonalityReady(source="seasonality_agent", payload={"ticker": ticker}))
          return result

      @staticmethod
      def default() -> SeasonalitySnapshot:
          return _DEFAULT
  ```
  > **Self-Review:** `avg_return_this_month` trägt nun den **Median** (Feldname aus Plan-übergreifender Kompatibilität beibehalten; Semantik in Kommentar dokumentiert). `_significant` als eigene Funktion testbar. `robust_z_score` (Plan 0) wird hier nicht zwingend benötigt, der t-Test deckt die Signifikanz ab; optional könnte der Median-Bias zusätzlich gegen `robust_z_score` der Monatsverteilung geprüft werden — als Folge-Verfeinerung notiert.
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/commodity/test_seasonality_agent.py`
- [ ] **Commit** — `feat(seasonality): 20J-Historie + t-Test-Signifikanz + Median + reale Preise (Review D7)`

---

### Task 8 — `index_breadth_agent`: echte Breadth aus Konstituenten

**Files:** `agents/stock_deep_dive/index/index_breadth_agent.py`, `core/ports/data_provider.py`, `adapters/data/yahoo_finance.py`, `tests/agents/stock_deep_dive/index/test_index_breadth_agent.py`

Befund (Review D6): reiner Stub. Lösung: % über MA200 der Konstituenten, Advance/Decline-Ratio, New-High/Low-Zählung — aus den Konstituenten-Historien. Braucht zwei neue Port-Methoden.

Neue Port-Methoden:
```python
# core/ports/data_provider.py  (MarketDataProvider)
@abstractmethod
def get_index_constituents(self, index_ticker: str) -> list[str]:
    """Konstituenten-Ticker des Index; leer = unbekannt."""
    ...

@abstractmethod
def get_constituent_histories(self, index_ticker: str, period: str = "2y") -> dict:
    """{ticker: Close-pandas.Series} der Konstituenten; leer = unbekannt."""
    ...
```

- [ ] **failing Test** — `tests/agents/stock_deep_dive/index/test_index_breadth_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  import pandas as pd

  from agents.stock_deep_dive.index.index_breadth_agent import (
      IndexBreadthAgent, _signal, _breadth,
  )
  from core.domain.models import Signal, SignalStatus


  def _series(values):
      idx = pd.date_range("2022-01-03", periods=len(values), freq="B")
      return pd.Series(values, index=idx, dtype=float)


  def test_signal_high_breadth_is_bullish():
      assert _signal(pct_above_ma200=75.0) == Signal.BULLISH


  def test_signal_low_breadth_is_bearish():
      assert _signal(pct_above_ma200=25.0) == Signal.BEARISH


  def test_signal_mid_breadth_is_neutral():
      assert _signal(pct_above_ma200=50.0) == Signal.NEUTRAL


  def test_breadth_counts_above_ma200():
      # 2 von 3 Titeln über ihrer MA200
      up = _series([float(100 + i) for i in range(260)])         # steigend → über MA200
      up2 = _series([float(100 + i) for i in range(260)])
      down = _series([float(360 - i) for i in range(260)])        # fallend → unter MA200
      stats = _breadth({"A": up, "B": up2, "C": down})
      assert stats["pct_above_ma200"] > 60.0
      assert stats["advance_decline_ratio"] is not None


  def test_run_unavailable_when_no_constituents():
      provider = MagicMock()
      provider.get_constituent_histories.return_value = {}
      agent = IndexBreadthAgent(provider, MagicMock())
      result = asyncio.run(agent.run("^GSPC"))
      assert result.status == SignalStatus.UNAVAILABLE
      assert result.signal == Signal.NEUTRAL


  def test_run_available_with_constituents():
      provider = MagicMock()
      up = _series([float(100 + i) for i in range(260)])
      provider.get_constituent_histories.return_value = {"A": up, "B": up, "C": up}
      agent = IndexBreadthAgent(provider, MagicMock())
      result = asyncio.run(agent.run("^GSPC"))
      assert result.status == SignalStatus.AVAILABLE
      assert result.signal == Signal.BULLISH
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/index/test_index_breadth_agent.py`
- [ ] **Port + Adapter** — `core/ports/data_provider.py`: beide Methoden in `MarketDataProvider`. `adapters/data/yahoo_finance.py`: `get_index_constituents` (statische Mapping-Tabelle der Hauptindizes auf bekannte Konstituenten oder ETF-Holdings-Fallback; leer falls unbekannt) und `get_constituent_histories` (yfinance Batch-Download `yf.download(tickers, period=...)`). Bei Fehler `{}`/`[]`.
- [ ] **echte Implementierung** — `agents/stock_deep_dive/index/index_breadth_agent.py` neu:
  ```python
  import asyncio

  from core.domain.events import IndexBreadthReady
  from core.domain.models import IndexBreadthSnapshot, Signal, SignalStatus
  from core.ports.data_provider import MarketDataProvider
  from core.ports.event_bus import EventBus

  _DEFAULT = IndexBreadthSnapshot(
      pct_above_ma50=None, pct_above_ma200=None, advance_decline_ratio=None,
      new_highs=None, new_lows=None, signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
  )


  def _signal(pct_above_ma200: float | None) -> Signal:
      if pct_above_ma200 is None:
          return Signal.NEUTRAL
      if pct_above_ma200 > 70:
          return Signal.BULLISH
      if pct_above_ma200 < 30:
          return Signal.BEARISH
      return Signal.NEUTRAL


  def _breadth(histories: dict) -> dict:
      above50 = above200 = advancers = decliners = new_high = new_low = total = 0
      for series in histories.values():
          s = series.dropna()
          if len(s) < 200:
              continue
          total += 1
          last = float(s.iloc[-1])
          if last > float(s.rolling(50).mean().iloc[-1]):
              above50 += 1
          if last > float(s.rolling(200).mean().iloc[-1]):
              above200 += 1
          if len(s) >= 2 and last > float(s.iloc[-2]):
              advancers += 1
          elif len(s) >= 2:
              decliners += 1
          window = s.iloc[-252:] if len(s) >= 252 else s
          if last >= float(window.max()):
              new_high += 1
          if last <= float(window.min()):
              new_low += 1
      if total == 0:
          return {}
      return {
          "pct_above_ma50": round(above50 / total * 100, 1),
          "pct_above_ma200": round(above200 / total * 100, 1),
          "advance_decline_ratio": round(advancers / decliners, 2) if decliners else None,
          "new_highs": new_high,
          "new_lows": new_low,
      }


  class IndexBreadthAgent:
      def __init__(self, market: MarketDataProvider, bus: EventBus):
          self.market = market
          self.bus = bus

      async def run(self, ticker: str) -> IndexBreadthSnapshot:
          histories = await asyncio.to_thread(self.market.get_constituent_histories, ticker, "2y")
          stats = _breadth(histories) if histories else {}
          if not stats:
              self.bus.publish(IndexBreadthReady(source="index_breadth_agent", payload={"ticker": ticker}))
              return _DEFAULT
          result = IndexBreadthSnapshot(
              pct_above_ma50=stats["pct_above_ma50"],
              pct_above_ma200=stats["pct_above_ma200"],
              advance_decline_ratio=stats["advance_decline_ratio"],
              new_highs=stats["new_highs"], new_lows=stats["new_lows"],
              signal=_signal(stats["pct_above_ma200"]), status=SignalStatus.AVAILABLE,
          )
          self.bus.publish(IndexBreadthReady(source="index_breadth_agent", payload={"ticker": ticker}))
          return result

      @staticmethod
      def default() -> IndexBreadthSnapshot:
          return _DEFAULT
  ```
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/index/test_index_breadth_agent.py`
- [ ] **Commit** — `feat(index_breadth): echte Breadth (% > MA200, A/D, New-High/Low) statt Stub (Review D6); + Konstituenten-Ports`

---

### Task 9 — `index_earnings_agent`: aggregierte Index-EPS + echte Revisions

**Files:** `agents/stock_deep_dive/index/index_earnings_agent.py`, `core/ports/data_provider.py`, `tests/agents/stock_deep_dive/index/test_index_earnings_agent.py`

Befund (Review D6): `earningsGrowth`/`operatingMargins` aus `get_info` sind Einzelaktien-Felder (auf Index meist `None`); `estimate_revision` ist ein Fwd/Trailing-PE-Proxy (fachlich falsch). Lösung: aggregierte (bottom-up) Index-Kennzahlen + **echte** Estimate-Revision aus neuer Port-Methode. Fehlt sie → UNAVAILABLE.

Neue Port-Methode:
```python
# core/ports/data_provider.py  (MarketDataProvider)
@abstractmethod
def get_index_fundamentals(self, index_ticker: str) -> dict:
    """Aggregierte (bottom-up) Index-Fundamentaldaten:
    {"eps_ttm","eps_fwd","eps_growth_1y","revenue_growth_1y","operating_margin",
     "estimate_revision": "up"|"stable"|"down"}; leeres dict = nicht verfügbar."""
    ...
```

- [ ] **failing Test** — `tests/agents/stock_deep_dive/index/test_index_earnings_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  from agents.stock_deep_dive.index.index_earnings_agent import IndexEarningsAgent, _signal
  from core.domain.models import Signal, SignalStatus


  def test_signal_strong_growth_and_up_revision_is_bullish():
      assert _signal(eps_growth=12.0, revision="up") == Signal.BULLISH


  def test_signal_negative_growth_is_bearish():
      assert _signal(eps_growth=-12.0, revision="stable") == Signal.BEARISH


  def test_signal_down_revision_is_bearish():
      assert _signal(eps_growth=5.0, revision="down") == Signal.BEARISH


  def test_signal_mid_is_neutral():
      assert _signal(eps_growth=5.0, revision="stable") == Signal.NEUTRAL


  def test_run_unavailable_without_index_fundamentals():
      provider = MagicMock()
      provider.get_index_fundamentals.return_value = {}
      agent = IndexEarningsAgent(provider, MagicMock())
      result = asyncio.run(agent.run("^GSPC"))
      assert result.status == SignalStatus.UNAVAILABLE
      assert result.signal == Signal.NEUTRAL


  def test_run_available_with_index_fundamentals():
      provider = MagicMock()
      provider.get_index_fundamentals.return_value = {
          "eps_ttm": 220.0, "eps_fwd": 245.0, "eps_growth_1y": 11.0,
          "revenue_growth_1y": 5.0, "operating_margin": 13.0, "estimate_revision": "up",
      }
      agent = IndexEarningsAgent(provider, MagicMock())
      result = asyncio.run(agent.run("^GSPC"))
      assert result.status == SignalStatus.AVAILABLE
      assert result.signal == Signal.BULLISH
      assert result.estimate_revision == "up"
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/index/test_index_earnings_agent.py`
- [ ] **Port-Methode** — `core/ports/data_provider.py`: `get_index_fundamentals` (oben). Adapter: aus den Konstituenten-Gewinnen aggregieren bzw. FMP `analyst-estimates` für Revisions; Stub liefert `{}`.
- [ ] **echte Implementierung** — `agents/stock_deep_dive/index/index_earnings_agent.py` neu:
  ```python
  import asyncio

  from core.domain.events import IndexEarningsReady
  from core.domain.models import IndexEarningsSnapshot, Signal, SignalStatus
  from core.ports.data_provider import MarketDataProvider
  from core.ports.event_bus import EventBus

  _DEFAULT = IndexEarningsSnapshot(
      eps_growth_1y=None, revenue_growth_1y=None, operating_margin=None,
      estimate_revision="stable", signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
  )


  def _signal(eps_growth: float | None, revision: str) -> Signal:
      if eps_growth is None:
          return Signal.NEUTRAL
      if eps_growth > 10 and revision == "up":
          return Signal.BULLISH
      if eps_growth < -10 or revision == "down":
          return Signal.BEARISH
      return Signal.NEUTRAL


  class IndexEarningsAgent:
      def __init__(self, market: MarketDataProvider, bus: EventBus):
          self.market = market
          self.bus = bus

      async def run(self, ticker: str) -> IndexEarningsSnapshot:
          data = await asyncio.to_thread(self.market.get_index_fundamentals, ticker)
          if not data:
              self.bus.publish(IndexEarningsReady(source="index_earnings_agent", payload={"ticker": ticker}))
              return _DEFAULT

          eps_g = data.get("eps_growth_1y")
          revision = data.get("estimate_revision", "stable")
          result = IndexEarningsSnapshot(
              eps_growth_1y=round(eps_g, 2) if eps_g is not None else None,
              revenue_growth_1y=data.get("revenue_growth_1y"),
              operating_margin=data.get("operating_margin"),
              estimate_revision=revision,
              signal=_signal(eps_g, revision),
              status=SignalStatus.AVAILABLE,
          )
          self.bus.publish(IndexEarningsReady(source="index_earnings_agent", payload={"ticker": ticker}))
          return result

      @staticmethod
      def default() -> IndexEarningsSnapshot:
          return _DEFAULT
  ```
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/index/test_index_earnings_agent.py`
- [ ] **Commit** — `feat(index_earnings): aggregierte Index-EPS + echte Revisions statt Fwd/Trailing-Proxy (Review D6); + get_index_fundamentals`

---

### Task 10 — `index_price_agent`: Total- vs. Price-Return + 52W aus Historie

**Files:** `agents/stock_deep_dive/index/index_price_agent.py`, `core/ports/data_provider.py`, `tests/agents/stock_deep_dive/index/test_index_price_agent.py`

Befund (Review D6 / P4.6): Index-Kurse sind Price-Return → perf_5y unterzeichnet; 52W-High/Low aus `info` (Inkonsistenz + ungenutzt). Lösung: wo verfügbar Total-Return-Historie (neue Port-Methode), sonst Price-Return mit Kennzeichnung; 52W-High/Low aus derselben Historie; Distanz zum 52W-Hoch als Momentum-Input ins Signal.

Neue Port-Methode:
```python
# core/ports/data_provider.py  (MarketDataProvider)
@abstractmethod
def get_total_return_history(self, ticker: str, period: str = "5y") -> object:
    """Total-Return-Historie (Dividenden reinvestiert) als DataFrame mit 'Close';
    None falls nur Price-Return verfügbar (Aufrufer fällt auf get_price_history zurück)."""
    ...
```

- [ ] **failing Test** — `tests/agents/stock_deep_dive/index/test_index_price_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  import pandas as pd

  from agents.stock_deep_dive.index.index_price_agent import IndexPriceAgent, _signal, _52w
  from core.domain.models import Signal, SignalStatus


  def _hist(values):
      idx = pd.date_range("2020-01-02", periods=len(values), freq="B")
      return pd.DataFrame({"Close": pd.Series(values, index=idx, dtype=float)})


  def test_signal_strong_uptrend_is_bullish():
      assert _signal(perf_1y=20.0, perf_3m=4.0, dist_52w_high=-2.0) == Signal.BULLISH


  def test_signal_deep_drawdown_is_bearish():
      assert _signal(perf_1y=-20.0, perf_3m=-5.0, dist_52w_high=-25.0) == Signal.BEARISH


  def test_52w_from_history():
      values = [float(100 + i) for i in range(300)]
      high, low = _52w(_hist(values)["Close"])
      assert high == max(values[-252:])
      assert low == min(values[-252:])


  def test_uses_total_return_when_available():
      provider = MagicMock()
      provider.get_total_return_history.return_value = _hist([float(100 + i) for i in range(300)])
      provider.get_info.return_value = {}
      agent = IndexPriceAgent(provider, MagicMock())
      result = asyncio.run(agent.run("^GSPC"))
      assert result.status == SignalStatus.AVAILABLE
      assert result.high_52w is not None  # aus Historie, nicht info


  def test_falls_back_to_price_return():
      provider = MagicMock()
      provider.get_total_return_history.return_value = None
      provider.get_price_history.return_value = _hist([float(100 + i) for i in range(300)])
      provider.get_info.return_value = {}
      agent = IndexPriceAgent(provider, MagicMock())
      result = asyncio.run(agent.run("^GSPC"))
      assert result.status == SignalStatus.AVAILABLE
      assert result.current_price is not None


  def test_unavailable_without_any_history():
      provider = MagicMock()
      provider.get_total_return_history.return_value = None
      provider.get_price_history.return_value = None
      provider.get_info.return_value = {}
      agent = IndexPriceAgent(provider, MagicMock())
      result = asyncio.run(agent.run("^GSPC"))
      assert result.status == SignalStatus.UNAVAILABLE
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/index/test_index_price_agent.py`
- [ ] **Port + Adapter** — `core/ports/data_provider.py`: `get_total_return_history`. `adapters/data/yahoo_finance.py`: `yf.Ticker(t).history(period=p, auto_adjust=True)` (Total-Return-Näherung) bzw. dedizierte TR-Ticker; `None` falls nicht ermittelbar.
- [ ] **echte Implementierung** — `agents/stock_deep_dive/index/index_price_agent.py` neu:
  ```python
  import asyncio
  from datetime import datetime

  import pandas as pd

  from core.domain.events import IndexPriceReady
  from core.domain.models import IndexPriceSnapshot, Signal, SignalStatus
  from core.ports.data_provider import MarketDataProvider
  from core.ports.event_bus import EventBus

  _DEFAULT = IndexPriceSnapshot(
      current_price=None, perf_1w=None, perf_1m=None, perf_3m=None, perf_ytd=None,
      perf_1y=None, perf_3y=None, perf_5y=None, high_52w=None, low_52w=None,
      signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
  )


  def _pct(new, old) -> float | None:
      if new is None or old is None or old == 0:
          return None
      return round((new - old) / abs(old) * 100, 2)


  def _52w(close: "object") -> tuple[float | None, float | None]:
      window = close.iloc[-252:] if len(close) >= 252 else close
      return round(float(window.max()), 2), round(float(window.min()), 2)


  def _signal(perf_1y: float | None, perf_3m: float | None, dist_52w_high: float | None) -> Signal:
      if perf_1y is None:
          return Signal.NEUTRAL
      near_high = dist_52w_high is None or dist_52w_high > -5.0
      if perf_1y > 15 and (perf_3m is None or perf_3m > 0) and near_high:
          return Signal.BULLISH
      if perf_1y < -15:
          return Signal.BEARISH
      return Signal.NEUTRAL


  class IndexPriceAgent:
      def __init__(self, market: MarketDataProvider, bus: EventBus):
          self.market = market
          self.bus = bus

      async def run(self, ticker: str) -> IndexPriceSnapshot:
          tr = await asyncio.to_thread(self.market.get_total_return_history, ticker, "5y")
          hist = tr
          if hist is None or "Close" not in getattr(hist, "columns", []):
              hist = await asyncio.to_thread(self.market.get_price_history, ticker, "5y")
          if hist is None or "Close" not in getattr(hist, "columns", []):
              self.bus.publish(IndexPriceReady(source="index_price_agent", payload={"ticker": ticker}))
              return _DEFAULT

          close = hist["Close"].dropna()
          now = float(close.iloc[-1])

          def _ago(days):
              idx = close.index.searchsorted(close.index[-1] - pd.Timedelta(days=days))
              return float(close.iloc[max(0, idx - 1)]) if idx > 0 else None

          high_52w, low_52w = _52w(close)
          dist_high = _pct(now, high_52w)
          p3m, p1y = _pct(now, _ago(90)), _pct(now, _ago(365))

          ytd_idx = close.index.searchsorted(f"{datetime.utcnow().year}-01-01")
          ytd_price = float(close.iloc[ytd_idx]) if ytd_idx < len(close) else None

          result = IndexPriceSnapshot(
              current_price=round(now, 2),
              perf_1w=_pct(now, _ago(7)), perf_1m=_pct(now, _ago(30)), perf_3m=p3m,
              perf_ytd=_pct(now, ytd_price), perf_1y=p1y,
              perf_3y=_pct(now, _ago(365 * 3)), perf_5y=_pct(now, _ago(365 * 5)),
              high_52w=high_52w, low_52w=low_52w,
              signal=_signal(p1y, p3m, dist_high), status=SignalStatus.AVAILABLE,
          )
          self.bus.publish(IndexPriceReady(source="index_price_agent", payload={"ticker": ticker}))
          return result

      @staticmethod
      def default() -> IndexPriceSnapshot:
          return _DEFAULT
  ```
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/index/test_index_price_agent.py`
- [ ] **Commit** — `feat(index_price): Total-Return-Historie + 52W aus Historie + Distanz-zum-Hoch im Signal (Review D6, P4.6)`

---

### Task 11 — `sector_composition_agent`: dynamische Konzentration/HHI

**Files:** `agents/stock_deep_dive/index/sector_composition_agent.py`, `core/ports/data_provider.py`, `tests/agents/stock_deep_dive/index/test_sector_composition_agent.py`

Befund (Review D6): vollständig hardcodiert, `top_10_concentration=None`, Signal immer NEUTRAL. Lösung: aktuelle Indexgewichte über neue Port-Methode laden; Top-Sektor/Top-Holding/Top-10-Konzentration und **HHI** berechnen; Signal aus Konzentrationsgrad. Fehlen die Holdings → UNAVAILABLE.

Neue Port-Methode:
```python
# core/ports/data_provider.py  (MarketDataProvider)
@abstractmethod
def get_index_holdings(self, index_ticker: str) -> list[dict]:
    """[{"name": str, "weight_pct": float, "sector": str}], absteigend nach Gewicht;
    leer = nicht verfügbar."""
    ...
```

- [ ] **failing Test** — `tests/agents/stock_deep_dive/index/test_sector_composition_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  from agents.stock_deep_dive.index.sector_composition_agent import (
      SectorCompositionAgent, _hhi, _concentration_signal,
  )
  from core.domain.models import Signal, SignalStatus


  def test_hhi_equal_weights():
      # 10 gleich gewichtete Titel à 10 % → HHI = 10 * 10^2 = 1000
      holdings = [{"name": f"T{i}", "weight_pct": 10.0, "sector": "X"} for i in range(10)]
      assert _hhi(holdings) == 1000.0


  def test_hhi_concentrated_is_higher():
      holdings = [{"name": "Big", "weight_pct": 50.0, "sector": "X"}] + \
                 [{"name": f"T{i}", "weight_pct": 5.0, "sector": "Y"} for i in range(10)]
      assert _hhi(holdings) > 2000.0


  def test_concentration_signal_high_is_bearish():
      assert _concentration_signal(hhi=2500.0) == Signal.BEARISH


  def test_concentration_signal_low_is_neutral():
      assert _concentration_signal(hhi=800.0) == Signal.NEUTRAL


  def test_run_unavailable_without_holdings():
      provider = MagicMock()
      provider.get_index_holdings.return_value = []
      agent = SectorCompositionAgent(provider, MagicMock())
      result = asyncio.run(agent.run("^GSPC"))
      assert result.status == SignalStatus.UNAVAILABLE


  def test_run_available_computes_top10_and_top_sector():
      provider = MagicMock()
      provider.get_index_holdings.return_value = [
          {"name": "Apple", "weight_pct": 7.0, "sector": "Technology"},
          {"name": "Microsoft", "weight_pct": 6.0, "sector": "Technology"},
          {"name": "Nvidia", "weight_pct": 5.0, "sector": "Technology"},
      ] + [{"name": f"T{i}", "weight_pct": 1.0, "sector": "Financials"} for i in range(20)]
      agent = SectorCompositionAgent(provider, MagicMock())
      result = asyncio.run(agent.run("^GSPC"))
      assert result.status == SignalStatus.AVAILABLE
      assert result.top_sector == "Technology"
      assert result.top_holding == "Apple"
      assert result.top_10_concentration is not None
  ```
- [ ] **Run FAIL** — `pytest tests/agents/stock_deep_dive/index/test_sector_composition_agent.py`
- [ ] **Port + Adapter** — `core/ports/data_provider.py`: `get_index_holdings`. Adapter über ETF-Holdings-API (iShares/SPDR-CSV) bzw. yfinance-Fonds-Holdings; Fehler → `[]`.
- [ ] **echte Implementierung** — `agents/stock_deep_dive/index/sector_composition_agent.py` neu:
  ```python
  import asyncio
  from collections import defaultdict

  from core.domain.events import SectorCompositionReady
  from core.domain.models import SectorCompositionSnapshot, Signal, SignalStatus
  from core.ports.data_provider import MarketDataProvider
  from core.ports.event_bus import EventBus

  _DEFAULT = SectorCompositionSnapshot(
      top_sector=None, top_sector_weight=None, top_holding=None, top_holding_weight=None,
      top_10_concentration=None, signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
  )

  _HHI_HIGH = 2000.0   # > 2000 → konzentriert (US-DOJ-Schwelle für "highly concentrated")


  def _hhi(holdings: list[dict]) -> float:
      return round(sum(float(h["weight_pct"]) ** 2 for h in holdings), 1)


  def _concentration_signal(hhi: float) -> Signal:
      # hohe Konzentration = höheres idiosynkratisches Risiko → vorsichtiger (bearish-Tilt)
      if hhi > _HHI_HIGH:
          return Signal.BEARISH
      return Signal.NEUTRAL


  class SectorCompositionAgent:
      def __init__(self, market: MarketDataProvider, bus: EventBus):
          self.market = market
          self.bus = bus

      async def run(self, ticker: str) -> SectorCompositionSnapshot:
          holdings = await asyncio.to_thread(self.market.get_index_holdings, ticker)
          if not holdings:
              self.bus.publish(SectorCompositionReady(source="sector_composition_agent", payload={"ticker": ticker}))
              return _DEFAULT

          by_sector: dict[str, float] = defaultdict(float)
          for h in holdings:
              by_sector[h.get("sector") or "Unknown"] += float(h["weight_pct"])
          top_sector, top_sector_w = max(by_sector.items(), key=lambda kv: kv[1])

          top = max(holdings, key=lambda h: float(h["weight_pct"]))
          top10 = round(sum(float(h["weight_pct"]) for h in holdings[:10]), 1)
          hhi = _hhi(holdings)

          result = SectorCompositionSnapshot(
              top_sector=top_sector, top_sector_weight=round(top_sector_w, 1),
              top_holding=top.get("name"), top_holding_weight=round(float(top["weight_pct"]), 1),
              top_10_concentration=top10,
              signal=_concentration_signal(hhi), status=SignalStatus.AVAILABLE,
          )
          self.bus.publish(SectorCompositionReady(source="sector_composition_agent", payload={"ticker": ticker}))
          return result

      @staticmethod
      def default() -> SectorCompositionSnapshot:
          return _DEFAULT
  ```
  > **Self-Review:** `holdings[:10]` setzt absteigende Sortierung der Port-Rückgabe voraus (in der Signatur dokumentiert). Falls der Adapter unsortiert liefert, im Adapter sortieren — nicht im Agenten doppelt.
- [ ] **Run PASS** — `pytest tests/agents/stock_deep_dive/index/test_sector_composition_agent.py`
- [ ] **Commit** — `feat(sector_composition): dynamische Top-10-Konzentration + HHI statt Hardcoding (Review D6); + get_index_holdings`

---

### Task 12 — `fear_greed_agent`: echte Datenquelle + Extremzonen-Signal

**Files:** `agents/market_cockpit/sentiment/fear_greed_agent.py`, `core/ports/data_provider.py`, `adapters/data/cnn_fear_greed.py` (neu), `tests/agents/market_cockpit/sentiment/test_fear_greed_agent.py`

Befund (Review D3): Datenquelle Stub (`_fetch_fear_greed` → immer `None`); BULLISH löst zu früh (≤45). Lösung: echte Quelle via neuem `SentimentDataProvider.get_fear_greed`; **symmetrische Extremzonen** — BULLISH nur ≤25, BEARISH nur ≥75, dazwischen NEUTRAL. Fehlt die Quelle → UNAVAILABLE.

Neuer Port:
```python
# core/ports/data_provider.py
class SentimentDataProvider(ABC):
    @abstractmethod
    def get_fear_greed(self) -> Optional[float]:
        """Aktueller CNN-Fear&Greed-Wert 0–100; None = nicht verfügbar."""
        ...
```

- [ ] **failing Test** — `tests/agents/market_cockpit/sentiment/test_fear_greed_agent.py`:
  ```python
  import asyncio
  from unittest.mock import MagicMock

  from agents.market_cockpit.sentiment.fear_greed_agent import FearGreedAgent, _signal, _label
  from core.domain.models import Signal, SignalStatus


  def test_extreme_fear_is_bullish():
      assert _signal(20.0) == Signal.BULLISH


  def test_moderate_fear_is_neutral():
      # 40 (Fear) ist KEIN Extrem mehr → neutral (Review D3)
      assert _signal(40.0) == Signal.NEUTRAL


  def test_extreme_greed_is_bearish():
      assert _signal(80.0) == Signal.BEARISH


  def test_moderate_greed_is_neutral():
      assert _signal(65.0) == Signal.NEUTRAL


  def test_label_unchanged():
      assert _label(20.0) == "Extreme Fear"
      assert _label(80.0) == "Extreme Greed"


  def test_run_available_with_provider():
      provider = MagicMock()
      provider.get_fear_greed.return_value = 18.0
      agent = FearGreedAgent(MagicMock(), provider=provider)
      result = asyncio.run(agent.run())
      assert result.status == SignalStatus.AVAILABLE
      assert result.signal == Signal.BULLISH


  def test_run_unavailable_without_value():
      provider = MagicMock()
      provider.get_fear_greed.return_value = None
      agent = FearGreedAgent(MagicMock(), provider=provider)
      result = asyncio.run(agent.run())
      assert result.status == SignalStatus.UNAVAILABLE
      assert result.signal == Signal.NEUTRAL
  ```
- [ ] **Run FAIL** — `pytest tests/agents/market_cockpit/sentiment/test_fear_greed_agent.py`
- [ ] **Port + Adapter** — `core/ports/data_provider.py`: `SentimentDataProvider` (oben). `adapters/data/cnn_fear_greed.py` (neu): GET `https://production.dataviz.cnn.io/index/fearandgreed/graphdata/` (User-Agent setzen), `score` aus JSON, Fehler → `None`.
- [ ] **echte Implementierung** — `agents/market_cockpit/sentiment/fear_greed_agent.py` neu:
  ```python
  import asyncio

  from core.domain.events import FearGreedDataReady
  from core.domain.models import FearGreedSnapshot, Signal, SignalStatus
  from core.ports.data_provider import SentimentDataProvider
  from core.ports.event_bus import EventBus

  _DEFAULT = FearGreedSnapshot(value=None, label="Unknown", signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE)


  def _label(value: float) -> str:
      if value <= 25:  return "Extreme Fear"
      if value <= 45:  return "Fear"
      if value <= 55:  return "Neutral"
      if value <= 75:  return "Greed"
      return "Extreme Greed"


  def _signal(value: float | None) -> Signal:
      if value is None:
          return Signal.NEUTRAL
      # Contrarian, NUR in den Extremen robust (symmetrisch; Review D3)
      if value <= 25:
          return Signal.BULLISH    # Extreme Fear → Contrarian Kauf
      if value >= 75:
          return Signal.BEARISH    # Extreme Greed → Contrarian Vorsicht
      return Signal.NEUTRAL


  class FearGreedAgent:
      def __init__(self, bus: EventBus, provider: SentimentDataProvider | None = None):
          self.bus = bus
          self.provider = provider

      async def run(self) -> FearGreedSnapshot:
          value = None
          if self.provider is not None:
              value = await asyncio.to_thread(self.provider.get_fear_greed)
          if value is None:
              self.bus.publish(FearGreedDataReady(source="fear_greed_agent", payload={"value": None, "label": "Unknown"}))
              return _DEFAULT
          label = _label(value)
          result = FearGreedSnapshot(value=value, label=label, signal=_signal(value), status=SignalStatus.AVAILABLE)
          self.bus.publish(FearGreedDataReady(source="fear_greed_agent", payload={"value": value, "label": label}))
          return result

      @staticmethod
      def default() -> FearGreedSnapshot:
          return _DEFAULT
  ```
  > **Self-Review:** `provider` optional → bestehender Aufruf `FearGreedAgent(bus)` bleibt valide und liefert dann UNAVAILABLE (statt vorgetäuschtem NEUTRAL). Der Sentiment-Chief sollte den `SentimentDataProvider` injizieren (Plan D1).
- [ ] **Run PASS** — `pytest tests/agents/market_cockpit/sentiment/test_fear_greed_agent.py`
- [ ] **Commit** — `feat(fear_greed): CNN-Datenquelle + symmetrische Extremzonen (Review D3); + SentimentDataProvider`

---

### Task 13 — Integration: Aufrufstellen & Stub-Adapter verdrahten

**Files:** Aufrufende Chiefs/Factories (per Grep ermitteln), Stub-Adapter (`adapters/data/ecb_snb_stub.py` o.ä.), `tests/...` (Smoke)

Mehrere Konstruktoren haben sich geändert (`cot_agent`, `supply_demand_agent`, `cross_metal_agent`-Param, `precious_metal_price_agent`-Macro, `fear_greed_agent`-Provider, neue Ports). Diese müssen verdrahtet werden, sonst brechen bestehende Tests/Läufe.

- [ ] **Aufrufstellen finden** — Grep nach `COTAgent(`, `SupplyDemandAgent(`, `CrossMetalAgent(`, `PreciousMetalPriceAgent(`, `FearGreedAgent(`, `CommodityValuationRangeAgent(` über `agents/` und `app/`/`composition`/Factory-Module.
- [ ] **failing Test** — Smoke-Test, der den jeweiligen Chief mit Fake-Providern instanziiert und `run()` ohne Exception durchläuft (mind. ein Test je geänderten Chief). Erwartung: UNAVAILABLE-Sub-Snapshots werden vom Chief nicht als NEUTRAL mitgewichtet (gegen Plan-0 `weighted_signal` prüfen, falls Chief bereits aggregiert).
- [ ] **Run FAIL** — `pytest tests/` (gesamte Suite) → zeigt gebrochene Konstruktor-Aufrufe.
- [ ] **echte Implementierung** — Konstruktor-Aufrufe an die neuen Signaturen anpassen; neue Stub-Adapter (`CommoditySupplyProvider`/`COTProvider`/`SentimentDataProvider` mit `[]`/`{}`/`None`-Rückgaben) registrieren, wo noch keine echte Quelle verdrahtet ist; `get_real_rate_history`, `get_index_*`, `get_total_return_history` in den vorhandenen Adaptern mindestens als sichere Defaults implementieren.
- [ ] **Run PASS** — `pytest tests/`
- [ ] **Commit** — `feat(wiring): geänderte Agenten-Signaturen + neue Stub-Adapter verdrahtet (Plan E)`

---

## Abdeckung

| Review-Punkt (Quelle der Wahrheit) | Task | Ergebnis |
|---|---|---|
| `index_breadth` echte Breadth-Berechnung (D6) | 8 | % > MA200, A/D-Ratio, New-High/Low aus Konstituenten; UNAVAILABLE ohne Konstituenten |
| `index_earnings` aggregierte Index-EPS + echte Revisions (D6) | 9 | `get_index_fundamentals`; Fwd/Trailing-Proxy entfernt |
| `index_price` Total- vs. Price-Return (P4.6) + 52W aus Historie (D6) | 10 | `get_total_return_history`, 52W aus Close, Distanz-zum-Hoch im Signal |
| `sector_composition` dynamische Konzentration/HHI (D6) | 11 | `get_index_holdings`, Top-10 + HHI; Hardcoding entfernt |
| `cot_agent` CFTC-COT-Index (D7) | 5 | `COTProvider` + COT-Index (Managed Money, 0–100, konträr) |
| `seasonality` längere Historie, Signifikanz, Median, real (D7) | 7 | 20J, t-Test, Median, `to_real` |
| `supply_demand` echte Lagerbalancen, einheitliche S2F (D7) | 6 | `get_inventory_history`, S2F nur wo definiert konsistent |
| `commodity_valuation_range` echtes Perzentil (P4.3), real, Cost-Curve (D7) | 4 | `percentile_rank`, `to_real`, `get_production_cost_curve` |
| `cross_metal` Perzentil-Anker, metallspezifische Richtung, Gold/Platin-Signal (D7) | 2 | rollierende Perzentile, GS hoch → bullish Silber/bearish Gold, Gold/Platin überführt |
| `precious_metal_price` Performance/RSI/MA/Realzins-Korrelation aus Historie (D7) | 3 | Wilder-RSI/MA/Perf + `get_real_rate_history`-Regression |
| `fear_greed` echte Datenquelle + Extremzonen-Signal (D3) | 12 | `SentimentDataProvider` + symmetrische Extremzonen ≤25 / ≥75 |
| Querschnitt: Stub→UNAVAILABLE statt NEUTRAL (Teil B 1.4) | 1–13 | jeder Agent setzt `SignalStatus.UNAVAILABLE` bei fehlender Quelle |
| Plan-0-Abhängigkeiten referenziert (nicht neu definiert) | 1 | `percentile_rank`, `robust_z_score`, `to_real`, `SignalStatus` |

**Neue Provider-/Port-Methoden (Signaturen):**
- `MarketDataProvider.get_index_constituents(index_ticker: str) -> list[str]`
- `MarketDataProvider.get_constituent_histories(index_ticker: str, period: str = "2y") -> dict`
- `MarketDataProvider.get_index_holdings(index_ticker: str) -> list[dict]`
- `MarketDataProvider.get_index_fundamentals(index_ticker: str) -> dict`
- `MarketDataProvider.get_total_return_history(ticker: str, period: str = "5y") -> object`
- `MacroDataProvider.get_real_rate_history(years: int = 5) -> list[dict]`
- `COTProvider.get_cot_history(commodity: str, years: int = 3) -> list[dict]` *(neuer Port)*
- `CommoditySupplyProvider.get_inventory_history(commodity: str, years: int = 5) -> list[dict]` *(neuer Port)*
- `CommoditySupplyProvider.get_production_cost_curve(commodity: str) -> dict` *(neuer Port)*
- `SentimentDataProvider.get_fear_greed() -> Optional[float]` *(neuer Port)*

**Vorerst `SignalStatus.UNAVAILABLE` (bis echte Datenquelle verdrahtet):**
- `cot_agent` — bis `COTProvider`/CFTC-Adapter Daten liefert.
- `supply_demand_agent` — bis `CommoditySupplyProvider.get_inventory_history` Daten liefert.
- `commodity_valuation_range_agent` — Cost-Curve-Anker optional; Range/Position liefern AVAILABLE, sobald Preis-Historie vorhanden ist.
- `sector_composition_agent` — bis `get_index_holdings` Daten liefert.
- `index_breadth_agent` — bis Konstituenten-Historien verfügbar.
- `index_earnings_agent` — bis `get_index_fundamentals` Daten liefert.
- `fear_greed_agent` — bis `SentimentDataProvider`/CNN-Adapter Daten liefert.
- `precious_metal_price_agent` — nur `real_yield_correlation` bleibt None ohne `get_real_rate_history`; Preis/RSI/MA/Perf sind AVAILABLE.
- `cross_metal_agent`, `seasonality_agent`, `index_price_agent` — AVAILABLE, sobald die bereits vorhandene `get_price_history` greift; UNAVAILABLE nur bei fehlender/zu kurzer Historie.
