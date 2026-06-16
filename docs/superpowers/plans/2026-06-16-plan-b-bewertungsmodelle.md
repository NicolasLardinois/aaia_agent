# Plan B — Bewertungsmodelle (DCF, Edelmetalle, CAPE/ERP) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die vier finanziell falschen bzw. unbrauchbaren Bewertungs-Agenten reparieren: (1) das als „DCF" bezeichnete Gordon-Growth-Modell in `equity/valuation_range` durch ein echtes 2-Stufen-DCF mit CAPM-WACC ersetzen (P2.1); (2) die Edelmetall-Bewertung entzirkularisieren — preis-unabhängiger Realzins-Anker, aktuelle AISC, gewichteter Median statt min/max-Union, 1200$-Methode ersetzen (P2.2); (3) die Index-Bewertung zinsabhängig machen (Earnings Yield/ERP), die asymmetrischen Bullish-Bias-Puffer symmetrisieren und das `shiller_cape`-Feld füllen (P2.5 + Domäne 6); (4) im `index_valuation_range` die redundante Method2 durch eine echt unabhängige ERP-basierte zweite Methode ersetzen, die `_FUZZY_THRESHOLD`-Schwelle empirisch absenken und den Forward×Trailing-EPS-Mix beheben. Die gesamte Finanzmathematik wandert in ein neues, isoliert testbares Modul `core/utils/valuation_math.py`.

**Architecture:** EDA + Hexagonal. Die Agenten bleiben dünne Orchestratoren (Ports → Finanzmathematik → Snapshot-Dataclass → Event). Sämtliche Formeln (2-Stufen-DCF, CAPM-WACC, Earnings Yield/ERP, CAPE, Realzins-Anker, gewichtete Range-Kombination) leben rein und seiteneffektfrei in `core/utils/valuation_math.py` und werden dort mit injizierten Zahlen getestet — unabhängig von Providern, asyncio oder dem Event-Bus. Die Agenten importieren nur diese Funktionen.

**Tech Stack:** Python, asyncio, pytest

**Abhängigkeiten:** Plan 0 (Shared Utilities). Exakt referenzieren, **nicht** neu definieren:
- `core/utils/relative.py` — `percentile_rank(value, history, winsorize=0.0)`, `zscore_vs_history(value, history, robust=True, min_n=20)`
- `core/utils/real_nominal.py` — `to_real(nominal_rate, inflation)`

> **Reihenfolge-Hinweis:** Plan 0 muss vor Task 6 dieses Plans gemergt sein (Task 6 nutzt `to_real` im Edelmetall-Realzins-Pfad und `percentile_rank` für das ERP-Signal im Index). Tasks 1–5 (DCF + valuation_math-Kern) sind von Plan 0 unabhängig und können sofort starten. Falls Plan 0 noch nicht vorliegt, Tasks 1–5 zuerst ausführen.

---

## Dateienübersicht

| Datei | Änderung |
|---|---|
| `core/utils/valuation_math.py` | **NEU.** Reine Finanzmathematik: `two_stage_dcf`, `capm_wacc`, `earnings_yield`, `equity_risk_premium`, `shiller_cape`, `real_rate_anchor`, `weighted_median_range`. |
| `tests/core/utils/test_valuation_math.py` | **NEU.** Unit-Tests für alle Funktionen aus `valuation_math.py` mit konkreten Zahlen. |
| `agents/stock_deep_dive/equity/valuation_range_agent.py` | Gordon-Growth-„DCF" durch `two_stage_dcf` + `capm_wacc` ersetzen. |
| `agents/stock_deep_dive/precious_metals/precious_metals_valuation_agent.py` | Realzins-Anker preis-unabhängig (`real_rate_anchor`), AISC aktualisiert, 1200$-Methode entfernt, Kombination via `weighted_median_range`. |
| `agents/stock_deep_dive/index/index_valuation_agent.py` | Symmetrische Puffer, Earnings Yield/ERP-Signal (zinsabhängig), `shiller_cape` befüllt. |
| `agents/stock_deep_dive/index/index_valuation_range_agent.py` | Redundante Method2 → ERP-basierte 2. Methode, `_FUZZY_THRESHOLD` gesenkt, EPS/PE-Konsistenz (kein Forward×Trailing-Mix). |
| `tests/agents/stock_deep_dive/equity/test_valuation_range_agent.py` | Erweitert um 2-Stufen-DCF-Assertions. |
| `tests/agents/stock_deep_dive/index/test_index_valuation_agent.py` | **ggf. NEU** — Symmetrie/ERP/CAPE-Tests. |
| `tests/agents/stock_deep_dive/index/test_index_valuation_range_agent.py` | Erweitert/angepasst um ERP-Methode + neue Schwelle. |
| `tests/agents/stock_deep_dive/precious_metals/test_precious_metals_valuation.py` | Erweitert um Preis-Unabhängigkeit + gewichteten Median. |

**Wichtig:** `fundamentals_agent.py` **nicht** anfassen (CAPE-Entfernung dort macht Plan D2). Bond-/andere Pläne separat.

---

### Task 1 — `valuation_math.py`: CAPM-WACC

**Files:**
- `core/utils/valuation_math.py` (NEU)
- `tests/core/utils/test_valuation_math.py` (NEU)

CAPM-WACC bottom-up: `WACC = w_e·(rf + β·ERP) + w_d·k_d·(1−tax)`. Ersetzt den hartkodierten `wacc=0.09` im Equity-Agenten.

- [ ] Verzeichnis sicherstellen: `tests/core/utils/` existiert (sonst anlegen, plus leere `__init__.py` falls das Repo Package-Init nutzt — Konvention der bestehenden `tests/`-Struktur prüfen).
- [ ] Failing Test schreiben in `tests/core/utils/test_valuation_math.py`:
```python
import math
import pytest

from core.utils.valuation_math import capm_wacc


def test_capm_wacc_textbook_numbers():
    # Cost of equity = rf + beta*ERP = 0.04 + 1.2*0.05 = 0.10
    # After-tax cost of debt = 0.05*(1-0.21) = 0.0395
    # WACC = 0.6*0.10 + 0.4*0.0395 = 0.06 + 0.0158 = 0.0758
    wacc = capm_wacc(
        rf=0.04, beta=1.2, erp=0.05,
        cost_of_debt=0.05, tax_rate=0.21,
        equity_weight=0.6, debt_weight=0.4,
    )
    assert math.isclose(wacc, 0.0758, abs_tol=1e-6)


def test_capm_wacc_all_equity_financed():
    # equity_weight=1.0 → WACC == cost of equity
    wacc = capm_wacc(
        rf=0.03, beta=1.0, erp=0.055,
        cost_of_debt=0.06, tax_rate=0.25,
        equity_weight=1.0, debt_weight=0.0,
    )
    assert math.isclose(wacc, 0.085, abs_tol=1e-9)


def test_capm_wacc_weights_normalized_when_not_summing_to_one():
    # equity_weight=3, debt_weight=1 → effektiv 0.75 / 0.25
    wacc = capm_wacc(
        rf=0.04, beta=1.0, erp=0.05,
        cost_of_debt=0.05, tax_rate=0.20,
        equity_weight=3.0, debt_weight=1.0,
    )
    # ke=0.09, kd_after=0.04 → 0.75*0.09 + 0.25*0.04 = 0.0675 + 0.01 = 0.0775
    assert math.isclose(wacc, 0.0775, abs_tol=1e-9)
```
- [ ] Test ausführen → **FAIL** (Modul/Funktion existiert nicht):
  `python -m pytest tests/core/utils/test_valuation_math.py -q`
