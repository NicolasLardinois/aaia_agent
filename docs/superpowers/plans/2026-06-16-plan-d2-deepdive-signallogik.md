# Plan D2 — Deep-Dive-Signallogik (Equity & Index-Momentum) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die fachlich fehlerhaften Signal-Logiken im Equity-Deep-Dive (`fundamentals`, `quality`, `earnings_trend`, `insider`, `short_interest`, `moat`) und im Index-Momentum (`index_momentum`) nach den CFA-Review-Befunden (Domäne 4 + Domäne 6 Momentum/Chief) reparieren: sektor-relative statt absoluter Schwellen, Neutralisierung von negativem/None-EPS, CAPE-Entfernung auf Einzelaktien-Ebene, Piotroski-F-Score + ROIC−WACC-Spread, SUE statt binärer Beat-Rate, wertgewichtete Insider-Aktivität, kombiniertes Short-Squeeze-Signal, Maximum-statt-Summen-Moat-Logik (entkoppelt von der Aktien-Empfehlung), Wilder-RSI + MA200 aus ≥2y + Trend-Status-Signal. `equity_chief` und `index_chief` verdichten ihre Sub-Signale erstmals via `weighted_signal` zu einer gewichteten Gesamtbeurteilung und reichen `sector` an alle sektor-sensitiven Sub-Agenten weiter.

**Architecture:** EDA + Hexagonal. Reine Signal-Helfer bleiben Modul-Funktionen je Agent; wiederverwendbare quantitative Bausteine (Piotroski-F-Score, SUE, Wilder-RSI, sektor-relative Schwellen-Helper) wandern nach `core/utils/scoring.py` (Domänen-Kern, infrastrukturfrei, numpy-frei wo möglich; Wilder-RSI nutzt pandas analog zum bestehenden `index_momentum_agent`). Die Chief-Agenten konsumieren ausschließlich die Plan-0-Aggregation `weighted_signal` und die Plan-0-Relativmaße — sie werden **referenziert, nicht neu definiert**.

**Tech Stack:** Python, asyncio, pytest

**Abhängigkeiten:** Plan 0 (Shared Utilities). Exakt referenziert (keine Neudefinition):
- `core/utils/relative.py`: `percentile_rank(value, history, winsorize=0.0) -> float | None`, `zscore_vs_history(value, history, robust=True, min_n=20) -> float`
- `core/utils/aggregation.py`: `weighted_signal(items: list[tuple[Signal, float, SignalStatus]]) -> tuple[Signal, float]`
- `core/domain/models.py`: `SignalStatus(str, Enum)` mit `AVAILABLE`/`UNAVAILABLE`
- `core/utils/statistics.py`: `MIN_SAMPLE_N`

---

## Dateienübersicht

| Datei | Aktion | Verantwortung |
|---|---|---|
| `core/utils/scoring.py` | Create | Gebündelte quantitative Bausteine: `piotroski_f_score` (9 Kriterien), `standardized_unexpected_earnings` (SUE), `sector_relative_signal` (Schwellen via Sektor-Median/Perzentil), `wilder_rsi` (ewm alpha=1/period). → Domäne 4 (quality/earnings/fundamentals) + Domäne 6 (Wilder-RSI). |
| `agents/stock_deep_dive/equity/fundamentals_agent.py` | Modify | CAPE-Faktor entfernen; negatives/None-EPS neutralisieren; P/E, EV/EBITDA sektor-relativ; PEG-Schwelle ~1.0 + Growth-Basis-Check; ungenutzte Multiples (P/FCF, P/B) einbeziehen; symmetrische begründete Aggregationsschwellen. → `fundamentals._score`. |
| `agents/stock_deep_dive/equity/quality_agent.py` | Modify | ROIC−WACC-Spread statt fixer 12 %; Piotroski-F-Score aus `scoring.py`; `interest_coverage`/`fcf_margin` einbeziehen; Altman-Variante nach Unternehmenstyp (Z'' für Nicht-Manufacturing). → `quality._signal`/Aggregation. |
| `agents/stock_deep_dive/equity/earnings_trend_agent.py` | Modify | SUE statt binärer Beat-Rate; Revisions-Trend gewichtet statt ODER-Veto; symmetrisches Scoring. → `earnings_trend.run`/`._signal`. |
| `agents/stock_deep_dive/equity/insider_agent.py` | Modify | Wertgewichtete Netto-Insider-Aktivität (Volumen/Wert); Käufe stärker gewichtet; 10b5-1/Optionsausübung herausrechnen (als Datenannahme dokumentiert). → `insider_agent.run`. |
| `agents/stock_deep_dive/equity/short_interest_agent.py` | Modify | Short-%-Float + `days_to_cover` + Trend kombiniert; niedriger Short-Float neutral statt bullish; hohe Werte als Squeeze-Kontext. → `short_interest.run`. |
| `agents/stock_deep_dive/equity/moat_agent.py` | Modify | Maximum-/Schwellen-pro-Kategorie statt linearer Summe; Moat-Signal von der Aktien-Empfehlung entkoppeln (`none` → nicht automatisch BEARISH). → `moat._overall`/`._signal`. |
| `agents/stock_deep_dive/equity_chief_agent.py` | Modify | Gewichtete Gesamtbeurteilung via `weighted_signal`; `sector` an `fundamentals`/`quality` weiterreichen. → `equity_chief.run`. |
| `agents/stock_deep_dive/index/index_momentum_agent.py` | Modify | Wilder-RSI (aus `scoring.py`); MA200 aus ≥2y Historie; Signal aus MA50/MA200-**Status** + RSI-Extreme statt nur Cross-Event. → `index_momentum._compute_rsi`/`._signal`. |
| `agents/stock_deep_dive/index_chief_agent.py` | Modify | Gewichtete Synthese der 7 Sub-Signale via `weighted_signal`. → `index_chief.run`. |

**Nicht anfassen** (andere Pläne): `index_valuation*`/`valuation_range` (Plan B); `index_earnings`/`index_breadth`/`index_price`/`sector_composition` (Plan E); precious metals / commodity deep-dive (Plan B/E).

**Hinweis zur Signatur-Erweiterung:** `quality_agent.run`, `fundamentals_agent.run` und die `_signal`/`_score`-Helfer erhalten einen `sector`-Parameter (Default `"default"`), damit die bestehenden Aufrufe (`EquityChiefAgent`) abwärtskompatibel bleiben, bis Task 8 die Weitergabe aktiviert.

---

## Task 1: `core/utils/scoring.py` — quantitative Bausteine (Piotroski, SUE, Wilder-RSI, sektor-relative Schwelle)

> Review-Bezug Domäne 4 (`quality` Piotroski/ROIC, `earnings_trend` SUE, `fundamentals` sektor-relativ) + Domäne 6 / P4.2 (Wilder-RSI). Diese vier Bausteine werden von mehreren Agenten genutzt und gehören gebündelt in den Domänen-Kern. `sector_relative_signal` kapselt die wiederkehrende „Schwelle = Sektor-Median oder Perzentil-Rang"-Logik (referenziert `percentile_rank` aus Plan 0).

**Files:**
- Create: `core/utils/scoring.py`
- Test: `tests/utils/test_scoring.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/utils/test_scoring.py`:

```python
import pandas as pd

from core.domain.models import Signal
from core.utils.scoring import (
    piotroski_f_score,
    standardized_unexpected_earnings,
    sector_relative_signal,
    wilder_rsi,
)


# ── Piotroski F-Score (9 Kriterien) ───────────────────────────────────────

def test_piotroski_perfektes_unternehmen_ist_9():
    """Alle 9 Kriterien erfüllt → 9."""
    data = {
        "net_income": 100.0, "roa": 8.0, "operating_cash_flow": 150.0,
        "roa_prev": 5.0,
        "long_term_debt": 50.0, "long_term_debt_prev": 80.0,
        "current_ratio": 2.0, "current_ratio_prev": 1.5,
        "shares_outstanding": 100.0, "shares_outstanding_prev": 100.0,
        "gross_margin": 40.0, "gross_margin_prev": 35.0,
        "asset_turnover": 1.2, "asset_turnover_prev": 1.0,
    }
    assert piotroski_f_score(data) == 9


def test_piotroski_schwaches_unternehmen_ist_niedrig():
    """Verlust, negativer OCF, steigende Verschuldung, Verwässerung → 0–2."""
    data = {
        "net_income": -50.0, "roa": -3.0, "operating_cash_flow": -20.0,
        "roa_prev": 2.0,
        "long_term_debt": 120.0, "long_term_debt_prev": 80.0,
        "current_ratio": 1.0, "current_ratio_prev": 1.8,
        "shares_outstanding": 130.0, "shares_outstanding_prev": 100.0,
        "gross_margin": 20.0, "gross_margin_prev": 30.0,
        "asset_turnover": 0.8, "asset_turnover_prev": 1.0,
    }
    assert piotroski_f_score(data) <= 2


def test_piotroski_accrual_kriterium_ocf_groesser_net_income():
    """Kriterium 'Accruals': OCF > Net Income gibt +1; OCF < NI nicht."""
    base = {
        "roa": 1.0, "roa_prev": 5.0,
        "long_term_debt": 80.0, "long_term_debt_prev": 80.0,
        "current_ratio": 1.0, "current_ratio_prev": 1.5,
        "shares_outstanding": 100.0, "shares_outstanding_prev": 100.0,
        "gross_margin": 30.0, "gross_margin_prev": 35.0,
        "asset_turnover": 1.0, "asset_turnover_prev": 1.1,
    }
    high_quality = {**base, "net_income": 50.0, "operating_cash_flow": 120.0}
    low_quality  = {**base, "net_income": 50.0, "operating_cash_flow": 40.0}
    assert piotroski_f_score(high_quality) > piotroski_f_score(low_quality)


def test_piotroski_fehlende_felder_ist_none():
    """Zu wenige Felder → None (kein irreführender 0-Score)."""
    assert piotroski_f_score({"net_income": 100.0}) is None


# ── SUE (Standardized Unexpected Earnings) ────────────────────────────────

def test_sue_positive_surprise():
    """actual 1.20, estimate 1.00, std 0.10 → (1.20-1.00)/0.10 = 2.0."""
    quarters = [
        {"actual": 1.20, "estimate": 1.00},
        {"actual": 1.05, "estimate": 1.00},
        {"actual": 0.95, "estimate": 1.00},
        {"actual": 1.10, "estimate": 1.00},
    ]
    sue = standardized_unexpected_earnings(quarters)
    # surprises: 0.20, 0.05, -0.05, 0.10; std (n-1) ≈ 0.10408; jüngste Surprise 0.20
    assert abs(sue - 0.20 / 0.10408) < 1e-2


def test_sue_zu_wenig_quartale_ist_none():
    assert standardized_unexpected_earnings([{"actual": 1.0, "estimate": 0.9}]) is None


def test_sue_std_null_ist_none():
    """Alle Surprises identisch → std 0 → None (keine Division durch 0)."""
    quarters = [{"actual": 1.1, "estimate": 1.0} for _ in range(4)]
    assert standardized_unexpected_earnings(quarters) is None


# ── sektor-relative Schwelle ──────────────────────────────────────────────

def test_sector_relative_billig_ist_bullish():
    """value deutlich unter Sektor-Median (niedriges Perzentil) → BULLISH bei lower_is_better."""
    history = [float(i) for i in range(10, 30)]   # Median 19.5
    sig = sector_relative_signal(12.0, history, lower_is_better=True)
    assert sig == Signal.BULLISH


def test_sector_relative_teuer_ist_bearish():
    history = [float(i) for i in range(10, 30)]
    sig = sector_relative_signal(28.0, history, lower_is_better=True)
    assert sig == Signal.BEARISH


def test_sector_relative_mitte_ist_neutral():
    history = [float(i) for i in range(10, 30)]
    sig = sector_relative_signal(19.0, history, lower_is_better=True)
    assert sig == Signal.NEUTRAL


def test_sector_relative_higher_is_better_dreht_richtung():
    """higher_is_better (z. B. Marge): hoher Wert → BULLISH."""
    history = [float(i) for i in range(0, 20)]    # Median 9.5
    assert sector_relative_signal(18.0, history, lower_is_better=False) == Signal.BULLISH
    assert sector_relative_signal(2.0, history, lower_is_better=False) == Signal.BEARISH


def test_sector_relative_leere_historie_ist_neutral():
    assert sector_relative_signal(12.0, [], lower_is_better=True) == Signal.NEUTRAL


# ── Wilder-RSI ────────────────────────────────────────────────────────────

def test_wilder_rsi_durchgehend_steigend_nahe_100():
    prices = pd.Series([float(i) for i in range(1, 60)])
    rsi = wilder_rsi(prices, period=14)
    assert rsi is not None and rsi > 99.0


def test_wilder_rsi_unterscheidet_sich_von_sma_rsi():
    """Nach einem starken Schock weicht Wilder vom SMA-RSI ab."""
    vals = [100.0] * 20 + [80.0] + [101.0 + i for i in range(20)]
    prices = pd.Series(vals)
    delta = prices.diff().dropna()
    gain_sma = delta.clip(lower=0).rolling(14).mean()
    loss_sma = (-delta.clip(upper=0)).rolling(14).mean()
    rs_sma = gain_sma / loss_sma.replace(0, float("nan"))
    sma_rsi = round(float((100 - 100 / (1 + rs_sma)).iloc[-1]), 2)
    wilder = wilder_rsi(prices, period=14)
    assert wilder is not None
    assert abs(wilder - sma_rsi) > 0.01


def test_wilder_rsi_zu_kurze_serie_ist_none():
    assert wilder_rsi(pd.Series([1.0, 2.0, 3.0]), period=14) is None
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/utils/test_scoring.py -q`. Erwarteter Grund: `ModuleNotFoundError: No module named 'core.utils.scoring'`.

