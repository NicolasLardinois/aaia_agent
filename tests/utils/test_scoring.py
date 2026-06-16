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
    """Nach einem starken Schock weicht Wilder vom SMA-RSI ab.
    Wilder 'erinnert' sich via EWM an den Einbruch (tieferer RSI),
    SMA-RSI sieht nur die letzten 14 Bars (alle positiv → NaN oder ~100).
    """
    import math
    vals = [100.0] * 20 + [80.0] + [101.0 + i for i in range(20)]
    prices = pd.Series(vals)
    delta = prices.diff().dropna()
    gain_sma = delta.clip(lower=0).rolling(14).mean()
    loss_sma = (-delta.clip(upper=0)).rolling(14).mean()
    rs_sma = gain_sma / loss_sma.replace(0, float("nan"))
    sma_rsi_val = float((100 - 100 / (1 + rs_sma)).iloc[-1])
    wilder = wilder_rsi(prices, period=14)
    assert wilder is not None
    # Wenn SMA-RSI NaN ist (letzten 14 Bars keine Verluste), ist Wilder per Definition anders
    if math.isnan(sma_rsi_val):
        assert wilder < 100.0   # Wilder erinnert sich an den Einbruch → kein reiner Aufwärtstrend
    else:
        assert abs(wilder - round(sma_rsi_val, 2)) > 0.01


def test_wilder_rsi_zu_kurze_serie_ist_none():
    assert wilder_rsi(pd.Series([1.0, 2.0, 3.0]), period=14) is None