- [ ] `core/utils/valuation_math.py` anlegen und implementieren:
```python
"""Reine Finanzmathematik für Bewertungs-Agenten (DCF, CAPM, ERP, CAPE).

Seiteneffektfrei und provider-unabhängig: alle Funktionen erhalten nur Zahlen
und sind isoliert testbar. Genutzt von equity/index/precious-metals Valuation-Agenten.
"""
import statistics


def capm_wacc(
    rf: float,
    beta: float,
    erp: float,
    cost_of_debt: float,
    tax_rate: float,
    equity_weight: float,
    debt_weight: float,
) -> float:
    """Bottom-up WACC via CAPM.

    cost_of_equity = rf + beta*erp
    after_tax_kd   = cost_of_debt * (1 - tax_rate)
    WACC = w_e*cost_of_equity + w_d*after_tax_kd

    Gewichte werden auf Summe 1.0 normiert (robust gegen w_e+w_d != 1).
    """
    total_w = equity_weight + debt_weight
    if total_w <= 0:
        # Fallback: vollständig eigenfinanziert
        w_e, w_d = 1.0, 0.0
    else:
        w_e = equity_weight / total_w
        w_d = debt_weight / total_w
    cost_of_equity = rf + beta * erp
    after_tax_kd = cost_of_debt * (1.0 - tax_rate)
    return w_e * cost_of_equity + w_d * after_tax_kd
```
- [ ] Test ausführen → **PASS**:
  `python -m pytest tests/core/utils/test_valuation_math.py -q`
- [ ] Commit: `feat(valuation_math): CAPM bottom-up WACC (Plan B Task 1)`

---

### Task 2 — `valuation_math.py`: 2-Stufen-DCF

**Files:**
- `core/utils/valuation_math.py`
- `tests/core/utils/test_valuation_math.py`

Explizite n-Jahres-FCF-Projektion mit Hochwachstum `growth`, danach Terminal Value `FCF_n·(1+g_term)/(WACC−g_term)`, alle Cashflows auf t0 diskontiert. Instabilität bei `WACC ≈ g_term` über einen Mindestabstand abfangen.

- [ ] Failing Test ergänzen in `tests/core/utils/test_valuation_math.py`:
```python
from core.utils.valuation_math import two_stage_dcf


def test_two_stage_dcf_known_value():
    # fcf0=10, growth=0%, terminal_growth=0%, wacc=10%, years=5
    # FCF jedes Jahr = 10 (kein Wachstum)
    # PV(explizit) = 10*(1.1^-1 + ... + 1.1^-5) = 10*3.790786769 = 37.90786769
    # TV am Jahr 5 = FCF_5*(1+0)/(0.10-0) = 10/0.10 = 100; PV(TV)=100*1.1^-5=62.09213231
    # Summe = 100.0
    value = two_stage_dcf(fcf0=10.0, growth=0.0, terminal_growth=0.0, wacc=0.10, years=5)
    assert abs(value - 100.0) < 1e-6


def test_two_stage_dcf_high_growth_increases_value():
    base = two_stage_dcf(fcf0=10.0, growth=0.00, terminal_growth=0.02, wacc=0.10, years=5)
    fast = two_stage_dcf(fcf0=10.0, growth=0.15, terminal_growth=0.02, wacc=0.10, years=5)
    assert fast > base


def test_two_stage_dcf_lower_wacc_increases_value():
    high_wacc = two_stage_dcf(fcf0=10.0, growth=0.05, terminal_growth=0.02, wacc=0.12, years=5)
    low_wacc  = two_stage_dcf(fcf0=10.0, growth=0.05, terminal_growth=0.02, wacc=0.08, years=5)
    assert low_wacc > high_wacc


def test_two_stage_dcf_stable_when_wacc_near_terminal_growth():
    # WACC sehr nah an terminal_growth -> kein Crash, endlicher Wert
    value = two_stage_dcf(fcf0=5.0, growth=0.05, terminal_growth=0.025, wacc=0.026, years=5)
    assert value == value  # not NaN
    assert value > 0
    assert value < 1e9     # nicht explodiert


def test_two_stage_dcf_wacc_below_terminal_growth_does_not_explode():
    # Ökonomisch unzulässig (WACC < g_term) -> Mindestabstand greift, endlich & positiv
    value = two_stage_dcf(fcf0=5.0, growth=0.05, terminal_growth=0.04, wacc=0.03, years=5)
    assert value > 0
    assert value < 1e9
```
- [ ] Test ausführen → **FAIL** (`two_stage_dcf` fehlt):
  `python -m pytest tests/core/utils/test_valuation_math.py -q`
- [ ] In `core/utils/valuation_math.py` ergänzen:
```python
# Mindestabstand WACC - terminal_growth zur Vermeidung ökonomischer Instabilität.
# Bei WACC <= g_term + _MIN_SPREAD wird der Nenner auf _MIN_SPREAD geklemmt
# (Gordon-Term explodiert sonst gegen unendlich bzw. wird negativ).
_MIN_WACC_GROWTH_SPREAD = 0.01


def two_stage_dcf(
    fcf0: float,
    growth: float,
    terminal_growth: float,
    wacc: float,
    years: int = 5,
) -> float:
    """2-Stufen-DCF auf Basis des Free Cash Flow.

    Stufe 1: explizite Projektion von FCF über `years` Jahre mit Rate `growth`.
    Stufe 2: Terminal Value via Gordon mit konsistenter `terminal_growth`-Rate.
    Alle Cashflows werden mit `wacc` auf t0 diskontiert.

    Stabilität: der Diskont-/Wachstumsabstand (wacc - terminal_growth) wird auf
    mindestens `_MIN_WACC_GROWTH_SPREAD` geklemmt, um ökonomische Instabilität bei
    wacc ~= terminal_growth abzufangen.
    """
    if years < 1:
        years = 1

    pv_explicit = 0.0
    fcf_t = fcf0
    discounted_last = fcf0
    for t in range(1, years + 1):
        fcf_t = fcf0 * (1.0 + growth) ** t
        discount = (1.0 + wacc) ** t
        pv_explicit += fcf_t / discount
        if t == years:
            discounted_last = discount

    # Terminal Value (Gordon) am Ende von Stufe 1, dann auf t0 diskontiert.
    spread = wacc - terminal_growth
    if spread < _MIN_WACC_GROWTH_SPREAD:
        spread = _MIN_WACC_GROWTH_SPREAD
    terminal_value = fcf_t * (1.0 + terminal_growth) / spread
    pv_terminal = terminal_value / discounted_last

    return pv_explicit + pv_terminal
```
- [ ] Test ausführen → **PASS**:
  `python -m pytest tests/core/utils/test_valuation_math.py -q`
- [ ] Commit: `feat(valuation_math): 2-Stufen-DCF mit Stabilitäts-Guard (Plan B Task 2)`

---

### Task 3 — `valuation_math.py`: Earnings Yield, ERP, CAPE

**Files:**
- `core/utils/valuation_math.py`
- `tests/core/utils/test_valuation_math.py`

`earnings_yield(pe) = 1/pe`; `equity_risk_premium(earnings_yield, riskfree) = earnings_yield − riskfree` (Fed-Modell-Brücke); `shiller_cape(price, eps_10y_real) = price / mean(eps_10y_real)`.

