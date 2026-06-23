from core.domain.models import AnomalyReport, DeepDiveResult, Signal
from core.domain.recommendation import InvestmentRecommendation, Recommendation
from core.domain.taxonomy import Underlying, Wrapper


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
        underlying=Underlying.EQUITY,
        wrapper=Wrapper.SINGLE,
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
    # Task 8: Übergangs-Property entfernt — direkt underlying/wrapper prüfen.
    assert result.underlying == Underlying.EQUITY
    assert result.wrapper == Wrapper.SINGLE


def test_anomaly_report_empty_factory():
    report = AnomalyReport.empty()
    assert report.has_anomalies is False
    assert report.severity == "none"
    assert report.statistical == []
    assert report.contradictions == []


def test_signal_status_werte():
    from core.domain.models import SignalStatus
    assert SignalStatus.AVAILABLE.value == "available"
    assert SignalStatus.UNAVAILABLE.value == "unavailable"


def test_signal_status_ist_str_enum():
    # Stil wie vorhandene Enums (Signal, MarketRegime): str-basiert
    from core.domain.models import SignalStatus
    assert isinstance(SignalStatus.AVAILABLE, str)
    assert SignalStatus.AVAILABLE == "available"


def test_buffett_relevant_nur_fuer_aktienartige_underlyings():
    """Buffett-Indikator (Marktkap./BIP) ist nur für aktienartige Basiswerte sinnvoll."""
    from core.domain.top_down_context import _is_buffett_relevant
    assert _is_buffett_relevant(Underlying.EQUITY) is True
    assert _is_buffett_relevant(Underlying.EQUITY_INDEX) is True
    assert _is_buffett_relevant(Underlying.BOND) is False
    assert _is_buffett_relevant(Underlying.COMMODITY) is False
    assert _is_buffett_relevant(Underlying.PRECIOUS_METAL) is False


def test_deepdive_has_short_thesis_fields():
    """DeepDiveResult hat short_thesis und short_xai als trailing-Default-Felder."""
    from core.domain.events import ShortThesisReady
    rec = InvestmentRecommendation(
        action=Recommendation.BUY,
        short_type=None,
        short_warning=None,
        confidence=0.75,
        reasoning="Test",
    )
    # Pflichtfelder wie in Nachbartests; short_thesis/short_xai greifen als Default
    r = DeepDiveResult(
        ticker="AAPL",
        underlying=Underlying.EQUITY,
        wrapper=Wrapper.SINGLE,
        market="USA",
        top_down_context="Test context",
        top_down_available=True,
        judgment="Test judgment",
        alignment="aligned_bullish",
        recommendation=rec,
    )
    assert r.short_thesis == ""
    assert r.short_xai == ""
    # ShortThesisReady-Event analog ConflictResolutionReady
    ev = ShortThesisReady(source="short_thesis_agent", payload={"ticker": "X"})
    assert ev.payload["ticker"] == "X"
