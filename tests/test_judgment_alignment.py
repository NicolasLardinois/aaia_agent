from core.domain.models import Signal
from agents.judgment.judgment_agent import _derive_alignment, _backtester_summary


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
