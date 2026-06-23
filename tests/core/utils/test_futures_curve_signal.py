import pytest

from core.domain.models import Signal
from core.utils.futures_curve import curve_signal, roll_warning


@pytest.mark.parametrize("slope,expected", [
    (-0.06, Signal.BULLISH),   # klare Backwardation
    (-0.05, Signal.BULLISH),   # genau auf der Schwelle
    (-0.04, Signal.NEUTRAL),   # knapp darüber
    (0.0,   Signal.NEUTRAL),
    (0.04,  Signal.NEUTRAL),
    (0.05,  Signal.BEARISH),   # genau auf der Schwelle
    (0.06,  Signal.BEARISH),   # klares Contango
])
def test_curve_signal_bands(slope, expected):
    assert curve_signal(slope) == expected


def test_curve_signal_none_is_neutral():
    assert curve_signal(None) == Signal.NEUTRAL


def test_roll_warning_threshold():
    assert roll_warning(4) is True
    assert roll_warning(5) is False     # 5 Tage = Fenstergrenze, keine Warnung mehr
    assert roll_warning(10) is False
    assert roll_warning(None) is False