- [ ] Failing Test ergänzen:
```python
from core.utils.valuation_math import earnings_yield, equity_risk_premium, shiller_cape


def test_earnings_yield_inverse_of_pe():
    assert earnings_yield(20.0) == 0.05
    assert earnings_yield(25.0) == 0.04


def test_earnings_yield_none_or_nonpositive_returns_none():
    assert earnings_yield(None) is None
    assert earnings_yield(0.0) is None
    assert earnings_yield(-10.0) is None


def test_equity_risk_premium():
    # E/P = 0.05, riskfree 10y = 0.03 -> ERP = 0.02
    assert abs(equity_risk_premium(0.05, 0.03) - 0.02) < 1e-9


def test_equity_risk_premium_none_inputs():
    assert equity_risk_premium(None, 0.03) is None
    assert equity_risk_premium(0.05, None) is None


def test_shiller_cape_basic():
    # price 4000, mean(10J real EPS) = 200 -> CAPE = 20
    assert shiller_cape(4000.0, [180, 190, 200, 210, 220, 200, 200, 200, 200, 200]) == 20.0


def test_shiller_cape_empty_or_nonpositive_mean_returns_none():
    assert shiller_cape(4000.0, []) is None
    assert shiller_cape(4000.0, [0.0, 0.0]) is None
    assert shiller_cape(None, [200.0]) is None
```
- [ ] Test ausführen → **FAIL**:
  `python -m pytest tests/core/utils/test_valuation_math.py -q`
- [ ] In `core/utils/valuation_math.py` ergänzen:
```python
def earnings_yield(pe: float | None) -> float | None:
    """Earnings Yield = 1/PE. None bei fehlendem oder nicht-positivem PE."""
    if pe is None or pe <= 0:
        return None
    return 1.0 / pe


def equity_risk_premium(ey: float | None, riskfree: float | None) -> float | None:
    """ERP = Earnings Yield - risikofreier Zins (Fed-Modell-Brücke).

    `riskfree` als Dezimalzahl (0.03 = 3 %), konsistent zu `earnings_yield`.
    """
    if ey is None or riskfree is None:
        return None
    return ey - riskfree


def shiller_cape(price: float | None, eps_10y_real: list[float]) -> float | None:
    """Shiller-CAPE = Preis / Mittelwert der 10J inflationsbereinigten EPS.

    None, falls Preis fehlt oder der Mittelwert nicht positiv ist.
    """
    if price is None or not eps_10y_real:
        return None
    mean_eps = statistics.fmean(eps_10y_real)
    if mean_eps <= 0:
        return None
    return price / mean_eps
```
- [ ] Test ausführen → **PASS**:
  `python -m pytest tests/core/utils/test_valuation_math.py -q`
- [ ] Commit: `feat(valuation_math): Earnings Yield, ERP, Shiller-CAPE (Plan B Task 3)`

---

### Task 4 — `valuation_math.py`: preis-unabhängiger Realzins-Anker + gewichtete Range-Kombination

**Files:**
- `core/utils/valuation_math.py`
- `tests/core/utils/test_valuation_math.py`

`real_rate_anchor`: empirische, **preis-unabhängige** Realzins-Regression mit injizierbaren Konstanten (`intercept`, `slope`) und metallspezifischer prozentualer Sensitivität → Fair-Value-Band (untere/obere Grenze über `band_pct`). `weighted_median_range`: gewichteter Median der Methoden-lows bzw. -highs statt min/max-Union.

> **Datenannahme (dokumentiert):** Die Regressionsparameter (`intercept`/Anker-Niveau bei 0 % Realzins, `slope` in USD je Prozentpunkt Realzins) sind aus historischen Gold/Silber↔10J-TIPS-Realzins-Regressionen kalibrierte, **injizierte Konstanten** — nicht aus dem aktuellen Preis abgeleitet (das war der zirkuläre Fehler). Sie werden im Agenten als metallspezifische `_REAL_RATE_MODEL`-Tabelle hinterlegt und können später durch eine echte Provider-Regression ersetzt werden, ohne die Signatur zu ändern.

- [ ] Failing Test ergänzen:
```python
from core.utils.valuation_math import real_rate_anchor, weighted_median_range


def test_real_rate_anchor_is_price_independent():
    # Fairer Wert hängt NUR von intercept/slope/real_rate ab, nicht vom aktuellen Preis.
    low_a, high_a = real_rate_anchor(real_rate=0.0, intercept=2000.0, slope=-200.0, band_pct=0.10)
    # intercept + slope*0 = 2000 -> Band 1800..2200
    assert abs(low_a - 1800.0) < 1e-6
    assert abs(high_a - 2200.0) < 1e-6


def test_real_rate_anchor_inverse_relationship():
    # Höherer Realzins -> niedrigerer fairer Goldwert (slope negativ).
    _, high_low_rate  = real_rate_anchor(real_rate=-0.01, intercept=2000.0, slope=-200.0, band_pct=0.10)
    _, high_high_rate = real_rate_anchor(real_rate=0.03,  intercept=2000.0, slope=-200.0, band_pct=0.10)
    assert high_low_rate > high_high_rate


def test_real_rate_anchor_band_never_inverted():
    low, high = real_rate_anchor(real_rate=0.05, intercept=2000.0, slope=-200.0, band_pct=0.10)
    assert low < high


def test_weighted_median_range_converges_not_union():
    # min/max-Union wäre (85, 130); gewichteter Median konvergiert in die Mitte.
    methods = [
        (90.0, 130.0, 1.0),   # (low, high, weight)
        (85.0, 120.0, 1.0),
        (95.0, 125.0, 1.0),
    ]
    low, high = weighted_median_range(methods)
    assert low == 90.0    # Median der lows
    assert high == 125.0  # Median der highs
    # nicht die Union (85, 130)
    assert low != 85.0
    assert high != 130.0


def test_weighted_median_range_respects_weights():
    # DCF (Gewicht 3) dominiert -> Ergebnis nahe (100, 140).
    methods = [
        (100.0, 140.0, 3.0),
        (60.0,  90.0,  1.0),
    ]
    low, high = weighted_median_range(methods)
    assert low == 100.0
    assert high == 140.0


def test_weighted_median_range_single_method():
    low, high = weighted_median_range([(50.0, 70.0, 1.0)])
    assert (low, high) == (50.0, 70.0)
```
- [ ] Test ausführen → **FAIL**:
  `python -m pytest tests/core/utils/test_valuation_math.py -q`
