# Plan D1 — Cockpit-Signallogik (Macro, Commodity, Sentiment, Yield, Sektor) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Signal-Logik aller Cockpit-Sub-Agenten (Domänen 1–3 des Konzept-Reviews) von US-zentrischen Absolut-Schwellen, Niveau-statt-Momentum-Fehlern, prozess-globalem Zustand und blinden Schwellen-Lücken auf relative, momentum-basierte, lückenlose und länderspezifische Maße umstellen. Stub-/fehlende Sub-Signale fließen nicht mehr als Schein-NEUTRAL in die Chief-Aggregation, sondern werden über `SignalStatus.UNAVAILABLE` aus der Gewichtung herausgenommen. Jeder Chief erzeugt ein echtes, gewichtetes Composite-Signal.

**Architecture:** EDA + Hexagonal. Reine Domänen-Logik liegt in modul-privaten `_signal`/`_point`-Funktionen (rein, ohne I/O — direkt unit-testbar, siehe bestehende Tests). Agenten orchestrieren nur Provider-Aufrufe + Event-Publishing. Diese Trennung bleibt erhalten: Wir testen ausschließlich die reinen Funktionen mit konkreten Zahlen und prüfen die Fehler-Defaults über MagicMock-Agenten (Stil aus `test_credit_labor_error_handling.py`). Die Plan-0-Utilities (`relative`, `real_nominal`, `aggregation`, `timeseries_history`) werden importiert und NICHT neu definiert.

**Tech Stack:** Python, asyncio, pytest

**Abhängigkeiten:** Plan 0 (Shared Utilities). Voraussetzung — diese Symbole existieren bereits, wenn dieser Plan startet:
- `core/utils/relative.py`: `percentile_rank(value, history, winsorize=0.0)`, `zscore_vs_history(value, history, robust=True, min_n=20)`
- `core/utils/real_nominal.py`: `to_real(nominal_rate, inflation)`, `excess_over_nominal_gdp(growth, nominal_gdp_growth)`
- `core/utils/aggregation.py`: `weighted_signal(items: list[tuple[Signal, float, SignalStatus]]) -> tuple[Signal, float]`
- `core/utils/timeseries_history.py`: `DatedHistory` (Methoden `value_on_or_before(date)`, `latest()`)
- `core/domain/models.py`: `SignalStatus` (Enum `AVAILABLE | UNAVAILABLE`)

---

## Dateienübersicht

| Task | Datei(en) | Befund(e) aus Review |
|---|---|---|
| 1 | `agents/.../commodity/energy_agent.py` | P2.4 — Niveau→Momentum, WTI/Brent getrennt, Gas |
| 2 | `agents/.../commodity/industrial_metals_agent.py` | P2.4 — Niveau→Momentum, Copper/Gold-Ratio |
| 3 | `agents/.../commodity/agricultural_agent.py` | D2 — z-Score statt fixer ±20%, geglättete Endpunkte |
| 4 | `agents/.../commodity/precious_metals_macro_agent.py` | D2/D7 — Perzentil-Schwellen, Gold-Momentum, Gold/Platin-Signal |
| 5 | `agents/.../commodity_chief_agent_makro.py` | D2 — gewichtetes Gesamt-Commodity-Signal |
| 6 | `agents/.../sentiment/vix_agent.py` | P3.4 — VIX contrarian, `is None` |
| 7 | `agents/.../sentiment/put_call_agent.py` | P3.4 — Schwellen relativ kalibriert |
| 8 | `agents/.../sentiment_chief_agent.py` | P3.4 — Composite via `weighted_signal` |
| 9 | `agents/.../yield_curve/yield_spread_agent.py` | P3.5 — 10Y-3M primär, Inversions-Lag |
| 10 | `agents/.../yield_curve/sovereign_spread_agent.py` | D3 — nur Peripherie in systemischer Zählung |
| 11 | `agents/.../yield_curve_chief_agent.py` | P3.3 — konsolidiertes Zinskurven-Signal |
| 12 | `agents/.../macro/inflation_agent.py` | P4.4/P4.5 — Lücke 3–4%, `trend`, `real_rate_10y` |
| 13 | `agents/.../macro/money_supply_agent.py` | P3.2/P4.4/P4.5 — real zum BIP, Lücke 8–10%, `velocity` |
| 14 | `agents/.../macro/credit_agent.py` | P3.2 — real, glockenförmig, `money_velocity` |
| 15 | `agents/.../macro/buffett_indicator_agent.py` | P3.1 — z-Score zur Landeshistorie, kein 135%-Fix |
| 16 | `agents/.../macro/gdp_agent.py` | P3.1 — Sahm-Regel, Score normiert, ECB-Proxy entfernen |
| 17 | `agents/.../macro/interest_rate_agent.py` | P3.7/P4.5 — `DatedHistory`, real_rate EU/CH |
| 18 | `core/domain/regime.py` | D1/D8 — Deflation negativ, Gewichte = 1.0, datierte History, Sub-Signale optional |
| 19 | `agents/.../macro_chief_agent.py` | P3.3 — Sub-Signale ins Regime, Yield-Mapping umbenennen |
| 20 | `agents/.../sector/sector_performance_agent.py` | P3.6 — relative Stärke vs. Benchmark, XLC |
| 21 | `agents/.../sector/sector_rotation_agent.py` | D3 — "Gold" raus, Top-N-Alignment |
| 22 | `agents/.../sector_chief_agent.py` | D3 — EU-Sektoren einbeziehen |
| 23 | `core/domain/top_down_context.py` | P3.1/D8 — länderspezifischer Buffett-Fallback |

**Konvention domänenweit (P2.4/D2):** Signal-Semantik aller Commodity-Agenten = "Marktimplikation für Risiko-Assets". Steigendes Commodity-Momentum = Inflationsdruck = leicht BEARISH für Aktien; stark fallendes Momentum (Nachfrageschwäche) ebenfalls BEARISH; moderates Momentum = NEUTRAL/BULLISH. Edelmetalle bleiben Safe-Haven-invers (Gold-Spike = BEARISH für Risiko). Diese Konvention wird in jedem `_signal`-Docstring genannt.

---

### Task 1 — Energy: Niveau → Momentum (WTI/Brent getrennt, Gas einbeziehen)

**Files:** `agents/market_cockpit/commodity/energy_agent.py`, `tests/agents/market_cockpit/commodity/test_energy_agent.py`

Befund P2.4 / D2-Energy (❌): Signal aus absolutem Preisniveau (`>100`/`<40`), `wti or brent`-Fallback verschluckt WTI=0.0 und den Spread, Gas erhoben aber ungenutzt. Lösung: Signal aus dem 3M/6M/12M-Momentum, z-Score-normiert via `zscore_vs_history`, WTI und Brent getrennt gemittelt, Gas als eigener hochvolatiler Faktor.

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/commodity/test_energy_agent.py`:
```python
from agents.market_cockpit.commodity.energy_agent import _signal
from core.domain.models import Signal


def test_no_momentum_is_neutral():
    # Alle Returns ~0 → NEUTRAL
    assert _signal(wti_z=0.0, brent_z=0.0, gas_z=0.0) == Signal.NEUTRAL


def test_strong_positive_oil_momentum_is_bearish():
    # WTI/Brent stark gestiegen (z > +1.0) → Inflationsdruck → BEARISH für Risiko
    assert _signal(wti_z=1.5, brent_z=1.4, gas_z=0.2) == Signal.BEARISH


def test_strong_negative_oil_momentum_is_bearish():
    # Öl bricht ein (z < -1.0) → Nachfrageschwäche → BEARISH
    assert _signal(wti_z=-1.6, brent_z=-1.5, gas_z=-0.3) == Signal.BEARISH


def test_gas_spike_alone_is_bearish():
    # Gas-z extrem (>2.0), Öl neutral → EU-Energiekosten-Schock → BEARISH
    assert _signal(wti_z=0.1, brent_z=0.0, gas_z=2.4) == Signal.BEARISH


def test_zero_wti_does_not_fall_back_silently():
    # wti_z=0.0 ist ein valider Wert (kein Falsiness-Fallback)
    assert _signal(wti_z=0.0, brent_z=0.0, gas_z=0.0) == Signal.NEUTRAL


def test_all_none_is_neutral():
    assert _signal(wti_z=None, brent_z=None, gas_z=None) == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/commodity/test_energy_agent.py -q` (neue `_signal`-Signatur existiert noch nicht).
- [ ] **Implementierung** — `energy_agent.py` umbauen:
```python
import asyncio
from core.domain.events import EnergyDataReady
from core.domain.models import EnergySnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.relative import zscore_vs_history

TICKERS = {"wti": "CL=F", "brent": "BZ=F", "natural_gas": "NG=F"}
_DEFAULT = EnergySnapshot(wti_usd=None, brent_usd=None, natural_gas_usd=None, signal=Signal.NEUTRAL)

# Schwellen auf der z-Score-Skala der 12M-Momentum-Verteilung.
_OIL_Z = 1.0   # |z| > 1.0 = signifikante Öl-Bewegung
_GAS_Z = 2.0   # Gas extrem volatil → höhere Schwelle


def _signal(wti_z: float | None, brent_z: float | None, gas_z: float | None) -> Signal:
    """
    Marktimplikation aus dem Öl-/Gas-MOMENTUM (z-Score der Veränderungsrate),
    NICHT aus dem nominalen Preisniveau. Konvention: starke Öl-Bewegung in beide
    Richtungen (Inflationsdruck bzw. Nachfrageschwäche) = BEARISH für Risiko-Assets.
    `is None`-Checks statt Falsiness (z=0.0 ist ein valider Wert).
    """
    oil = [z for z in (wti_z, brent_z) if z is not None]
    oil_z = sum(oil) / len(oil) if oil else None

    if oil_z is not None and abs(oil_z) > _OIL_Z:
        return Signal.BEARISH
    if gas_z is not None and abs(gas_z) > _GAS_Z:
        return Signal.BEARISH
    if oil_z is None and gas_z is None:
        return Signal.NEUTRAL
    return Signal.NEUTRAL


def _momentum_z(hist) -> float | None:
    """12M-Total-Return als z-Score gegen die rollierende Return-Historie."""
    if hist is None or isinstance(hist, Exception):
        return None
    try:
        close = hist["Close"].dropna()
        if len(close) < 30:
            return None
        # 21-Handelstage-Returns als Momentum-Verteilung; aktueller 12M-Return als Punkt
        monthly = close.pct_change(21).dropna()
        if len(monthly) < 20:
            return None
        current = float((close.iloc[-1] - close.iloc[0]) / close.iloc[0])
        return zscore_vs_history(current, monthly.tolist(), robust=True, min_n=20)
    except Exception:
        return None


class EnergyAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> EnergySnapshot:
        (wti, brent, gas), (h_wti, h_brent, h_gas) = await asyncio.gather(
            asyncio.gather(
                asyncio.to_thread(self.provider.get_current_price, TICKERS["wti"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["brent"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["natural_gas"]),
                return_exceptions=True,
            ),
            asyncio.gather(
                asyncio.to_thread(self.provider.get_price_history, TICKERS["wti"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["brent"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["natural_gas"], "1y"),
                return_exceptions=True,
            ),
        )
        def _safe(v): return None if isinstance(v, Exception) else v
        wti = _safe(wti); brent = _safe(brent); gas = _safe(gas)

        result = EnergySnapshot(
            wti_usd=wti, brent_usd=brent, natural_gas_usd=gas,
            signal=_signal(_momentum_z(h_wti), _momentum_z(h_brent), _momentum_z(h_gas)),
        )
        self.bus.publish(EnergyDataReady(source="energy_agent", payload={
            "wti": wti, "brent": brent, "natural_gas": gas,
        }))
        return result

    @staticmethod
    def default() -> EnergySnapshot:
        return _DEFAULT
```
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/commodity/test_energy_agent.py -q`.
- [ ] **Commit** — `fix(energy): Signal aus Momentum-z-Score statt Preisniveau, WTI/Brent getrennt + Gas (P2.4)`

**Self-Review:** WTI=0.0 kann kein stilles Fallback mehr auslösen (`is None`-Check). Annahme: `get_price_history(ticker, "1y")` liefert ein DataFrame mit Spalte `"Close"` (wie im bestehenden `agricultural_agent` und `sector_performance_agent`). `zscore_vs_history` aus Plan 0 wird nur konsumiert.

---

### Task 2 — Industrial Metals: Niveau → Momentum + Copper/Gold-Ratio

**Files:** `agents/market_cockpit/commodity/industrial_metals_agent.py`, `tests/agents/market_cockpit/commodity/test_industrial_metals_agent.py`

Befund P2.4 / D2 (❌): Kupfer-Niveau (`>4.5`/`<3.0`) statt Dynamik; Al/Zn/Ni verworfen; Einheiten-Falle (USD/lb vs. USD/Tonne) latent. Lösung: Signal aus Kupfer-Momentum, idealerweise als Copper/Gold-Ratio-Momentum (etablierter Zins-/Makro-Frühindikator), z-Score-normiert. Aggregation bleibt einheiten-sicher (nur Ratio, keine Vermischung).

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/commodity/test_industrial_metals_agent.py`:
```python
from agents.market_cockpit.commodity.industrial_metals_agent import _signal
from core.domain.models import Signal


def test_no_momentum_is_neutral():
    assert _signal(copper_gold_z=0.0) == Signal.NEUTRAL


def test_rising_copper_gold_ratio_is_bullish():
    # Dr. Copper steigt relativ zu Gold → Risk-on / Wachstum → BULLISH
    assert _signal(copper_gold_z=1.3) == Signal.BULLISH


def test_falling_copper_gold_ratio_is_bearish():
    # Kupfer fällt relativ zu Gold → Flucht in Sicherheit → BEARISH
    assert _signal(copper_gold_z=-1.3) == Signal.BEARISH


def test_none_is_neutral():
    assert _signal(copper_gold_z=None) == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/commodity/test_industrial_metals_agent.py -q`.
- [ ] **Implementierung** — `_signal` und `run` umbauen (FMP-Fetcher für Zn/Ni bleibt nur als Snapshot-Feld, NICHT im Signal — Einheiten-Falle vermieden):
```python
from core.utils.relative import zscore_vs_history

_COPPER_GOLD_Z = 1.0   # |z| > 1.0 = signifikante Copper/Gold-Bewegung


def _signal(copper_gold_z: float | None) -> Signal:
    """
    Dr. Copper als Frühindikator über die DYNAMIK des Copper/Gold-Ratios
    (dimensionslos, zins-/wachstumssensitiv), NICHT über ein statisches
    Kupfer-Niveau. Steigendes Ratio = Risk-on (BULLISH), fallendes = Risk-off (BEARISH).
    """
    if copper_gold_z is None:
        return Signal.NEUTRAL
    if copper_gold_z > _COPPER_GOLD_Z:
        return Signal.BULLISH
    if copper_gold_z < -_COPPER_GOLD_Z:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _copper_gold_z(copper_hist, gold_hist) -> float | None:
    """z-Score der 12M-Veränderung des Copper/Gold-Ratios."""
    if copper_hist is None or gold_hist is None:
        return None
    if isinstance(copper_hist, Exception) or isinstance(gold_hist, Exception):
        return None
    try:
        cu = copper_hist["Close"].dropna()
        au = gold_hist["Close"].dropna()
        ratio = (cu / au).dropna()
        if len(ratio) < 30:
            return None
        monthly = ratio.pct_change(21).dropna()
        if len(monthly) < 20:
            return None
        current = float((ratio.iloc[-1] - ratio.iloc[0]) / ratio.iloc[0])
        return zscore_vs_history(current, monthly.tolist(), robust=True, min_n=20)
    except Exception:
        return None
```
Im `run()`: zusätzlich `gold`-Historie (`GC=F`) per `get_price_history` laden, `_copper_gold_z(h_copper, h_gold)` ans `_signal` geben; Snapshot-Felder `copper_usd/aluminium_usd/zinc_usd/nickel_usd` unverändert befüllen (FMP-Fetcher bleibt).
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/commodity/test_industrial_metals_agent.py -q`.
- [ ] **Commit** — `fix(industrial_metals): Signal aus Copper/Gold-Momentum-z-Score statt Kupfer-Niveau (P2.4)`

**Self-Review:** Zn/Ni in USD/Tonne fließen NICHT ins Signal → Einheiten-Falle bleibt geschlossen. Annahme: `GC=F`-Historie über denselben `get_price_history` verfügbar. Copper/Gold beide aus Yahoo (`HG=F`, `GC=F`) → konsistente Einheit für den dimensionslosen Quotienten.

---

### Task 3 — Agricultural: z-Score statt fixer ±20%, geglättete Endpunkte

**Files:** `agents/market_cockpit/commodity/agricultural_agent.py`, `tests/agents/market_cockpit/commodity/test_agricultural_agent.py` (erweitern)

Befund D2 (⚠️): `_yoy_change` endpunktsensitiv (`iloc[0]` vs `iloc[-1]`); `_signal` fix ±20% nicht vol-adjustiert. Lösung: Endpunkte 5-Tage-glätten; Schwelle auf z-Score der Jahresveränderungen umstellen. Median bleibt (robust). Die Marktimplikations-Konvention (hohe Agrarpreise → BEARISH) bleibt.

- [ ] **Failing Test schreiben** — bestehende Datei `test_agricultural_agent.py` um z-Score-basierte Fälle erweitern (alte ±20%-Tests werden ersetzt, da `_signal` jetzt z-Scores erwartet):
```python
from agents.market_cockpit.commodity.agricultural_agent import _signal
from core.domain.models import Signal


def test_all_near_zero_z_is_neutral():
    assert _signal([0.2, -0.1, 0.0, 0.3, -0.2, 0.1, 0.0]) == Signal.NEUTRAL


def test_median_z_above_threshold_is_bearish():
    # Median-z > +1.0 → Agrar-Inflation → BEARISH
    assert _signal([1.4, 1.2, 1.6, 1.1, 1.3, 0.2, 1.5]) == Signal.BEARISH


def test_median_z_below_threshold_is_bullish():
    # Median-z < -1.0 → Preisentlastung → BULLISH
    assert _signal([-1.4, -1.2, -1.6, -1.1, -1.3, -0.2, -1.5]) == Signal.BULLISH


def test_single_outlier_does_not_flip_median():
    assert _signal([3.0, 0.1, -0.1, 0.0, 0.2, 0.1, 0.0]) == Signal.NEUTRAL


def test_empty_returns_neutral():
    assert _signal([]) == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/commodity/test_agricultural_agent.py -q`.
- [ ] **Implementierung** — `_signal` auf z-Score-Median, `_yoy_change` auf geglättete Endpunkte + z-Score:
```python
import statistics
from core.utils.relative import zscore_vs_history

_Z_THRESHOLD = 1.0   # Median-z der Jahresveränderungen


def _signal(z_changes: list[float]) -> Signal:
    """
    Median der z-Normierten Jahresveränderungen aller Agrar-Rohstoffe.
    Hohe Agrarpreise (Median-z > +1) = Inflationsdruck → BEARISH;
    Preisentlastung (Median-z < -1) = BULLISH. z-Score statt fixer ±20%
    macht die Schwelle volatilitäts-adjustiert.
    """
    if not z_changes:
        return Signal.NEUTRAL
    med = statistics.median(z_changes)
    if med > _Z_THRESHOLD:
        return Signal.BEARISH
    if med < -_Z_THRESHOLD:
        return Signal.BULLISH
    return Signal.NEUTRAL


def _yoy_change_z(hist) -> float | None:
    """Geglättete (5-Tage) Jahresveränderung als z-Score gegen die Return-Historie."""
    if isinstance(hist, Exception) or hist is None:
        return None
    try:
        close = hist["Close"].dropna()
        if len(close) < 30:
            return None
        start = float(close.iloc[:5].mean())
        end   = float(close.iloc[-5:].mean())
        if start <= 0:
            return None
        current = (end - start) / start
        monthly = close.pct_change(21).dropna()
        if len(monthly) < 20:
            return None
        return zscore_vs_history(current, monthly.tolist(), robust=True, min_n=20)
    except Exception:
        return None
```
Im `run()`: `changes = [z for z in (_yoy_change_z(h) for h in histories) if z is not None]`, `signal=_signal(changes)`. **Wichtig:** Falls `AgriculturalSnapshot.median_yoy_change` aus dem vorhandenen Agri-Investment-Plan existiert, weiterhin den *rohen* Median befüllen (separat berechnen) — dieses Feld nicht durch z-Scores überschreiben.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/commodity/test_agricultural_agent.py -q`.
- [ ] **Commit** — `fix(agricultural): z-Score-Median statt fixer ±20%, geglättete Endpunkte (D2)`

**Self-Review:** Roll-Yield/Contango (echter Spot-Index) bleibt out-of-scope (eigener Plan), aber Endpunkt-Glättung mildert die Ausreißer-Sensitivität. Falls `median_yoy_change` nicht existiert, diesen Hinweis ignorieren.

---

### Task 4 — Precious Metals Macro: Perzentil-Schwellen, Gold-Momentum, Gold/Platin-Signal

**Files:** `agents/market_cockpit/commodity/precious_metals_macro_agent.py`, `tests/agents/market_cockpit/commodity/test_precious_metals_macro_agent.py`

Befund D2/D7 (⚠️): GS-Schwellen 50/80 veraltet; `GOLD_PLATINUM_AVG=1.0` faktisch falsch; Gold-Momentum nie implementiert; Gold/Platin-Ratio nie zum Signal. Lösung: GS-Ratio über `percentile_rank` gegen rollierende Historie, Gold-Momentum (Safe-Haven) als z-Score, Gold/Platin ebenfalls perzentil-basiert.

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/commodity/test_precious_metals_macro_agent.py`:
```python
from agents.market_cockpit.commodity.precious_metals_macro_agent import _signal
from core.domain.models import Signal


def test_none_inputs_is_neutral():
    assert _signal(gs_pct=None, gold_z=None) == Signal.NEUTRAL


def test_high_gs_percentile_is_bearish():
    # GS-Ratio im oberen Extrem (>0.85 Perzentil) → Risikoaversion → BEARISH für Risiko
    assert _signal(gs_pct=0.92, gold_z=0.3) == Signal.BEARISH


def test_low_gs_percentile_is_bullish():
    # GS-Ratio im unteren Extrem (<0.15) → Risk-on → BULLISH
    assert _signal(gs_pct=0.08, gold_z=0.0) == Signal.BULLISH


def test_gold_momentum_spike_is_bearish():
    # Gold-z > +1.5 (Safe-Haven-Flucht) überschreibt neutrales GS → BEARISH
    assert _signal(gs_pct=0.50, gold_z=1.8) == Signal.BEARISH


def test_mid_percentile_no_momentum_is_neutral():
    assert _signal(gs_pct=0.50, gold_z=0.2) == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/commodity/test_precious_metals_macro_agent.py -q`.
- [ ] **Implementierung** — fixe Anker entfernen, `_signal` perzentil-/momentum-basiert:
```python
from core.utils.relative import percentile_rank, zscore_vs_history

_GS_HIGH = 0.85
_GS_LOW  = 0.15
_GOLD_Z  = 1.5


def _signal(gs_pct: float | None, gold_z: float | None) -> Signal:
    """
    Edelmetall-Makro-Signal über RELATIVE Maße:
    - Gold/Silber-Ratio als Perzentil-Rang gegen die rollierende Historie
      (oberes Extrem = Risikoaversion → BEARISH; unteres = Risk-on → BULLISH).
    - Gold-Momentum-z (Safe-Haven-Nachfrage) als Override Richtung BEARISH.
    Keine fixen Absolut-Anker (80/50, 1.0) mehr.
    """
    if gold_z is not None and gold_z > _GOLD_Z:
        return Signal.BEARISH
    if gs_pct is None:
        return Signal.NEUTRAL
    if gs_pct >= _GS_HIGH:
        return Signal.BEARISH
    if gs_pct <= _GS_LOW:
        return Signal.BULLISH
    return Signal.NEUTRAL
```
Im `run()`: zusätzlich Gold-Historie (`GC=F`, "1y") und GS-Ratio-Historie laden; `gs_pct = percentile_rank(current_gs, gs_history)`, `gold_z` analog Task 1 (`zscore_vs_history`). Snapshot-Felder (`gold_silver_ratio`, `gold_platinum_ratio`) bleiben befüllt. Konstanten `GOLD_SILVER_AVG`/`GOLD_PLATINUM_AVG` entfernen.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/commodity/test_precious_metals_macro_agent.py -q`.
- [ ] **Commit** — `fix(precious_metals_macro): Perzentil-Schwellen + Gold-Momentum statt fixer Anker (D7)`

**Self-Review:** `gold_platinum_ratio` bleibt im Snapshot (Dashboard), fließt aber bewusst nicht ins Makro-Signal (Vermeidung von Doppelzählung; das Deep-Dive übernimmt die GP-Signalisierung). Annahme: Provider liefert ausreichende GS-Ratio-Historie über Gold- und Silber-Historien.

---

### Task 5 — Commodity Chief: gewichtetes Gesamt-Commodity-Signal

**Files:** `agents/market_cockpit/commodity_chief_agent_makro.py`, `core/domain/models.py` (nur `CommodityChiefResult` um `signal` erweitern), `tests/agents/market_cockpit/test_commodity_chief_makro.py`

Befund D2 (⚠️): keine Aggregation, kein Gesamtsignal, keine Sektorgewichtung (GSCI/BCOM: Energie dominiert). Lösung: `weighted_signal` über die vier Sub-Signale mit makro-relevanten Gewichten (Energie höchstes Gewicht). `SignalStatus` aus dem jeweiligen Sub-Snapshot ableiten (Sub-NEUTRAL bei fehlenden Daten → UNAVAILABLE).

- [ ] **Models erweitern** — `CommodityChiefResult` um `signal: Signal = Signal.NEUTRAL` ergänzen.
- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/test_commodity_chief_makro.py`:
```python
from agents.market_cockpit.commodity_chief_agent_makro import _aggregate
from core.domain.models import Signal, SignalStatus


def test_energy_dominates_aggregate():
    # Energie BEARISH (höchstes Gewicht) schlägt drei neutrale → BEARISH
    items = [
        (Signal.BEARISH, 0.50, SignalStatus.AVAILABLE),   # energy
        (Signal.NEUTRAL, 0.20, SignalStatus.AVAILABLE),   # industrial
        (Signal.NEUTRAL, 0.15, SignalStatus.AVAILABLE),   # precious
        (Signal.NEUTRAL, 0.15, SignalStatus.AVAILABLE),   # agricultural
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.BEARISH


def test_unavailable_excluded_from_weight():
    # Energie UNAVAILABLE → industrial BULLISH bestimmt das Ergebnis
    items = [
        (Signal.NEUTRAL, 0.50, SignalStatus.UNAVAILABLE),
        (Signal.BULLISH, 0.20, SignalStatus.AVAILABLE),
        (Signal.NEUTRAL, 0.15, SignalStatus.AVAILABLE),
        (Signal.NEUTRAL, 0.15, SignalStatus.AVAILABLE),
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.BULLISH
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/test_commodity_chief_makro.py -q`.
- [ ] **Implementierung** — `_aggregate` als dünner Wrapper um `weighted_signal`, im `run()` befüllt:
```python
from core.domain.models import CommodityChiefResult, Signal, SignalStatus
from core.utils.aggregation import weighted_signal

# Makro-Relevanz-Gewichte (GSCI/BCOM-nah: Energie dominiert)
_WEIGHTS = {"energy": 0.50, "industrial": 0.20, "precious": 0.15, "agricultural": 0.15}


def _status(snapshot) -> SignalStatus:
    # Sub-Snapshot ohne berechenbares Signal → UNAVAILABLE (raus aus Gewichtung)
    return SignalStatus.AVAILABLE if snapshot.signal != Signal.NEUTRAL else SignalStatus.AVAILABLE
    # Hinweis: NEUTRAL ist hier ein gültiges Ergebnis (Daten vorhanden, aber kein Tilt).
    # UNAVAILABLE wird nur gesetzt, wenn die zugrunde liegenden Rohdaten fehlen — siehe run().


def _aggregate(items):
    return weighted_signal(items)
```
Im `run()`: Status je Sub-Agent aus dem Vorhandensein der Rohdaten bestimmen (z. B. Energy `UNAVAILABLE`, wenn `wti_usd is None and brent_usd is None and natural_gas_usd is None`), dann:
```python
items = [
    (energy.signal, _WEIGHTS["energy"], _status_energy),
    (industrial_metals.signal, _WEIGHTS["industrial"], _status_industrial),
    (precious_metals.signal, _WEIGHTS["precious"], _status_precious),
    (agricultural.signal, _WEIGHTS["agricultural"], _status_agri),
]
overall, _conf = _aggregate(items)
return CommodityChiefResult(..., signal=overall)
```
Die `default()`-Variante bekommt `signal=Signal.NEUTRAL`.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/test_commodity_chief_makro.py -q`.
- [ ] **Commit** — `feat(commodity_chief): gewichtetes Gesamt-Commodity-Signal via weighted_signal (D2)`

**Self-Review:** `weighted_signal` aus Plan 0 wird nur konsumiert. Status-Bestimmung erfolgt aus Rohdaten-Vorhandensein, nicht aus dem Signal-Wert (NEUTRAL ≠ UNAVAILABLE). Annahme: Sub-Snapshots tragen die nötigen Preis-/Ratio-Felder zur Verfügbarkeitsprüfung (siehe `models.py`).

---

### Task 6 — VIX: contrarian + `is None`

**Files:** `agents/market_cockpit/sentiment/vix_agent.py`, `tests/agents/market_cockpit/sentiment/test_vix_agent.py`

Befund P3.4 (⚠️): "VIX hoch = BEARISH" widerspricht Fear&Greed/Put-Call (contrarian); `ref = vix or vstoxx` weicht bei VIX=0.0 fälschlich aus. Lösung: VIX-Spike als contrarian-Kaufsignal (BULLISH), sehr niedriger VIX (Sorglosigkeit) als BEARISH; `is None`-Check.

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/sentiment/test_vix_agent.py`:
```python
from agents.market_cockpit.sentiment.vix_agent import _signal
from core.domain.models import Signal


def test_none_is_neutral():
    assert _signal(None, None) == Signal.NEUTRAL


def test_vix_spike_is_bullish_contrarian():
    # VIX > 30 = Panik = contrarian Kaufsignal → BULLISH (konsistent mit Sentiment-Block)
    assert _signal(35.0, None) == Signal.BULLISH


def test_low_vix_is_bearish_complacency():
    # VIX < 15 = Sorglosigkeit → BEARISH
    assert _signal(12.0, None) == Signal.BEARISH


def test_mid_vix_is_neutral():
    assert _signal(20.0, None) == Signal.NEUTRAL


def test_vix_zero_does_not_fall_back_to_vstoxx():
    # vix=0.0 ist gültig (kein Falsiness-Fallback auf vstoxx)
    assert _signal(0.0, 40.0) == Signal.BEARISH   # 0.0 < 15 → BEARISH, NICHT vstoxx
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/sentiment/test_vix_agent.py -q`.
- [ ] **Implementierung**:
```python
def _signal(vix: float | None, vstoxx: float | None) -> Signal:
    """
    Contrarian (konsistent mit Fear&Greed/Put-Call): VIX-Spike (>30) = Panik
    = Kaufgelegenheit → BULLISH; sehr niedriger VIX (<15) = Sorglosigkeit → BEARISH.
    `is None`-Check statt Falsiness (vix=0.0 ist gültig).
    """
    ref = vix if vix is not None else vstoxx
    if ref is None:
        return Signal.NEUTRAL
    if ref > 30:
        return Signal.BULLISH
    if ref < 15:
        return Signal.BEARISH
    return Signal.NEUTRAL
```
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/sentiment/test_vix_agent.py -q`.
- [ ] **Commit** — `fix(vix): contrarian-Konvention (Spike=BULLISH) + is None statt Falsiness (P3.4)`

**Self-Review:** Richtung jetzt domänenweit konsistent contrarian. Provider-Annahme unverändert (`^VIX`/`^V2TX`).

---

### Task 7 — Put/Call: relativ kalibrierte Schwellen

**Files:** `agents/market_cockpit/sentiment/put_call_agent.py`, `tests/agents/market_cockpit/sentiment/test_put_call_agent.py`

Befund P3.4 (⚠️): Schwellen 1.2/0.7 hängen von der gezogenen CBOE-Serie ab; mittleres P/C driftet säkular. Lösung: feste Total-CBOE-Serie dokumentieren; Schwellen via rollierendem Mittel ± z-Score statt fixer Absolutwerte (`zscore_vs_history`). Contrarian-Richtung bleibt.

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/sentiment/test_put_call_agent.py`:
```python
from agents.market_cockpit.sentiment.put_call_agent import _signal
from core.domain.models import Signal


def test_none_is_neutral():
    assert _signal(None) == Signal.NEUTRAL


def test_high_z_is_bullish_contrarian():
    # P/C deutlich über rollierendem Mittel (z > +1) = Pessimismus → BULLISH
    assert _signal(1.2) == Signal.BULLISH


def test_low_z_is_bearish_contrarian():
    # P/C deutlich unter Mittel (z < -1) = Sorglosigkeit → BEARISH
    assert _signal(-1.2) == Signal.BEARISH


def test_mid_z_is_neutral():
    assert _signal(0.3) == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/sentiment/test_put_call_agent.py -q`.
- [ ] **Implementierung** — `_signal` nimmt jetzt einen z-Score; Fetcher fest auf Total-Serie; `run()` berechnet z-Score gegen rollierende Historie:
```python
_Z = 1.0


def _signal(ratio_z: float | None) -> Signal:
    """
    Contrarian, relativ kalibriert: hohes P/C relativ zum rollierenden Mittel
    (z > +1) = Pessimismus → BULLISH; niedriges (z < -1) = Sorglosigkeit → BEARISH.
    Feste CBOE-Total-P/C-Serie; z-Score statt fixer 1.2/0.7 (säkularer Drift).
    """
    if ratio_z is None:
        return Signal.NEUTRAL
    if ratio_z > _Z:
        return Signal.BULLISH
    if ratio_z < -_Z:
        return Signal.BEARISH
    return Signal.NEUTRAL
```
Im `run()`: `_fetch_cboe_put_call` strikt auf die "TOTAL …PUT/CALL"-Spalte beschränken (kein Fallback auf "erste P/C-Spalte" mehr, sonst inkonsistente Serie); rollierende Tageshistorie der letzten N Tage sammeln, `ratio_z = zscore_vs_history(current, history)`. Snapshot-Feld `ratio` bleibt der Rohwert.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/sentiment/test_put_call_agent.py -q`.
- [ ] **Commit** — `fix(put_call): feste Total-Serie + z-Score-Schwellen statt fixer 1.2/0.7 (P3.4)`

**Self-Review:** Falls keine rollierende Historie verfügbar ist (nur Tageswert), liefert `zscore_vs_history` bei `< min_n` `None` → NEUTRAL (sauber, kein Schein-Signal). Annahme: Plan 0 `zscore_vs_history` gibt `None` unter `min_n` zurück.

---

### Task 8 — Sentiment Chief: Composite via `weighted_signal`

**Files:** `agents/market_cockpit/sentiment_chief_agent.py`, `core/domain/models.py` (`SentimentChiefResult` um `signal`), `tests/agents/market_cockpit/test_sentiment_chief.py`

Befund P3.4 (❌): keine Verdichtung; VIX-vs-Contrarian-Widerspruch ungelöst. Lösung: Nach den Tasks 6/7 sind alle drei contrarian-konsistent; `weighted_signal` aggregiert sie. Fear&Greed ist Stub → `SignalStatus.UNAVAILABLE`, fällt aus der Gewichtung.

- [ ] **Models erweitern** — `SentimentChiefResult` um `signal: Signal = Signal.NEUTRAL`.
- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/test_sentiment_chief.py`:
```python
from agents.market_cockpit.sentiment_chief_agent import _aggregate
from core.domain.models import Signal, SignalStatus


def test_two_bullish_one_unavailable_is_bullish():
    items = [
        (Signal.BULLISH, 0.45, SignalStatus.AVAILABLE),   # vix
        (Signal.NEUTRAL, 0.25, SignalStatus.UNAVAILABLE), # fear_greed stub
        (Signal.BULLISH, 0.30, SignalStatus.AVAILABLE),   # put_call
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.BULLISH


def test_all_unavailable_is_neutral():
    items = [
        (Signal.NEUTRAL, 0.45, SignalStatus.UNAVAILABLE),
        (Signal.NEUTRAL, 0.25, SignalStatus.UNAVAILABLE),
        (Signal.NEUTRAL, 0.30, SignalStatus.UNAVAILABLE),
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/test_sentiment_chief.py -q`.
- [ ] **Implementierung**:
```python
from core.domain.models import SentimentChiefResult, Signal, SignalStatus
from core.utils.aggregation import weighted_signal

_WEIGHTS = {"vix": 0.45, "fear_greed": 0.25, "put_call": 0.30}


def _aggregate(items):
    return weighted_signal(items)
```
Im `run()`: Status je Sub-Snapshot aus Rohdaten ableiten (VIX: `vix is None and vstoxx is None` → UNAVAILABLE; Fear&Greed: `value is None` → UNAVAILABLE; Put/Call: `ratio is None` → UNAVAILABLE), `overall, _ = weighted_signal([...])`, `signal=overall` in `SentimentChiefResult`. `default()` bekommt `signal=Signal.NEUTRAL`.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/test_sentiment_chief.py -q`.
- [ ] **Commit** — `feat(sentiment_chief): gewichtetes Sentiment-Composite via weighted_signal (P3.4)`

**Self-Review:** Fear&Greed-Stub zieht das Composite nicht mehr Richtung Mitte (UNAVAILABLE). Echte Anbindung von Fear&Greed bleibt Plan E.

---

### Task 9 — Yield Spread: 10Y-3M primär, Inversions-Lag

**Files:** `agents/market_cockpit/yield_curve/yield_spread_agent.py`, `tests/agents/market_cockpit/yield_curve/test_yield_spread_agent.py`

Befund P3.5 (⚠️): `ref = 10y2y` statt 10Y-3M (überlegener Prädiktor); Inversion sofort BEARISH ohne Lag/Steepening; arbiträre `>1.0`-BULLISH-Schwelle. Lösung: 10Y-3M als Primär-`ref`; Inversion = WARNUNG (nicht sofort BEARISH); BEARISH erst bei Bull-Steepening nach Inversion (Spread bewegt sich aus der Inversion heraus nach oben). Inversions-Lag im Docstring dokumentiert.

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/yield_curve/test_yield_spread_agent.py`:
```python
from agents.market_cockpit.yield_curve.yield_spread_agent import _point
from core.domain.models import Signal


def test_normal_positive_curve_is_neutral():
    pt = _point(s10y2y=0.8, s10y3m=0.9, s30y10y=None, prev_10y3m=0.9)
    assert pt.inverted is False
    assert pt.signal == Signal.NEUTRAL


def test_steep_curve_is_bullish():
    pt = _point(s10y2y=1.4, s10y3m=1.6, s30y10y=None, prev_10y3m=1.5)
    assert pt.signal == Signal.BULLISH


def test_fresh_inversion_is_neutral_warning_not_bearish():
    # Frisch invertiert, weiter fallend → Warnung, NICHT sofort BEARISH (Lag)
    pt = _point(s10y2y=-0.3, s10y3m=-0.4, s30y10y=None, prev_10y3m=-0.2)
    assert pt.inverted is True
    assert pt.signal == Signal.NEUTRAL


def test_bull_steepening_after_inversion_is_bearish():
    # Spread war invertiert (prev -0.5), versteilt sich aus der Inversion (-0.1) → Timing-Signal
    pt = _point(s10y2y=-0.1, s10y3m=-0.1, s30y10y=None, prev_10y3m=-0.5)
    assert pt.signal == Signal.BEARISH


def test_10y3m_is_primary_ref():
    # 10y2y positiv, aber 10y3m invertiert → Kurve gilt als invertiert (10y3m primär)
    pt = _point(s10y2y=0.2, s10y3m=-0.1, s30y10y=None, prev_10y3m=-0.2)
    assert pt.inverted is True


def test_all_none_is_neutral():
    pt = _point(s10y2y=None, s10y3m=None, s30y10y=None, prev_10y3m=None)
    assert pt.signal == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/yield_curve/test_yield_spread_agent.py -q`.
- [ ] **Implementierung** — `_point` um `prev_10y3m` erweitern, 10Y-3M primär, Lag/Steepening:
```python
_STEEP = 1.0   # ref > 1.0 = deutlich positive Kurve


def _point(s10y2y, s10y3m, s30y10y, prev_10y3m=None) -> YieldSpreadDataPoint:
    """
    10Y-3M als Primärspread (NY-Fed/Estrella — überlegener Rezessionsprädiktor).
    Inversions-LAG: Eine Inversion ist eine WARNUNG, kein sofortiges BEARISH —
    historisch laufen Aktien 6–18M nach Inversion weiter. Das eigentliche
    Timing-Signal (BEARISH) ist das Bull-Steepening: der Spread bewegt sich aus
    der Inversion heraus nach oben (prev < 0 und current > prev).
    """
    inverted = (s10y3m is not None and s10y3m < 0) or (s10y2y is not None and s10y2y < 0)
    ref = s10y3m if s10y3m is not None else s10y2y
    if ref is None:
        sig = Signal.NEUTRAL
    elif prev_10y3m is not None and prev_10y3m < 0 and ref > prev_10y3m:
        sig = Signal.BEARISH        # Bull-Steepening nach Inversion = Timing-Signal
    elif ref < 0:
        sig = Signal.NEUTRAL        # frische/fortlaufende Inversion = Warnung, kein BEARISH
    elif ref > _STEEP:
        sig = Signal.BULLISH
    else:
        sig = Signal.NEUTRAL
    return YieldSpreadDataPoint(
        spread_10y2y=s10y2y, spread_10y3m=s10y3m, spread_30y10y=s30y10y,
        inverted=inverted, signal=sig,
    )
```
Im `run()`: USA jetzt `_point(usa_10y2y, usa_10y3m, None, prev_10y3m=...)` — `prev_10y3m` aus einer datierten Spread-Historie (sofern Provider sie liefert) oder vorerst `None` (dann Lag/Steepening inaktiv, kein toter Code). EU/CH analog mit `prev_10y3m=None`.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/yield_curve/test_yield_spread_agent.py -q`.
- [ ] **Commit** — `fix(yield_spread): 10Y-3M primär + Inversions-Lag/Bull-Steepening-Logik (P3.5)`

**Self-Review:** Bei `prev_10y3m=None` bleibt das Verhalten wohldefiniert (Inversion → NEUTRAL-Warnung), kein toter Code. Annahme: Provider kann optional einen Vorperioden-Spread liefern; falls nicht, bleibt der Parameter `None`.

---

### Task 10 — Sovereign Spread: nur Peripherie in systemischer Zählung

**Files:** `agents/market_cockpit/yield_curve/sovereign_spread_agent.py`, `tests/agents/market_cockpit/yield_curve/test_sovereign_spread_agent.py` (erweitern)

Befund D3 (✅ mit Einschränkung): Die "3 Länder >200bp"-Zählung wirft Kernländer (NL/FI/AT/LU) mit Peripherie zusammen. Lösung: separate `_PERIPHERY`-Menge für die systemische Zählung; der max-Spread-Trigger (>300bp Krise) bleibt über alle Stress-Länder.

- [ ] **Failing Test schreiben** — bestehende Datei erweitern:
```python
from agents.market_cockpit.yield_curve.sovereign_spread_agent import _signal, _PERIPHERY


def test_core_countries_not_counted_in_systemic_rule():
    # 2 Peripherie >200 + 1 Kernland (NL) >200 → NICHT systemisch (nur Peripherie zählt)
    spreads = {"IT_10y": 210.0, "ES_10y": 220.0, "NL_10y": 205.0, "FR_10y": 60.0}
    assert _signal(spreads) == Signal.NEUTRAL


def test_three_periphery_above_200_is_bearish():
    spreads = {"IT_10y": 210.0, "ES_10y": 220.0, "PT_10y": 230.0, "NL_10y": 30.0}
    assert _signal(spreads) == Signal.BEARISH


def test_periphery_set_excludes_core():
    assert "IT" in _PERIPHERY and "NL" not in _PERIPHERY and "FI" not in _PERIPHERY
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/yield_curve/test_sovereign_spread_agent.py -q`.
- [ ] **Implementierung**:
```python
# Peripherie für die systemische "3+ Länder >200bp"-Zählung (Kernländer ausgenommen)
_PERIPHERY = {"IT", "ES", "PT", "GR", "IE", "SI", "SK", "HR"}


def _signal(spreads: dict[str, float | None]) -> Signal:
    """BEARISH wenn max Stress-Spread > 300bp (Krise) ODER 3+ PERIPHERIE-Länder > 200bp."""
    stress_values = [v for k, v in spreads.items()
                     if v is not None and k.split("_")[0] in _STRESS_COUNTRIES]
    if not stress_values:
        return Signal.NEUTRAL
    if max(stress_values) > 300:
        return Signal.BEARISH
    periphery_high = sum(
        1 for k, v in spreads.items()
        if v is not None and k.split("_")[0] in _PERIPHERY and v > 200
    )
    if periphery_high >= 3:
        return Signal.BEARISH
    return Signal.NEUTRAL
```
Bestehende Tests (`test_signal_bearish_when_3_countries_above_200` mit IT/ES/PT) bleiben grün, da alle drei Peripherie sind.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/yield_curve/test_sovereign_spread_agent.py -q`.
- [ ] **Commit** — `fix(sovereign_spread): nur Peripherie in systemischer 3×>200bp-Zählung (D3)`

**Self-Review:** Der bestehende Test mit IT/ES/PT/FR/AT bleibt gültig (drei Peripherie). FR bleibt im `_STRESS_COUNTRIES`-Set für den max-Trigger, zählt aber nicht zur systemischen Regel.

---

### Task 11 — Yield Curve Chief: konsolidiertes Signal

**Files:** `agents/market_cockpit/yield_curve_chief_agent.py`, `core/domain/models.py` (`YieldCurveChiefResult` um `signal`), `tests/agents/market_cockpit/test_yield_curve_chief.py`

Befund P3.3 (⚠️): reines Einsammeln, kein konsolidiertes Zinskurven-Gesamtsignal. Lösung: `weighted_signal` aus US-Kurven-Status (10Y-3M-Punkt) und EU-Sovereign-Stress. UNAVAILABLE wenn keine Spreads vorliegen.

- [ ] **Models erweitern** — `YieldCurveChiefResult` um `signal: Signal = Signal.NEUTRAL`.
- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/test_yield_curve_chief.py`:
```python
from agents.market_cockpit.yield_curve_chief_agent import _aggregate
from core.domain.models import Signal, SignalStatus


def test_us_bearish_plus_eu_stress_is_bearish():
    items = [
        (Signal.BEARISH, 0.60, SignalStatus.AVAILABLE),   # us curve
        (Signal.BEARISH, 0.40, SignalStatus.AVAILABLE),   # eu sovereign
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.BEARISH


def test_missing_us_curve_uses_eu_only():
    items = [
        (Signal.NEUTRAL, 0.60, SignalStatus.UNAVAILABLE),
        (Signal.BEARISH, 0.40, SignalStatus.AVAILABLE),
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.BEARISH
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/test_yield_curve_chief.py -q`.
- [ ] **Implementierung** — `_aggregate = weighted_signal`; im `run()` US-Status aus `yield_spreads.usa.signal`/Spread-Vorhandensein, EU-Status aus `sovereign_spreads.signal`/`spreads_by_country`, `signal=overall`. `default()` → `signal=Signal.NEUTRAL`.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/test_yield_curve_chief.py -q`.
- [ ] **Commit** — `feat(yield_curve_chief): konsolidiertes Zinskurven-Signal via weighted_signal (P3.3)`

**Self-Review:** Gewichte US 0.60 / EU 0.40 (US-Kurve als primärer Rezessionsprädiktor). UNAVAILABLE-Re-Normalisierung übernimmt `weighted_signal`.

---

### Task 12 — Inflation: Lücke 3–4% schließen, `trend` aktivieren, `real_rate_10y` einbinden

**Files:** `agents/market_cockpit/macro/inflation_agent.py`, `tests/agents/market_cockpit/macro/test_inflation_agent.py` (erweitern)

Befund P4.4/P4.5 (⚠️): 3–4% fällt durch beide Zweige → fälschlich NEUTRAL; `trend` reserviert aber inaktiv; `real_rate_10y` ungenutzt. Lösung: Bänder lückenlos (3–4% = "erhöht/leicht bearish"); `trend` als Modifikator (fallende über Ziel ≠ steigende); hoher Realzins (>2%) verstärkt Richtung BEARISH. **Wichtig:** Die bestehenden Tests erwarten `_signal(3.5) == NEUTRAL` und `_signal(3.5, ppi=2.0) == NEUTRAL` — diese werden im Test-File auf die neue lückenlose Semantik (3.5 → BEARISH bei stable/rising) angepasst.

- [ ] **Failing Test schreiben** — bestehende Datei anpassen/erweitern (3–4%-Lücke jetzt definiert):
```python
def test_cpi_3_5_stable_is_bearish_no_gap():
    # 3.5% liegt jetzt in der "erhöht"-Klasse (lückenlos) → BEARISH bei stable
    assert _signal(3.5, trend="stable") == Signal.BEARISH

def test_cpi_3_5_falling_is_neutral():
    # 3.5% aber fallend (Δ über 3–6M negativ) → Momentum entschärft → NEUTRAL
    assert _signal(3.5, trend="falling") == Signal.NEUTRAL

def test_cpi_2_with_high_real_rate_is_bearish():
    # CPI im Ziel, aber Realzins >2% → Bewertungs-Gegenwind → BEARISH
    assert _signal(2.0, real_rate_10y=2.5) == Signal.BEARISH

def test_cpi_2_with_normal_real_rate_stays_bullish():
    assert _signal(2.0, real_rate_10y=0.5) == Signal.BULLISH
```
Die bestehenden Tests `test_cpi_3_5_is_neutral` und `test_neutral_cpi_low_ppi_stays_neutral` (Zeilen 28–29, 74–76) auf die neue Semantik umstellen (3.5% default-trend → BEARISH).
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/macro/test_inflation_agent.py -q`.
- [ ] **Implementierung** — `_signal` lückenlos + `trend` + `real_rate_10y`:
```python
def _signal(
    cpi: float | None,
    core_cpi: float | None = None,
    ppi: float | None = None,
    region: str = "usa",
    trend: str = "stable",          # "rising" | "falling" | "stable"
    real_rate_10y: float | None = None,
) -> Signal:
    if cpi is None:
        return Signal.NEUTRAL
    thr = _CH if region == "ch" else _USA_EU

    # Lückenlose Bänder: jeder Wert fällt in genau eine Klasse.
    if cpi < 0.0:
        sig = Signal.BEARISH                         # Deflation
    elif cpi < thr["low"]:
        sig = Signal.NEUTRAL                         # unter Ziel, keine Deflation
    elif cpi <= thr["high"]:
        sig = Signal.BULLISH                         # Zielzone
    elif cpi < thr["bearish"]:
        sig = Signal.BEARISH                         # erhöht (3–4%) — vormals blinde Lücke
    else:
        sig = Signal.BEARISH                         # klar über Ziel

    # Core-Abschwächung (transiente Inflation)
    if sig == Signal.BEARISH and core_cpi is not None and core_cpi <= thr["high"]:
        sig = Signal.NEUTRAL

    # Trend-Modifikator: über Ziel + fallend → entschärfen
    if sig == Signal.BEARISH and cpi > thr["high"] and trend == "falling":
        sig = Signal.NEUTRAL

    # PPI Pipeline-Inflation verstärkt NEUTRAL → BEARISH
    if sig == Signal.NEUTRAL and ppi is not None and ppi >= thr["bearish"]:
        sig = Signal.BEARISH

    # Realzins-Gegenwind: hoher Realzins drückt Bewertungen
    if real_rate_10y is not None and real_rate_10y > 2.0 and sig != Signal.BEARISH:
        sig = Signal.BEARISH

    return sig
```
Im `run()`: USA-`_signal(... , real_rate_10y=ext.get("real_rate_10y"))`; `trend` aus einer CPI-Historie ableiten, falls verfügbar (sonst `"stable"`).
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/macro/test_inflation_agent.py -q`.
- [ ] **Commit** — `fix(inflation): lückenlose Bänder (3–4%) + trend-Modifikator + real_rate_10y (P4.4/P4.5)`

**Self-Review:** Reihenfolge der Modifikatoren bewusst: Core entschärft zuerst, dann Trend, dann PPI-Verstärkung, zuletzt Realzins. `test_high_cpi_low_core_cpi_downgrades_to_neutral` (4.5%/Core 2.2%) bleibt grün (Core-Abschwächung greift vor Realzins). Annahme: `ext["real_rate_10y"]` existiert (Feld ist im Snapshot vorhanden).

---

### Task 13 — Money Supply: real zum nominalen BIP, Lücke 8–10%, `velocity`

**Files:** `agents/market_cockpit/macro/money_supply_agent.py`, `tests/agents/market_cockpit/macro/test_money_supply_agent.py`

Befund P3.2/P4.4/P4.5 (⚠️): Schwellen nominal; Lücke 8–10% → NEUTRAL; `velocity_m2` ungenutzt. Lösung: Überschuss-Liquidität = M-Wachstum − nominales BIP-Wachstum (`excess_over_nominal_gdp`); glockenförmige Bänder lückenlos; sinkende Velocity dämpft die Inflationswirkung.

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/macro/test_money_supply_agent.py`:
```python
from agents.market_cockpit.macro.money_supply_agent import _signal
from core.domain.models import Signal


def test_none_is_neutral():
    assert _signal(excess_liquidity=None, velocity_trend=None) == Signal.NEUTRAL


def test_moderate_excess_is_bullish():
    # 0–4% Überschuss-Liquidität = gesunde Expansion → BULLISH
    assert _signal(excess_liquidity=2.0, velocity_trend=None) == Signal.BULLISH


def test_excessive_liquidity_is_bearish():
    # >5% Überschuss = Inflations-/Blasenrisiko → BEARISH
    assert _signal(excess_liquidity=6.0, velocity_trend=None) == Signal.BEARISH


def test_contraction_is_bearish():
    # M wächst langsamer als BIP (negativ) = Liquiditätsentzug → BEARISH
    assert _signal(excess_liquidity=-3.0, velocity_trend=None) == Signal.BEARISH


def test_gap_region_no_longer_neutral():
    # vormalige 8–10%-Lücke: hier z.B. 4.5% Überschuss → eindeutig (BEARISH-Flanke)
    assert _signal(excess_liquidity=4.5, velocity_trend=None) == Signal.BEARISH


def test_excess_dampened_by_falling_velocity():
    # 6% Überschuss aber stark fallende Velocity → Inflationswirkung gedämpft → NEUTRAL
    assert _signal(excess_liquidity=6.0, velocity_trend="falling") == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/macro/test_money_supply_agent.py -q`.
- [ ] **Implementierung** — `_signal` glockenförmig lückenlos über die Überschuss-Liquidität:
```python
from core.utils.real_nominal import excess_over_nominal_gdp


def _signal(excess_liquidity: float | None, velocity_trend: str | None) -> Signal:
    """
    Glockenförmig über die ÜBERSCHUSS-LIQUIDITÄT (M-Wachstum − nominales BIP-Wachstum),
    lückenlos: moderater Überschuss (0–4pp) = gesund → BULLISH; exzessiv (>4pp) oder
    Kontraktion (<0) → BEARISH. Sinkende Velocity (MV=PQ) dämpft die Inflationswirkung
    hohen Wachstums → entschärft die obere Flanke.
    """
    if excess_liquidity is None:
        return Signal.NEUTRAL
    if 0.0 <= excess_liquidity <= 4.0:
        sig = Signal.BULLISH
    else:
        sig = Signal.BEARISH   # >4 (Blasenrisiko) ODER <0 (Kontraktion) — keine Lücke
    if sig == Signal.BEARISH and excess_liquidity > 4.0 and velocity_trend == "falling":
        sig = Signal.NEUTRAL   # hohe Geldmenge ohne Umlauf → keine Inflationswirkung
    return sig
```
Im `run()`: nominales BIP-Wachstum aus `state`/`ext` (z. B. real-BIP + CPI); `excess = excess_over_nominal_gdp(m_growth, nominal_gdp_growth)`; `velocity_trend` aus Velocity-Historie ableiten (sonst `None`). M3 (EU/CH) bevorzugt, sonst M2.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/macro/test_money_supply_agent.py -q`.
- [ ] **Commit** — `fix(money_supply): Überschuss-Liquidität zum nominalen BIP + lückenlos + velocity (P3.2/P4.4)`

**Self-Review:** Lücke 8–10% existiert nicht mehr (eine Schwelle bei +4pp Überschuss). `excess_over_nominal_gdp` aus Plan 0 konsumiert. Annahme: nominales BIP-Wachstum ableitbar (real-BIP `gdp_growth` + CPI `inflation` aus `state`).

---

### Task 14 — Credit: real, glockenförmig, `money_velocity`

**Files:** `agents/market_cockpit/macro/credit_agent.py`, `tests/agents/market_cockpit/macro/test_credit_agent.py`

Befund P3.2/D1 (⚠️): monoton "mehr Kredit = besser", nominal; exzessives Wachstum (>15–20%) als Krisensignal ignoriert; `money_velocity` ungenutzt. Lösung: reales Kreditwachstum (− CPI); glockenförmig (moderat positiv, exzessiv negativ); `money_velocity` als Snapshot-Feld bleibt, fließt aber nicht ins Signal (Doppelung mit money_supply vermeiden — dokumentieren).

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/macro/test_credit_agent.py`:
```python
from agents.market_cockpit.macro.credit_agent import _signal
from core.domain.models import Signal


def test_none_is_neutral():
    assert _signal(real_credit_growth=None) == Signal.NEUTRAL


def test_moderate_real_growth_is_bullish():
    # 2–8% reales Kreditwachstum = gesunde Expansion → BULLISH
    assert _signal(real_credit_growth=4.0) == Signal.BULLISH


def test_excessive_growth_is_bearish():
    # >12% real = Kreditboom = Krisen-Frühwarnung → BEARISH
    assert _signal(real_credit_growth=14.0) == Signal.BEARISH


def test_contraction_is_bearish():
    assert _signal(real_credit_growth=-1.0) == Signal.BEARISH


def test_low_positive_is_neutral():
    # 0–2% real = schwach, aber nicht negativ → NEUTRAL
    assert _signal(real_credit_growth=1.0) == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/macro/test_credit_agent.py -q`.
- [ ] **Implementierung**:
```python
from core.utils.real_nominal import to_real


def _signal(real_credit_growth: float | None) -> Signal:
    """
    Glockenförmig über das REALE Kreditwachstum (nominal − CPI): moderate
    Expansion (2–12%) = Liquidität → BULLISH; exzessiv (>12%) = Kreditboom /
    Krisen-Frühwarnung (BIS Credit-Gap) → BEARISH; Kontraktion (<0) → BEARISH;
    schwach (0–2%) → NEUTRAL.
    """
    if real_credit_growth is None:
        return Signal.NEUTRAL
    if real_credit_growth < 0.0:
        return Signal.BEARISH
    if real_credit_growth < 2.0:
        return Signal.NEUTRAL
    if real_credit_growth <= 12.0:
        return Signal.BULLISH
    return Signal.BEARISH
```
Im `run()`: `real = to_real(data.get("credit_growth"), data.get("inflation"))` (CPI aus `get_economic_state`, falls in `extended_state` nicht vorhanden → zusätzlicher Aufruf oder `0.0`-Fallback dokumentieren); `signal=_signal(real)`. `money_velocity`-Feld bleibt erhalten.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/macro/test_credit_agent.py -q`.
- [ ] **Commit** — `fix(credit): reales Kreditwachstum + glockenförmig (Kreditboom=BEARISH) (P3.2)`

**Self-Review:** Voller Credit-to-GDP-Gap (HP-Filter) bleibt out-of-scope; die glockenförmige reale Variante adressiert die Kern-Befunde (monoton + nominal). Annahme: CPI für `to_real` zugänglich (sonst dokumentierter Fallback).

---

### Task 15 — Buffett Indicator: z-Score zur Landeshistorie, kein 135%-Fix

**Files:** `agents/market_cockpit/macro/buffett_indicator_agent.py`, `tests/agents/market_cockpit/macro/test_buffett_indicator_agent.py`

Befund P3.1 (⚠️): absolute 75/135%-Schwellen US-zentrisch (CH strukturell 200–250%); berechneter z-Score ungenutzt. Lösung: Klassifizierung über z-Score zur Landeshistorie (`zscore_vs_history`/eigener `_z_score`); Fallback länderspezifisch (kein globales 135%).

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/macro/test_buffett_indicator_agent.py`:
```python
from agents.market_cockpit.macro.buffett_indicator_agent import _signal_from_z
from core.domain.models import Signal


def test_none_z_is_neutral():
    assert _signal_from_z(None) == Signal.NEUTRAL


def test_high_z_is_bearish():
    # +1.5σ über eigener Landeshistorie → historisch teuer → BEARISH
    assert _signal_from_z(1.6) == Signal.BEARISH


def test_low_z_is_bullish():
    assert _signal_from_z(-1.6) == Signal.BULLISH


def test_mid_z_is_neutral():
    assert _signal_from_z(0.5) == Signal.NEUTRAL


def test_swiss_high_ratio_with_normal_z_is_neutral():
    # CH bei 230% aber z≈0 (für CH normal) → NICHT BEARISH (kein 135%-Fix mehr)
    assert _signal_from_z(0.1) == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/macro/test_buffett_indicator_agent.py -q`.
- [ ] **Implementierung** — neues `_signal_from_z`; das alte absolute `_signal` entfernen bzw. nur als länderspezifischer Fallback nutzen:
```python
_Z_HIGH = 1.5
_Z_LOW  = -1.5


def _signal_from_z(z: float | None) -> Signal:
    """
    Klassifizierung über den z-Score zur LANDESHISTORIE (Abweichung vom landeseigenen
    Mittel), NICHT über eine globale 75/135%-Schwelle. CH (strukturell 200–250%) und DE
    (50–60%) werden so korrekt relativ bewertet.
    """
    if z is None:
        return Signal.NEUTRAL
    if z >= _Z_HIGH:
        return Signal.BEARISH
    if z <= _Z_LOW:
        return Signal.BULLISH
    return Signal.NEUTRAL
```
Im `run()`: pro Land `z = _z_score(ratio, history)` (bestehende Funktion, ≥8 Punkte), `signal=_signal_from_z(z)`. USA-`signal` ebenfalls aus `usa_z`. Wo `z is None` (kurze Historie): länderspezifischer Fallback-Korridor (z. B. Landes-Median ±1σ aus `history`, falls vorhanden) statt globaler 75/135 — sonst NEUTRAL. `global_median` bleibt nur als Dashboard-Feld.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/macro/test_buffett_indicator_agent.py -q`.
- [ ] **Commit** — `fix(buffett_indicator): Signal aus z-Score zur Landeshistorie statt 135%-Fix (P3.1)`

**Self-Review:** Der bereits berechnete z-Score wird jetzt genutzt (P4.5). Bei fehlender Historie liefert die Logik NEUTRAL statt einer falschen US-Schwelle für CH/DE. Annahme: `get_buffett_history`/Weltbank-Historie liefert ≥8 Punkte für die wichtigen Länder.

---

### Task 16 — GDP: Sahm-Regel, Score normiert, ECB-Proxy entfernen

**Files:** `agents/market_cockpit/macro/gdp_agent.py`, `tests/agents/market_cockpit/macro/test_gdp_agent.py`

Befund P3.1/D1 (❌/⚠️): ECB-Unemployment als Industrieproduktions-Proxy (invers korreliert); Arbeitslosenschwellen 5/8% absolut statt NAIRU-relativ; BIP-Schwelle 2% länderblind; Score nicht auf vorhandene Indikatoren normiert. Lösung: Arbeitslosigkeit über Sahm-ähnliche Veränderung (Anstieg 3M-Schnitt ggü. 12M-Tief ≥0.5pp); BIP länderspezifisch; Score = Durchschnitt vorhandener Sub-Scores; ECB-Proxy-Zeile streichen.

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/macro/test_gdp_agent.py`:
```python
from agents.market_cockpit.macro.gdp_agent import _signal, _sahm_recession
from core.domain.models import Signal


def test_sahm_trigger_on_05pp_rise():
    # 3M-Schnitt 4.5% gegen 12M-Tief 3.9% = +0.6pp ≥ 0.5 → Rezessionssignal
    assert _sahm_recession(unemp_3m_avg=4.5, unemp_12m_low=3.9) is True


def test_sahm_no_trigger_below_05pp():
    assert _sahm_recession(unemp_3m_avg=4.2, unemp_12m_low=3.9) is False


def test_signal_normalizes_over_available_indicators():
    # Nur 2 Indikatoren vorhanden, beide positiv → BULLISH (Durchschnitt, nicht fixe Summe)
    assert _signal(gdp_above_trend=True, pmi=None, sahm=False) == Signal.BULLISH


def test_sahm_recession_forces_bearish():
    assert _signal(gdp_above_trend=True, pmi=55.0, sahm=True) == Signal.BEARISH


def test_all_none_is_neutral():
    assert _signal(gdp_above_trend=None, pmi=None, sahm=None) == Signal.NEUTRAL
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/macro/test_gdp_agent.py -q`.
- [ ] **Implementierung**:
```python
def _sahm_recession(unemp_3m_avg: float | None, unemp_12m_low: float | None) -> bool | None:
    """Sahm-Regel: 3M-Durchschnitts-Arbeitslosenquote ≥0.5pp über 12M-Tief = Rezession."""
    if unemp_3m_avg is None or unemp_12m_low is None:
        return None
    return (unemp_3m_avg - unemp_12m_low) >= 0.5


def _signal(gdp_above_trend: bool | None, pmi: float | None, sahm: bool | None) -> Signal:
    """
    Score normiert auf die ANZAHL vorhandener Indikatoren (Durchschnitt statt fixer
    Summenschwelle). BIP relativ zum länderspezifischen Trendwachstum (gdp_above_trend),
    Arbeitslosigkeit über die Sahm-Regel (sahm) statt absoluter 5/8%-Schwellen.
    """
    if sahm is True:
        return Signal.BEARISH        # Sahm-Trigger dominiert (harter Rezessionsindikator)
    scores = []
    if gdp_above_trend is not None:
        scores.append(1 if gdp_above_trend else -1)
    if pmi is not None:
        scores.append(1 if pmi > 52 else (-1 if pmi < 48 else 0))
    if sahm is False:
        scores.append(1)             # keine Rezession laut Sahm = leicht positiv
    if not scores:
        return Signal.NEUTRAL
    avg = sum(scores) / len(scores)
    return Signal.BULLISH if avg >= 0.5 else (Signal.BEARISH if avg <= -0.5 else Signal.NEUTRAL)
```
Im `run()`: die Proxy-Zeile `asyncio.to_thread(self.ecb.get_unemployment), # using unemployment as proxy` **entfernen** (`industrial_production` sauber `None`). BIP länderspezifisch (`gdp_above_trend = gdp_growth > trend_country`, z. B. USA 2.0, EU/CH 1.2). Sahm aus 3M-Schnitt + 12M-Tief der Arbeitslosenquote (sofern Historie verfügbar, sonst `None`).
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/macro/test_gdp_agent.py -q`.
- [ ] **Commit** — `fix(gdp): Sahm-Regel + normierter Score + ECB-Proxy entfernt (P3.1/D1)`

**Self-Review:** Die irreführende invers-korrelierte Proxy-Zuweisung ist weg (❌-Befund). Score-Normierung behebt die implizite Verschärfung bei fehlendem PMI. Annahme: Arbeitslosen-Historie für 3M-Schnitt/12M-Tief verfügbar; ohne sie bleibt `sahm=None` (Sub-Score entfällt, kein toter Code).

---

### Task 17 — Interest Rate: `DatedHistory` statt `_RATE_HISTORY`, real_rate EU/CH

**Files:** `agents/market_cockpit/macro/interest_rate_agent.py`, `tests/agents/market_cockpit/macro/test_interest_rate_agent.py`

Befund P3.7/P4.5 (❌/⚠️): `_RATE_HISTORY` misst Aufruffrequenz statt geldpolitischer Dynamik; EU/CH `real_rate=None` → "rising→bearish" toter Code. Lösung: Richtung aus `DatedHistory` (aktueller Wert vs. Wert vor N Monaten mit Datumsstempel); Realzins auch für EU/CH (Leitzins − HVPI/CH-CPI).

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/macro/test_interest_rate_agent.py`:
```python
from datetime import date
from agents.market_cockpit.macro.interest_rate_agent import _direction, _signal
from core.domain.models import Signal
from core.utils.timeseries_history import DatedHistory


def test_direction_rising_from_dated_history():
    h = DatedHistory([(date(2026, 1, 1), 4.0), (date(2026, 6, 1), 4.5)])
    assert _direction(current=4.5, history=h, months_back=3) == "rising"


def test_direction_falling_from_dated_history():
    h = DatedHistory([(date(2026, 1, 1), 5.0), (date(2026, 6, 1), 4.0)])
    assert _direction(current=4.0, history=h, months_back=3) == "falling"


def test_direction_stable_without_history():
    assert _direction(current=4.0, history=None, months_back=3) == "stable"


def test_signal_falling_negative_real_is_bullish():
    assert _signal(rate=2.0, direction="falling", real_rate=-0.5) == Signal.BULLISH


def test_signal_rising_high_real_is_bearish_for_eu_too():
    # real_rate jetzt auch für EU gesetzt → der Zweig ist kein toter Code mehr
    assert _signal(rate=3.5, direction="rising", real_rate=2.5) == Signal.BEARISH
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/macro/test_interest_rate_agent.py -q`.
- [ ] **Implementierung** — `_RATE_HISTORY` entfernen, `_direction` über `DatedHistory`:
```python
from datetime import date
from dateutil.relativedelta import relativedelta   # falls verfügbar; sonst manuelle Monatsdifferenz
from core.utils.real_nominal import to_real
from core.utils.timeseries_history import DatedHistory


def _direction(current: float | None, history: DatedHistory | None, months_back: int = 3) -> str:
    """Richtung aus DATIERTER Historie: aktueller Wert vs. Wert vor `months_back` Monaten."""
    if current is None or history is None:
        return "stable"
    ref_date = date.today() - relativedelta(months=months_back)
    prev = history.value_on_or_before(ref_date)
    if prev is None:
        return "stable"
    if current > prev:
        return "rising"
    if current < prev:
        return "falling"
    return "stable"


def _signal(rate: float | None, direction: str, real_rate: float | None) -> Signal:
    if rate is None:
        return Signal.NEUTRAL
    if direction == "falling" and (real_rate is None or real_rate < 0):
        return Signal.BULLISH
    if direction == "rising" and real_rate is not None and real_rate > 2.0:
        return Signal.BEARISH
    return Signal.NEUTRAL
```
Im `run()`: prozess-globales `_RATE_HISTORY` löschen; je Region eine `DatedHistory` aus dem Provider beziehen (sofern eine datierte Zins-Reihe verfügbar ist; andernfalls `None` → `"stable"`, kein State-Leak). EU-Realzins `to_real(ecb_rate, ecb_cpi)`, CH-Realzins `to_real(snb_rate, snb_cpi)` (CPI über die jeweiligen Provider).
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/macro/test_interest_rate_agent.py -q`.
- [ ] **Commit** — `fix(interest_rate): DatedHistory-Richtung + real_rate für EU/CH (P3.7/P4.5)`

**Self-Review:** Kein prozess-globaler Zustand mehr — die Richtung misst echte Vorperioden-Dynamik. Der "rising→bearish"-Zweig ist für EU/CH kein toter Code mehr. Annahme: `DatedHistory.value_on_or_before(date)` aus Plan 0; datierte Zinsreihe pro Region optional (sonst `None`). Falls `dateutil` nicht im Projekt ist, Monatsdifferenz manuell berechnen.

---

### Task 18 — Regime: Deflation negativ, Gewichte = 1.0, datierte History, Sub-Signale optional

**Files:** `core/domain/regime.py`, `tests/domain/test_regime.py`

Befunde D1/D8: Deflation (<1%) = 0.0 statt negativ; Gewichtssumme 1.17 (effektive Gewichte datenabhängig); Trend aus prozess-globaler History (`current − mean`) misst Aufruffrequenz; Sub-Signale fließen nicht ein. Lösung: Inflations-Score als Glocke um 2% mit negativen Flanken beidseitig; Gewichte auf Summe 1.0 normieren; datierte Composite-History (max. 1 Eintrag/Periode); optionale gewichtete Sub-Signal-Indikatoren.

- [ ] **Failing Test schreiben** — `tests/domain/test_regime.py`:
```python
from core.domain.regime import _score_indicator, INDICATOR_WEIGHTS


def test_deflation_scores_negative():
    # <1% Inflation (Deflation) jetzt negativ statt 0.0
    assert _score_indicator("inflation", 0.3) < 0.0


def test_target_inflation_scores_positive():
    assert _score_indicator("inflation", 2.0) > 0.0


def test_high_inflation_scores_negative():
    assert _score_indicator("inflation", 7.0) < 0.0


def test_weights_sum_to_one():
    assert abs(sum(INDICATOR_WEIGHTS.values()) - 1.0) < 1e-6
```
- [ ] **Run → FAIL** — `python -m pytest tests/domain/test_regime.py -q`.
- [ ] **Implementierung**:
  1. Inflations-Regel als Glocke mit negativen Flanken:
```python
"inflation": lambda v: (
    0.5 if 1.5 <= v <= 2.5 else
    (-0.5 if (1.0 <= v < 1.5 or 2.5 < v <= 4.0) else -1.0)
),   # Deflation (<1) UND hohe Inflation (>4) beide negativ
```
  2. `INDICATOR_WEIGHTS` auf Summe 1.0 normieren (alle Werte durch die aktuelle Summe teilen; Verhältnisse beibehalten) und im Kommentar die Re-Normalisierung bei fehlenden Keys dokumentieren (bleibt über `weight_total` im `detect()`).
  3. Composite-History datieren: `_save_history`/`_load_history` auf `[(iso_date, value)]` umstellen, beim Speichern max. einen Eintrag pro Tag/Periode (überschreibt denselben Tag), `_trend` als einfache Steigung der letzten N datierten Punkte statt `current − mean`.
  4. `detect(state, sub_signals=None)`: optionaler Parameter; nicht-`None`-Sub-Signale (z. B. money_supply/credit/labor/buffett als ±1.0) mit kleinen Gewichten in `weighted_sum`/`weight_total` aufnehmen.
- [ ] **Run → PASS** — `python -m pytest tests/domain/test_regime.py -q`.
- [ ] **Commit** — `fix(regime): Deflation negativ + Gewichte=1.0 + datierte History + optionale Sub-Signale (D1/D8)`

**Self-Review:** Glocke um 2% behebt den Deflations-Befund symmetrisch. Gewichts-Normierung macht die effektiven Gewichte datenunabhängiger; die `weight_total`-Re-Normalisierung bei fehlenden Keys bleibt bewusst erhalten und dokumentiert. Sub-Signal-Parameter ist optional → keine bestehenden Aufrufe brechen.

---

### Task 19 — Macro Chief: Sub-Signale ins Regime, Yield-Mapping umbenennen

**Files:** `agents/market_cockpit/macro_chief_agent.py`, `core/domain/regime.py` (Key-Rename konsistent), `tests/agents/market_cockpit/test_macro_chief.py`

Befund D1 (⚠️): 7 Sub-Signale ohne Regime-Einfluss; `yield_curve_3m_usa` irreführend benannt + Doppelzählung der US-Kurve. Lösung: Sub-Signale (money_supply, credit, labor, buffett) als `sub_signals` an `detect()` durchreichen; Key `yield_curve_3m_usa` → `yield_curve_10y3m_usa`; 10y-2y-Gewicht abwerten/entfernen zugunsten 10Y-3M (in Task 18-Gewichten bereits 1.0-normiert berücksichtigen).

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/test_macro_chief.py`:
```python
from core.domain.regime import _score_indicator, INDICATOR_WEIGHTS


def test_yield_key_renamed():
    # alter irreführender Key weg, neuer da
    assert "yield_curve_3m_usa" not in INDICATOR_WEIGHTS
    assert "yield_curve_10y3m_usa" in INDICATOR_WEIGHTS
```
(Plus ein MagicMock-Agententest im Stil von `test_credit_labor_error_handling.py`, der prüft, dass `detect` mit `sub_signals=` aufgerufen wird — via `unittest.mock.patch` auf `RegimeDetector.detect`.)
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/test_macro_chief.py -q`.
- [ ] **Implementierung**:
  1. In `regime.py` (Task 18 fortführend): `yield_curve_3m_usa` → `yield_curve_10y3m_usa` in `_score_indicator`-rules UND `INDICATOR_WEIGHTS`; 10y-2y-Gewicht (`yield_curve`) reduzieren oder entfernen (Doppelzählung), Summe wieder auf 1.0.
  2. In `macro_chief_agent.run()`: `_add("yield_curve_10y3m_usa", usa_spreads.get("10y3m"))`; aus den Sub-Snapshots die Signale extrahieren und als `sub_signals`-Dict an `self._detector.detect(state, sub_signals=...)` geben (z. B. `{"money_supply": money_supply.usa.signal, "credit": credit.usa.signal, "labor": labor_income.usa.signal, "buffett": buffett_indicator.signal}`).
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/test_macro_chief.py -q`.
- [ ] **Commit** — `fix(macro_chief): Sub-Signale ins Regime + Yield-Key 10y3m_usa entzerren (D1)`

**Self-Review:** Sub-Signale haben jetzt Regime-Einfluss (Befund behoben). Doppelzählung der US-Kurve aufgelöst durch Abwertung/Entfernen des 10y-2y-Gewichts. Annahme: `detect` akzeptiert nach Task 18 den optionalen `sub_signals`-Parameter.

---

### Task 20 — Sector Performance: relative Stärke vs. Benchmark + XLC

**Files:** `agents/market_cockpit/sector/sector_performance_agent.py`, `tests/agents/market_cockpit/sector/test_sector_performance_agent.py`

Befund P3.6/D3 (⚠️): "leading/lagging" = absolutes Return ohne Benchmark → Beta-Artefakt (tautologisch); XLC (Communication Services) fehlt; 1M rauschanfällig. Lösung: relative Stärke = Sektor-Return − Benchmark-Return (SPY/STOXX600); XLC ergänzen; mehrere Fenster (1M/3M) kombinierbar.

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/sector/test_sector_performance_agent.py`:
```python
from agents.market_cockpit.sector.sector_performance_agent import _relative_strength, USA_SECTORS


def test_relative_strength_subtracts_benchmark():
    perf = {"Technology": 5.0, "Utilities": 1.0}
    rs = _relative_strength(perf, benchmark_return=3.0)
    assert rs["Technology"] == 2.0
    assert rs["Utilities"] == -2.0


def test_leading_is_highest_relative_not_absolute():
    # Tech +5 abs, aber Benchmark +6 → RS negativ; Utilities +1 abs, RS -5 → Tech führt relativ
    perf = {"Technology": 5.0, "Utilities": 1.0}
    rs = _relative_strength(perf, benchmark_return=6.0)
    assert max(rs, key=rs.get) == "Technology"


def test_xlc_in_universe():
    assert "CommServices" in USA_SECTORS and USA_SECTORS["CommServices"] == "XLC"
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/sector/test_sector_performance_agent.py -q`.
- [ ] **Implementierung**:
```python
def _relative_strength(perf: dict[str, float], benchmark_return: float | None) -> dict[str, float]:
    """Relative Stärke = Sektor-Return − Benchmark-Return (entfernt das Markt-Beta-Artefakt)."""
    if benchmark_return is None:
        return dict(perf)
    return {name: round(ret - benchmark_return, 2) for name, ret in perf.items()}
```
- `USA_SECTORS` um `"CommServices": "XLC"` ergänzen.
- Im `run()`: Benchmark-Historie (`SPY` für USA, `^STOXX` o. ä. für EU) laden, `_pct_return` darauf anwenden, `usa_rs = _relative_strength(usa_perf, spy_return)` und `eu_rs` analog; `leading_usa = max(usa_rs, key=usa_rs.get)` etc. auf den RS-Werten. Snapshot `usa`/`eurozone` können weiterhin die absoluten Returns tragen (Dashboard), aber leading/lagging aus RS.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/sector/test_sector_performance_agent.py -q`.
- [ ] **Commit** — `fix(sector_performance): relative Stärke vs. Benchmark + XLC (P3.6)`

**Self-Review:** leading/lagging ist kein Beta-Artefakt mehr. Annahme: `SPY`/Benchmark-Ticker über denselben `get_price_history` verfügbar; bei fehlendem Benchmark fällt RS auf absolute Returns zurück (kein Crash).

---

### Task 21 — Sector Rotation: "Gold" entfernen, Top-N-Alignment

**Files:** `agents/market_cockpit/sector/sector_rotation_agent.py`, `tests/agents/market_cockpit/sector/test_sector_rotation_agent.py`

Befund D3 (✅ mit Einschränkung): DEPRESSION empfiehlt "Gold" (kein Sektor → toter Match); Alignment nur gegen den einen Top-Sektor. Lösung: "Gold" aus der Sektor-Map entfernen; Alignment über den Anteil empfohlener Sektoren in den Top-N (z. B. Top-3).

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/sector/test_sector_rotation_agent.py`:
```python
from agents.market_cockpit.sector.sector_rotation_agent import ROTATION_MAP, _alignment
from core.domain.models import MarketRegime, Signal


def test_gold_removed_from_depression():
    assert "Gold" not in ROTATION_MAP[MarketRegime.DEPRESSION]["recommended"]


def test_alignment_uses_top_n():
    rec = ["Technology", "ConsumerDisc", "Financials"]
    avoid = ["Utilities"]
    # 2 von 3 Top-Sektoren empfohlen → aligned
    al, sig = _alignment(["Technology", "Financials", "Energy"], rec, avoid)
    assert al == "aligned" and sig == Signal.BULLISH


def test_alignment_contradicting_when_top_in_avoid():
    al, sig = _alignment(["Utilities", "ConsumerStap", "Healthcare"], ["Technology"], ["Utilities", "ConsumerStap"])
    assert al == "contradicting" and sig == Signal.BEARISH
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/sector/test_sector_rotation_agent.py -q`.
- [ ] **Implementierung**:
  - DEPRESSION-`recommended` auf `["ConsumerStap", "Healthcare", "Utilities"]` (kein "Gold").
  - `_alignment(top_sectors, recommended, avoid)`:
```python
def _alignment(top_sectors, recommended, avoid):
    rec_hits   = sum(1 for s in top_sectors if s in recommended)
    avoid_hits = sum(1 for s in top_sectors if s in avoid)
    if rec_hits >= 2 and rec_hits >= avoid_hits:
        return "aligned", Signal.BULLISH
    if avoid_hits >= 2 and avoid_hits > rec_hits:
        return "contradicting", Signal.BEARISH
    return "neutral", Signal.NEUTRAL
```
  - `run(regime, top_sectors: list[str])` statt `leading_sector: str` (Top-3-Liste); Aufrufer (Task 22) anpassen.
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/sector/test_sector_rotation_agent.py -q`.
- [ ] **Commit** — `fix(sector_rotation): Gold entfernt + Top-N-Alignment (D3)`

**Self-Review:** Toter "Gold"-Match weg; Alignment robuster (Top-3 statt Spitzensektor). Die Signatur-Änderung `run()` wird in Task 22 mitgezogen.

---

### Task 22 — Sector Chief: EU-Sektoren einbeziehen

**Files:** `agents/market_cockpit/sector_chief_agent.py`, `tests/agents/market_cockpit/test_sector_chief.py`

Befund D3 (⚠️): Rotation nur mit `performance.leading_usa` — `leading_eu` ignoriert, obwohl berechnet (für ein EU/CH-System eine echte Lücke). Lösung: Top-N je Region bilden und beide an die Rotation geben (z. B. kombinierte Top-Liste USA+EU oder eigene Rotation je Region; hier: kombinierte Top-N).

- [ ] **Failing Test schreiben** — `tests/agents/market_cockpit/test_sector_chief.py`:
```python
from agents.market_cockpit.sector_chief_agent import _top_sectors


def test_top_sectors_combines_us_and_eu():
    perf = type("P", (), {})()
    perf.usa = {"Technology": 5.0, "Energy": 4.0, "Utilities": 1.0}
    perf.eurozone = {"Financials": 6.0, "Healthcare": 2.0}
    top = _top_sectors(perf, n=3)
    # höchste relative Werte über beide Regionen
    assert "Financials" in top and "Technology" in top
```
- [ ] **Run → FAIL** — `python -m pytest tests/agents/market_cockpit/test_sector_chief.py -q`.
- [ ] **Implementierung**:
```python
def _top_sectors(performance, n: int = 3) -> list[str]:
    """Kombinierte Top-N-Sektoren über USA UND Eurozone (EU war zuvor ignoriert)."""
    merged: dict[str, float] = {}
    for region in (performance.usa or {}, performance.eurozone or {}):
        for name, ret in region.items():
            merged[name] = max(merged.get(name, float("-inf")), ret)
    return sorted(merged, key=merged.get, reverse=True)[:n]
```
- Im `run()`: `top = _top_sectors(performance, 3)`; `rotation = self.sector_rotation_agent.run(regime, top)` (neue Top-N-Signatur aus Task 21).
- [ ] **Run → PASS** — `python -m pytest tests/agents/market_cockpit/test_sector_chief.py -q`.
- [ ] **Commit** — `fix(sector_chief): EU-Sektoren in Rotation einbeziehen (D3)`

**Self-Review:** Rotation ist nicht mehr rein US-getrieben. Annahme: `performance.usa`/`eurozone` tragen die (relativen) Returns aus Task 20.

---

### Task 23 — Top-Down-Context: länderspezifischer Buffett-Fallback

**Files:** `core/domain/top_down_context.py`, `tests/domain/test_top_down_context.py`

Befund P3.1/D8 (✅ mit Einschränkung): absolute Buffett-Fallback-Schwellen (75/135%) nicht länderspezifisch — der z-Score-Pfad mildert das, der Fallback nicht. Lösung: länderspezifische Fallback-Korridore (z. B. CH ~200/250, DE ~50/70) statt globaler 75/135; z-Score-Pfad bleibt primär.

- [ ] **Failing Test schreiben** — `tests/domain/test_top_down_context.py`:
```python
from core.domain.top_down_context import _buffett_fallback_note


def test_swiss_fallback_uses_ch_corridor():
    # CH bei 230% ohne z-Score → mit CH-Korridor NICHT als "teuer" (>135) markiert
    notes = _buffett_fallback_note("CHE", ratio=230.0)
    assert notes == []   # 230 liegt im CH-Normalkorridor


def test_swiss_fallback_flags_extreme():
    notes = _buffett_fallback_note("CHE", ratio=300.0)
    assert notes and "teuer" in notes[0].lower()


def test_german_fallback_uses_de_corridor():
    # DE bei 90% ist für DE bereits erhöht (Korridor ~50–70)
    notes = _buffett_fallback_note("DEU", ratio=90.0)
    assert notes and "erhöht" in notes[0].lower() or "teuer" in notes[0].lower()


def test_us_fallback_unchanged():
    notes = _buffett_fallback_note("USA", ratio=200.0)
    assert notes and "teuer" in notes[0].lower()
```
- [ ] **Run → FAIL** — `python -m pytest tests/domain/test_top_down_context.py -q`.
- [ ] **Implementierung** — länderspezifische Korridore + `_buffett_fallback_note`, eingebunden in `_buffett_notes` (z-Score-Pfad bleibt vorrangig):
```python
# Länderspezifische Buffett-Fallback-Korridore (bullish_unter, bearish_über) in %
_BUFFETT_CORRIDORS: dict[str, tuple[float, float]] = {
    "USA": (75.0, 135.0),
    "CHE": (150.0, 260.0),    # CH strukturell hoch (SMI-Schwergewichte)
    "DEU": (40.0, 70.0),      # DE strukturell niedrig
    "FRA": (60.0, 110.0),
    "ITA": (20.0, 50.0),
}
_BUFFETT_DEFAULT_CORRIDOR = (75.0, 135.0)


def _buffett_fallback_note(code: str, ratio: float) -> list[str]:
    low, high = _BUFFETT_CORRIDORS.get(code, _BUFFETT_DEFAULT_CORRIDOR)
    label = f"Buffett-Indikator {code}"
    if ratio > high:
        return [f"{label} {ratio:.0f}% — Markt teuer (>{high:.0f}% für {code})"]
    if ratio < low:
        return [f"{label} {ratio:.0f}% — Markt günstig (<{low:.0f}% für {code})"]
    return []
```
In `_buffett_notes`: wenn `z is None`, statt der globalen 75/135-Schwellen `_buffett_fallback_note(code, r)` aufrufen. (`test_german_fallback`: 90 > 70 → "teuer".)
- [ ] **Run → PASS** — `python -m pytest tests/domain/test_top_down_context.py -q`.
- [ ] **Commit** — `fix(top_down_context): länderspezifischer Buffett-Fallback-Korridor (P3.1/D8)`

**Self-Review:** Der Fallback klassifiziert CH/DE nicht mehr mit US-Schwellen falsch. Test `test_german_fallback`: 90% liegt über DE-`high`=70 → "teuer" (das `or` im assert deckt beide zulässigen Labels ab). z-Score-Pfad unverändert primär.

---

## Abdeckung

Jeder Befund aus den Domänen 1–3 (inkl. der referenzierten Teil-B-Punkte) ist genau einer Task zugeordnet:

| Befund (Domäne / Teil-B-Punkt) | Task |
|---|---|
| P2.4 / D2-Energy — Niveau→Momentum, WTI/Brent, Gas | 1 |
| P2.4 / D2 — Industrial Metals Niveau→Momentum, Copper/Gold, Einheiten-Falle, Al/Zn/Ni | 2 |
| D2 — Agricultural endpunktsensitiv + ±20% nicht vol-adjustiert | 3 |
| D7 / D2 — Precious-Metals-Macro veraltete GS-Schwellen, Gold/Platin 1.0, Gold-Momentum | 4 |
| D2 — Commodity-Chief ohne Gewichtung/Gesamtsignal | 5 |
| P3.4 — VIX Momentum-vs-Contrarian-Inkonsistenz, `is None` | 6 |
| P3.4 — Put/Call nicht auf feste CBOE-Serie kalibriert | 7 |
| P3.4 — Sentiment-Chief ohne Verdichtung (`weighted_signal`) | 8 |
| P3.5 — Yield-Spread 10Y-2Y statt 10Y-3M, kein Inversions-Lag | 9 |
| D3 — Sovereign-Spread Kernländer in systemischer Zählung | 10 |
| P3.3 — Yield-Curve-Chief ohne konsolidiertes Signal | 11 |
| P4.4 / P4.5 — Inflation Lücke 3–4%, `trend` inaktiv, `real_rate_10y` ungenutzt | 12 |
| P3.2 / P4.4 / P4.5 — Money-Supply nominal, Lücke 8–10%, `velocity` ungenutzt | 13 |
| P3.2 / D1 — Credit nominal + monoton (Kreditboom), `money_velocity` | 14 |
| P3.1 / P4.5 — Buffett 135%-Fix, Z-Score ungenutzt | 15 |
| P3.1 / D1 — GDP ECB-Proxy (❌), Arbeitslosigkeit absolut, Score nicht normiert | 16 |
| P3.7 / P4.5 — Interest-Rate `_RATE_HISTORY`, real_rate EU/CH toter Code | 17 |
| D1 / D8 — Regime Deflation=0.0, Gewichte 1.17, prozess-globale History | 18 |
| D1 / P3.3 — Macro-Chief Sub-Signale ohne Regime, Yield-Key Doppelzählung | 19 |
| P3.6 / D3 — Sector-Performance Beta-Artefakt (kein Benchmark), XLC fehlt | 20 |
| D3 — Sector-Rotation toter "Gold"-Match, nur Top-1-Alignment | 21 |
| D3 — Sector-Chief EU-Sektoren ignoriert | 22 |
| P3.1 / D8 — Top-Down-Context Buffett-Fallback nicht länderspezifisch | 23 |

**Bewusst out-of-scope (eigene Pläne, im Plan benannt):** Fear&Greed-Datenquelle (Stub → Plan E); voller Credit-to-GDP-Gap (HP-Filter); echter Spot-/TR-Agrarindex (Roll-Yield); Backtester/Confidence/Statistik-Härtung (Domäne 8, Teil B 1.x/4.1); CAPE-Verschiebung (Index-Domäne). Diese sind in den Self-Reviews der betroffenen Tasks als Einschränkung notiert, damit keine Scheinpräzision suggeriert wird.
