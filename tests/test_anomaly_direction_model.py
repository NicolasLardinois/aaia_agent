from core.domain.models import AnomalyReport


def test_direction_defaults_neutral():
    r = AnomalyReport(has_anomalies=False, statistical=[], contradictions=[],
                      severity="none", summary="")
    assert r.direction == "neutral"


def test_empty_is_neutral():
    assert AnomalyReport.empty().direction == "neutral"


def test_direction_can_be_set():
    r = AnomalyReport(has_anomalies=True, statistical=["x"], contradictions=[],
                      severity="high", summary="s", direction="bearish")
    assert r.direction == "bearish"
