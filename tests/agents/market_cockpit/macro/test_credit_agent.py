from agents.market_cockpit.macro.credit_agent import _signal
from core.domain.models import Signal


def test_none_is_neutral():
    assert _signal(real_credit_growth=None) == Signal.NEUTRAL


def test_moderate_real_growth_is_bullish():
    # 2–8% reales Kreditwachstum = gesunde Expansion → BULLISH
    assert _signal(real_credit_growth=4.0) == Signal.BULLISH


def test_excessive_growth_is_bearish():
    # >12% real = Kreditboom = Krisen-Frühwarnung → BEARISH
    assert _signal(real_credit_growth=14.0) == Signal.BEARISH


def test_contraction_is_bearish():
    assert _signal(real_credit_growth=-1.0) == Signal.BEARISH


def test_low_positive_is_neutral():
    # 0–2% real = schwach, aber nicht negativ → NEUTRAL
    assert _signal(real_credit_growth=1.0) == Signal.NEUTRAL
