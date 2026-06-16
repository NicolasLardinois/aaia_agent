from core.domain.regime import _score_indicator, INDICATOR_WEIGHTS


def test_yield_key_renamed():
    # alter irreführender Key weg, neuer da
    assert "yield_curve_3m_usa" not in INDICATOR_WEIGHTS
    assert "yield_curve_10y3m_usa" in INDICATOR_WEIGHTS
