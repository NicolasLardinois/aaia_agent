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
