import pytest

from core.domain.taxonomy import Underlying, Wrapper
from core.domain.recommendation import _short_type, derive_recommendation
from core.domain.models import (
    Recommendation, PositionState, Signal, ShortType,
)


# ---------------------------------------------------------------------------
# Matrix-Test für _short_type(underlying, wrapper) — Spec §8.4
# Regel: DEFENSIV wenn underlying == EQUITY_INDEX ODER wrapper == FUND,
# sonst AGGRESSIV. Ersetzt ETF_ASSET_CLASSES + alten String-Vergleich.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("underlying, wrapper, expected", [
    (Underlying.EQUITY,         Wrapper.SINGLE,       ShortType.AGGRESSIVE),
    (Underlying.EQUITY,         Wrapper.FUND,         ShortType.DEFENSIVE),   # Aktien-ETF = breit
    (Underlying.EQUITY_INDEX,   Wrapper.SINGLE,       ShortType.DEFENSIVE),
    (Underlying.EQUITY_INDEX,   Wrapper.FUND,         ShortType.DEFENSIVE),
    (Underlying.EQUITY_INDEX,   Wrapper.FUTURE,       ShortType.DEFENSIVE),   # Index-Future bleibt breit
    (Underlying.BOND,           Wrapper.SINGLE,       ShortType.AGGRESSIVE),
    (Underlying.BOND,           Wrapper.FUND,         ShortType.DEFENSIVE),
    (Underlying.COMMODITY,      Wrapper.FUTURE,       ShortType.AGGRESSIVE),
    (Underlying.PRECIOUS_METAL, Wrapper.FUTURE,       ShortType.AGGRESSIVE),
    (Underlying.PRECIOUS_METAL, Wrapper.PHYSICAL_ETC, ShortType.AGGRESSIVE),
])
def test_short_type_matrix(underlying, wrapper, expected):
    assert _short_type(underlying, wrapper) == expected


# ---------------------------------------------------------------------------
# derive_recommendation — Regressions-Tests mit neuer Signatur (underlying/wrapper)
# ---------------------------------------------------------------------------

def _rec(signal, pos, conf=0.7, alignment="mixed"):
    return derive_recommendation(
        alignment=alignment, signal=signal,
        underlying=Underlying.EQUITY, wrapper=Wrapper.SINGLE,
        current_position=pos, market="USA", cockpit=None,
        top_down_available=True, confidence=conf,
    ).action


def test_not_held_bullish_is_buy():
    assert _rec(Signal.BULLISH, PositionState.NONE) == Recommendation.BUY


def test_not_held_bearish_is_none():
    assert _rec(Signal.BEARISH, PositionState.NONE) == Recommendation.NONE


def test_not_held_neutral_is_none():
    assert _rec(Signal.NEUTRAL, PositionState.NONE) == Recommendation.NONE


def test_long_bullish_is_buy_plus():
    assert _rec(Signal.BULLISH, PositionState.LONG) == Recommendation.BUY_PLUS


def test_long_neutral_is_hold():
    assert _rec(Signal.NEUTRAL, PositionState.LONG) == Recommendation.HOLD


def test_long_bearish_is_sell():
    assert _rec(Signal.BEARISH, PositionState.LONG) == Recommendation.SELL


def test_short_position_long_lens_defers_to_none():
    for sig in (Signal.BULLISH, Signal.BEARISH, Signal.NEUTRAL):
        assert _rec(sig, PositionState.SHORT) == Recommendation.NONE


def test_low_confidence_held_is_hold_not_held_is_none():
    assert _rec(Signal.BULLISH, PositionState.LONG, conf=0.4) == Recommendation.HOLD
    assert _rec(Signal.BULLISH, PositionState.NONE, conf=0.4) == Recommendation.NONE


def test_never_emits_short():
    actions = {_rec(s, p) for s in (Signal.BULLISH, Signal.BEARISH, Signal.NEUTRAL)
               for p in PositionState}
    assert Recommendation.SHORT not in actions