- [ ] **(3) Minimale Implementierung** — `core/utils/scoring.py` (Create):

```python
import statistics

from core.domain.models import Signal
from core.utils.relative import percentile_rank

# Perzentil-Schwellen für sektor-relative Klassifikation (symmetrisch)
_CHEAP_PCTL = 30.0
_RICH_PCTL  = 70.0


def piotroski_f_score(data: dict) -> int | None:
    """Piotroski F-Score (0–9). 9 Kriterien in 3 Gruppen.
    None, falls die Pflichtfelder fehlen (kein irreführender 0-Score).

    Profitabilität (4): net_income>0; roa>0; operating_cash_flow>0; OCF>net_income (Accruals).
    Leverage/Liquidität (3): long_term_debt fällt; current_ratio steigt; keine Aktien-Verwässerung.
    Operative Effizienz (2): gross_margin steigt; asset_turnover steigt.
    """
    required = (
        "net_income", "roa", "operating_cash_flow", "roa_prev",
        "long_term_debt", "long_term_debt_prev",
        "current_ratio", "current_ratio_prev",
        "shares_outstanding", "shares_outstanding_prev",
        "gross_margin", "gross_margin_prev",
        "asset_turnover", "asset_turnover_prev",
    )
    if any(data.get(k) is None for k in required):
        return None

    score = 0
    # Profitabilität
    score += 1 if data["net_income"] > 0 else 0
    score += 1 if data["roa"] > 0 else 0
    score += 1 if data["operating_cash_flow"] > 0 else 0
    score += 1 if data["operating_cash_flow"] > data["net_income"] else 0
    # Leverage / Liquidität
    score += 1 if data["long_term_debt"] < data["long_term_debt_prev"] else 0
    score += 1 if data["current_ratio"] > data["current_ratio_prev"] else 0
    score += 1 if data["shares_outstanding"] <= data["shares_outstanding_prev"] else 0
    # Operative Effizienz
    score += 1 if data["gross_margin"] > data["gross_margin_prev"] else 0
    score += 1 if data["asset_turnover"] > data["asset_turnover_prev"] else 0
    return score


def standardized_unexpected_earnings(quarters: list[dict]) -> float | None:
    """SUE = jüngste Earnings-Surprise / Std(historische Surprises).
    quarters: chronologisch (älteste zuerst), je {'actual', 'estimate'}.
    None bei <4 Quartalen oder Std==0. Misst die Magnitude statt nur Beat/Miss.
    """
    surprises = [
        q["actual"] - q["estimate"]
        for q in quarters
        if q.get("actual") is not None and q.get("estimate") is not None
    ]
    if len(surprises) < 4:
        return None
    std = statistics.stdev(surprises)
    if std == 0.0:
        return None
    return surprises[-1] / std


def sector_relative_signal(value: float, sector_history: list[float],
                           lower_is_better: bool) -> Signal:
    """Klassifiziert `value` relativ zur Sektor-Verteilung über den Perzentil-Rang
    (Plan-0 `percentile_rank`). NEUTRAL bei leerer Historie.

    lower_is_better=True (Bewertungs-Multiples wie P/E): niedriges Perzentil = günstig = BULLISH.
    lower_is_better=False (Qualität wie Marge): hohes Perzentil = stark = BULLISH.
    """
    pctl = percentile_rank(value, sector_history)
    if pctl is None:
        return Signal.NEUTRAL
    cheap = pctl <= _CHEAP_PCTL
    rich  = pctl >= _RICH_PCTL
    if lower_is_better:
        if cheap:
            return Signal.BULLISH
        if rich:
            return Signal.BEARISH
    else:
        if rich:
            return Signal.BULLISH
        if cheap:
            return Signal.BEARISH
    return Signal.NEUTRAL


def wilder_rsi(prices, period: int = 14) -> float | None:
    """RSI nach Wilder (ewm alpha=1/period, adjust=False) statt SMA (Cutler).
    Erwartet eine pandas-Series. None bei Fehler / zu kurzer Historie.
    """
    try:
        delta = prices.diff().dropna()
        if len(delta) < period:
            return None
        gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
        rs = gain / loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 2)
    except Exception:
        return None
```

> Hinweis: `tests/utils/` ggf. mit leerer `__init__.py` anlegen, falls das Test-Paket noch nicht existiert (Stil wie vorhandene `tests/agents/.../__init__.py`).

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/utils/test_scoring.py -q`. Erwartung: 15 passed.

- [ ] **(5) Commit** — `git add core/utils/scoring.py tests/utils/test_scoring.py && git commit -m "feat(scoring): piotroski_f_score, SUE, sector_relative_signal, wilder_rsi"`

---

## Task 2: `fundamentals_agent` — CAPE entfernen, sektor-relativ, negatives EPS neutralisieren, ungenutzte Multiples

> Review-Bezug Domäne 4 `fundamentals._score`: (1) absolute, sektor-blinde P/E-/EV-EBITDA-Schwellen; (2) negatives EPS wird wie „extrem billig" als +1 gewertet; (3) **CAPE auf Einzelaktie ist fachlich falsch** → entfernen; (4) PEG-Schwelle 1,5 zu großzügig + Growth-Basis ungeprüft; (5) P/FCF und P/B erfasst, aber ungenutzt; (6) asymmetrische, unbegründete Aggregationsschwellen (≥+3 / ≤−2). `sector` wird als Parameter durchgereicht (Sektor-Multiple-Historie aus `_SECTOR_MULTIPLES` als Verteilungs-Proxy für `sector_relative_signal`).

**Files:**
- Modify: `agents/stock_deep_dive/equity/fundamentals_agent.py`
- Test: `tests/agents/stock_deep_dive/equity/test_fundamentals_agent.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/agents/stock_deep_dive/equity/test_fundamentals_agent.py`:

```python
import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.fundamentals_agent import FundamentalsAgent, _score
from core.domain.models import Signal


def _make_agent(data: dict) -> FundamentalsAgent:
    provider = MagicMock()
    provider.get_fundamentals.return_value = data
    return FundamentalsAgent(provider, MagicMock())


# ── CAPE entfernt ─────────────────────────────────────────────────────────

def test_score_signatur_ohne_shiller():
    """_score nimmt kein shiller-Argument mehr (CAPE auf Einzelaktie entfernt)."""
    import inspect
    params = inspect.signature(_score).parameters
    assert "shiller" not in params
    assert "shiller_cape" not in params


def test_shiller_cape_bleibt_im_snapshot_aber_ohne_signalwirkung():
    """Snapshot trägt shiller_cape weiter (Backward-Compat), aber es beeinflusst das Signal nicht."""
    with_cape    = asyncio.run(_make_agent({"pe_ratio": 18.0, "shiller_cape": 5.0}).run("X"))
    without_cape = asyncio.run(_make_agent({"pe_ratio": 18.0, "shiller_cape": None}).run("X"))
    assert with_cape.signal == without_cape.signal


# ── negatives / None EPS neutralisieren ───────────────────────────────────

def test_negatives_eps_pe_neutral_nicht_bullish():
    """Negatives P/E (Verlust) darf NICHT bullish gewertet werden."""
    sig = _score(pe=-12.0, forward_pe=None, peg=None, ev_ebitda=None,
                 price_fcf=None, price_book=None, revenue_cagr=None,
                 op_margin=None, debt_equity=None, sector="default")
    assert sig == Signal.NEUTRAL


# ── sektor-relativ ────────────────────────────────────────────────────────

def test_pe_billig_im_sektor_ist_bullish():
    """P/E 11 ist bei Financials (Sektor-Band 10–16) eher günstig → BULLISH-Tendenz."""
    sig = _score(pe=11.0, forward_pe=None, peg=None, ev_ebitda=None,
                 price_fcf=None, price_book=None, revenue_cagr=None,
                 op_margin=None, debt_equity=None, sector="Financials")
    assert sig in (Signal.BULLISH, Signal.NEUTRAL)


def test_pe_teuer_im_sektor_ist_bearish_tendenz():
    """P/E 40 bei Financials (Band 10–16) ist klar teuer."""
    sig = _score(pe=40.0, forward_pe=None, peg=None, ev_ebitda=None,
                 price_fcf=None, price_book=None, revenue_cagr=None,
                 op_margin=None, debt_equity=None, sector="Financials")
    assert sig in (Signal.BEARISH, Signal.NEUTRAL)


# ── PEG mit Growth-Basis-Check ────────────────────────────────────────────

def test_peg_ohne_growth_basis_neutral():
    """PEG aus trivialem/negativem g ist sinnlos → kein Beitrag."""
    sig = _score(pe=20.0, forward_pe=None, peg=0.2, ev_ebitda=None,
                 price_fcf=None, price_book=None, revenue_cagr=-5.0,
                 op_margin=None, debt_equity=None, sector="default")
    # revenue_cagr < 0 → PEG darf nicht bullish ziehen
    assert sig != Signal.BULLISH


# ── ungenutzte Multiples aktiviert ────────────────────────────────────────

def test_price_fcf_und_price_book_fliessen_ein():
    """Sehr niedriges P/FCF und P/B verschieben das Signal in Richtung BULLISH."""
    cheap = _score(pe=15.0, forward_pe=None, peg=None, ev_ebitda=None,
                   price_fcf=6.0, price_book=0.8, revenue_cagr=None,
                   op_margin=None, debt_equity=None, sector="default")
    pricey = _score(pe=15.0, forward_pe=None, peg=None, ev_ebitda=None,
                    price_fcf=40.0, price_book=8.0, revenue_cagr=None,
                    op_margin=None, debt_equity=None, sector="default")
    order = {Signal.BEARISH: -1, Signal.NEUTRAL: 0, Signal.BULLISH: 1}
    assert order[cheap] >= order[pricey]


# ── symmetrische Aggregationsschwellen ────────────────────────────────────

def test_aggregation_symmetrisch():
    """Spiegelbildlich gleich starke Bull-/Bear-Inputs ergeben spiegelbildliche Signale."""
    bull = _score(pe=11.0, forward_pe=10.0, peg=None, ev_ebitda=6.0,
                  price_fcf=6.0, price_book=0.8, revenue_cagr=None,
                  op_margin=None, debt_equity=None, sector="default")
    bear = _score(pe=40.0, forward_pe=45.0, peg=None, ev_ebitda=30.0,
                  price_fcf=45.0, price_book=9.0, revenue_cagr=None,
                  op_margin=None, debt_equity=None, sector="default")
    assert bull == Signal.BULLISH
    assert bear == Signal.BEARISH
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/agents/stock_deep_dive/equity/test_fundamentals_agent.py -q`. Erwarteter Grund: `TypeError: _score() got an unexpected keyword argument 'price_fcf'` bzw. die alte Signatur enthält `shiller`.

- [ ] **(3) Implementierung** — `agents/stock_deep_dive/equity/fundamentals_agent.py` vollständig ersetzen:

```python
import asyncio

from core.domain.events import FundamentalsReady
from core.domain.models import FundamentalsSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus
from core.utils.scoring import sector_relative_signal

_DEFAULT = FundamentalsSnapshot(
    pe_ratio=None, forward_pe=None, shiller_cape=None, peg_ratio=None,
    ev_ebitda=None, ev_revenue=None, price_book=None, price_sales=None,
    price_fcf=None, dividend_yield=None, wacc=None,
    revenue_cagr_3y=None, operating_margin=None, gross_margin=None,
    debt_to_equity=None, signal=Signal.NEUTRAL,
)

# Sektor-typische Multiple-Verteilungen als Proxy-Historie (bis Peer-API verfügbar).
# Werte = repräsentative Stützstellen je Sektor → Basis für percentile_rank.
_SECTOR_PE: dict[str, list[float]] = {
    "Technology":  [18, 22, 26, 30, 35, 40],
    "Healthcare":  [14, 18, 22, 26, 30],
    "Financials":  [8, 10, 12, 14, 16],
    "Energy":      [6, 8, 10, 12, 15],
    "default":     [10, 14, 18, 22, 28],
}
_SECTOR_EV_EBITDA: dict[str, list[float]] = {
    "Technology":  [12, 15, 18, 22, 26],
    "Healthcare":  [9, 12, 15, 18, 22],
    "Financials":  [6, 8, 10, 12, 14],
    "Energy":      [4, 6, 8, 10, 12],
    "default":     [8, 10, 13, 16, 20],
}

