from core.domain.models import RiskAffinity, CreditBand


def test_risk_affinity_values():
    assert RiskAffinity.KONSERVATIV.value == "konservativ"
    assert RiskAffinity.NEUTRAL.value == "neutral"
    assert RiskAffinity.RISIKOFREUDIG.value == "risikofreudig"
    assert RiskAffinity("neutral") == RiskAffinity.NEUTRAL


def test_credit_band_values():
    assert CreditBand.SICHER.value == "sicher"
    assert CreditBand.MITTEL.value == "mittel"
    assert CreditBand.RISKANT.value == "riskant"
