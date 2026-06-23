import math

import pytest

from core.utils.fund_info import tracking_error_ann


def test_perfect_tracking_is_zero():
    etf = [0.01, -0.02, 0.015, 0.0]
    assert tracking_error_ann(etf, etf) == 0.0


def test_tracking_error_annualises_diff_stdev():
    etf = [0.012, -0.018, 0.016, -0.009]
    bench = [0.010, -0.020, 0.015, -0.010]
    diffs = [e - b for e, b in zip(etf, bench)]
    mean = sum(diffs) / len(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / (len(diffs) - 1)
    expected = (var ** 0.5) * math.sqrt(252)
    assert tracking_error_ann(etf, bench) == pytest.approx(expected)


def test_guards_unequal_or_too_short():
    assert tracking_error_ann([0.01], [0.01]) is None          # < 2 Punkte
    assert tracking_error_ann([0.01, 0.02], [0.01]) is None     # ungleiche Länge
    assert tracking_error_ann([], []) is None