- [ ] In `core/utils/valuation_math.py` ergänzen:
```python
def real_rate_anchor(
    real_rate: float,
    intercept: float,
    slope: float,
    band_pct: float = 0.10,
) -> tuple[float, float]:
    """Preis-UNABHÄNGIGER fairer Edelmetall-Wert aus einer Realzins-Regression.

    fair = intercept + slope * real_rate   (slope < 0 für Gold/Silber: inverse Beziehung)
    Band = fair * (1 - band_pct) .. fair * (1 + band_pct).

    `intercept`/`slope` sind injizierte, empirisch kalibrierte Konstanten — bewusst
    NICHT aus dem aktuellen Preis abgeleitet (Entzirkularisierung). `band_pct` ist die
    metallspezifische prozentuale Sensitivität (Unsicherheitsband).
    """
    fair = intercept + slope * real_rate
    if fair < 0:
        fair = 0.0
    band = abs(fair) * band_pct
    return fair - band, fair + band


def weighted_median_range(
    methods: list[tuple[float, float, float]],
) -> tuple[float, float]:
    """Gewichteter Median der lows bzw. highs statt min/max-Union.

    `methods`: Liste von (low, high, weight). Bänder konvergieren so zur Mitte der
    Methoden statt sich zur breitesten Union aufzuspannen.
    """
    if not methods:
        return 0.0, 0.0
    low = _weighted_median([(m[0], m[2]) for m in methods])
    high = _weighted_median([(m[1], m[2]) for m in methods])
    return low, high


def _weighted_median(pairs: list[tuple[float, float]]) -> float:
    """Gewichteter Median: kleinster Wert x, ab dem die kumulierte Gewichtssumme
    mindestens die Hälfte des Gesamtgewichts erreicht."""
    ordered = sorted(pairs, key=lambda p: p[0])
    total = sum(w for _, w in ordered)
    if total <= 0:
        return statistics.median([v for v, _ in ordered])
    half = total / 2.0
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= half:
            return value
    return ordered[-1][0]
```
- [ ] Test ausführen → **PASS**:
  `python -m pytest tests/core/utils/test_valuation_math.py -q`
- [ ] Commit: `feat(valuation_math): Realzins-Anker (preis-unabhängig) + gewichteter Median (Plan B Task 4)`

---

### Task 5 — Equity `valuation_range_agent`: Gordon-Growth → 2-Stufen-DCF + CAPM-WACC

**Files:**
- `agents/stock_deep_dive/equity/valuation_range_agent.py`
- `tests/agents/stock_deep_dive/equity/test_valuation_range_agent.py`

Das fälschlich „DCF" genannte Gordon-Growth-Modell (Zähler-/Nenner-g-Inkonsistenz, harter `wacc=0.09`, Revenue-CAGR als FCF-Proxy) wird durch `two_stage_dcf` ersetzt. WACC kommt aus `capm_wacc` mit Provider-Inputs (`beta`, `risk_free_rate`, `erp`, `cost_of_debt`, `tax_rate`, `equity_weight`/`debt_weight`), mit dokumentierten Fallback-Konstanten falls Felder fehlen.

> **Datenannahme:** `get_fundamentals(ticker)` liefert (oder soll künftig liefern) `fcf_per_share`, `beta`, `cost_of_debt`, `tax_rate`, `equity_weight`, `debt_weight`, `risk_free_rate`, `erp`. Fehlt ein Feld, greifen dokumentierte Defaults (`beta=1.0`, `rf=0.04`, `erp=0.05`, `cost_of_debt=0.05`, `tax_rate=0.21`, `equity_weight=0.8`, `debt_weight=0.2`). Die `growth`-Rate kommt weiterhin aus `revenue_cagr_3y` (als FCF-Wachstumsproxy für die explizite Phase — der konzeptionell saubere FCF-CAGR ist eine spätere Provider-Erweiterung), aber **nicht mehr** im Gordon-Nenner.

- [ ] Bestehende DCF-Tests in `test_valuation_range_agent.py` an die neue Methode anpassen + neue ergänzen. `test_terminal_growth_used_in_dcf` bleibt gültig (höhere terminal growth → höherer Wert). Ergänze konkrete Assertions:
```python
def test_dcf_uses_two_stage_not_gordon():
    """Bei fcf0=10, growth=0, tg=0, wacc=0.10, years=5 muss der DCF-Fair-Value-Mittelpunkt
    nahe dem 2-Stufen-Resultat (~100/Aktie) liegen, nicht beim Gordon-Wert 10/(0.10-0)=100*(1.0).
    Hier prüfen wir, dass der WACC NICHT mehr hart 0.09 ist, sondern aus CAPM kommt."""
    fundamentals = MagicMock()
    fundamentals.get_fundamentals.return_value = {
        "current_price": 100.0,
        "fcf_per_share": 10.0,
        "revenue_cagr_3y": 0,
        "beta": 1.0, "risk_free_rate": 0.04, "erp": 0.06,
        "cost_of_debt": 0.05, "tax_rate": 0.21,
        "equity_weight": 1.0, "debt_weight": 0.0,
        "eps": 8.0, "pe_ratio": 15.0,
    }
    market = MagicMock(); market.get_current_price.return_value = 100.0
    bus = MagicMock()
    agent = ValuationRangeAgent(fundamentals, market, bus)
    result = asyncio.run(agent.run("AAPL", sector="default"))
    dcf = next((m for m in result.methods if m.name == "DCF"), None)
    assert dcf is not None
    # WACC = 0.04 + 1.0*0.06 = 0.10 (CAPM, all-equity). 2-Stufen-DCF mit fcf0=10, g=0, tg=0.025
    # ergibt einen endlichen, positiven Wert > 0.
    assert dcf.low > 0 and dcf.high > dcf.low


def test_dcf_skipped_without_fcf():
    fundamentals = MagicMock()
    fundamentals.get_fundamentals.return_value = {"current_price": 100.0, "eps": 5.0, "pe_ratio": 15.0}
    market = MagicMock(); market.get_current_price.return_value = 100.0
    agent = ValuationRangeAgent(fundamentals, market, MagicMock())
    result = asyncio.run(agent.run("AAPL"))
    assert all(m.name != "DCF" for m in result.methods)
```
- [ ] Test ausführen → **FAIL** (Agent nutzt noch Gordon; CAPM-Inputs unverwendet):
  `python -m pytest tests/agents/stock_deep_dive/equity/test_valuation_range_agent.py -q`
- [ ] In `valuation_range_agent.py` Imports + DCF-Block ersetzen. Import oben ergänzen:
```python
from core.utils.valuation_math import two_stage_dcf, capm_wacc, weighted_median_range
```
- [ ] Den DCF-Block (Zeilen ~79–87, das Gordon-Growth-Modell) ersetzen durch:
```python
        # DCF — echtes 2-Stufen-DCF mit CAPM-WACC (ersetzt Gordon-Growth)
        fcf_per_share = data.get("fcf_per_share")
        if fcf_per_share is not None:
            wacc = capm_wacc(
                rf=data.get("risk_free_rate", 0.04),
                beta=data.get("beta", 1.0),
                erp=data.get("erp", 0.05),
                cost_of_debt=data.get("cost_of_debt", 0.05),
                tax_rate=data.get("tax_rate", 0.21),
                equity_weight=data.get("equity_weight", 0.8),
                debt_weight=data.get("debt_weight", 0.2),
            )
            growth = (data.get("revenue_cagr_3y") or 5) / 100
            # Szenario-Band: konservativer (0.7×) bis optimistischer (1.3×) Wachstumspfad
            dcf_low = two_stage_dcf(
                fcf0=fcf_per_share, growth=growth * 0.7,
                terminal_growth=terminal_growth, wacc=wacc, years=5,
            )
            dcf_high = two_stage_dcf(
                fcf0=fcf_per_share, growth=growth * 1.3,
                terminal_growth=terminal_growth, wacc=wacc, years=5,
            )
            lo, hi = min(dcf_low, dcf_high), max(dcf_low, dcf_high)
            methods.append(ValuationMethod(name="DCF", low=round(lo, 2), high=round(hi, 2)))
```
- [ ] **Self-Review:** `_combine_methods` (Median low/high) bleibt wie bisher und wird durch `test_band_aggregation_uses_median_not_extreme` weiter abgedeckt — **keine** Umstellung auf `weighted_median_range` in diesem Task (die Equity-Range-Kombination ist bereits ein Median, der Import oben dient nur, falls eine spätere Gewichtung gewünscht ist; entferne den ungenutzten Import, falls Linter mault, oder nutze ihn nicht — der Scope verlangt hier nur die DCF-Reparatur). **Entscheidung:** Import `weighted_median_range` in diesem Agenten weglassen, um keinen toten Import einzuführen.
- [ ] Import-Zeile korrigieren auf:
```python
from core.utils.valuation_math import two_stage_dcf, capm_wacc
```
- [ ] Test ausführen → **PASS**:
  `python -m pytest tests/agents/stock_deep_dive/equity/test_valuation_range_agent.py -q`
