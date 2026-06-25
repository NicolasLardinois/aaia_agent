"""TDD: ECB AAA 10J-Nominalrendite (get_aaa_10y_yield) für die EU-Realzins-Berechnung."""
from unittest.mock import MagicMock, patch

from adapters.data.ecb_sdw import EcbSdwProvider
from adapters.data.eurostat import EurostatEcbProvider

_GET = "adapters.data.ecb_sdw.requests.get"


def _sdmx(value):
    return {"dataSets": [{"series": {"0:0:0:0:0:0:0": {"observations": {"0": [value]}}}}]}


def _resp(payload):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    return r


def test_get_aaa_10y_yield_parst_sr_10y():
    with patch(_GET, return_value=_resp(_sdmx(2.9379971807))) as m:
        assert EcbSdwProvider().get_aaa_10y_yield() == 2.938
    assert "SR_10Y" in m.call_args.args[0]


def test_get_aaa_10y_yield_netzfehler_none():
    with patch(_GET, side_effect=ConnectionError("boom")):
        assert EcbSdwProvider().get_aaa_10y_yield() is None


def test_eurostat_decorator_delegiert_aaa_10y():
    base = MagicMock()
    base.get_aaa_10y_yield.return_value = 2.5
    assert EurostatEcbProvider(base).get_aaa_10y_yield() == 2.5
