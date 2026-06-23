import pytest
from core.domain.taxonomy import Underlying, Wrapper, legacy_to_taxonomy, legacy_asset_class


def test_enum_werte_sind_lesbare_strings():
    assert Underlying.EQUITY == "equity"
    assert Underlying.EQUITY_INDEX == "equity_index"
    assert Wrapper.FUTURE == "future"
    assert Wrapper.PHYSICAL_ETC == "physical_etc"


@pytest.mark.parametrize("legacy, expected", [
    ("equity",         (Underlying.EQUITY,         Wrapper.SINGLE)),
    ("etf",            (Underlying.EQUITY_INDEX,   Wrapper.FUND)),     # behebt den Durchfall-Bug
    ("index",          (Underlying.EQUITY_INDEX,   Wrapper.SINGLE)),
    ("bond",           (Underlying.BOND,           Wrapper.SINGLE)),
    ("commodity",      (Underlying.COMMODITY,      Wrapper.FUTURE)),
    ("precious_metal", (Underlying.PRECIOUS_METAL, Wrapper.FUTURE)),
    ("EQUITY",         (Underlying.EQUITY,         Wrapper.SINGLE)),    # case-insensitiv
])
def test_legacy_to_taxonomy(legacy, expected):
    assert legacy_to_taxonomy(legacy) == expected


def test_legacy_to_taxonomy_unbekannt_faellt_auf_equity_single():
    # Unbekannter Alt-Wert: defensiver Default (kein Crash an der Eingangsgrenze).
    assert legacy_to_taxonomy("hudelei") == (Underlying.EQUITY, Wrapper.SINGLE)


@pytest.mark.parametrize("underlying, wrapper, expected", [
    (Underlying.EQUITY,         Wrapper.SINGLE, "equity"),
    (Underlying.EQUITY_INDEX,   Wrapper.FUND,   "etf"),
    (Underlying.EQUITY_INDEX,   Wrapper.SINGLE, "index"),
    (Underlying.BOND,           Wrapper.SINGLE, "bond"),
    (Underlying.COMMODITY,      Wrapper.FUTURE, "commodity"),
    (Underlying.PRECIOUS_METAL, Wrapper.FUTURE, "precious_metal"),
    (Underlying.PRECIOUS_METAL, Wrapper.PHYSICAL_ETC, "precious_metal"),  # ETC nutzt PM-Engine
])
def test_legacy_asset_class_rueckabbildung(underlying, wrapper, expected):
    assert legacy_asset_class(underlying, wrapper) == expected
