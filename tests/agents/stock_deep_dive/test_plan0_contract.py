from core.domain.models import SignalStatus
from core.utils.relative import percentile_rank
from core.utils.statistics import robust_z_score
from core.utils.real_nominal import to_real


def test_signal_status_enum_exists():
    assert SignalStatus.AVAILABLE.value == "available"
    assert SignalStatus.UNAVAILABLE.value == "unavailable"


def test_percentile_rank_basic():
    # 60 ist größer als 5 von 10 Werten → 50. Perzentil
    hist = [10, 20, 30, 40, 50, 70, 80, 90, 100, 110]
    assert percentile_rank(60, hist) == 50.0


def test_robust_z_score_uses_median():
    # Ausreißer 1000 darf den Z-Score des Werts 5 nicht aufblähen (MAD-basiert)
    hist = [1, 2, 3, 4, 5, 6, 7, 1000]
    assert abs(robust_z_score(5, hist)) < 1.0
