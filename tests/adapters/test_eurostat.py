"""TDD-Tests fuer den Eurostat-Adapter (EurostatEcbProvider) und _parse_jsonstat_latest."""
from unittest.mock import patch, MagicMock

from adapters.data.eurostat import _parse_jsonstat_latest


# ── _parse_jsonstat_latest (rein, kein Netz) ───────────────────────────────
def test_parse_nimmt_groessten_integer_key():
    # value-Keys sind Positions-Indizes; die juengste BEFUELLTE Beobachtung
    # hat den groessten Key. "5" (juengste Periode) fehlt absichtlich (unveroeffentlicht).
    data = {"value": {"0": -2.1, "1": -2.2, "4": 4.9}}
    assert _parse_jsonstat_latest(data) == 4.9


def test_parse_einzelne_beobachtung():
    assert _parse_jsonstat_latest({"value": {"0": 2.0}}) == 2.0


def test_parse_leeres_value_none():
    assert _parse_jsonstat_latest({"value": {}}) is None


def test_parse_fehlendes_value_none():
    assert _parse_jsonstat_latest({}) is None
    assert _parse_jsonstat_latest({"value": None}) is None


def test_parse_nicht_numerisch_none():
    assert _parse_jsonstat_latest({"value": {"0": "abc"}}) is None


# ── Fetch-Response-Helfer ──────────────────────────────────────────────────
def _resp(payload):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    return r


_GET = "adapters.data.eurostat.requests.get"


# ── Die 5 echten Methoden (gemocktes requests.get) ─────────────────────────
def test_get_cpi_liefert_jahresrate_und_richtige_codes():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"0": 2.0}})) as m:
        prov = EurostatEcbProvider(MagicMock())
        assert prov.get_cpi() == 2.0
    url = m.call_args.args[0]
    params = m.call_args.kwargs["params"]
    assert "prc_hicp_manr" in url
    assert params["coicop"] == "CP00" and params["unit"] == "RCH_A" and params["geo"] == "EA20"
    assert params["lastTimePeriod"] == 6


def test_get_core_cpi_codes():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"0": 2.3}})) as m:
        assert EurostatEcbProvider(MagicMock()).get_core_cpi() == 2.3
    params = m.call_args.kwargs["params"]
    assert params["coicop"] == "TOT_X_NRG_FOOD" and params["geo"] == "EA20"


def test_get_ppi_codes():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"3": 1.9, "4": 4.9}})) as m:
        assert EurostatEcbProvider(MagicMock()).get_ppi() == 4.9   # groesster Key
    url = m.call_args.args[0]
    params = m.call_args.kwargs["params"]
    assert "sts_inppd_m" in url
    assert params["indic_bt"] == "PRC_PRR_DOM" and params["nace_r2"] == "B-E36"
    assert params["s_adj"] == "NSA" and params["unit"] == "PCH_SM" and params["geo"] == "EA20"


def test_get_gdp_growth_codes():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"0": 0.3}})) as m:
        assert EurostatEcbProvider(MagicMock()).get_gdp_growth() == 0.3
    url = m.call_args.args[0]
    params = m.call_args.kwargs["params"]
    assert "namq_10_gdp" in url
    assert params["na_item"] == "B1GQ" and params["unit"] == "CLV_PCH_SM"
    assert params["s_adj"] == "SCA" and params["geo"] == "EA20"


def test_get_unemployment_codes_nutzt_ea21():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"4": 6.3}})) as m:
        assert EurostatEcbProvider(MagicMock()).get_unemployment() == 6.3
    url = m.call_args.args[0]
    params = m.call_args.kwargs["params"]
    assert "une_rt_m" in url
    assert params["sex"] == "T" and params["age"] == "TOTAL"
    assert params["unit"] == "PC_ACT" and params["s_adj"] == "SA"
    assert params["geo"] == "EA21"   # Stolperstein: NICHT EA20


def test_rundet_auf_eine_stelle():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"0": 2.34}})):
        assert EurostatEcbProvider(MagicMock()).get_cpi() == 2.3


def test_implausibler_wert_none():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, return_value=_resp({"value": {"0": 999.0}})):
        assert EurostatEcbProvider(MagicMock()).get_cpi() is None


def test_netzfehler_none():
    from adapters.data.eurostat import EurostatEcbProvider
    with patch(_GET, side_effect=ConnectionError("boom")):
        assert EurostatEcbProvider(MagicMock()).get_gdp_growth() is None


# ── Decorator-Delegation: nicht-Eurostat-Methoden gehen an base ────────────
def test_delegiert_nicht_eurostat_methoden_an_base():
    from adapters.data.eurostat import EurostatEcbProvider
    base = MagicMock()
    base.get_yield_spreads.return_value = {"10y2y": 0.5, "10y3m": 0.4}
    base.get_pmi.return_value = None
    prov = EurostatEcbProvider(base)

    assert prov.get_yield_spreads() == {"10y2y": 0.5, "10y3m": 0.4}
    base.get_yield_spreads.assert_called_once()
    assert prov.get_pmi() is None
    base.get_pmi.assert_called_once()
    prov.get_interest_rate()
    base.get_interest_rate.assert_called_once()
    prov.get_m3_growth()
    base.get_m3_growth.assert_called_once()
    prov.get_sovereign_yields()
    base.get_sovereign_yields.assert_called_once()
