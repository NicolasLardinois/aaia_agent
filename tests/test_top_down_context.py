from unittest.mock import MagicMock
from core.domain.top_down_context import derive_top_down_context
from core.domain.models import MarketRegime


def _make_cockpit(inverted: bool, spread: float | None):
    cockpit = MagicMock()
    cockpit.macro.regime = MarketRegime.EXPANSION
    cockpit.yield_curve.yield_spreads.usa.inverted = inverted
    cockpit.yield_curve.yield_spreads.usa.spread_10y2y = spread
    cockpit.sentiment.vix.vix = None
    cockpit.sectors.performance.leading_usa = None
    cockpit.macro.buffett_indicator = MagicMock(countries={})
    return cockpit


def test_derive_context_inverted_with_none_spread_does_not_crash():
    cockpit = _make_cockpit(inverted=True, spread=None)
    result = derive_top_down_context(cockpit, sector="Technology")
    assert isinstance(result, str)


def test_derive_context_inverted_with_spread_shows_value():
    cockpit = _make_cockpit(inverted=True, spread=-0.45)
    result = derive_top_down_context(cockpit, sector="Technology")
    assert "-0.45" in result
