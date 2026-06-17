import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.short_interest_agent import ShortInterestAgent, _signal
from core.domain.models import Signal


def _make_agent(data: dict) -> ShortInterestAgent:
    provider = MagicMock()
    provider.get_short_interest.return_value = data
    return ShortInterestAgent(provider, MagicMock())


# ── niedriger Short-Float ist NEUTRAL (nicht mehr bullish) ─────────────────

def test_niedriger_short_float_ist_neutral():
    sig = _signal(short_float=3.0, dtc=1.0, trend="stable")
    assert sig == Signal.NEUTRAL


# ── hoher Short-Float + steigender Trend = bearish-Bestätigung ─────────────

def test_hoher_short_float_steigend_ist_bearish():
    sig = _signal(short_float=28.0, dtc=8.0, trend="rising")
    assert sig == Signal.BEARISH


# ── hoher Short-Float + fallender Trend + hoher DTC = Squeeze-Potenzial ────

def test_hoher_short_float_fallend_hoher_dtc_ist_bullish():
    """Sich auflösende Skepsis bei hohem Days-to-Cover → Squeeze-Brennstoff (bullish)."""
    sig = _signal(short_float=28.0, dtc=9.0, trend="falling")
    assert sig == Signal.BULLISH


# ── days_to_cover fließt ein ──────────────────────────────────────────────

def test_days_to_cover_verstaerkt_squeeze():
    """Hoher Short-Float, fallend, aber niedriger DTC → kein starkes Squeeze-Signal."""
    low_dtc  = _signal(short_float=28.0, dtc=1.0, trend="falling")
    high_dtc = _signal(short_float=28.0, dtc=9.0, trend="falling")
    order = {Signal.BEARISH: -1, Signal.NEUTRAL: 0, Signal.BULLISH: 1}
    assert order[high_dtc] >= order[low_dtc]


# ── fehlende Daten ────────────────────────────────────────────────────────

def test_keine_daten_neutral():
    sig = _signal(short_float=None, dtc=None, trend="stable")
    assert sig == Signal.NEUTRAL


def test_run_durchreichung():
    result = asyncio.run(_make_agent({
        "short_float_pct": 28.0, "days_to_cover": 9.0, "short_float_trend": "falling",
    }).run("X"))
    assert result.signal == Signal.BULLISH
    assert result.days_to_cover == 9.0
