from core.domain.models import (
    BondResult, BondMetricsSnapshot, BondDurationSnapshot, BondCreditSnapshot,
    BondSpreadSnapshot, Signal, RiskAffinity, CreditBand,
)
from adapters.cache.result_cache import _bond_result_out, _load_bond_result


def _bond(**over):
    m = BondMetricsSnapshot(bond_type="corporate", current_price=None, coupon=None,
        maturity_years=None, ytm=None, ytc=None, current_yield=None, real_yield=None,
        country=None, breakeven_inflation=None, issuer=None, sector=None, signal=Signal.BULLISH)
    d = BondDurationSnapshot(macaulay_duration=None, modified_duration=None, convexity=None, dv01=None, signal=Signal.NEUTRAL)
    c = BondCreditSnapshot(moodys=None, sp="BB", fitch=None, category="high_yield", trend="stable", default_probability=None, signal=Signal.NEUTRAL)
    s = BondSpreadSnapshot(spread_bps=None, oas=None, z_spread=None, spread_trend="stable", signal=Signal.NEUTRAL)
    base = dict(ticker="X", bond_type="corporate", metrics=m, duration=d, credit=c, spread=s,
                overall_signal=Signal.BULLISH, confidence=0.25,
                risk_affinity=RiskAffinity.RISIKOFREUDIG, credit_band=CreditBand.MITTEL)
    base.update(over)
    return BondResult(**base)


def test_roundtrip_preserves_overall_and_affinity():
    """Cache-Round-Trip (out → load) darf die neuen Bond-Felder nicht verlieren."""
    br = _load_bond_result(_bond_result_out(_bond()))
    assert br.overall_signal == Signal.BULLISH
    assert br.confidence == 0.25
    assert br.risk_affinity == RiskAffinity.RISIKOFREUDIG
    assert br.credit_band == CreditBand.MITTEL


def test_roundtrip_handles_none_affinity_and_band():
    """Unverfügbares Rating / keine Affinität bleibt None (kein Crash, kein Default-Enum)."""
    br = _load_bond_result(_bond_result_out(_bond(risk_affinity=None, credit_band=None)))
    assert br.risk_affinity is None
    assert br.credit_band is None
