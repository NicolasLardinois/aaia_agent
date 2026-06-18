from types import SimpleNamespace as NS
from core.domain.short_flags import SHORT_FLAGS


def _bu(**kw):
    base = dict(asset_class="equity", quality=None, earnings_trend=None,
                fundamentals=None, valuation_range=None, moat=None,
                insider=None, short_interest=None)
    base.update(kw)
    return NS(**base)


def _flag(name):
    return next(f for f in SHORT_FLAGS if f.name == name)


def test_altman_distress_fires_and_is_defensive():
    f = _flag("altman_distress")
    assert f.fires(_bu(quality=NS(altman_z=1.4))) is True
    assert f.fires(_bu(quality=NS(altman_z=3.0))) is False
    assert f.fires(_bu(quality=None)) is False


def test_earnings_collapse_on_down_revision():
    f = _flag("earnings_collapse")
    assert f.fires(_bu(earnings_trend=NS(estimate_revision="down", beat_rate=0.9))) is True
    assert f.fires(_bu(earnings_trend=NS(estimate_revision="up", beat_rate=0.9))) is False
    assert f.fires(_bu(earnings_trend=None)) is False


def test_valuation_extreme_overvalued():
    f = _flag("valuation_extreme")
    assert f.fires(_bu(valuation_range=NS(position="overvalued"), fundamentals=NS(peg_ratio=1.0))) is True
    assert f.fires(_bu(valuation_range=NS(position="fair"), fundamentals=NS(peg_ratio=1.0))) is False


def test_kinds_and_archetypes():
    kern = {f.name for f in SHORT_FLAGS if f.kind == "kern"}
    assert {"altman_distress", "earnings_collapse", "growth_collapse"} <= kern
    assert _flag("valuation_extreme").kind == "verstaerker"
