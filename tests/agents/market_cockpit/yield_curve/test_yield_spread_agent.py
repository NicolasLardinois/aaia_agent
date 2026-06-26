import asyncio
import logging
from unittest.mock import MagicMock

from agents.market_cockpit.yield_curve.yield_spread_agent import YieldSpreadAgent, _point
from core.domain.models import Signal


def test_run_loggt_warnung_bei_ausgefallener_quelle(caplog):
    # Logging-Pass: ausgefallene EU-Spread-Quelle -> sichtbare warning (Default greift weiter).
    macro = MagicMock()
    macro.get_economic_state.return_value = {}
    macro.get_extended_state.return_value = {}
    ecb = MagicMock()
    ecb.get_yield_spreads.side_effect = RuntimeError("ECB SDW down")
    snb = MagicMock()
    snb.get_yield_spreads.return_value = {}
    agent = YieldSpreadAgent(macro=macro, ecb=ecb, snb=snb, bus=MagicMock())
    with caplog.at_level(logging.WARNING):
        asyncio.run(agent.run())
    assert "Yield Spread ECB SDW (EU)" in caplog.text


def test_normal_positive_curve_is_neutral():
    pt = _point(s10y2y=0.8, s10y3m=0.9, s30y10y=None, prev_10y3m=0.9)
    assert pt.inverted is False
    assert pt.signal == Signal.NEUTRAL


def test_steep_curve_is_bullish():
    pt = _point(s10y2y=1.4, s10y3m=1.6, s30y10y=None, prev_10y3m=1.5)
    assert pt.signal == Signal.BULLISH


def test_fresh_inversion_is_neutral_warning_not_bearish():
    # Frisch invertiert, weiter fallend → Warnung, NICHT sofort BEARISH (Lag)
    pt = _point(s10y2y=-0.3, s10y3m=-0.4, s30y10y=None, prev_10y3m=-0.2)
    assert pt.inverted is True
    assert pt.signal == Signal.NEUTRAL


def test_bull_steepening_after_inversion_is_bearish():
    # Spread war invertiert (prev -0.5), versteilt sich aus der Inversion (-0.1) → Timing-Signal
    pt = _point(s10y2y=-0.1, s10y3m=-0.1, s30y10y=None, prev_10y3m=-0.5)
    assert pt.signal == Signal.BEARISH


def test_10y3m_is_primary_ref():
    # 10y2y positiv, aber 10y3m invertiert → Kurve gilt als invertiert (10y3m primär)
    pt = _point(s10y2y=0.2, s10y3m=-0.1, s30y10y=None, prev_10y3m=-0.2)
    assert pt.inverted is True


def test_all_none_is_neutral():
    pt = _point(s10y2y=None, s10y3m=None, s30y10y=None, prev_10y3m=None)
    assert pt.signal == Signal.NEUTRAL
