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


def test_evaluate_market_ueberspringt_fehlenden_forward_kurs():
    # Forward-Kurs fehlt (Fenster-Rand, Zukunft) → Urteil NICHT gezählt (kein -100%-Schein-Miss)
    j = [{"as_of": date(2030, 1, 1), "regime": MarketRegime.EXPANSION}]
    prices = {date(2030, 1, 1): 100.0}  # kein Kurs für 2030-04-01
    report = evaluate_market(j, lambda d: prices.get(d), horizons_months=(3,))
    assert report[3]["n"] == 0
    assert report[3]["hit_rate"] is None
    # Ohne auswertbare Urteile gibt es auch keinen Mittel-Return je Richtung.
    assert report[3]["mean_ret_bullish"] is None
    assert report[3]["mean_ret_bearish"] is None


def test_evaluate_market_mean_return_je_richtung():
    # Plausibilitätscheck (Spec §3.1): mittlerer Forward-Return der bullish- vs. bearish-Calls.
    # Ein bullisch-treffender Motor zeigt mean_ret_bullish > mean_ret_bearish.
    j = [
        {"as_of": date(2000, 1, 1), "regime": MarketRegime.EXPANSION},   # bullish, +10 %
        {"as_of": date(2001, 1, 1), "regime": MarketRegime.BOOM},        # bullish, +20 %
        {"as_of": date(2002, 1, 1), "regime": MarketRegime.RECESSION},   # bearish, -10 %
    ]
    prices = {
        date(2000, 1, 1): 100.0, date(2000, 4, 1): 110.0,   # +0.10
        date(2001, 1, 1): 100.0, date(2001, 4, 1): 120.0,   # +0.20
        date(2002, 1, 1): 100.0, date(2002, 4, 1):  90.0,   # -0.10
    }
    report = evaluate_market(j, lambda d: prices.get(d), horizons_months=(3,))
    h3 = report[3]
    # bullish-Mittel = (0.10 + 0.20) / 2 = 0.15
    assert h3["mean_ret_bullish"] == 0.15
    # bearish-Mittel = -0.10
    assert h3["mean_ret_bearish"] == -0.10
    # Plausibilität: bullische Calls liefen im Mittel besser als die bearischen.
    assert h3["mean_ret_bullish"] > h3["mean_ret_bearish"]


def test_evaluate_market_mean_return_nur_eine_richtung():
    # Nur bullische Urteile vorhanden → bearish-Mittel bleibt None (keine Division durch 0).
    j = [{"as_of": date(2000, 1, 1), "regime": MarketRegime.EXPANSION}]
    prices = {date(2000, 1, 1): 100.0, date(2000, 4, 1): 105.0}  # +0.05
    report = evaluate_market(j, lambda d: prices.get(d), horizons_months=(3,))
    assert report[3]["mean_ret_bullish"] == 0.05
    assert report[3]["mean_ret_bearish"] is None
