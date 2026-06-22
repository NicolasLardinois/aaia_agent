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
