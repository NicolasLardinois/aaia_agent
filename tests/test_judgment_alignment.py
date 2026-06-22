import asyncio
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, patch

from core.domain.models import (
    AnomalyReport, MarketRegime, PositionState, ShortAction, Signal,
)
from agents.judgment.judgment_agent import (
    _derive_alignment, _backtester_summary, _bottom_up_signals, _ALIGNMENT_WEIGHTS, JudgmentAgent,
)


def test_alignment_relative_majority_bullish():
    # 4 von 5 nicht-neutralen bullish (>60 %) → aligned_bullish
    sigs = [Signal.BULLISH, Signal.BULLISH, Signal.BULLISH, Signal.BULLISH, Signal.BEARISH]
    assert _derive_alignment(sigs) == "aligned_bullish"


def test_alignment_not_aligned_when_below_threshold():
    # 3 von 5 bullish (60 %, nicht > 60 %) → contradicting (beide Richtungen vorhanden)
    sigs = [Signal.BULLISH, Signal.BULLISH, Signal.BULLISH, Signal.BEARISH, Signal.BEARISH]
    assert _derive_alignment(sigs) == "contradicting"


def test_alignment_two_of_two_bullish_is_aligned():
    # Relative Schwelle löst auch bei wenigen Signalen sauber aus
    assert _derive_alignment([Signal.BULLISH, Signal.BULLISH]) == "aligned_bullish"


def test_alignment_all_neutral_is_mixed():
    assert _derive_alignment([Signal.NEUTRAL, Signal.NEUTRAL]) == "mixed"


def test_alignment_weighted_valuation_counts_more():
    # Gewichtung: Valuation (idx 5) zählt stärker; wenn die schwergewichtige
    # Valuation bearish ist, kippt das Alignment trotz numerischer Gleichheit.
    sigs = [Signal.BULLISH, Signal.BULLISH, Signal.BEARISH, Signal.BEARISH,
            Signal.NEUTRAL, Signal.BEARISH]
    assert _derive_alignment(sigs) == "aligned_bearish"


def test_backtester_summary_labels_horizon_and_ci():
    ctx = {"sample_size": 40, "hit_rate": 0.62,
           "hit_rate_ci_low": 0.48, "hit_rate_ci_high": 0.74}
    s = _backtester_summary(ctx)
    assert "62%" in s and "48%" in s and "74%" in s
    assert "30 Tage" not in s


def test_backtester_summary_empty():
    assert "Noch kein" in _backtester_summary({})


# ─────────────────────────────────────────────
# Task 5: Verdrahtungs-Integrationstests (JudgmentAgent.run)
# ─────────────────────────────────────────────

def _make_distress_bu():
    """BottomUp mit starkem Distress-Signal (Altman-Z < 1.0, schlechte Kennzahlen)."""
    return NS(
        asset_class="equity",
        quality=NS(altman_z=0.8, interest_coverage=0.5, fcf_margin=-8.0,
                   debt_to_equity=2.5, current_ratio=0.7),
        # earnings_trend wird von judgment_agent auf .signal geprüft → bearish angeben
        earnings_trend=NS(estimate_revision="down", beat_rate=0.25, signal=Signal.BEARISH),
        fundamentals=None,
        valuation_range=None,
        moat=None,
        insider=None,
        short_interest=None,
    )


def _make_cockpit_recession():
    cockpit = MagicMock()
    cockpit.macro.regime = MarketRegime.RECESSION
    cockpit.macro.regime_confidence = 0.80
    return cockpit


async def _to_thread_mock(fn, *args, **kw):
    """Python-3.12-kompatibler Ersatz für asyncio.to_thread in Tests."""
    return fn(*args, **kw)


def _run_judgment(current_position, bottom_up=None, cockpit=None):
    bus = MagicMock()
    llm = MagicMock()
    llm.complete.return_value = "Urteil"
    agent = JudgmentAgent(llm, bus)

    if bottom_up is None:
        bottom_up = _make_distress_bu()
    if cockpit is None:
        cockpit = _make_cockpit_recession()

    with patch("asyncio.to_thread", side_effect=_to_thread_mock):
        return asyncio.run(agent.run(
            ticker="TEST",
            top_down_context="Rezession, bearish Makro",
            bottom_up=bottom_up,
            cockpit=cockpit,
            market="USA",
            current_position=current_position,
            top_down_available=True,
            top_down_anomaly=AnomalyReport.empty(),
            bottom_up_anomaly=AnomalyReport.empty(),
            backtester_context={},
        ))


def test_judgment_short_held_distress_gives_hold():
    """SHORT gehalten + starke Distress-These → short_action == HOLD."""
    result = _run_judgment(PositionState.SHORT)
    assert result.short_action == ShortAction.HOLD


def test_judgment_long_held_distress_gives_conflict():
    """LONG gehalten + starke Distress-These → conflict == True."""
    result = _run_judgment(PositionState.LONG)
    assert result.conflict is True


# ─────────────────────────────────────────────
# Task 5: Momentum-Integration in Alignment (Step 1 — Failing Tests)
# ─────────────────────────────────────────────

def test_bottom_up_signals_includes_momentum():
    """Momentum erscheint an Position 6 (vor Bond) in _bottom_up_signals.
    _ALIGNMENT_WEIGHTS muss mindestens 8 Einträge haben:
    Momentum-Gewicht 0.5 an Pos 6, Bond-Gewicht 1.0 an Pos 7.
    """
    from types import SimpleNamespace as NS
    bu = NS(
        fundamentals=None, short_interest=None, insider=None, earnings_trend=None,
        moat=None, valuation_range=None, bond=None,
        momentum=NS(signal=Signal.BEARISH),
    )
    sigs = _bottom_up_signals(bu)
    assert sigs[6] == Signal.BEARISH, f"Erwartet Signal.BEARISH an Index 6, aber: {sigs[6]}"
    assert len(_ALIGNMENT_WEIGHTS) >= 8, (
        f"_ALIGNMENT_WEIGHTS hat nur {len(_ALIGNMENT_WEIGHTS)} Einträge, benötigt mind. 8"
    )
    assert _ALIGNMENT_WEIGHTS[6] == 0.5, (
        f"Momentum-Gewicht (Index 6) sollte 0.5 sein, ist aber: {_ALIGNMENT_WEIGHTS[6]}"
    )
    assert _ALIGNMENT_WEIGHTS[7] == 1.0, (
        f"Bond-Gewicht (Index 7) sollte 1.0 sein, ist aber: {_ALIGNMENT_WEIGHTS[7]}"
    )
