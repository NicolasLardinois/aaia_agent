from core.domain.models import AnomalyReport, DeepDiveResult, Signal
from core.domain.recommendation import InvestmentRecommendation, Recommendation


def test_anomaly_report_no_anomalies():
    report = AnomalyReport(
        has_anomalies=False,
        statistical=[],
        contradictions=[],
        severity="none",
        summary="Keine Anomalien erkannt.",
    )
    assert report.has_anomalies is False
    assert report.severity == "none"


def test_anomaly_report_high_severity():
    report = AnomalyReport(
        has_anomalies=True,
        statistical=["VIX=45 ist ungewöhnlich hoch (Z=3.2)"],
        contradictions=["Macro=BULLISH widerspricht Sentiment=BEARISH"],
        severity="high",
        summary="Kritische Anomalien erkannt.",
    )
    assert report.severity == "high"
    assert len(report.statistical) == 1
    assert len(report.contradictions) == 1


def test_deep_dive_result_has_new_fields():
    rec = InvestmentRecommendation(
        action=Recommendation.BUY,
        short_type=None,
        short_warning=None,
        confidence=0.75,
        reasoning="Test",
    )
    result = DeepDiveResult(
        ticker="AAPL",
        asset_class="equity",
        market="USA",
        top_down_context="Test context",
        top_down_available=True,
        bottom_up=None,
        judgment="Test judgment",
        alignment="aligned_bullish",
        recommendation=rec,
        dominant_signal="bullish",
        confidence=0.75,
        xai_explanation="Ausführliche Erklärung...",
    )
    assert result.confidence == 0.75
    assert result.xai_explanation == "Ausführliche Erklärung..."
    assert result.market == "USA"
    assert result.dominant_signal == "bullish"


def test_anomaly_report_empty_factory():
    report = AnomalyReport.empty()
    assert report.has_anomalies is False
    assert report.severity == "none"
    assert report.statistical == []
    assert report.contradictions == []
