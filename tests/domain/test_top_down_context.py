from unittest.mock import MagicMock

from core.domain.top_down_context import _buffett_fallback_note, derive_top_down_context
from core.domain.models import MarketRegime


# ── Buffett-Fallback (länderspezifische Korridore) ───────────────────────────

def test_swiss_fallback_uses_ch_corridor():
    # CH bei 230% ohne z-Score → mit CH-Korridor NICHT als "teuer" (>135) markiert
    notes = _buffett_fallback_note("CHE", ratio=230.0)
    assert notes == []   # 230 liegt im CH-Normalkorridor


def test_swiss_fallback_flags_extreme():
    notes = _buffett_fallback_note("CHE", ratio=300.0)
    assert notes and "teuer" in notes[0].lower()


def test_german_fallback_uses_de_corridor():
    # DE bei 90% ist für DE bereits erhöht (Korridor ~50–70)
    notes = _buffett_fallback_note("DEU", ratio=90.0)
    assert notes and "erhöht" in notes[0].lower() or "teuer" in notes[0].lower()


def test_us_fallback_unchanged():
    notes = _buffett_fallback_note("USA", ratio=200.0)
    assert notes and "teuer" in notes[0].lower()


# ── derive_top_down_context (None-Guard + market-aware Routing) ───────────────
# (zusammengeführt aus der frueheren tests/test_top_down_context.py, §7 Aufräumen)

def _make_cockpit(
    usa_inverted=False, usa_spread=None,
    eu_inverted=False,  eu_spread=None,
    ch_inverted=False,  ch_spread=None,
):
    cockpit = MagicMock()
    cockpit.macro.regime = MarketRegime.EXPANSION
    cockpit.yield_curve.yield_spreads.usa.inverted        = usa_inverted
    cockpit.yield_curve.yield_spreads.usa.spread_10y2y   = usa_spread
    cockpit.yield_curve.yield_spreads.eurozone.inverted      = eu_inverted
    cockpit.yield_curve.yield_spreads.eurozone.spread_10y2y  = eu_spread
    cockpit.yield_curve.yield_spreads.switzerland.inverted     = ch_inverted
    cockpit.yield_curve.yield_spreads.switzerland.spread_10y2y = ch_spread
    cockpit.sentiment.vix.vix = None
    cockpit.sectors.performance.leading_usa = None
    cockpit.macro.buffett_indicator = MagicMock(countries={})
    return cockpit


def test_derive_context_inverted_with_none_spread_does_not_crash():
    cockpit = _make_cockpit(usa_inverted=True, usa_spread=None)
    result = derive_top_down_context(cockpit, sector="Technology", market="USA")
    assert isinstance(result, str)


def test_derive_context_inverted_with_spread_shows_value():
    cockpit = _make_cockpit(usa_inverted=True, usa_spread=-0.45)
    result = derive_top_down_context(cockpit, sector="Technology", market="USA")
    assert "-0.45" in result


def test_ch_market_uses_swiss_yield_curve():
    """market='CH' + Schweizer Spread invertiert → Note erscheint."""
    cockpit = _make_cockpit(ch_inverted=True, ch_spread=-0.30)
    result = derive_top_down_context(cockpit, sector="Technology", market="CH")
    assert "invertiert" in result
    assert "-0.30" in result


def test_eu_market_uses_eurozone_yield_curve():
    """market='IT' + Eurozone invertiert → Note erscheint (Routing korrekt)."""
    cockpit = _make_cockpit(eu_inverted=True, eu_spread=-0.20)
    result = derive_top_down_context(cockpit, sector="Technology", market="IT")
    assert "invertiert" in result
    assert "-0.20" in result


def test_ch_market_ignores_usa_inversion():
    """market='CH' + USA invertiert, CH nicht → keine Note (kein falscher Alarm)."""
    cockpit = _make_cockpit(usa_inverted=True, usa_spread=-0.50)
    result = derive_top_down_context(cockpit, sector="Technology", market="CH")
    assert "invertiert" not in result