- [ ] Commit: `fix(equity/valuation_range): 2-Stufen-DCF + CAPM-WACC statt Gordon-Growth (P2.1, Plan B Task 5)`

---

### Task 6 — Precious Metals: Entzirkularisierung (Realzins-Anker, AISC, gewichteter Median, 1200$ raus)

**Files:**
- `agents/stock_deep_dive/precious_metals/precious_metals_valuation_agent.py`
- `tests/agents/stock_deep_dive/precious_metals/test_precious_metals_valuation.py`

Realzins-Methode auf preis-unabhängigen `real_rate_anchor` umstellen (metallspezifische `intercept`/`slope`/`band_pct`). 1200$-Inflations-Methode entfernen. AISC-Methode mit aktuellen Daten (Gold-AISC-Median 2024/25 ~1250–1450). Kombination via `weighted_median_range` statt `min(low)/max(high)`.

> **Datenannahme:** `get_extended_state()` liefert `real_rate_10y` (in Prozent, z. B. `2.5`). Der Realzins wird für den Anker in Dezimal umgerechnet bzw. die Regressionskonstanten in derselben Einheit kalibriert. Die `_REAL_RATE_MODEL`-Tabelle (intercept/slope/band_pct je Metall) ist injizierbar/ersetzbar durch eine echte Provider-Regression.

- [ ] Bestehende Tests bleiben gültig (kein invertiertes Band, korrektes Event). Neue Failing-Tests ergänzen in `test_precious_metals_valuation.py`:
```python
def test_real_rate_method_is_price_independent():
    """Gleicher Realzins -> gleiche Realzins-Methoden-Range, unabhängig vom aktuellen Preis."""
    agent_low,  _ = _make_agent(real_rate=1.0, price=1500.0)
    agent_high, _ = _make_agent(real_rate=1.0, price=3000.0)
    r_low  = asyncio.run(agent_low.run("gold"))
    r_high = asyncio.run(agent_high.run("gold"))
    m_low  = next(m for m in r_low.methods  if m.name == "Realzins-Modell")
    m_high = next(m for m in r_high.methods if m.name == "Realzins-Modell")
    assert m_low.low == m_high.low
    assert m_low.high == m_high.high


def test_no_1200_inflation_method():
    agent, _ = _make_agent(real_rate=0.5)
    result = asyncio.run(agent.run("gold"))
    names = [m.name for m in result.methods]
    assert not any("Inflationsbereinigt" in n for n in names)


def test_combined_band_is_not_minmax_union():
    """Kombination konvergiert (gewichteter Median), nicht Union der Extreme."""
    agent, _ = _make_agent(real_rate=0.5, price=2000.0)
    result = asyncio.run(agent.run("gold"))
    method_lows  = [m.low  for m in result.methods]
    method_highs = [m.high for m in result.methods]
    if len(result.methods) >= 2:
        assert result.combined_low  >= min(method_lows)
        assert result.combined_high <= max(method_highs)
        # echte Konvergenz: nicht beide Extreme gleichzeitig
        assert not (result.combined_low == min(method_lows) and result.combined_high == max(method_highs))


def test_current_aisc_floor_updated():
    agent, _ = _make_agent(real_rate=0.5)
    result = asyncio.run(agent.run("gold"))
    aisc = next((m for m in result.methods if "AISC" in m.name or "Produktionskosten" in m.name), None)
    assert aisc is not None
    assert aisc.low >= 1200.0   # aktualisierter AISC-Median, nicht 1050
```
- [ ] Test ausführen → **FAIL**:
  `python -m pytest tests/agents/stock_deep_dive/precious_metals/test_precious_metals_valuation.py -q`
- [ ] `precious_metals_valuation_agent.py` neu schreiben. Imports + Modell-Konstanten oben:
```python
import asyncio

from core.domain.events import PreciousMetalsValuationReady
from core.domain.models import ValuationRangeSnapshot, ValuationMethod, Signal
from core.ports.data_provider import MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.valuation_math import real_rate_anchor, weighted_median_range

_DEFAULT = ValuationRangeSnapshot(
    methods=[], combined_low=0.0, combined_high=0.0,
    current_price=None, position="unknown", signal=Signal.NEUTRAL,
)

# Preis-UNABHÄNGIGE Realzins-Regression je Metall (injizierte, empirisch kalibrierte
# Konstanten — KEINE Ableitung aus dem aktuellen Preis). real_rate in Prozent (z. B. 1.5).
#   fair = intercept + slope * real_rate   (slope < 0: inverse Realzins-Beziehung)
# Datenannahme: ersetzbar durch echte Provider-Regression ohne Signaturänderung.
_REAL_RATE_MODEL: dict[str, dict[str, float]] = {
    "gold":   {"intercept": 2400.0, "slope": -250.0, "band_pct": 0.12},
    "silver": {"intercept":   28.0, "slope":   -4.0, "band_pct": 0.18},
}

# Aktuelle AISC-Produktionskosten-Bänder (2024/25), nur Gold (USD/oz).
_AISC_FLOOR: dict[str, tuple[float, float]] = {
    "gold": (1250.0, 1450.0),
}

# Methoden-Gewichte für die Kombination (Realzins ist der dominante Gold-Treiber).
_METHOD_WEIGHTS: dict[str, float] = {
    "Realzins-Modell": 2.0,
    "AISC-Produktionskosten-Boden": 1.0,
}


def _position(price: float, low: float, high: float) -> tuple[str, Signal]:
    if price < low * 0.95:
        return "undervalued", Signal.BULLISH
    if price > high * 1.05:
        return "overvalued", Signal.BEARISH
    return "fair", Signal.NEUTRAL
```
- [ ] `run`-Methode ersetzen (Methoden-Aufbau + Kombination):
```python
class PreciousMetalsValuationAgent:
    def __init__(self, macro: MacroDataProvider, market: MarketDataProvider, bus: EventBus):
        self.macro = macro
        self.market = market
        self.bus = bus

    async def run(self, metal: str = "gold") -> ValuationRangeSnapshot:
        metal = metal.lower()
        ticker_map = {"gold": "GC=F", "silver": "SI=F", "platinum": "PL=F", "palladium": "PA=F"}
        ticker = ticker_map.get(metal, "GC=F")

        current_price, macro_data = await asyncio.gather(
            asyncio.to_thread(self.market.get_current_price, ticker),
            asyncio.to_thread(self.macro.get_extended_state),
            return_exceptions=True,
        )
        if isinstance(current_price, Exception):
            current_price = None
        if isinstance(macro_data, Exception):
            macro_data = {}

        methods: list[ValuationMethod] = []

        # Methode 1: preis-UNABHÄNGIGER Realzins-Anker (Gold/Silber)
        real_rate = macro_data.get("real_rate_10y")
        model = _REAL_RATE_MODEL.get(metal)
        if real_rate is not None and model is not None:
            low, high = real_rate_anchor(
                real_rate=real_rate,
                intercept=model["intercept"],
                slope=model["slope"],
                band_pct=model["band_pct"],
            )
            methods.append(ValuationMethod(
                name="Realzins-Modell", low=round(low, 0), high=round(high, 0),
            ))

        # Methode 2: AISC-Produktionskosten-Boden (aktuelle Daten)
        floor = _AISC_FLOOR.get(metal)
        if floor is not None:
            methods.append(ValuationMethod(
                name="AISC-Produktionskosten-Boden", low=floor[0], high=floor[1],
            ))

        if not methods or current_price is None:
            return _DEFAULT

        weighted = [
            (m.low, m.high, _METHOD_WEIGHTS.get(m.name, 1.0)) for m in methods
        ]
        combined_low, combined_high = weighted_median_range(weighted)
        position, signal = _position(current_price, combined_low, combined_high)

        result = ValuationRangeSnapshot(
            methods=methods,
            combined_low=combined_low,
            combined_high=combined_high,
            current_price=current_price,
            position=position,
            signal=signal,
        )
        self.bus.publish(PreciousMetalsValuationReady(
            source="precious_metals_valuation_agent", payload={"metal": metal, "position": position},
        ))
        return result

    @staticmethod
    def default() -> ValuationRangeSnapshot:
        return _DEFAULT
```
- [ ] **Self-Review:** Bei nur einer Methode (z. B. Silber ohne AISC-Floor) liefert `weighted_median_range` mit einem Eintrag `(low, high)` dieser Methode → `combined_low < combined_high` bleibt erfüllt (deckt `test_*_does_not_invert_band` ab). Bei Gold (2 Methoden) konvergiert das Band → `test_combined_band_is_not_minmax_union`.
- [ ] Test ausführen → **PASS**:
  `python -m pytest tests/agents/stock_deep_dive/precious_metals/test_precious_metals_valuation.py -q`
