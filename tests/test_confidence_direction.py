from core.domain.models import AnomalyReport
from core.domain.recommendation import compute_confidence


def _rep(direction, severity="high"):
    return AnomalyReport(has_anomalies=True, statistical=["x"], contradictions=[],
                         severity=severity, summary="s", direction=direction)


def test_confirming_anomaly_no_penalty():
    conf_confirm = compute_confidence("aligned_bearish", 0.6, AnomalyReport.empty(), _rep("bearish"))
    conf_neutral = compute_confidence("aligned_bearish", 0.6, AnomalyReport.empty(), _rep("neutral"))
    assert conf_confirm > conf_neutral


def test_contradicting_anomaly_keeps_penalty():
    conf_contra  = compute_confidence("aligned_bullish", 0.6, AnomalyReport.empty(), _rep("bearish"))
    conf_neutral = compute_confidence("aligned_bullish", 0.6, AnomalyReport.empty(), _rep("neutral"))
    assert conf_contra == conf_neutral


def test_neutral_direction_keeps_penalty():
    conf_with = compute_confidence("aligned_bearish", 0.6, AnomalyReport.empty(), _rep("neutral"))
    conf_none = compute_confidence("aligned_bearish", 0.6, AnomalyReport.empty(), AnomalyReport.empty())
    assert conf_with < conf_none