# Wachstums-Mindestbasis, ab der PEG aussagekräftig ist (Prozentpunkte).
_PEG_MIN_GROWTH = 3.0
# PEG-Schwelle nahe Peter-Lynch-Standard 1.0 (statt großzügiger 1.5).
_PEG_CHEAP = 1.0
_PEG_RICH  = 2.0

_SCORE = {Signal.BULLISH: 1, Signal.NEUTRAL: 0, Signal.BEARISH: -1}


def _score(pe, forward_pe, peg, ev_ebitda, price_fcf, price_book,
           revenue_cagr, op_margin, debt_equity, sector: str = "default") -> Signal:
    score = 0

    # P/E — negatives/None EPS neutralisieren, sonst sektor-relativ
    if pe is not None and pe > 0:
        score += _SCORE[sector_relative_signal(pe, _SECTOR_PE.get(sector, _SECTOR_PE["default"]),
                                                lower_is_better=True)]

    # Forward < Trailing = erwartetes EPS-Wachstum (nur bei positivem Trailing-P/E)
    if forward_pe is not None and pe is not None and pe > 0:
        score += 1 if forward_pe < pe else 0

    # EV/EBITDA — sektor-relativ
    if ev_ebitda is not None and ev_ebitda > 0:
        score += _SCORE[sector_relative_signal(ev_ebitda, _SECTOR_EV_EBITDA.get(sector, _SECTOR_EV_EBITDA["default"]),
                                               lower_is_better=True)]

    # PEG — nur bei sinnvoller Wachstumsbasis, Schwelle ~1.0
    if peg is not None and revenue_cagr is not None and revenue_cagr >= _PEG_MIN_GROWTH:
        score += 1 if peg < _PEG_CHEAP else (-1 if peg > _PEG_RICH else 0)

    # P/FCF — vorher ungenutzt
    if price_fcf is not None and price_fcf > 0:
        score += 1 if price_fcf < 12 else (-1 if price_fcf > 30 else 0)

    # P/B — vorher ungenutzt (relevant v. a. für Financials)
    if price_book is not None and price_book > 0:
        score += 1 if price_book < 1.5 else (-1 if price_book > 5.0 else 0)

    # Wachstum / Marge / Verschuldung
    if revenue_cagr is not None:
        score += 1 if revenue_cagr > 10 else (-1 if revenue_cagr < 0 else 0)
    if op_margin is not None:
        score += 1 if op_margin > 15 else (-1 if op_margin < 0 else 0)
    if debt_equity is not None:
        score += 1 if debt_equity < 0.5 else (-1 if debt_equity > 2.0 else 0)

    # Symmetrische, begründete Schwellen (gleicher Betrag beidseitig)
    return Signal.BULLISH if score >= 3 else (Signal.BEARISH if score <= -3 else Signal.NEUTRAL)


class FundamentalsAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str, sector: str = "default") -> FundamentalsSnapshot:
        data = await asyncio.to_thread(self.provider.get_fundamentals, ticker)
        pe          = data.get("pe_ratio")
        forward_pe  = data.get("forward_pe")
        shiller     = data.get("shiller_cape")   # nur durchgereicht, NICHT im Signal
        peg         = data.get("peg_ratio")
        ev_ebitda   = data.get("ev_ebitda")
        ev_revenue  = data.get("ev_revenue")
        price_book  = data.get("price_book")
        price_sales = data.get("price_sales")
        price_fcf   = data.get("price_fcf")
        div_yield   = data.get("dividend_yield")
        wacc        = data.get("wacc")
        cagr_3y     = data.get("revenue_cagr_3y")
        op_margin   = data.get("operating_margin")
        gross_m     = data.get("gross_margin")
        debt_eq     = data.get("debt_to_equity")

        result = FundamentalsSnapshot(
            pe_ratio=pe, forward_pe=forward_pe, shiller_cape=shiller,
            peg_ratio=peg, ev_ebitda=ev_ebitda, ev_revenue=ev_revenue,
            price_book=price_book, price_sales=price_sales, price_fcf=price_fcf,
            dividend_yield=div_yield, wacc=wacc, revenue_cagr_3y=cagr_3y,
            operating_margin=op_margin, gross_margin=gross_m, debt_to_equity=debt_eq,
            signal=_score(pe, forward_pe, peg, ev_ebitda, price_fcf, price_book,
                          cagr_3y, op_margin, debt_eq, sector=sector),
        )
        self.bus.publish(FundamentalsReady(source="fundamentals_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> FundamentalsSnapshot:
        return _DEFAULT
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/agents/stock_deep_dive/equity/test_fundamentals_agent.py -q`. Erwartung: 8 passed. Regression: `python -m pytest tests/agents/stock_deep_dive -q`.

- [ ] **(5) Self-Review** — Prüfen: `shiller_cape` nirgends mehr in `_score`; negatives P/E ergibt 0 Beitrag (nicht +1); PEG nur bei `revenue_cagr >= 3`; Aggregationsschwelle beidseitig `±3`. Mit Grep verifizieren: `rg "shiller" agents/stock_deep_dive/equity/fundamentals_agent.py` darf nur die Snapshot-Durchreichung zeigen, keine Signal-Logik.

- [ ] **(6) Commit** — `git add agents/stock_deep_dive/equity/fundamentals_agent.py tests/agents/stock_deep_dive/equity/test_fundamentals_agent.py && git commit -m "fix(fundamentals): CAPE entfernt, sektor-relative Schwellen, neg. EPS neutral, P/FCF+P/B aktiviert"`

---

## Task 3: `quality_agent` — ROIC−WACC-Spread, Piotroski-F-Score, interest_coverage/fcf_margin, Altman-Variante

> Review-Bezug Domäne 4 `quality._signal`/Aggregation: (1) ROIC sollte gegen **WACC** verglichen werden (Wertschöpfung nur bei ROIC > WACC) statt fixer 12 %; (2) kein echter **Piotroski-F-Score** trotz vorhandener Rohdaten; (3) `interest_coverage`/`fcf_margin`/`net_margin`/`roa` erfasst, aber ungenutzt; (4) Altman-Z nur für Manufacturing gültig → Z''-Variante (2,6/1,1) für Nicht-Manufacturing. `sector` als Parameter, um den Unternehmenstyp (Financials → Altman gar nicht; Nicht-Manufacturing → Z'') zu wählen.

**Files:**
- Modify: `agents/stock_deep_dive/equity/quality_agent.py`
- Test: `tests/agents/stock_deep_dive/equity/test_quality_agent.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/agents/stock_deep_dive/equity/test_quality_agent.py`:

```python
import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.quality_agent import QualityAgent, _signal, _altman_thresholds
from core.domain.models import Signal


def _make_agent(data: dict) -> QualityAgent:
    provider = MagicMock()
    provider.get_fundamentals.return_value = data
    return QualityAgent(provider, MagicMock())


# ── ROIC − WACC-Spread statt fixer 12 % ───────────────────────────────────

def test_roic_ueber_wacc_ist_wertschoepfend():
    """ROIC 10 % bei WACC 7 % = +3 pp Spread → wertschöpfend (bullish-Beitrag)."""
    pos = _signal(roe=None, roic=10.0, wacc=7.0, net_debt_ebitda=None, altman_z=None,
                  interest_coverage=None, fcf_margin=None, f_score=None, sector="default")
    neg = _signal(roe=None, roic=10.0, wacc=13.0, net_debt_ebitda=None, altman_z=None,
                  interest_coverage=None, fcf_margin=None, f_score=None, sector="default")
    order = {Signal.BEARISH: -1, Signal.NEUTRAL: 0, Signal.BULLISH: 1}
    # Gleicher ROIC, aber bei höherem WACC schlechter
    assert order[pos] >= order[neg]


def test_roic_ohne_wacc_faellt_auf_absolutschwelle_zurueck():
    """Fehlt WACC, nutzt der Spread-Check eine konservative Default-Schwelle."""
    sig = _signal(roe=None, roic=18.0, wacc=None, net_debt_ebitda=None, altman_z=None,
                  interest_coverage=None, fcf_margin=None, f_score=None, sector="default")
    assert sig in (Signal.BULLISH, Signal.NEUTRAL)


# ── Piotroski F-Score fließt ein ──────────────────────────────────────────

def test_hoher_f_score_ist_bullish_beitrag():
    high = _signal(roe=None, roic=None, wacc=None, net_debt_ebitda=None, altman_z=None,
                   interest_coverage=None, fcf_margin=None, f_score=9, sector="default")
    low  = _signal(roe=None, roic=None, wacc=None, net_debt_ebitda=None, altman_z=None,
                   interest_coverage=None, fcf_margin=None, f_score=1, sector="default")
    assert high == Signal.BULLISH
    assert low == Signal.BEARISH


# ── interest_coverage / fcf_margin aktiviert ──────────────────────────────

def test_interest_coverage_und_fcf_margin_wirken():
    strong = _signal(roe=None, roic=None, wacc=None, net_debt_ebitda=None, altman_z=None,
                     interest_coverage=12.0, fcf_margin=15.0, f_score=None, sector="default")
    weak   = _signal(roe=None, roic=None, wacc=None, net_debt_ebitda=None, altman_z=None,
                     interest_coverage=1.0, fcf_margin=-5.0, f_score=None, sector="default")
    order = {Signal.BEARISH: -1, Signal.NEUTRAL: 0, Signal.BULLISH: 1}
    assert order[strong] > order[weak]


# ── Altman-Variante nach Unternehmenstyp ──────────────────────────────────

def test_altman_manufacturing_klassische_schwellen():
    safe, distress = _altman_thresholds("Industrials")
    assert safe == 2.99 and distress == 1.81


def test_altman_nicht_manufacturing_z_doppelstrich():
    safe, distress = _altman_thresholds("Technology")
    assert safe == 2.6 and distress == 1.1


def test_altman_financials_nicht_angewendet():
    """Für Financials liefert die Schwellen-Funktion None → Altman ignoriert."""
    assert _altman_thresholds("Financials") is None


def test_financials_altman_z_kein_beitrag():
    """Auch ein extrem niedriger Altman-Z darf bei Financials NICHT bearish ziehen."""
    sig = _signal(roe=None, roic=None, wacc=None, net_debt_ebitda=None, altman_z=0.5,
                  interest_coverage=None, fcf_margin=None, f_score=None, sector="Financials")
    assert sig == Signal.NEUTRAL


# ── Piotroski-Felddurchreichung end-to-end ────────────────────────────────

def test_run_berechnet_f_score_aus_provider_feldern():
    data = {
        "net_income": 100.0, "roa": 8.0, "operating_cash_flow": 150.0, "roa_prev": 5.0,
        "long_term_debt": 50.0, "long_term_debt_prev": 80.0,
        "current_ratio": 2.0, "current_ratio_prev": 1.5,
        "shares_outstanding": 100.0, "shares_outstanding_prev": 100.0,
        "gross_margin": 40.0, "gross_margin_prev": 35.0,
        "asset_turnover": 1.2, "asset_turnover_prev": 1.0,
    }
    result = asyncio.run(_make_agent(data).run("X"))
    assert result.signal == Signal.BULLISH
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/agents/stock_deep_dive/equity/test_quality_agent.py -q`. Erwarteter Grund: `ImportError: cannot import name '_altman_thresholds'` und geänderte `_signal`-Signatur.

- [ ] **(3) Implementierung** — `agents/stock_deep_dive/equity/quality_agent.py` vollständig ersetzen:

```python
import asyncio

from core.domain.events import QualityReady
from core.domain.models import QualitySnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus
from core.utils.scoring import piotroski_f_score

_DEFAULT = QualitySnapshot(
    gross_margin=None, operating_margin=None, net_margin=None, fcf_margin=None,
    roe=None, roa=None, roic=None, debt_to_equity=None, net_debt_ebitda=None,
    interest_coverage=None, current_ratio=None, altman_z=None, signal=Signal.NEUTRAL,
)

# Sektoren, für die Altman-Z nicht definiert ist (keine sinnvolle Z-Anwendung).
_ALTMAN_EXCLUDED = {"Financials", "Financial Services", "Banks", "Insurance"}
# Manufacturing-nahe Sektoren → Original-Z (2,99/1,81); sonst Z'' (2,6/1,1).
_ALTMAN_MANUFACTURING = {"Industrials", "Materials", "Manufacturing", "Consumer Cyclical"}

# Default-Mindest-ROIC, falls WACC fehlt (konservativ).
_ROIC_DEFAULT_HURDLE = 12.0


def _altman_thresholds(sector: str) -> tuple[float, float] | None:
    """(safe, distress)-Schwellen je Unternehmenstyp. None = nicht anwenden (Financials)."""
    if sector in _ALTMAN_EXCLUDED:
        return None
    if sector in _ALTMAN_MANUFACTURING:
        return 2.99, 1.81          # Original Altman Z (1968)
    return 2.6, 1.1               # Z'' für Dienstleister / Nicht-Manufacturing


def _signal(roe, roic, wacc, net_debt_ebitda, altman_z,
            interest_coverage, fcf_margin, f_score, sector: str = "default") -> Signal:
    score = 0

    # ROIC − WACC-Spread (Wertschöpfung nur bei ROIC > WACC)
    if roic is not None:
        if wacc is not None:
            spread = roic - wacc
            score += 1 if spread > 2.0 else (-1 if spread < -2.0 else 0)
        else:
            score += 1 if roic > _ROIC_DEFAULT_HURDLE else (-1 if roic < 5 else 0)

    # ROE (Leverage-verzerrt → schwächer gewichtet, nur als Bestätigung)
    if roe is not None:
        score += 1 if roe > 15 else (-1 if roe < 5 else 0)

    # Net Debt / EBITDA (Standard-Schwellen, beibehalten)
    if net_debt_ebitda is not None:
        score += 1 if net_debt_ebitda < 2.0 else (-1 if net_debt_ebitda > 4.0 else 0)

    # Altman-Z nur bei anwendbarem Unternehmenstyp
    if altman_z is not None:
        thr = _altman_thresholds(sector)
        if thr is not None:
            safe, distress = thr
            score += 1 if altman_z > safe else (-1 if altman_z < distress else 0)

    # interest_coverage (zuvor ungenutzt)
    if interest_coverage is not None:
        score += 1 if interest_coverage > 5.0 else (-1 if interest_coverage < 1.5 else 0)

    # fcf_margin (zuvor ungenutzt)
    if fcf_margin is not None:
        score += 1 if fcf_margin > 10.0 else (-1 if fcf_margin < 0.0 else 0)

    # Piotroski F-Score als Gesamt-Qualitätsanker (kräftig gewichtet)
    if f_score is not None:
        if f_score >= 7:
            score += 2
        elif f_score <= 3:
            score -= 2

    return Signal.BULLISH if score >= 2 else (Signal.BEARISH if score <= -2 else Signal.NEUTRAL)


class QualityAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self, ticker: str, sector: str = "default") -> QualitySnapshot:
        data = await asyncio.to_thread(self.provider.get_fundamentals, ticker)
        if isinstance(data, Exception):
            data = {}

        roe            = data.get("roe")
        roa            = data.get("roa")
        roic           = data.get("roic")
        wacc           = data.get("wacc")
        gross_margin   = data.get("gross_margin")
        op_margin      = data.get("operating_margin")
        net_margin     = data.get("net_margin")
        fcf_margin     = data.get("fcf_margin")
        dte            = data.get("debt_to_equity")
        net_debt_ebitda = data.get("net_debt_ebitda")
        interest_cov   = data.get("interest_coverage")
        current_ratio  = data.get("current_ratio")
        altman_z       = data.get("altman_z")
        f_score        = piotroski_f_score(data)

        result = QualitySnapshot(
            gross_margin=gross_margin, operating_margin=op_margin,
            net_margin=net_margin, fcf_margin=fcf_margin,
            roe=roe, roa=roa, roic=roic,
            debt_to_equity=dte, net_debt_ebitda=net_debt_ebitda,
            interest_coverage=interest_cov, current_ratio=current_ratio,
            altman_z=altman_z,
            signal=_signal(roe, roic, wacc, net_debt_ebitda, altman_z,
                           interest_cov, fcf_margin, f_score, sector=sector),
        )
        self.bus.publish(QualityReady(source="quality_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> QualitySnapshot:
        return _DEFAULT
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/agents/stock_deep_dive/equity/test_quality_agent.py -q`. Erwartung: 9 passed. Regression: `python -m pytest tests/agents/stock_deep_dive -q`.

- [ ] **(5) Self-Review** — Prüfen: ROIC−WACC-Spread bei vorhandenem WACC, Default-Hürde sonst; Financials → kein Altman-Beitrag; Piotroski mit `±2` am stärksten gewichtet; `interest_coverage`/`fcf_margin` aktiv.

- [ ] **(6) Commit** — `git add agents/stock_deep_dive/equity/quality_agent.py tests/agents/stock_deep_dive/equity/test_quality_agent.py && git commit -m "fix(quality): ROIC-WACC-Spread, Piotroski-F-Score, interest_coverage/fcf_margin, Altman nach Typ"`

---

## Task 4: `earnings_trend_agent` — SUE statt binärer Beat-Rate, Revisions-Trend gewichtet

> Review-Bezug Domäne 4 `earnings_trend`: (1) binäre Beat-Rate ignoriert **Magnitude** und Sandbagging (75 % Beat ist Normalfall); (2) Revisionen aus nur 2 Datenpunkten dünn; (3) asymmetrische UND/ODER-Veto-Logik macht BEARISH überempfindlich. Umstellung auf **SUE** (aus `scoring.py`) + gewichtetes Scoring (Revisions-Momentum höher als rohe Beat-Rate), kein ODER-Veto.

**Files:**
- Modify: `agents/stock_deep_dive/equity/earnings_trend_agent.py`
- Test: `tests/agents/stock_deep_dive/equity/test_earnings_trend_agent.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/agents/stock_deep_dive/equity/test_earnings_trend_agent.py`:

```python
import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.earnings_trend_agent import EarningsTrendAgent, _signal
from core.domain.models import Signal


def _make_agent(history: list[dict]) -> EarningsTrendAgent:
    provider = MagicMock()
    provider.get_earnings_history.return_value = history
    return EarningsTrendAgent(provider, MagicMock())


def _quarters(actuals, estimates, revisions=None):
    revisions = revisions or [0] * len(actuals)
    return [
        {"actual": a, "estimate": e, "revision": r, "beat": a > e}
        for a, e, r in zip(actuals, estimates, revisions)
    ]


# ── SUE statt binärer Beat-Rate ───────────────────────────────────────────

def test_grosse_positive_surprise_ist_bullish():
    """Letzte Surprise weit über der Streuung (hoher SUE) + Up-Revision → BULLISH."""
    sig = _signal(sue=2.5, revision_label="up")
    assert sig == Signal.BULLISH


def test_kleine_surprise_trotz_beat_neutral():
    """Routine-Beat innerhalb der Streuung (SUE ~0.3) ohne Revisionsschub → NEUTRAL."""
    sig = _signal(sue=0.3, revision_label="flat")
    assert sig == Signal.NEUTRAL


# ── Revisions-Trend gewichtet statt ODER-Veto ─────────────────────────────

def test_down_revision_kippt_nicht_allein_bei_starkem_sue():
    """Starker positiver SUE + eine Down-Revision → NICHT automatisch BEARISH (kein Veto)."""
    sig = _signal(sue=2.5, revision_label="down")
    assert sig != Signal.BEARISH


def test_negative_surprise_und_down_revision_ist_bearish():
    sig = _signal(sue=-2.0, revision_label="down")
    assert sig == Signal.BEARISH


# ── End-to-End: SUE wird aus history berechnet ────────────────────────────

def test_run_berechnet_sue_aus_history():
    history = _quarters(
        actuals=[1.0, 0.95, 1.05, 1.40],
        estimates=[1.0, 1.0, 1.0, 1.0],
        revisions=[0, 0, 1, 1],     # jüngste zwei Up-Revisions
    )
    result = asyncio.run(_make_agent(history).run("X"))
    assert result.signal == Signal.BULLISH


def test_leere_history_neutral():
    result = asyncio.run(_make_agent([]).run("X"))
    assert result.signal == Signal.NEUTRAL
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/agents/stock_deep_dive/equity/test_earnings_trend_agent.py -q`. Erwarteter Grund: `TypeError: _signal() got an unexpected keyword argument 'sue'` (alte Signatur war `beat_rate`/`revision_label`).

- [ ] **(3) Implementierung** — `agents/stock_deep_dive/equity/earnings_trend_agent.py` vollständig ersetzen:

```python
import asyncio

from core.domain.events import EarningsTrendReady
from core.domain.models import EarningsTrendSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus
from core.utils.scoring import standardized_unexpected_earnings

_DEFAULT = EarningsTrendSnapshot(beat_rate=None, estimate_revision="flat", signal=Signal.NEUTRAL)

# SUE-Schwelle für „signifikante" Überraschung (in Std-Einheiten).
_SUE_STRONG = 1.0


def _signal(sue: float | None, revision_label: str) -> Signal:
    """Gewichtetes Scoring: SUE (Magnitude) + Revisions-Momentum, kein ODER-Veto.
    Revisionen werden höher gewichtet als die rohe Surprise (PEAD-Literatur)."""
    score = 0.0

    if sue is not None:
        if sue > _SUE_STRONG:
            score += 1.0
        elif sue < -_SUE_STRONG:
            score -= 1.0

    # Revisions-Momentum stärker gewichtet (1.5) als SUE — aber additiv, kein Veto
    if revision_label == "up":
        score += 1.5
    elif revision_label == "down":
        score -= 1.5

    if score >= 1.0:
        return Signal.BULLISH
    if score <= -1.0:
        return Signal.BEARISH
    return Signal.NEUTRAL


class EarningsTrendAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> EarningsTrendSnapshot:
        history = await asyncio.to_thread(self.provider.get_earnings_history, ticker)
        if not history:
            self.bus.publish(EarningsTrendReady(source="earnings_trend_agent", payload={"ticker": ticker}))
            return _DEFAULT

        # Beat-Rate weiterhin als deskriptive Kennzahl im Snapshot (nicht mehr signal-tragend)
        beats = sum(1 for q in history if q.get("beat") is True)
        beat_rate = beats / len(history)

        sue = standardized_unexpected_earnings(history)

        revisions = [q.get("revision", 0) for q in history[-3:]]
        avg_rev = sum(revisions) / len(revisions) if revisions else 0
        revision_label = "up" if avg_rev > 0 else ("down" if avg_rev < 0 else "flat")

        result = EarningsTrendSnapshot(
            beat_rate=beat_rate,
            estimate_revision=revision_label,
            signal=_signal(sue, revision_label),
        )
        self.bus.publish(EarningsTrendReady(source="earnings_trend_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> EarningsTrendSnapshot:
        return _DEFAULT
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/agents/stock_deep_dive/equity/test_earnings_trend_agent.py -q`. Erwartung: 6 passed. Regression: `python -m pytest tests/agents/stock_deep_dive -q`.

- [ ] **(5) Self-Review** — Prüfen: kein ODER-Veto mehr (Down-Revision kann bei starkem SUE nur dämpfen, nicht allein kippen); Revisionsfenster auf 3 Quartale erweitert; `beat_rate` bleibt deskriptiv im Snapshot.

- [ ] **(6) Commit** — `git add agents/stock_deep_dive/equity/earnings_trend_agent.py tests/agents/stock_deep_dive/equity/test_earnings_trend_agent.py && git commit -m "fix(earnings_trend): SUE statt binärer Beat-Rate, gewichteter Revisions-Trend ohne ODER-Veto"`

---

## Task 5: `insider_agent` — wertgewichtete Netto-Aktivität, Käufe stärker, 10b5-1 herausrechnen

> Review-Bezug Domäne 4 `insider_agent` / P3.6: Es wird die **Anzahl** der Transaktionen gezählt, nicht **Volumen/Wert**. 10 kleine automatische 10b5-1-Verkäufe vs. 1 großer Conviction-Kauf → fälschlich „net_sell". Lösung: wertgewichtete Netto-Aktivität (Dollar-Betrag, ersatzweise Aktienzahl), Käufe stärker gewichten, geplante 10b5-1-Programme und Optionsausübungen herausrechnen.

> **Datenannahme (dokumentiert):** Jede Transaktion liefert idealerweise `value` (USD) oder `shares`; ein `plan`-Feld (`"10b5-1"`) bzw. `acquisition_type=="option_exercise"` markiert nicht-informative Transaktionen. Fehlt `value`, wird auf `shares` zurückgegriffen; fehlt auch das, zählt die Transaktion mit Einheitsgewicht 1.0. Fehlt das `plan`-Feld, wird die Transaktion als open-market (informativ) behandelt.

**Files:**
- Modify: `agents/stock_deep_dive/equity/insider_agent.py`
- Test: `tests/agents/stock_deep_dive/equity/test_insider_agent.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/agents/stock_deep_dive/equity/test_insider_agent.py`:

```python
import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.insider_agent import InsiderAgent, _net_value, _signal
from core.domain.models import Signal


def _make_agent(transactions: list[dict]) -> InsiderAgent:
    provider = MagicMock()
    provider.get_insider_activity.return_value = transactions
    return InsiderAgent(provider, MagicMock())


# ── wertgewichtet statt Anzahl ────────────────────────────────────────────

def test_grosser_kauf_schlaegt_viele_kleine_verkaeufe():
    """1 Conviction-Kauf 1.0M vs. 10 kleine Verkäufe à 10k → netto BULLISH."""
    txns = [{"type": "buy", "value": 1_000_000}] + \
           [{"type": "sell", "value": 10_000} for _ in range(10)]
    result = asyncio.run(_make_agent(txns).run("X"))
    assert result.signal == Signal.BULLISH
    assert result.net_direction == "net_buy"


def test_alte_anzahl_logik_haette_net_sell_gegeben():
    """Gegenprobe: nach Anzahl wären 10 Verkäufe > 1 Kauf → der Bug ist behoben."""
    txns = [{"type": "buy", "value": 1_000_000}] + \
           [{"type": "sell", "value": 10_000} for _ in range(10)]
    assert _net_value(txns) > 0   # wertgewichtet positiv


# ── Käufe stärker gewichtet ───────────────────────────────────────────────

def test_kaeufe_staerker_gewichtet_als_verkaeufe():
    """Gleicher Dollar-Betrag Kauf vs. Verkauf → Netto positiv (Käufe signalstärker)."""
    txns = [{"type": "buy", "value": 100_000}, {"type": "sell", "value": 100_000}]
    assert _net_value(txns) > 0


# ── 10b5-1 / Optionsausübung herausrechnen ────────────────────────────────

def test_10b5_1_verkaeufe_werden_ignoriert():
    """Geplante 10b5-1-Verkäufe zählen nicht; nur der Open-Market-Kauf bleibt."""
    txns = [
        {"type": "buy", "value": 50_000},
        {"type": "sell", "value": 500_000, "plan": "10b5-1"},
    ]
    result = asyncio.run(_make_agent(txns).run("X"))
    assert result.signal == Signal.BULLISH


def test_optionsausuebung_wird_ignoriert():
    txns = [
        {"type": "sell", "value": 80_000, "acquisition_type": "option_exercise"},
        {"type": "buy", "value": 80_000},
    ]
    assert _net_value(txns) > 0


# ── Fallback shares, wenn value fehlt ─────────────────────────────────────

def test_fallback_auf_shares_ohne_value():
    txns = [{"type": "buy", "shares": 10_000}, {"type": "sell", "shares": 1_000}]
    assert _net_value(txns) > 0


# ── Schwellen-Signal ──────────────────────────────────────────────────────

def test_ausgeglichen_ist_neutral():
    assert _signal(0.0, total_abs=0.0) == Signal.NEUTRAL


def test_leere_liste_neutral():
    result = asyncio.run(_make_agent([]).run("X"))
    assert result.signal == Signal.NEUTRAL
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/agents/stock_deep_dive/equity/test_insider_agent.py -q`. Erwarteter Grund: `ImportError: cannot import name '_net_value'`.

- [ ] **(3) Implementierung** — `agents/stock_deep_dive/equity/insider_agent.py` vollständig ersetzen:

```python
import asyncio

from core.domain.events import InsiderDataReady
from core.domain.models import InsiderSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = InsiderSnapshot(net_direction="neutral", recent_transactions=0, signal=Signal.NEUTRAL)

# Käufe signalstärker als Verkäufe (Verkäufe oft liquiditäts-/diversifikationsgetrieben).
_BUY_WEIGHT  = 1.5
_SELL_WEIGHT = 1.0
# Signal-Schwelle als Anteil des Netto- am Brutto-Volumen (Richtungs-Klarheit).
_NET_THRESHOLD = 0.20


def _is_informative(t: dict) -> bool:
    """Filtert geplante 10b5-1-Programme und Optionsausübungen heraus (nicht-informativ).
    Datenannahme: fehlende Felder → Transaktion gilt als open-market (informativ)."""
    if str(t.get("plan", "")).lower() in ("10b5-1", "10b5_1", "rule 10b5-1"):
        return False
    if t.get("acquisition_type") == "option_exercise":
        return False
    return True


def _magnitude(t: dict) -> float:
    """Wert (USD) bevorzugt, sonst Aktienzahl, sonst Einheitsgewicht 1.0."""
    val = t.get("value")
    if val is not None:
        return abs(float(val))
    shares = t.get("shares")
    if shares is not None:
        return abs(float(shares))
    return 1.0


def _net_value(transactions: list[dict]) -> float:
    """Wertgewichtete Netto-Insider-Aktivität (Käufe positiv, stärker gewichtet)."""
    net = 0.0
    for t in transactions:
        if not _is_informative(t):
            continue
        mag = _magnitude(t)
        if t.get("type") == "buy":
            net += _BUY_WEIGHT * mag
        elif t.get("type") == "sell":
            net -= _SELL_WEIGHT * mag
    return net


def _gross_value(transactions: list[dict]) -> float:
    total = 0.0
    for t in transactions:
        if not _is_informative(t):
            continue
        w = _BUY_WEIGHT if t.get("type") == "buy" else _SELL_WEIGHT
        total += w * _magnitude(t)
    return total


def _signal(net: float, total_abs: float) -> Signal:
    if total_abs <= 0.0:
        return Signal.NEUTRAL
    ratio = net / total_abs
    if ratio > _NET_THRESHOLD:
        return Signal.BULLISH
    if ratio < -_NET_THRESHOLD:
        return Signal.BEARISH
    return Signal.NEUTRAL


class InsiderAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> InsiderSnapshot:
        transactions = await asyncio.to_thread(self.provider.get_insider_activity, ticker)
        net   = _net_value(transactions)
        gross = _gross_value(transactions)
        signal = _signal(net, gross)
        direction = (
            "net_buy" if signal == Signal.BULLISH
            else "net_sell" if signal == Signal.BEARISH
            else "neutral"
        )
        result = InsiderSnapshot(net_direction=direction, recent_transactions=len(transactions), signal=signal)
        self.bus.publish(InsiderDataReady(source="insider_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> InsiderSnapshot:
        return _DEFAULT
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/agents/stock_deep_dive/equity/test_insider_agent.py -q`. Erwartung: 8 passed. Regression: `python -m pytest tests/agents/stock_deep_dive -q`.

- [ ] **(5) Self-Review** — Prüfen: 10b5-1/option_exercise gefiltert; Käufe mit `1.5` gewichtet; Signal aus Netto/Brutto-Verhältnis (nicht absoluter Dollar-Betrag, damit kleine wie große Titel vergleichbar sind); Datenannahme im Modul-Docstring/Plan dokumentiert.

- [ ] **(6) Commit** — `git add agents/stock_deep_dive/equity/insider_agent.py tests/agents/stock_deep_dive/equity/test_insider_agent.py && git commit -m "fix(insider): wertgewichtete Netto-Aktivität, Käufe stärker, 10b5-1/Optionen herausgerechnet"`

---

## Task 6: `short_interest_agent` — Short-%-Float + days_to_cover + Trend kombiniert

> Review-Bezug Domäne 4 `short_interest`: „Hoher Short-Interest = bearish" ist eindimensional und teils gegenläufig — hoher Short-Float ist auch **Squeeze-Brennstoff**. `days_to_cover` (Short-Interest-Ratio) erfasst, aber ungenutzt. Niedriger Short-Float <5 % als „bullish" schwach begründet. Lösung: Short-%-Float + Days-to-Cover + Trend kombiniert; hohe Werte als Risiko-/Squeeze-Flag (kontextabhängig), niedrigen Short-Float **neutral** statt bullish.

> **Datenannahme:** `get_short_interest` liefert zusätzlich `short_float_trend` (`"rising" | "stable" | "falling"`). Fehlt es, gilt `"stable"`. Steigender Short-Float bei bereits hohem Niveau = Bestätigung der Skepsis (bearish), fallender hoher Short-Float = sich auflösende Skepsis / Squeeze-Potenzial (eher bullish).

**Files:**
- Modify: `agents/stock_deep_dive/equity/short_interest_agent.py`
- Test: `tests/agents/stock_deep_dive/equity/test_short_interest_agent.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/agents/stock_deep_dive/equity/test_short_interest_agent.py`:

```python
import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.short_interest_agent import ShortInterestAgent, _signal
from core.domain.models import Signal


def _make_agent(data: dict) -> ShortInterestAgent:
    provider = MagicMock()
    provider.get_short_interest.return_value = data
    return ShortInterestAgent(provider, MagicMock())


# ── niedriger Short-Float ist NEUTRAL (nicht mehr bullish) ─────────────────

def test_niedriger_short_float_ist_neutral():
    sig = _signal(short_float=3.0, dtc=1.0, trend="stable")
    assert sig == Signal.NEUTRAL


# ── hoher Short-Float + steigender Trend = bearish-Bestätigung ─────────────

def test_hoher_short_float_steigend_ist_bearish():
    sig = _signal(short_float=28.0, dtc=8.0, trend="rising")
    assert sig == Signal.BEARISH


# ── hoher Short-Float + fallender Trend + hoher DTC = Squeeze-Potenzial ────

def test_hoher_short_float_fallend_hoher_dtc_ist_bullish():
    """Sich auflösende Skepsis bei hohem Days-to-Cover → Squeeze-Brennstoff (bullish)."""
    sig = _signal(short_float=28.0, dtc=9.0, trend="falling")
    assert sig == Signal.BULLISH


# ── days_to_cover fließt ein ──────────────────────────────────────────────

def test_days_to_cover_verstaerkt_squeeze():
    """Hoher Short-Float, fallend, aber niedriger DTC → kein starkes Squeeze-Signal."""
    low_dtc  = _signal(short_float=28.0, dtc=1.0, trend="falling")
    high_dtc = _signal(short_float=28.0, dtc=9.0, trend="falling")
    order = {Signal.BEARISH: -1, Signal.NEUTRAL: 0, Signal.BULLISH: 1}
    assert order[high_dtc] >= order[low_dtc]


# ── fehlende Daten ────────────────────────────────────────────────────────

def test_keine_daten_neutral():
    sig = _signal(short_float=None, dtc=None, trend="stable")
    assert sig == Signal.NEUTRAL


def test_run_durchreichung():
    result = asyncio.run(_make_agent({
        "short_float_pct": 28.0, "days_to_cover": 9.0, "short_float_trend": "falling",
    }).run("X"))
    assert result.signal == Signal.BULLISH
    assert result.days_to_cover == 9.0
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/agents/stock_deep_dive/equity/test_short_interest_agent.py -q`. Erwarteter Grund: `TypeError: _signal() got an unexpected keyword argument 'dtc'` (alte Signatur war nur `short_float`/inline).

- [ ] **(3) Implementierung** — `agents/stock_deep_dive/equity/short_interest_agent.py` vollständig ersetzen:

```python
import asyncio

from core.domain.events import ShortInterestReady
from core.domain.models import ShortInterestSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = ShortInterestSnapshot(short_float_pct=None, days_to_cover=None, signal=Signal.NEUTRAL)

_HIGH_FLOAT = 20.0       # % des Float → erhöhte Aufmerksamkeit
_HIGH_DTC   = 5.0        # Days-to-Cover → Squeeze-Anfälligkeit


def _signal(short_float: float | None, dtc: float | None, trend: str) -> Signal:
    """Kombiniert Short-%-Float, days_to_cover und Trend.
    - Niedriger Short-Float: NEUTRAL (keine Information).
    - Hoher Short-Float + steigend: BEARISH (bestätigte Skepsis).
    - Hoher Short-Float + fallend + hoher DTC: BULLISH (Squeeze-Brennstoff, sich auflösend).
    - Sonst: NEUTRAL.
    """
    if short_float is None:
        return Signal.NEUTRAL
    if short_float < _HIGH_FLOAT:
        return Signal.NEUTRAL

    # Ab hier: hoher Short-Float → kontextabhängig
    if trend == "rising":
        return Signal.BEARISH
    if trend == "falling" and dtc is not None and dtc >= _HIGH_DTC:
        return Signal.BULLISH
    return Signal.NEUTRAL


class ShortInterestAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> ShortInterestSnapshot:
        data = await asyncio.to_thread(self.provider.get_short_interest, ticker)
        short_float = data.get("short_float_pct")
        dtc = data.get("days_to_cover")
        trend = data.get("short_float_trend", "stable")
        result = ShortInterestSnapshot(
            short_float_pct=short_float, days_to_cover=dtc,
            signal=_signal(short_float, dtc, trend),
        )
        self.bus.publish(ShortInterestReady(source="short_interest_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> ShortInterestSnapshot:
        return _DEFAULT
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/agents/stock_deep_dive/equity/test_short_interest_agent.py -q`. Erwartung: 6 passed. Regression: `python -m pytest tests/agents/stock_deep_dive -q`.

- [ ] **(5) Self-Review** — Prüfen: niedriger Float ist NEUTRAL (nicht bullish); `days_to_cover` wirklich genutzt (Squeeze-Pfad); Trend-Datenannahme dokumentiert.

- [ ] **(6) Commit** — `git add agents/stock_deep_dive/equity/short_interest_agent.py tests/agents/stock_deep_dive/equity/test_short_interest_agent.py && git commit -m "fix(short_interest): Short-%-Float + days_to_cover + Trend kombiniert, niedriger Float neutral"`

---

## Task 7: `moat_agent` — Maximum-/Schwellen-pro-Kategorie, Moat von Empfehlung entkoppeln

> Review-Bezug Domäne 4 `moat._overall`/`._signal`: (1) **ungewichtete Summe** — ein einzelner sehr starker Netzwerkeffekt (Visa, Google) begründet real allein einen Wide Moat, erreicht hier nur „narrow"; (2) Score ≥7 für „wide" verlangt 3–4 gleichzeitig starke Kategorien → zu streng; (3) `none → BEARISH` fragwürdig (fehlender Moat ist Bewertungssache, nicht per se bärisch). Lösung: **Maximum-/Schwellen-pro-Kategorie** (eine dominante Quelle kann „wide" begründen); Moat-Signal von der Aktien-Empfehlung **entkoppeln** (Wide → BULLISH-Qualitätsmerkmal; None/Narrow → NEUTRAL statt BEARISH).

**Files:**
- Modify: `agents/stock_deep_dive/equity/moat_agent.py`
- Test: `tests/agents/stock_deep_dive/equity/test_moat_agent.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/agents/stock_deep_dive/equity/test_moat_agent.py`:

```python
from agents.stock_deep_dive.equity.moat_agent import _overall, _signal
from core.domain.models import Signal, MoatScore


def _scores(**kw) -> list[MoatScore]:
    base = {"ia": 0, "sc": 0, "ne": 0, "ca": 0, "es": 0}
    base.update(kw)
    return [MoatScore(score=v, evidence="") for v in base.values()]


# ── Maximum-/Schwellen-pro-Kategorie ──────────────────────────────────────

def test_eine_dominante_quelle_begruendet_wide():
    """Ein einzelner sehr starker Netzwerkeffekt (2) → 'wide', auch wenn Rest 0."""
    assert _overall(_scores(ne=2)) == "wide"


def test_zwei_starke_quellen_sind_wide():
    assert _overall(_scores(ne=2, sc=2)) == "wide"


def test_eine_schwache_quelle_ist_narrow():
    """Genau eine Kategorie mit Score 1 → 'narrow'."""
    assert _overall(_scores(sc=1)) == "narrow"


def test_keine_quelle_ist_none():
    assert _overall(_scores()) == "none"


def test_alte_summenlogik_haette_narrow_gegeben():
    """Gegenprobe: Summe=2 (ein 2er) hätte alt 'none' ergeben; neu ist es 'wide'."""
    scores = _scores(ne=2)
    assert sum(s.score for s in scores) == 2     # alte Summe → wäre 'none'
    assert _overall(scores) == "wide"            # neue Maximum-Logik


# ── Moat von Empfehlung entkoppelt ────────────────────────────────────────

def test_wide_ist_bullish():
    assert _signal("wide") == Signal.BULLISH


def test_none_ist_neutral_nicht_bearish():
    """Fehlender Moat ist Bewertungssache, nicht per se bärisch."""
    assert _signal("none") == Signal.NEUTRAL


def test_narrow_ist_neutral():
    assert _signal("narrow") == Signal.NEUTRAL
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/agents/stock_deep_dive/equity/test_moat_agent.py -q`. Erwarteter Grund: `TypeError: _overall() takes 1 positional argument (an int) but a list was given` und `_signal("none") == BEARISH` (alte Entkopplung fehlt).

- [ ] **(3) Implementierung** — in `agents/stock_deep_dive/equity/moat_agent.py` die Funktionen `_overall`/`_signal` und ihre Aufrufstelle ersetzen (Imports + Prompt + Klasse bleiben unverändert):

```python
def _overall(scores: list[MoatScore]) -> str:
    """Maximum-/Schwellen-pro-Kategorie statt linearer Summe.
    Eine dominante Quelle (Score 2) begründet allein 'wide'; eine 1er-Quelle 'narrow'."""
    max_score = max((s.score for s in scores), default=0)
    if max_score >= 2:
        return "wide"
    if max_score >= 1:
        return "narrow"
    return "none"


def _signal(overall: str) -> Signal:
    """Moat ist ein Qualitäts-/Prämien-Merkmal, kein Timing-Signal.
    Wide → BULLISH (rechtfertigt Bewertungsprämie); None/Narrow → NEUTRAL (nicht BEARISH)."""
    if overall == "wide":
        return Signal.BULLISH
    return Signal.NEUTRAL
```

Und in `run()` die Aufrufe anpassen (statt `_overall(total)` / `_signal(total)`):

```python
        all_scores = [ia, sc, ne, ca, es]
        total = ia.score + sc.score + ne.score + ca.score + es.score
        overall = _overall(all_scores)

        result = MoatSnapshot(
            intangible_assets=ia, switching_costs=sc, network_effects=ne,
            cost_advantages=ca, efficient_scale=es,
            total_score=total,
            overall=overall,
            llm_reasoning=data.get("reasoning", ""),
            signal=_signal(overall),
        )
```

> `total_score` bleibt als deskriptive Summe im Snapshot erhalten (Backward-Compat / Dashboard), trägt aber das Signal nicht mehr.

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/agents/stock_deep_dive/equity/test_moat_agent.py -q`. Erwartung: 8 passed. Regression: `python -m pytest tests/agents/stock_deep_dive -q`.

- [ ] **(5) Self-Review** — Prüfen: `_overall` nimmt jetzt die Score-Liste; `_signal` nimmt den `overall`-String; `none`/`narrow` → NEUTRAL; `_DEFAULT.signal` ist `Signal.NEUTRAL` (war es bereits) — konsistent zur Entkopplung.

- [ ] **(6) Commit** — `git add agents/stock_deep_dive/equity/moat_agent.py tests/agents/stock_deep_dive/equity/test_moat_agent.py && git commit -m "fix(moat): Maximum-pro-Kategorie statt Summe, Moat von Empfehlung entkoppelt (none→NEUTRAL)"`

---

## Task 8: `equity_chief_agent` — gewichtete Gesamtbeurteilung via `weighted_signal`, `sector` weiterreichen

> Review-Bezug Domäne 4 `equity_chief.run`: Reiner Orchestrator ohne Aggregation der 7 Einzelsignale; `sector` wird nur an `valuation_range` weitergereicht, **nicht** an `fundamentals`/`quality`. Lösung: gewichtete Gesamtbeurteilung via Plan-0 `weighted_signal` (Bewertung als Langfrist-Anker, Qualität/Moat als Prämien-Rechtfertigung, Earnings/Momentum als Timing); `sector` an alle sektor-sensitiven Sub-Agenten. Sub-Snapshots tragen `Signal`; ein fehlendes/Default-Signal wird als `UNAVAILABLE` markiert und re-normalisiert (Plan-0-Semantik).

**Files:**
- Modify: `agents/stock_deep_dive/equity_chief_agent.py`
- Test: `tests/agents/stock_deep_dive/equity/test_equity_chief_agent.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/agents/stock_deep_dive/equity/test_equity_chief_agent.py`:

```python
import asyncio
from unittest.mock import MagicMock, patch

from agents.stock_deep_dive.equity_chief_agent import EquityChiefAgent, _aggregate_signal
from core.domain.models import (
    Signal, SignalStatus,
    FundamentalsSnapshot, QualitySnapshot, MoatSnapshot, MoatScore,
    EarningsTrendSnapshot, InsiderSnapshot, ShortInterestSnapshot,
    ValuationRangeSnapshot,
)


# ── gewichtete Gesamtbeurteilung ──────────────────────────────────────────

def test_aggregate_dominiert_von_bewertung_und_qualitaet():
    """Bullish Bewertung + bullish Qualität + bullish Moat → BULLISH gesamt."""
    sig, conf = _aggregate_signal(
        fundamentals_sig=Signal.BULLISH,
        quality_sig=Signal.BULLISH,
        valuation_sig=Signal.BULLISH,
        moat_sig=Signal.BULLISH,
        earnings_sig=Signal.NEUTRAL,
        insider_sig=Signal.NEUTRAL,
        short_sig=Signal.NEUTRAL,
    )
    assert sig == Signal.BULLISH
    assert conf > 0.0


def test_aggregate_konflikt_neutralisiert():
    """Bullish Bewertung gegen bearish Qualität (gleich gewichtet) → tendenziell NEUTRAL."""
    sig, _ = _aggregate_signal(
        fundamentals_sig=Signal.BULLISH,
        quality_sig=Signal.BEARISH,
        valuation_sig=Signal.NEUTRAL,
        moat_sig=Signal.NEUTRAL,
        earnings_sig=Signal.NEUTRAL,
        insider_sig=Signal.NEUTRAL,
        short_sig=Signal.NEUTRAL,
    )
    assert sig == Signal.NEUTRAL


# ── sector wird an fundamentals UND quality weitergereicht ─────────────────

def test_sector_an_fundamentals_und_quality_weitergereicht():
    fundamentals = MagicMock(); market = MagicMock(); llm = MagicMock(); bus = MagicMock()
    chief = EquityChiefAgent(fundamentals, market, llm, bus)

    chief.fundamentals_agent.run    = MagicMock(return_value=_afut(FundamentalsAgentDefault()))
    chief.quality_agent.run         = MagicMock(return_value=_afut(QualityAgentDefault()))
    chief.short_agent.run           = MagicMock(return_value=_afut(_short_default()))
    chief.insider_agent.run         = MagicMock(return_value=_afut(_insider_default()))
    chief.earnings_agent.run        = MagicMock(return_value=_afut(_earnings_default()))
    chief.moat_agent.run            = MagicMock(return_value=_afut(_moat_default()))
    chief.valuation_range_agent.run = MagicMock(return_value=_afut(_val_default()))

    asyncio.run(chief.run("AAPL", sector="Technology"))

    chief.fundamentals_agent.run.assert_called_once_with("AAPL", sector="Technology")
    chief.quality_agent.run.assert_called_once_with("AAPL", sector="Technology")
    chief.valuation_range_agent.run.assert_called_once_with("AAPL", "Technology")


# ── Helpers ───────────────────────────────────────────────────────────────

def _afut(value):
    fut = asyncio.Future()
    fut.set_result(value)
    return fut

def _moat_default():
    z = MoatScore(score=0, evidence="")
    return MoatSnapshot(z, z, z, z, z, 0, "none", "", Signal.NEUTRAL)

def FundamentalsAgentDefault():
    from agents.stock_deep_dive.equity.fundamentals_agent import FundamentalsAgent
    return FundamentalsAgent.default()

def QualityAgentDefault():
    from agents.stock_deep_dive.equity.quality_agent import QualityAgent
    return QualityAgent.default()

def _short_default():
    return ShortInterestSnapshot(None, None, Signal.NEUTRAL)

def _insider_default():
    return InsiderSnapshot("neutral", 0, Signal.NEUTRAL)

def _earnings_default():
    return EarningsTrendSnapshot(None, "flat", Signal.NEUTRAL)

def _val_default():
    return ValuationRangeSnapshot([], 0.0, 0.0, None, "unknown", Signal.NEUTRAL)
```

> Hinweis: `_afut` ersetzt jeden `*_agent.run`-Coroutine durch ein bereits gelöstes Future, damit `asyncio.gather` synchron auswertbar bleibt (Stil wie bestehende Chief-Tests in `tests/agents/stock_deep_dive`).

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/agents/stock_deep_dive/equity/test_equity_chief_agent.py -q`. Erwarteter Grund: `ImportError: cannot import name '_aggregate_signal'` und `assert_called_once_with("AAPL", sector="Technology")` schlägt fehl (alter Code ruft `fundamentals_agent.run(ticker)` ohne sector).

- [ ] **(3) Implementierung** — `agents/stock_deep_dive/equity_chief_agent.py` anpassen. (a) Import ergänzen, (b) `_aggregate_signal` einführen, (c) `run()` sektor-durchreichen + aggregieren:

Imports am Kopf ergänzen:

```python
from core.domain.models import EquityChiefResult, Signal, SignalStatus
from core.utils.aggregation import weighted_signal
```

Vor der Klasse einfügen:

```python
# Gewichte: Bewertung = Langfrist-Anker, Qualität/Moat = Prämien-Rechtfertigung,
# Earnings/Insider/Short = Timing/Bestätigung.
_W_VALUATION = 0.25
_W_FUNDAMENTALS = 0.20
_W_QUALITY = 0.20
_W_MOAT = 0.15
_W_EARNINGS = 0.10
_W_INSIDER = 0.05
_W_SHORT = 0.05


def _status(sig: Signal) -> SignalStatus:
    """NEUTRAL gilt als verfügbar (eine bewusste neutrale Aussage), aber neutrale
    Default-Snapshots tragen ohnehin Gewicht 0-Wirkung im Voting. Hier: alle
    vorhandenen Sub-Signale sind AVAILABLE; UNAVAILABLE bleibt späteren Stubs
    vorbehalten (Plan 0 P1.4)."""
    return SignalStatus.AVAILABLE


def _aggregate_signal(fundamentals_sig, quality_sig, valuation_sig, moat_sig,
                      earnings_sig, insider_sig, short_sig) -> tuple[Signal, float]:
    items = [
        (valuation_sig,    _W_VALUATION,    _status(valuation_sig)),
        (fundamentals_sig, _W_FUNDAMENTALS, _status(fundamentals_sig)),
        (quality_sig,      _W_QUALITY,      _status(quality_sig)),
        (moat_sig,         _W_MOAT,         _status(moat_sig)),
        (earnings_sig,     _W_EARNINGS,     _status(earnings_sig)),
        (insider_sig,      _W_INSIDER,      _status(insider_sig)),
        (short_sig,        _W_SHORT,        _status(short_sig)),
    ]
    return weighted_signal(items)
```

In `run()` die Sub-Agenten-Aufrufe und die Aggregation anpassen:

```python
    async def run(self, ticker: str, sector: str = "default") -> EquityChiefResult:
        results = await asyncio.gather(
            self.fundamentals_agent.run(ticker, sector=sector),
            self.quality_agent.run(ticker, sector=sector),
            self.short_agent.run(ticker),
            self.insider_agent.run(ticker),
            self.earnings_agent.run(ticker),
            self.moat_agent.run(ticker),
            self.valuation_range_agent.run(ticker, sector),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        fundamentals    = _safe(results[0], FundamentalsAgent.default())
        quality         = _safe(results[1], QualityAgent.default())
        short_interest  = _safe(results[2], ShortInterestAgent.default())
        insider         = _safe(results[3], InsiderAgent.default())
        earnings_trend  = _safe(results[4], EarningsTrendAgent.default())
        moat            = _safe(results[5], MoatAgent.default())
        valuation_range = _safe(results[6], ValuationRangeAgent.default())

        overall_signal, confidence = _aggregate_signal(
            fundamentals_sig=fundamentals.signal,
            quality_sig=quality.signal,
            valuation_sig=valuation_range.signal,
            moat_sig=moat.signal,
            earnings_sig=earnings_trend.signal,
            insider_sig=insider.signal,
            short_sig=short_interest.signal,
        )

        self.bus.publish(EquityChiefReady(source="equity_chief_agent", payload={
            "ticker": ticker, "signal": overall_signal.value, "confidence": round(confidence, 3),
        }))

        return EquityChiefResult(
            fundamentals=fundamentals,
            quality=quality,
            short_interest=short_interest,
            insider=insider,
            earnings_trend=earnings_trend,
            moat=moat,
            valuation_range=valuation_range,
        )
```

> `EquityChiefResult` bleibt strukturell unverändert (keine Modelländerung in Scope dieses Plans); das aggregierte Gesamturteil wird über das `EquityChiefReady`-Event publiziert. Falls ein nachgelagerter Konsument das Gesamturteil im Result-Objekt benötigt, erfolgt die Felderweiterung in einem späteren Plan (Recommendation/Judgment).

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/agents/stock_deep_dive/equity/test_equity_chief_agent.py -q`. Erwartung: 3 passed. Regression: `python -m pytest tests/agents/stock_deep_dive -q` (insbesondere bestehende Chief-/Bottom-Up-Tests, die `equity_chief.run(ticker)` ohne sector aufrufen — Default `"default"` sichert Abwärtskompatibilität).

- [ ] **(5) Self-Review** — Prüfen: `fundamentals_agent.run` und `quality_agent.run` mit `sector=` aufgerufen; Gewichtssumme = 1.0; Bewertung höchstes Einzelgewicht; bestehende Aufrufer des Chiefs ohne `sector` weiterhin grün (mit `rg "equity_chief.*\.run\(" -n` Aufrufstellen prüfen).

- [ ] **(6) Commit** — `git add agents/stock_deep_dive/equity_chief_agent.py tests/agents/stock_deep_dive/equity/test_equity_chief_agent.py && git commit -m "feat(equity_chief): gewichtete Gesamtbeurteilung via weighted_signal, sector an fundamentals/quality"`

---

## Task 9: `index_momentum_agent` — Wilder-RSI, MA200 aus ≥2y, Signal aus MA50/MA200-Status

> Review-Bezug Domäne 6 / P4.2 + `index_momentum._signal`: (1) RSI nutzt `rolling(14).mean()` (Cutler) statt **Wilder-Smoothing**; (2) MA200 aus nur „1y"-Historie ist fragil; (3) BEARISH nur bei `not golden_cross and rsi>70` → praktisch unerreichbar, und `golden_cross is None` (häufigster Fall) ignoriert die berechnete Trendlage. Lösung: Wilder-RSI aus `scoring.py`; Historie „2y" laden; Signal aus dem **Status** `ma50 vs ma200` (über MA200 + RSI nicht überkauft = bullish; unter MA200 / Death Cross = bearish) plus RSI-Extreme. Die bestehende `_detect_crossover`-Funktion und ihre Tests bleiben unverändert (Cross-Event weiterhin als Snapshot-Feld).

**Files:**
- Modify: `agents/stock_deep_dive/index/index_momentum_agent.py`
- Test: `tests/agents/stock_deep_dive/index/test_index_momentum_agent.py` (Modify — neue Tests anhängen; bestehende `_detect_crossover`-Tests bleiben)

- [ ] **(1) Failing Test schreiben** — bestehende Datei `tests/agents/stock_deep_dive/index/test_index_momentum_agent.py` anpassen. Die alten `_signal`-Tests (binär `golden_cross`/`rsi`) werden durch die neue Status-basierte Signatur ersetzt; `_detect_crossover`-Tests bleiben. Neuen `_signal`-Block oben einfügen (alte `_signal`-Tests Zeilen ~8–35 entfernen) und Import um `wilder_rsi`-Bezug ergänzen:

```python
import pandas as pd
from agents.stock_deep_dive.index.index_momentum_agent import _signal, _detect_crossover, _compute_rsi
from core.domain.models import Signal


# ── Status-basiertes Signal (MA50/MA200 + RSI-Extreme) ────────────────────

def test_ueber_ma200_rsi_normal_ist_bullish():
    """ma50 > ma200 (Aufwärtstrend) + RSI nicht überkauft → BULLISH."""
    assert _signal(ma50=110.0, ma200=100.0, rsi=55.0) == Signal.BULLISH


def test_ueber_ma200_aber_ueberkauft_ist_neutral():
    """Aufwärtstrend, aber RSI > 70 (überkauft) → NEUTRAL (kein frischer Einstieg)."""
    assert _signal(ma50=110.0, ma200=100.0, rsi=78.0) == Signal.NEUTRAL


def test_unter_ma200_ist_bearish():
    """ma50 < ma200 (Abwärtstrend) → BEARISH — unabhängig von einem frischen Cross-Event."""
    assert _signal(ma50=95.0, ma200=100.0, rsi=50.0) == Signal.BEARISH


def test_unter_ma200_ueberverkauft_ist_neutral():
    """Abwärtstrend, aber RSI < 30 (überverkauft) → NEUTRAL (Downside verbraucht)."""
    assert _signal(ma50=95.0, ma200=100.0, rsi=22.0) == Signal.NEUTRAL


def test_fehlende_mas_ist_neutral():
    assert _signal(ma50=None, ma200=100.0, rsi=50.0) == Signal.NEUTRAL


def test_compute_rsi_nutzt_wilder():
    """_compute_rsi delegiert an Wilder (ewm) — weicht vom SMA-RSI ab."""
    vals = [100.0] * 20 + [80.0] + [101.0 + i for i in range(20)]
    prices = pd.Series(vals)
    delta = prices.diff().dropna()
    gain_sma = delta.clip(lower=0).rolling(14).mean()
    loss_sma = (-delta.clip(upper=0)).rolling(14).mean()
    rs_sma = gain_sma / loss_sma.replace(0, float("nan"))
    sma_rsi = round(float((100 - 100 / (1 + rs_sma)).iloc[-1]), 2)
    assert abs(_compute_rsi(prices) - sma_rsi) > 0.01


# ── Crossover-Erkennung (unverändert) ─────────────────────────────────────

def _make_series(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


def test_detect_golden_cross():
    ma50  = _make_series([98, 99, 100, 101, 102, 103])
    ma200 = _make_series([101, 101, 101, 101, 101, 101])
    assert _detect_crossover(ma50, ma200) is True


def test_detect_death_cross():
    ma50  = _make_series([103, 102, 101, 100, 99, 98])
    ma200 = _make_series([101, 101, 101, 101, 101, 101])
    assert _detect_crossover(ma50, ma200) is False


def test_detect_no_cross_stable_above():
    ma50  = _make_series([105, 105, 105, 105, 105, 105])
    ma200 = _make_series([100, 100, 100, 100, 100, 100])
    assert _detect_crossover(ma50, ma200) is None


def test_detect_no_cross_stable_below():
    ma50  = _make_series([95, 95, 95, 95, 95, 95])
    ma200 = _make_series([100, 100, 100, 100, 100, 100])
    assert _detect_crossover(ma50, ma200) is None
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/agents/stock_deep_dive/index/test_index_momentum_agent.py -q`. Erwarteter Grund: `TypeError: _signal() got an unexpected keyword argument 'ma50'` (alte Signatur `_signal(golden_cross, rsi)`).

- [ ] **(3) Implementierung** — `agents/stock_deep_dive/index/index_momentum_agent.py` anpassen. (a) `_compute_rsi` an `wilder_rsi` delegieren, (b) `_signal` auf Status umstellen, (c) Historie „2y" laden:

```python
import asyncio

from core.domain.events import IndexMomentumReady
from core.domain.models import IndexMomentumSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.scoring import wilder_rsi

_WORLD_BENCHMARK = "URTH"   # iShares MSCI World ETF
_CROSS_WINDOW    = 5        # Handelstage für Kreuzungspunkt-Erkennung
_HISTORY_PERIOD  = "2y"     # MA200 braucht ≥2y für ein stabiles Cross-Fenster (P4.2)
_RSI_OVERBOUGHT  = 70.0
_RSI_OVERSOLD    = 30.0

_DEFAULT = IndexMomentumSnapshot(
    rsi_14=None, ma50=None, ma200=None,
    golden_cross=None, relative_strength=None, signal=Signal.NEUTRAL,
)


def _compute_rsi(prices, period: int = 14) -> float | None:
    """Wilder-Smoothing-RSI (delegiert an core.utils.scoring.wilder_rsi)."""
    return wilder_rsi(prices, period=period)


def _detect_crossover(ma50_series, ma200_series) -> bool | None:
    """True = Golden Cross, False = Death Cross, None = kein Kreuzungspunkt in letzten 5 Tagen."""
    try:
        diff   = ma50_series - ma200_series
        recent = diff.iloc[-(_CROSS_WINDOW + 1):]
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


def _signal(ma50: float | None, ma200: float | None, rsi: float | None) -> Signal:
    """Signal aus dem Trend-STATUS (ma50 vs ma200) + RSI-Extreme statt nur Cross-Event.
    - Aufwärtstrend (ma50 > ma200) + RSI nicht überkauft → BULLISH.
    - Abwärtstrend (ma50 < ma200) + RSI nicht überverkauft → BEARISH.
    - Extreme dämpfen (überkauft im Up / überverkauft im Down) → NEUTRAL.
    """
    if ma50 is None or ma200 is None:
        return Signal.NEUTRAL
    uptrend = ma50 > ma200
    if uptrend:
        if rsi is not None and rsi > _RSI_OVERBOUGHT:
            return Signal.NEUTRAL
        return Signal.BULLISH
    # Abwärtstrend
    if rsi is not None and rsi < _RSI_OVERSOLD:
        return Signal.NEUTRAL
    return Signal.BEARISH


class IndexMomentumAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> IndexMomentumSnapshot:
        try:
            hist, bench = await asyncio.gather(
                asyncio.to_thread(self.market.get_price_history, ticker, _HISTORY_PERIOD),
                asyncio.to_thread(self.market.get_price_history, _WORLD_BENCHMARK, _HISTORY_PERIOD),
                return_exceptions=True,
            )
            if isinstance(hist, Exception):
                return _DEFAULT

            close    = hist["Close"]
            ma50_s   = close.rolling(50).mean()
            ma200_s  = close.rolling(200).mean()
            ma50     = round(float(ma50_s.iloc[-1]), 2)
            ma200    = round(float(ma200_s.iloc[-1]), 2)
            rsi      = _compute_rsi(close)
            golden   = _detect_crossover(ma50_s, ma200_s)

            rs = None
            if not isinstance(bench, Exception):
                bc = bench["Close"]
                ticker_ret = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
                bench_ret  = (bc.iloc[-1] - bc.iloc[0]) / bc.iloc[0]
                rs = round(float(ticker_ret - bench_ret) * 100, 2)

            result = IndexMomentumSnapshot(
                rsi_14=rsi, ma50=ma50, ma200=ma200,
                golden_cross=golden, relative_strength=rs,
                signal=_signal(ma50, ma200, rsi),
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(IndexMomentumReady(source="index_momentum_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> IndexMomentumSnapshot:
        return _DEFAULT
```

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/agents/stock_deep_dive/index/test_index_momentum_agent.py -q`. Erwartung: alle grün (neue `_signal`- + Wilder-Tests + unveränderte `_detect_crossover`-Tests). Regression: `python -m pytest tests/agents/stock_deep_dive/index -q`.

- [ ] **(5) Self-Review** — Prüfen: `_compute_rsi` ruft `wilder_rsi`; Historie `"2y"`; BEARISH jetzt regulär erreichbar (Abwärtstrend ohne Überverkauft-Dämpfung); `golden_cross` bleibt als Snapshot-Feld erhalten, ist aber nicht mehr alleiniger Signal-Treiber.

- [ ] **(6) Commit** — `git add agents/stock_deep_dive/index/index_momentum_agent.py tests/agents/stock_deep_dive/index/test_index_momentum_agent.py && git commit -m "fix(index_momentum): Wilder-RSI, MA200 aus 2y, Signal aus MA50/MA200-Status + RSI-Extreme"`

---

## Task 10: `index_chief_agent` — gewichtete Synthese der Sub-Signale via `weighted_signal`

> Review-Bezug Domäne 6 `index_chief.run`: Reiner Aggregator ohne Gesamt-Signal-Synthese (kein gewichtetes Voting, kein Konfliktauflöser zwischen BULLISH-Valuation und BEARISH-Momentum). Lösung: top-down-gewichtete Synthese — Bewertung (Langfrist-Anker) + Momentum/Breadth (Timing) mit definierten Gewichten. Die Sub-Agenten `valuation`/`earnings`/`breadth`/`composition` werden von anderen Plänen (B/E) inhaltlich repariert; hier wird **nur** die Verdichtung über die bereits vorhandenen `signal`-Felder ergänzt — ohne die fremden Agenten anzufassen.

**Files:**
- Modify: `agents/stock_deep_dive/index_chief_agent.py`
- Test: `tests/agents/stock_deep_dive/index/test_index_chief_agent.py` (Create)

- [ ] **(1) Failing Test schreiben** — `tests/agents/stock_deep_dive/index/test_index_chief_agent.py`:

```python
from agents.stock_deep_dive.index_chief_agent import _aggregate_index_signal
from core.domain.models import Signal


def test_bewertung_und_momentum_bullish_ist_bullish():
    sig, conf = _aggregate_index_signal(
        valuation_sig=Signal.BULLISH,
        momentum_sig=Signal.BULLISH,
        earnings_sig=Signal.NEUTRAL,
        breadth_sig=Signal.NEUTRAL,
        price_sig=Signal.NEUTRAL,
    )
    assert sig == Signal.BULLISH
    assert conf > 0.0


def test_bewertung_bullish_momentum_bearish_konflikt():
    """Gegenläufige gleich gewichtete Hauptsignale → NEUTRAL (Konfliktauflösung)."""
    sig, _ = _aggregate_index_signal(
        valuation_sig=Signal.BULLISH,
        momentum_sig=Signal.BEARISH,
        earnings_sig=Signal.NEUTRAL,
        breadth_sig=Signal.NEUTRAL,
        price_sig=Signal.NEUTRAL,
    )
    assert sig == Signal.NEUTRAL


def test_alle_neutral_ist_neutral():
    sig, conf = _aggregate_index_signal(
        valuation_sig=Signal.NEUTRAL, momentum_sig=Signal.NEUTRAL,
        earnings_sig=Signal.NEUTRAL, breadth_sig=Signal.NEUTRAL,
        price_sig=Signal.NEUTRAL,
    )
    assert sig == Signal.NEUTRAL
    assert conf == 0.0


def test_momentum_und_breadth_bearish_ist_bearish():
    sig, _ = _aggregate_index_signal(
        valuation_sig=Signal.NEUTRAL,
        momentum_sig=Signal.BEARISH,
        earnings_sig=Signal.NEUTRAL,
        breadth_sig=Signal.BEARISH,
        price_sig=Signal.BEARISH,
    )
    assert sig == Signal.BEARISH
```

- [ ] **(2) Test laufen lassen → erwartet FAIL** — `python -m pytest tests/agents/stock_deep_dive/index/test_index_chief_agent.py -q`. Erwarteter Grund: `ImportError: cannot import name '_aggregate_index_signal'`.

- [ ] **(3) Implementierung** — `agents/stock_deep_dive/index_chief_agent.py` anpassen. (a) Imports ergänzen, (b) `_aggregate_index_signal` einführen, (c) im `run()` synthetisieren und über das Event publizieren:

Imports ergänzen:

```python
from core.domain.models import IndexResult, Signal, SignalStatus
from core.utils.aggregation import weighted_signal
```

Vor der Klasse einfügen:

```python
# Top-down-Gewichte: Bewertung = Langfrist-Anker, Momentum/Breadth = Timing.
_W_VALUATION = 0.30
_W_MOMENTUM  = 0.25
_W_BREADTH   = 0.20
_W_EARNINGS  = 0.15
_W_PRICE     = 0.10


def _aggregate_index_signal(valuation_sig, momentum_sig, earnings_sig,
                            breadth_sig, price_sig) -> tuple[Signal, float]:
    A = SignalStatus.AVAILABLE
    items = [
        (valuation_sig, _W_VALUATION, A),
        (momentum_sig,  _W_MOMENTUM,  A),
        (breadth_sig,   _W_BREADTH,   A),
        (earnings_sig,  _W_EARNINGS,  A),
        (price_sig,     _W_PRICE,     A),
    ]
    return weighted_signal(items)
```

> Hinweis: `composition` und `valuation_range` werden von Plan B/E behandelt und bewusst (noch) nicht ins Voting aufgenommen; sobald sie verlässliche Signale liefern, können sie hier mit eigenem Gewicht ergänzt werden. Bis dahin würden ihre Default-NEUTRAL/UNAVAILABLE-Signale das Bild nur Richtung Mitte ziehen (Plan-0-Begründung P1.4).

Im `run()` nach dem `_safe`-Block die Synthese ergänzen und das Event anreichern:

```python
        overall_signal, confidence = _aggregate_index_signal(
            valuation_sig=valuation.signal,
            momentum_sig=momentum.signal,
            earnings_sig=earnings.signal,
            breadth_sig=breadth.signal,
            price_sig=price.signal,
        )

        self.bus.publish(IndexChiefReady(source="index_chief_agent", payload={
            "ticker": ticker, "signal": overall_signal.value, "confidence": round(confidence, 3),
        }))
```

(die bestehende `self.bus.publish(IndexChiefReady(...))`-Zeile durch obige ersetzen; `IndexResult`-Rückgabe bleibt strukturell unverändert).

- [ ] **(4) Test laufen → erwartet PASS** — `python -m pytest tests/agents/stock_deep_dive/index/test_index_chief_agent.py -q`. Erwartung: 4 passed. Regression: `python -m pytest tests/agents/stock_deep_dive/index -q`.

- [ ] **(5) Self-Review** — Prüfen: Gewichtssumme = 1.0; Bewertung höchstes Gewicht; Synthese ändert die `IndexResult`-Struktur nicht (nur Event-Payload); `composition`/`valuation_range` bewusst ausgelassen mit Begründung.

- [ ] **(6) Commit** — `git add agents/stock_deep_dive/index_chief_agent.py tests/agents/stock_deep_dive/index/test_index_chief_agent.py && git commit -m "feat(index_chief): gewichtete Synthese der Sub-Signale via weighted_signal"`

---

## Task 11: Gesamt-Regression Deep-Dive-Signallogik

> Sicherstellen, dass alle geänderten Agenten + neue `scoring.py`-Schicht grün sind und keine bestehenden Tests brechen. Reiner Verifikations-Task.

**Files:**
- Test: gesamte `tests/`-Suite (Schwerpunkt `tests/agents/stock_deep_dive`, `tests/utils`)

- [ ] **(1) Scope-Testlauf** — `python -m pytest tests/utils/test_scoring.py tests/agents/stock_deep_dive -q`. Erwartung: alle grün.

- [ ] **(2) Gesamt-Suite** — `python -m pytest -q`. Erwartung: keine Regression. Besonders prüfen: Bottom-Up-/Recommendation-/Judgment-Tests, die `EquityChiefAgent.run(ticker)` bzw. `IndexChiefAgent.run(ticker)` ohne neue Parameter aufrufen (Default-Parameter sichern Abwärtskompatibilität).

- [ ] **(3) Bei Fehlern** superpowers:systematic-debugging anwenden, Ursache beheben, (1)/(2) wiederholen. Häufigste Ursache: ein Aufrufer erwartet die alte `_signal`-/`_score`-Signatur — dann den Aufrufer (innerhalb des Scopes) bzw. den Test anpassen, NICHT die fachliche Logik aufweichen.

- [ ] **(4) Abschluss-Commit (nur falls Fixes nötig)** — `git add -A && git commit -m "fix(deep_dive): Regression-Fixes nach Signallogik-Überarbeitung D2"`

---

## Abdeckung

| Review-Punkt (Domäne 4 / 6) | Beschreibung | Task(s) |
|---|---|---|
| `fundamentals._score` P/E sektor-relativ | absolute → sektor-relative Schwellen (Perzentil) | Task 1, Task 2 |
| `fundamentals._score` negatives EPS | negatives/None-P/E neutralisieren statt +1 | Task 2 |
| `fundamentals._score` CAPE entfernen | Shiller-CAPE aus Einzelaktien-Score raus | Task 2 |
| `fundamentals._score` PEG | Schwelle ~1.0 + Growth-Basis-Check | Task 2 |
| `fundamentals._score` EV/EBITDA sektor | sektor-relative Multiples | Task 1, Task 2 |
| `fundamentals._score` Asymmetrie/Doppelzählung/ungenutzte Multiples | symmetrische Schwellen, P/FCF + P/B aktiviert | Task 2 |
| `quality._signal` ROIC−WACC | Spread statt fixer 12 % | Task 3 |
| `quality` Piotroski F-Score | 9-Kriterien-Score in scoring.py | Task 1, Task 3 |
| `quality` ungenutzte Felder | interest_coverage / fcf_margin im Signal | Task 3 |
| `quality` Altman-Variante | Z'' für Nicht-Manufacturing, Financials aus | Task 3 |
| `earnings_trend` SUE | SUE statt binärer Beat-Rate | Task 1, Task 4 |
| `earnings_trend` Revisions-Trend / UND-ODER | gewichtet statt ODER-Veto | Task 4 |
| `insider_agent` wertgewichtet (P3.6) | Volumen/Wert, Käufe stärker, 10b5-1 raus | Task 5 |
| `short_interest` days_to_cover / Squeeze | Float + DTC + Trend kombiniert, niedrig=neutral | Task 6 |
| `moat` Maximum- statt Summen-Logik | dominante Quelle begründet „wide" | Task 7 |
| `moat` none→BEARISH entkoppeln | none/narrow → NEUTRAL | Task 7 |
| `equity_chief` gewichtete Gesamtbeurteilung | `weighted_signal` über 7 Sub-Signale | Task 8 |
| `equity_chief` sector weiterreichen | an fundamentals + quality | Task 8 |
| `index_momentum` Wilder-RSI (P4.2) | ewm alpha=1/period | Task 1, Task 9 |
| `index_momentum` MA200 aus ≥2y (P4.2) | Historie „2y" | Task 9 |
| `index_momentum` Signal aus Status | MA50/MA200-Status + RSI-Extreme statt Cross-Event | Task 9 |
| `index_chief` gewichtete Synthese | `weighted_signal` über Sub-Signale | Task 10 |

**Datenannahmen (dokumentiert):**
- Insider: Transaktionen tragen `value` (USD) oder ersatzweise `shares`; `plan == "10b5-1"` bzw. `acquisition_type == "option_exercise"` markieren nicht-informative Transaktionen (werden herausgerechnet). Fehlende Felder → open-market / Einheitsgewicht.
- Short Interest: `get_short_interest` liefert zusätzlich `short_float_trend` (`rising|stable|falling`); fehlt es → `stable`.
- Quality/Piotroski: `get_fundamentals` liefert die Vorperioden-Felder (`*_prev`) sowie `operating_cash_flow`, `asset_turnover`, `long_term_debt`, `shares_outstanding`; fehlen sie → `piotroski_f_score` gibt `None` (kein Beitrag).
- Earnings: `get_earnings_history` liefert je Quartal `actual`, `estimate`, `revision`, `beat`; SUE braucht ≥4 Quartale.
- Fundamentals/Quality sektor-relativ: Sektor-Multiple-Verteilungen sind als repräsentative Stützstellen hinterlegt, bis eine echte Peer-API verfügbar ist.

**Neue Helper-Signaturen (`core/utils/scoring.py`):**
```python
def piotroski_f_score(data: dict) -> int | None
def standardized_unexpected_earnings(quarters: list[dict]) -> float | None
def sector_relative_signal(value: float, sector_history: list[float], lower_is_better: bool) -> Signal
def wilder_rsi(prices, period: int = 14) -> float | None
```
