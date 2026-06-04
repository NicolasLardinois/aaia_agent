from core.utils.statistics import z_score, compute_severity


def test_z_score_normal_value():
    history = [10.0, 11.0, 10.5, 10.8, 9.9, 11.2, 10.3]
    assert abs(z_score(10.5, history)) < 1.0


def test_z_score_outlier():
    history = [10.0, 11.0, 10.5, 10.8, 9.9, 11.2, 10.3]
    assert z_score(25.0, history) > 2.5


def test_z_score_too_short_history():
    assert z_score(100.0, [10.0, 11.0]) == 0.0


def test_z_score_zero_std():
    assert z_score(5.0, [5.0, 5.0, 5.0, 5.0, 5.0]) == 0.0


def test_severity_none():
    assert compute_severity([], []) == "none"


def test_severity_low_one_statistical():
    assert compute_severity(["VIX anomal"], []) == "low"


def test_severity_low_one_contradiction():
    assert compute_severity([], ["Macro vs Sentiment"]) == "low"


def test_severity_medium_two_statistical():
    assert compute_severity(["A", "B"], []) == "medium"


def test_severity_high_both():
    assert compute_severity(["A"], ["B"]) == "high"
