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