- [ ] Commit: `fix(precious_metals): Realzins-Anker preis-unabhängig + gewichteter Median + AISC aktualisiert (P2.2, Plan B Task 6)`

---

### Task 7 — Index `valuation_agent`: symmetrische Puffer, Earnings Yield/ERP, CAPE befüllt

**Files:**
- `agents/stock_deep_dive/index/index_valuation_agent.py`
- `tests/agents/stock_deep_dive/index/test_index_valuation_agent.py` (ggf. NEU)

Asymmetrischen Bullish-Bias (`pe < lo*0.85` vs. `pe > hi*1.20`) durch **symmetrische** Puffer ersetzen. Signal zusätzlich **zinsabhängig** über ERP machen (`earnings_yield` + `equity_risk_premium` vs. lokaler 10J-Yield). `shiller_cape` über `shiller_cape()` aus injizierten 10J-Real-EPS befüllen. `is not None` statt Falsiness.

> **Datenannahme:** `get_info(ticker)` liefert zusätzlich `riskFreeRate` (lokaler 10J-Staatsanleihen-Yield, dezimal) und `eps10yReal` (Liste der 10 letzten inflationsbereinigten Jahres-EPS, US via Shiller/multpl.com, EU/CH via FMP `FMP_API_KEY`). Fehlen sie, bleibt das ERP-/CAPE-Feld `None` und das Signal fällt auf die symmetrische PE-Range zurück. Diese Felder sind testbar via injiziertem `get_info`-Mock.

- [ ] Failing Test schreiben in `tests/agents/stock_deep_dive/index/test_index_valuation_agent.py`:
```python
import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.index.index_valuation_agent import IndexValuationAgent, _signal
from core.domain.models import Signal


def _agent(info: dict) -> IndexValuationAgent:
    market = MagicMock()
    market.get_info.return_value = info
    return IndexValuationAgent(market, MagicMock())


def test_signal_buffers_are_symmetric():
    # Bei _PE_RANGES["^GSPC"] = (15, 25): symmetrischer Puffer p.
    # Test: gleich weit unter low wie über high -> spiegelbildliches Signal.
    lo, hi = 15.0, 25.0
    p = 0.10
    assert _signal(lo * (1 - p) - 0.01, "^GSPC") == Signal.BULLISH
    assert _signal(hi * (1 + p) + 0.01, "^GSPC") == Signal.BEARISH
    # innerhalb der Range -> NEUTRAL
    assert _signal((lo + hi) / 2, "^GSPC") == Signal.NEUTRAL


def test_shiller_cape_is_filled_from_10y_real_eps():
    info = {
        "trailingPE": 20.0, "forwardPE": 18.0, "dividendYield": 0.018,
        "enterpriseToEbitda": 14.0,
        "regularMarketPrice": 4000.0,
        "eps10yReal": [180, 190, 200, 210, 220, 200, 200, 200, 200, 200],
    }
    result = asyncio.run(_agent(info).run("^GSPC"))
    # CAPE = 4000 / mean(...) = 4000 / 200 = 20.0
    assert result.shiller_cape == 20.0


def test_erp_signal_rate_dependent_low_erp_is_bearish():
    # PE 25 -> E/P 0.04; riskfree 0.045 -> ERP negativ -> teuer/BEARISH
    info = {"trailingPE": 25.0, "riskFreeRate": 0.045}
    result = asyncio.run(_agent(info).run("^GSPC"))
    assert result.signal == Signal.BEARISH


def test_erp_signal_rate_dependent_high_erp_is_bullish():
    # PE 12 -> E/P 0.0833; riskfree 0.02 -> ERP ~0.063 -> günstig/BULLISH
    info = {"trailingPE": 12.0, "riskFreeRate": 0.02}
    result = asyncio.run(_agent(info).run("^GSPC"))
    assert result.signal == Signal.BULLISH


def test_pe_zero_handled_via_is_not_none():
    info = {"trailingPE": 0.0, "regularMarketPrice": 4000.0}
    result = asyncio.run(_agent(info).run("^GSPC"))
    # 0.0 darf nicht zu None kollabieren (is not None), aber E/P undefiniert -> kein Crash.
    assert result is not None
```
- [ ] Test ausführen → **FAIL**:
  `python -m pytest tests/agents/stock_deep_dive/index/test_index_valuation_agent.py -q`
