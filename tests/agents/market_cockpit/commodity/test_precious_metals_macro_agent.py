from agents.market_cockpit.commodity.precious_metals_macro_agent import _signal
from core.domain.models import Signal


def test_none_inputs_is_neutral():
    assert _signal(gs_pct=None, gold_z=None) == Signal.NEUTRAL


def test_high_gs_percentile_is_bearish():
    # GS-Ratio im oberen Extrem (>0.85 Perzentil) → Risikoaversion → BEARISH für Risiko
    assert _signal(gs_pct=0.92, gold_z=0.3) == Signal.BEARISH


def test_low_gs_percentile_is_bullish():
    # GS-Ratio im unteren Extrem (<0.15) → Risk-on → BULLISH
    assert _signal(gs_pct=0.08, gold_z=0.0) == Signal.BULLISH


def test_gold_momentum_spike_is_bearish():
    # Gold-z > +1.5 (Safe-Haven-Flucht) überschreibt neutrales GS → BEARISH
    assert _signal(gs_pct=0.50, gold_z=1.8) == Signal.BEARISH


def test_mid_percentile_no_momentum_is_neutral():
    assert _signal(gs_pct=0.50, gold_z=0.2) == Signal.NEUTRAL
