from core.domain.models import (
    BondResult, BondMetricsSnapshot, BondDurationSnapshot, BondCreditSnapshot,
    BondSpreadSnapshot, Signal, RiskAffinity, CreditBand,
)


def _snap():
    m = BondMetricsSnapshot(bond_type="corporate", current_price=None, coupon=None,
        maturity_years=None, ytm=None, ytc=None, current_yield=None, real_yield=None,
        country=None, breakeven_inflation=None, issuer=None, sector=None, signal=Signal.BULLISH)
    d = BondDurationSnapshot(macaulay_duration=None, modified_duration=None, convexity=None, dv01=None, signal=Signal.NEUTRAL)
    c = BondCreditSnapshot(moodys=None, sp="BB", fitch=None, category="high_yield", trend="stable", default_probability=None, signal=Signal.NEUTRAL)
    s = BondSpreadSnapshot(spread_bps=None, oas=None, z_spread=None, spread_trend="stable", signal=Signal.NEUTRAL)
    return m, d, c, s


def test_bond_result_has_overall_and_affinity_defaults():
    m, d, c, s = _snap()
    r = BondResult(ticker="X", bond_type="corporate", metrics=m, duration=d, credit=c, spread=s)
    assert r.overall_signal == Signal.NEUTRAL
    assert r.confidence == 0.0
    assert r.risk_affinity is None
    assert r.credit_band is None


def test_bond_result_accepts_overall_and_affinity():
    m, d, c, s = _snap()
    r = BondResult(ticker="X", bond_type="corporate", metrics=m, duration=d, credit=c, spread=s,
                   overall_signal=Signal.BULLISH, confidence=0.25,
                   risk_affinity=RiskAffinity.RISIKOFREUDIG, credit_band=CreditBand.MITTEL)
    assert r.overall_signal == Signal.BULLISH
    assert r.risk_affinity == RiskAffinity.RISIKOFREUDIG
    assert r.credit_band == CreditBand.MITTEL