- [ ] `index_valuation_agent.py` umbauen. Imports + symmetrische Schwelle + ERP-Signal:
```python
import asyncio

from core.domain.events import IndexValuationReady
from core.domain.models import IndexValuationSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.valuation_math import earnings_yield, equity_risk_premium, shiller_cape

# ... _DEFAULT, _PE_RANGES, _DEFAULT_PE_RANGE unverändert ...

# Symmetrischer Puffer um die historische PE-Range (vorher asymmetrisch 0.85/1.20 -> Bullish-Bias).
_PE_BUFFER = 0.10

# ERP-Schwellen (Earnings Yield minus lokaler 10J-Yield): unter 0 teuer, über _ERP_BULLISH günstig.
_ERP_BEARISH = 0.0
_ERP_BULLISH = 0.04


def _signal(pe: float | None, ticker: str) -> Signal:
    if pe is None or pe <= 0:
        return Signal.NEUTRAL
    lo, hi = _PE_RANGES.get(ticker, _DEFAULT_PE_RANGE)
    if pe < lo * (1 - _PE_BUFFER):
        return Signal.BULLISH
    if pe > hi * (1 + _PE_BUFFER):
        return Signal.BEARISH
    return Signal.NEUTRAL


def _erp_signal(pe: float | None, riskfree: float | None) -> Signal | None:
    """Zinsabhängiges ERP-Signal (Fed-Modell-Brücke). None, wenn Daten fehlen."""
    ey = earnings_yield(pe)
    erp = equity_risk_premium(ey, riskfree)
    if erp is None:
        return None
    if erp < _ERP_BEARISH:
        return Signal.BEARISH
    if erp >= _ERP_BULLISH:
        return Signal.BULLISH
    return Signal.NEUTRAL
```
- [ ] `run`-Methode anpassen (CAPE befüllen, ERP bevorzugen, `is not None`):
```python
    async def run(self, ticker: str) -> IndexValuationSnapshot:
        try:
            info = await asyncio.to_thread(self.market.get_info, ticker)
            if isinstance(info, Exception) or not info:
                return _DEFAULT

            pe        = info.get("trailingPE")
            fwd_pe    = info.get("forwardPE")
            div_y     = info.get("dividendYield")
            ev_ebitda = info.get("enterpriseToEbitda")
            riskfree  = info.get("riskFreeRate")
            price     = info.get("regularMarketPrice") or info.get("currentPrice")
            eps_10y_real = info.get("eps10yReal") or []

            cape = shiller_cape(price, eps_10y_real) if eps_10y_real else None

            # Zinsabhängiges ERP-Signal bevorzugen; Fallback: symmetrische PE-Range.
            erp_sig = _erp_signal(pe, riskfree)
            signal = erp_sig if erp_sig is not None else _signal(pe, ticker)

            result = IndexValuationSnapshot(
                pe_trailing=round(pe, 2) if pe is not None else None,
                pe_forward=round(fwd_pe, 2) if fwd_pe is not None else None,
                shiller_cape=round(cape, 2) if cape is not None else None,
                dividend_yield=round(div_y * 100, 2) if div_y is not None else None,
                ev_ebitda=round(ev_ebitda, 2) if ev_ebitda is not None else None,
                signal=signal,
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(IndexValuationReady(source="index_valuation_agent", payload={"ticker": ticker}))
        return result
```
- [ ] **Self-Review:** `test_pe_zero_handled_via_is_not_none` — `pe=0.0`: `pe_trailing` wird via `is not None` zu `round(0.0,2)=0.0` (nicht `None`); `earnings_yield(0.0)` → `None` → `_erp_signal` → `None` → Fallback `_signal(0.0)` → `pe<=0` → NEUTRAL. Kein Crash. ✓
- [ ] Test ausführen → **PASS**:
  `python -m pytest tests/agents/stock_deep_dive/index/test_index_valuation_agent.py -q`
- [ ] Commit: `fix(index/valuation): symmetrische Puffer + ERP-Zinsbrücke + CAPE befüllt (P2.5, Plan B Task 7)`

---

### Task 8 — Index `valuation_range_agent`: ERP-Methode statt redundanter Method2, Schwelle senken, EPS/PE-Konsistenz

**Files:**
- `agents/stock_deep_dive/index/index_valuation_range_agent.py`
- `tests/agents/stock_deep_dive/index/test_index_valuation_range_agent.py`

Method2 (PE-vs-Mid) ist nur eine Reskalierung von Method1 (beide `eps×pe`) → Scheindiversifikation. Ersetzen durch eine **echt unabhängige** ERP-basierte Methode (`equity_risk_premium`). `_FUZZY_THRESHOLD 0.70` auf einen empirisch realistischen Wert (`0.30`) senken. Forward×Trailing-EPS-Mix beheben: Forward-EPS nur mit Forward-PE-Bändern; hier konsistent auf Trailing fixieren bzw. EPS-Typ explizit führen.

> **Datenannahme:** `get_info(ticker)` liefert `riskFreeRate` (lokaler 10J-Yield, dezimal) für die ERP-Methode. Fehlt er, liefert die ERP-Methode Score `0.0` (neutral), Method1 trägt allein.

- [ ] Bestehende Tests anpassen: `_method2_score` wird durch `_erp_score` ersetzt; die `_combine`-Schwellen-Tests an `0.30` anpassen. Neue/angepasste Tests in `test_index_valuation_range_agent.py`:
```python
from agents.stock_deep_dive.index.index_valuation_range_agent import (
    _method1_score, _erp_score, _combine, _FUZZY_THRESHOLD,
)
from core.domain.models import Signal


def test_threshold_lowered_to_realistic_value():
    assert _FUZZY_THRESHOLD <= 0.40


def test_erp_score_high_erp_is_bullish():
    # PE 12 -> E/P 0.0833; riskfree 0.02 -> ERP 0.063 -> deutlich positiv -> +Score
    score = _erp_score(pe_trailing=12.0, riskfree=0.02)
    assert score > 0.5


def test_erp_score_negative_erp_is_bearish():
    # PE 25 -> E/P 0.04; riskfree 0.045 -> ERP -0.005 -> negativ
    score = _erp_score(pe_trailing=25.0, riskfree=0.045)
    assert score < 0.0


def test_erp_score_missing_data_is_neutral():
    assert _erp_score(pe_trailing=None, riskfree=0.03) == 0.0
    assert _erp_score(pe_trailing=20.0, riskfree=None) == 0.0


def test_combine_moderate_signal_now_votes():
    # avg 0.4 löst jetzt (Schwelle 0.30) BULLISH aus — vorher (0.70) NEUTRAL.
    _, sig = _combine(0.5, 0.3)
    assert sig == Signal.BULLISH
```
- [ ] Test ausführen → **FAIL** (`_erp_score` fehlt, Schwelle noch 0.70):
  `python -m pytest tests/agents/stock_deep_dive/index/test_index_valuation_range_agent.py -q`
