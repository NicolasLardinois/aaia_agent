"""TDD Task 2: BottomUpResult trägt underlying+wrapper statt asset_class.

Round-Trip-Test: save→load muss beide Felder erhalten (schliesst Bug-#1-Typ).
"""
from core.domain.taxonomy import Underlying, Wrapper
from core.domain.models import BottomUpResult


def _minimal_bottom_up(underlying, wrapper):
    return BottomUpResult(
        ticker="X", underlying=underlying, wrapper=wrapper,
        fundamentals=None, quality=None, short_interest=None, insider=None,
        earnings_trend=None, moat=None, valuation_range=None,
        precious_metals=None, bond=None, index=None, commodity_deep=None,
    )


def test_underlying_wrapper_gesetzt():
    """Task 8: Übergangs-Property entfernt — underlying/wrapper direkt prüfen."""
    r = _minimal_bottom_up(Underlying.EQUITY_INDEX, Wrapper.FUND)
    assert r.underlying == Underlying.EQUITY_INDEX
    assert r.wrapper == Wrapper.FUND
    # Sicherstellung: kein legacy-Property mehr vorhanden (Task 8).
    assert not hasattr(r.__class__, "asset_class"), "asset_class-Property darf nicht mehr existieren"


def test_cache_roundtrip_erhaelt_underlying_wrapper(tmp_path, monkeypatch):
    """Schliesst die offene Round-Trip-Lücke (Bug-#1-Typ): save→load muss beide Felder erhalten."""
    import adapters.cache.result_cache as rc_module
    # Cache-Verzeichnis auf tmp_path umbiegen, damit kein echtes .cache-Verzeichnis geschrieben wird.
    bottomup_tpl = str(tmp_path / "bottomup_{ticker}.json")
    monkeypatch.setattr(rc_module, "BOTTOMUP_FILE", bottomup_tpl)
    # _is_fresh patchen: liefert immer True (kein MAX_AGE-Problem im Test)
    monkeypatch.setattr(rc_module, "_is_fresh", lambda path: True)

    from adapters.cache.result_cache import ResultCache
    cache = ResultCache()
    original = _minimal_bottom_up(Underlying.COMMODITY, Wrapper.FUTURE)
    cache.save_bottom_up(original)
    loaded = cache.load_bottom_up("X")
    assert loaded.underlying == Underlying.COMMODITY
    assert loaded.wrapper == Wrapper.FUTURE
