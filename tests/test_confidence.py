from core.domain.models import AnomalyReport, Signal
from core.domain.recommendation import compute_confidence, derive_recommendation, Recommendation


def _empty_anomaly():
    return AnomalyReport(False, [], [], "none", "")


def _anomaly(severity: str):
    return AnomalyReport(True, ["x"], [], severity, "")


def test_confidence_baseline_aligned_bullish():
    conf = compute_confidence(
        alignment="aligned_bullish",
        regime_confidence=0.75,
        td_anomaly=_empty_anomaly(),
        bu_anomaly=_empty_anomaly(),
    )
    assert conf == round(0.70 + 0.10, 2)


def test_confidence_deduction_contradicting():
    conf = compute_confidence(
        alignment="contradicting",
        regime_confidence=0.75,
        td_anomaly=_empty_anomaly(),
        bu_anomaly=_empty_anomaly(),
    )
    assert conf == round(0.70 - 0.15, 2)


def test_confidence_high_anomaly_deduction():
    conf = compute_confidence(
        alignment="mixed",
        regime_confidence=0.75,
        td_anomaly=_anomaly("high"),
        bu_anomaly=_anomaly("high"),
    )
    assert conf <= 0.20


def test_confidence_floor():
    conf = compute_confidence(
        alignment="contradicting",
        regime_confidence=0.20,
        td_anomaly=_anomaly("high"),
        bu_anomaly=_anomaly("high"),
    )
    assert conf == 0.10


def test_cash_bias_below_0_50():
    rec = derive_recommendation(
        alignment="mixed",
        signal=Signal.BULLISH,
        asset_class="equity",
        in_portfolio=False,
        market="USA",
        cockpit=None,
        top_down_available=False,
        confidence=0.45,
    )
    assert rec.action == Recommendation.HOLD
    assert "widersprüchlich" in rec.reasoning


def test_cash_bias_below_0_35():
    rec = derive_recommendation(
        alignment="mixed",
        signal=Signal.BULLISH,
        asset_class="equity",
        in_portfolio=False,
        market="USA",
        cockpit=None,
        top_down_available=False,
        confidence=0.30,
    )
    assert rec.action == Recommendation.HOLD
    assert "Cash" in rec.reasoning


def test_normal_buy_high_confidence():
    rec = derive_recommendation(
        alignment="aligned_bullish",
        signal=Signal.BULLISH,
        asset_class="equity",
        in_portfolio=False,
        market="USA",
        cockpit=None,
        top_down_available=False,
        confidence=0.80,
    )
    assert rec.action == Recommendation.BUY