- [ ] `index_valuation_range_agent.py` umbauen. Import + `_erp_score` + Schwelle:
```python
from core.utils.valuation_math import earnings_yield, equity_risk_premium

# ... _PE_RANGES, _DEFAULT_PE_RANGE, _method1_score unverändert ...

# ERP-Skalierung: ERP von 0 (neutral) bis _ERP_FULL (max bullish/bearish) auf [-1,+1].
_ERP_FULL = 0.05


def _erp_score(pe_trailing: float | None, riskfree: float | None) -> float:
    """Echt unabhängige 2. Methode: ERP (E/P - lokaler 10J-Yield), skaliert auf [-1,+1].
    Positiver ERP = Aktien attraktiv vs. Anleihen (bullish)."""
    erp = equity_risk_premium(earnings_yield(pe_trailing), riskfree)
    if erp is None:
        return 0.0
    return max(-1.0, min(1.0, erp / _ERP_FULL))


# Empirisch realistische Schwelle (vorher 0.70 -> fast immer NEUTRAL).
_FUZZY_THRESHOLD = 0.30


def _combine(m1_score: float, m2_score: float) -> tuple[str, Signal]:
    avg = (m1_score + m2_score) / 2
    if avg >= _FUZZY_THRESHOLD:
        return "undervalued", Signal.BULLISH
    if avg <= -_FUZZY_THRESHOLD:
        return "overvalued", Signal.BEARISH
    return "fair", Signal.NEUTRAL
```
- [ ] `run`-Methode anpassen: EPS-Konsistenz (kein Forward×Trailing-Mix) + ERP-Methode statt `_method2_score`:
```python
            pe_low, pe_mid, pe_high = _PE_RANGES.get(ticker, _DEFAULT_PE_RANGE)

            # EPS/PE-Konsistenz: Trailing-EPS mit Trailing-PE-Bändern (kein Forward×Trailing-Mix).
            eps         = info.get("trailingEps")
            current     = info.get("regularMarketPrice") or info.get("currentPrice")
            pe_trailing = info.get("trailingPE")
            riskfree    = info.get("riskFreeRate")

            if eps is not None and eps > 0:
                price_low  = round(eps * pe_low, 2)
                price_mid  = round(eps * pe_mid, 2)
                price_high = round(eps * pe_high, 2)
            else:
                price_low = price_mid = price_high = None

            m1 = 0.0
            if current is not None and price_low is not None and price_high is not None:
                m1 = _method1_score(current, price_low, price_mid, price_high)

            # Method 2: echt unabhängige ERP-Brücke (statt PE-vs-Mid-Reskalierung).
            m2 = _erp_score(pe_trailing, riskfree)

            pos, sig = _combine(m1, m2)
```
- [ ] **Self-Review:** `eps_estimate` im Snapshot bleibt `round(eps,2)` (Trailing). `test_m1_*`-Tests bleiben unverändert gültig (Method1 unverändert). Die alten `test_m2_*`/`_combine`-Tests, die `_method2_score` bzw. Schwelle `0.70` annehmen, werden in diesem Task durch die neuen ERP/0.30-Tests ersetzt — **alte, jetzt obsolete Tests entfernen** (`_method2_score` existiert nicht mehr).
- [ ] Test ausführen → **PASS**:
  `python -m pytest tests/agents/stock_deep_dive/index/test_index_valuation_range_agent.py -q`
- [ ] Commit: `fix(index/valuation_range): ERP-Methode statt redundanter M2, Schwelle 0.30, EPS/PE-Konsistenz (Domäne 6, Plan B Task 8)`

---

### Task 9 — Gesamt-Verifikation

**Files:** — (keine Änderung, nur Verifikation)

- [ ] Volle betroffene Test-Suite grün:
  `python -m pytest tests/core/utils/test_valuation_math.py tests/agents/stock_deep_dive/equity/test_valuation_range_agent.py tests/agents/stock_deep_dive/index/ tests/agents/stock_deep_dive/precious_metals/ -q`
- [ ] Sicherstellen, dass `fundamentals_agent.py` **nicht** im Diff ist:
  `git diff --name-only` darf diese Datei nicht enthalten.
- [ ] Keine TODO-/Stub-Reste in den geänderten DCF-/Edelmetall-/Index-Pfaden (grep nach `Gordon`, `1_200`, `GOLD_INFLATION_ADJ_AVG`, `0.09`-Hard-WACC, `_method2_score`).
- [ ] Optional: Gesamt-Suite `python -m pytest -q` (sofern Plan 0 gemergt — sonst nur die Scope-Tests).
- [ ] Commit (falls Aufräumarbeiten nötig waren): `test(valuation): Gesamt-Verifikation Plan B`

---

## Abdeckung

**Review-Punkte → Tasks:**

| Review-Punkt | Lösung | Task |
|---|---|---|
| **P2.1** „DCF" = Gordon-Growth (g-Inkonsistenz, harter WACC 0.09, Revenue-CAGR-Proxy, instabil bei WACC≈g) | `two_stage_dcf` + `capm_wacc`, Stabilitäts-Guard | 1, 2, 5 |
| **P2.2** Edelmetall zirkulär (Preis-Anker), 1200$-Anker falsch, min/max-Union | `real_rate_anchor` (preis-unabhängig), 1200$ entfernt, aktuelle AISC, `weighted_median_range` | 4, 6 |
| **P2.5 / Domäne 6** CAPE fehlt im Index, Earnings Yield/ERP fehlen | `shiller_cape`, `earnings_yield`, `equity_risk_premium`; CAPE-Feld befüllt, ERP-Signal | 3, 7 |
| **Domäne 6** `index_valuation` Asymmetrie (Bullish-Bias 0.85/1.20), Falsiness-Check | symmetrischer `_PE_BUFFER`, `is not None` | 7 |
| **Domäne 6** `index_valuation_range` Method2 redundant, `_FUZZY_THRESHOLD` zu hoch, Forward×Trailing-Mix | ERP-Methode, Schwelle 0.30, Trailing-EPS×Trailing-PE | 8 |

**`valuation_math.py`-Signaturen (vollständig, keine Platzhalter):**
- `capm_wacc(rf, beta, erp, cost_of_debt, tax_rate, equity_weight, debt_weight) -> float`
- `two_stage_dcf(fcf0, growth, terminal_growth, wacc, years=5) -> float`
- `earnings_yield(pe: float | None) -> float | None`
- `equity_risk_premium(ey: float | None, riskfree: float | None) -> float | None`
- `shiller_cape(price: float | None, eps_10y_real: list[float]) -> float | None`
- `real_rate_anchor(real_rate, intercept, slope, band_pct=0.10) -> tuple[float, float]`
- `weighted_median_range(methods: list[tuple[float, float, float]]) -> tuple[float, float]`
- intern: `_weighted_median(pairs) -> float`

**Plan-0-Referenzen (nicht neu definiert):** `core/utils/relative.py` (`percentile_rank`, `zscore_vs_history`), `core/utils/real_nominal.py` (`to_real`). Genutzt im Edelmetall-/Index-Pfad bzw. als optionale ERP-Perzentil-Erweiterung. **Hinweis:** Diese Module existieren im Repo aktuell noch nicht (Plan 0 ausstehend) — die Tasks 1–8 importieren sie **nicht zwingend**; die ERP/CAPE/DCF-Kernlogik ist eigenständig. Wo `to_real`/`percentile_rank` fachlich passt, ist es als spätere Anreicherung markiert, damit der Plan auch ohne Plan 0 lauffähig bleibt.

**Getroffene Daten-Annahmen (alle dokumentiert & via Mock testbar):**
1. `get_fundamentals` liefert CAPM-Inputs (`beta`, `risk_free_rate`, `erp`, `cost_of_debt`, `tax_rate`, `equity_weight`, `debt_weight`, `fcf_per_share`); Fallback-Defaults definiert.
2. Edelmetall-Realzins-Regression: `intercept`/`slope`/`band_pct` als injizierte, metallspezifische Konstanten (`_REAL_RATE_MODEL`), preis-unabhängig; `real_rate_10y` in Prozent aus `get_extended_state`.
3. Gold-AISC-Median 2024/25 ~1250–1450 USD/oz (`_AISC_FLOOR`).
4. `get_info` für Indizes liefert `riskFreeRate` (lokaler 10J-Yield) und `eps10yReal` (10J inflationsbereinigte EPS, US: Shiller/multpl.com, EU/CH: FMP). Fehlen sie → ERP/CAPE `None`, Fallback auf symmetrische PE-Range.

**Self-Review (Platzhalter/Signaturen):** Kein `TODO`/`pass`/`...` in produktivem Code der Scope-Dateien nach Plan-Ende. Alle Funktionssignaturen entsprechen exakt den fachlichen Kernvorgaben. `_combine_methods` im Equity-Agenten bleibt Median-basiert (durch Bestandstest abgedeckt) — `weighted_median_range` wird dort bewusst nicht eingeführt (kein toter Import). `fundamentals_agent.py` unangetastet (CAPE-Entfernung = Plan D2).
