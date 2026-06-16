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


def test_confidence_uses_calibration_bucket():
    # Bucket (aligned_bullish, none) hat historische Trefferrate 0.62 → ersetzt 0.70-Basis
    calib = {("aligned_bullish", "none"): {"hit_rate": 0.62, "n": 40}}
    conf = compute_confidence(
        alignment="aligned_bullish",
        regime_confidence=0.75,
        td_anomaly=_empty_anomaly(),
        bu_anomaly=_empty_anomaly(),
        calibration=calib,
    )
    # Basis 0.62 (kalibriert) statt 0.70; aligned_bullish-Bonus +0.10
    assert conf == round(0.62 + 0.10, 2)


def test_confidence_ignores_thin_bucket():
    # n unter Mindestgröße → Fallback auf 0.70-Heuristik
    calib = {("aligned_bullish", "none"): {"hit_rate": 0.62, "n": 3}}
    conf = compute_confidence(
        alignment="aligned_bullish",
        regime_confidence=0.75,
        td_anomaly=_empty_anomaly(),
        bu_anomaly=_empty_anomaly(),
        calibration=calib,
    )
    assert conf == round(0.70 + 0.10, 2)


def test_confidence_backward_compatible_without_calibration():
    conf = compute_confidence(
        alignment="aligned_bullish",
        regime_confidence=0.75,
        td_anomaly=_empty_anomaly(),
        bu_anomaly=_empty_anomaly(),
    )
    assert conf == round(0.70 + 0.10, 2)


def test_position_size_scales_with_confidence():
    rec_hi = derive_recommendation(
        alignment="aligned_bullish", signal=Signal.BULLISH, asset_class="equity",
        in_portfolio=False, market="USA", cockpit=None,
        top_down_available=False, confidence=0.90,
    )
    rec_lo = derive_recommendation(
        alignment="aligned_bullish", signal=Signal.BULLISH, asset_class="equity",
        in_portfolio=False, market="USA", cockpit=None,
        top_down_available=False, confidence=0.55,
    )
    assert rec_hi.action == Recommendation.BUY
    assert "Positionsgröße" in rec_hi.reasoning
    # höhere Konfidenz → größere empfohlene Positionsgröße (als Prozent im Text)
    import re
    hi = float(re.search(r"Positionsgröße[^0-9]*([0-9.]+)%", rec_hi.reasoning).group(1))
    lo = float(re.search(r"Positionsgröße[^0-9]*([0-9.]+)%", rec_lo.reasoning).group(1))
    assert hi > lo


def test_short_includes_borrow_warning_on_high_dtc():
    rec = derive_recommendation(
        alignment="aligned_bearish", signal=Signal.BEARISH, asset_class="equity",
        in_portfolio=False, market="USA", cockpit=None,
        top_down_available=True, confidence=0.80,
        days_to_cover=9.0, short_float_pct=22.0,
    )
    assert rec.action == Recommendation.SHORT
    assert "Squeeze" in rec.reasoning or "Borrow" in rec.reasoning
