from core.domain.models import Signal, RiskAffinity
from core.utils.bond_recompute import recompute_bond_signal


def _blocks():
    return {"bond_credit_band": "mittel", "bond_metrics_signal": "bullish",
            "bond_duration_signal": "neutral", "bond_spread_signal": "neutral"}


def test_recompute_aendert_signal_mit_affinitaet():
    assert recompute_bond_signal(_blocks(), RiskAffinity.RISIKOFREUDIG)[0] == Signal.BULLISH
    assert recompute_bond_signal(_blocks(), RiskAffinity.KONSERVATIV)[0] == Signal.NEUTRAL


def test_recompute_ohne_band_renormalisiert():
    blocks = {"bond_metrics_signal": "bullish", "bond_duration_signal": "bullish",
              "bond_spread_signal": "neutral"}
    assert recompute_bond_signal(blocks, RiskAffinity.NEUTRAL)[0] == Signal.BULLISH
