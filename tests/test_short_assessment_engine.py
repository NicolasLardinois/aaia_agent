from types import SimpleNamespace as NS
from core.domain.models import (
    ShortAction, PositionState, MarketRegime, AnomalyReport,
)
from core.domain.short_assessment import derive_short_assessment
from core.domain.recommendation import _position_size_pct


def _bu(**kw):
    base = dict(asset_class="equity", quality=None, earnings_trend=None, fundamentals=None,
                valuation_range=None, moat=None, insider=None, short_interest=None)
    base.update(kw)
    return NS(**base)


def _cockpit(regime):
    return NS(macro=NS(regime=regime))


_NA = AnomalyReport.empty()


def _run(bu, pos=PositionState.NONE, cockpit=None, td=True, bua=_NA, tda=_NA, pnl=None):
    return derive_short_assessment(bu, cockpit, pos, td, bua, tda, position_pnl_pct=pnl)


def test_distress_only_is_moderate_short():
    bu = _bu(quality=NS(altman_z=1.4, interest_coverage=2.0, fcf_margin=5.0,
                        debt_to_equity=0.5, current_ratio=2.0))
    a = _run(bu)
    assert a.short_action == ShortAction.SHORT
    assert 0.50 <= a.confidence <= 0.70
    assert "distress" in a.archetypes


def test_no_kern_only_verstaerker_is_none():
    bu = _bu(valuation_range=NS(position="overvalued"), fundamentals=NS(peg_ratio=3.0),
             moat=NS(total_score=2))
    a = _run(bu)
    assert a.short_action == ShortAction.NONE
    assert a.archetypes == []


def test_no_top_down_is_none():
    bu = _bu(quality=NS(altman_z=1.0, interest_coverage=0.5, fcf_margin=-5.0,
                        debt_to_equity=2.0, current_ratio=0.8))
    assert _run(bu, td=False).short_action == ShortAction.NONE


def test_catalyst_enables_high_confidence():
    bu = _bu(quality=NS(altman_z=1.4, interest_coverage=2.0, fcf_margin=5.0,
                        debt_to_equity=0.5, current_ratio=2.0),
             earnings_trend=NS(estimate_revision="down", beat_rate=0.3),
             valuation_range=NS(position="overvalued"), fundamentals=NS(peg_ratio=3.0),
             insider=NS(net_direction="selling"))
    a = _run(bu, cockpit=_cockpit(MarketRegime.RECESSION))
    assert a.short_action == ShortAction.SHORT
    assert a.confidence > 0.70
    assert "broken_growth" in a.archetypes


def test_risk_on_regime_dampens():
    bu = _bu(quality=NS(altman_z=1.6, interest_coverage=2.0, fcf_margin=5.0,
                        debt_to_equity=0.5, current_ratio=2.0))
    on  = _run(bu, cockpit=_cockpit(MarketRegime.BOOM))
    off = _run(bu, cockpit=_cockpit(MarketRegime.RECESSION))
    assert off.confidence > on.confidence
    assert on.regime_effect == "headwind"


def test_short_held_strong_holds_weak_covers():
    strong = _bu(quality=NS(altman_z=1.0, interest_coverage=0.5, fcf_margin=-5.0,
                            debt_to_equity=2.0, current_ratio=0.8),
                 earnings_trend=NS(estimate_revision="down", beat_rate=0.3))
    weak = _bu()
    assert _run(strong, pos=PositionState.SHORT).short_action == ShortAction.HOLD
    assert _run(weak, pos=PositionState.SHORT).short_action == ShortAction.COVER


def test_long_held_defers_but_keeps_confidence():
    bu = _bu(quality=NS(altman_z=1.0, interest_coverage=0.5, fcf_margin=-5.0,
                        debt_to_equity=2.0, current_ratio=0.8),
             earnings_trend=NS(estimate_revision="down", beat_rate=0.3))
    a = _run(bu, pos=PositionState.LONG)
    assert a.short_action == ShortAction.NONE
    assert a.confidence >= 0.50


def test_bearish_anomaly_boosts():
    bu = _bu(quality=NS(altman_z=1.6, interest_coverage=2.0, fcf_margin=5.0,
                        debt_to_equity=0.5, current_ratio=2.0))
    bear = AnomalyReport(has_anomalies=True, statistical=["x"], contradictions=[],
                         severity="high", summary="s", direction="bearish")
    assert _run(bu, bua=bear).confidence > _run(bu).confidence


def test_non_equity_fallback():
    a = _run(_bu(asset_class="commodity"))
    assert a.short_action == ShortAction.NONE
    assert "Fallback" in a.thesis_flags[0]


def test_no_catalyst_cap_is_hard_ceiling():
    """Ohne Katalysator (earnings_collapse) ist 0.70 ein HARTER Deckel — auch
    Rückenwind-Regime + bearishe Anomalie dürfen ihn nicht durchbrechen."""
    bu = _bu(quality=NS(altman_z=0.9, interest_coverage=0.5, fcf_margin=-5.0,
                        debt_to_equity=2.0, current_ratio=0.8))   # Distress, KEIN Katalysator
    bear = AnomalyReport(has_anomalies=True, statistical=["x"], contradictions=[],
                         severity="high", summary="s", direction="bearish")
    a = _run(bu, cockpit=_cockpit(MarketRegime.RECESSION), bua=bear)   # tailwind + Boost
    assert "broken_growth" not in a.archetypes        # wirklich kein Katalysator
    assert a.confidence <= 0.70


# ---------------------------------------------------------------------------
# SHORT_PLUS — in einen Gewinner-Short nachlegen (Task 1)
# ---------------------------------------------------------------------------

_STRONG = dict(quality=NS(altman_z=1.0, interest_coverage=0.5, fcf_margin=-5.0,
                          debt_to_equity=2.0, current_ratio=0.8),
               earnings_trend=NS(estimate_revision="down", beat_rate=0.3))


def test_short_plus_when_winning_and_thesis_holds():
    a = _run(_bu(**_STRONG), pos=PositionState.SHORT, pnl=6.0)
    assert a.short_action == ShortAction.SHORT_PLUS
    assert a.suggested_size_pct == round(_position_size_pct(a.confidence) * 0.25, 1)
    assert a.stop_pct == 15.0


def test_short_plus_boundary_exactly_5pct():
    assert _run(_bu(**_STRONG), pos=PositionState.SHORT, pnl=5.0).short_action == ShortAction.SHORT_PLUS
    assert _run(_bu(**_STRONG), pos=PositionState.SHORT, pnl=4.9).short_action == ShortAction.HOLD


def test_short_plus_none_pnl_holds():
    assert _run(_bu(**_STRONG), pos=PositionState.SHORT, pnl=None).short_action == ShortAction.HOLD


def test_short_plus_blocked_by_high_squeeze():
    bu = _bu(**_STRONG, short_interest=NS(days_to_cover=3, short_float_pct=25.0))
    assert _run(bu, pos=PositionState.SHORT, pnl=8.0).short_action == ShortAction.HOLD


def test_short_plus_weak_thesis_still_covers():
    assert _run(_bu(), pos=PositionState.SHORT, pnl=20.0).short_action == ShortAction.COVER
