"""
TDD tests for EcbSdwProvider.get_yield_spreads()
"""
from unittest.mock import patch, MagicMock
import pytest

from adapters.data.ecb_sdw import EcbSdwProvider


def _make_response(value: float) -> MagicMock:
    """Build a mock requests.Response with a single ECB SDW JSON payload."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "dataSets": [{
            "series": {
                "0:0:0:0:0:0:0": {
                    "observations": {
                        "0": [value]
                    }
                }
            }
        }]
    }
    return resp


def test_get_yield_spreads_returns_both_spreads():
    """Normal case: all three maturities succeed → both spreads computed."""
    SR_10Y, SR_2Y, SR_3M = 3.09, 2.62, 2.27

    def mock_get(url, timeout):
        if "SR_10Y" in url:
            return _make_response(SR_10Y)
        if "SR_2Y" in url:
            return _make_response(SR_2Y)
        if "SR_3M" in url:
            return _make_response(SR_3M)
        raise ValueError(f"Unexpected URL: {url}")

    with patch("adapters.data.ecb_sdw.requests.get", side_effect=mock_get):
        provider = EcbSdwProvider()
        result = provider.get_yield_spreads()

    assert result["10y2y"] == round(SR_10Y - SR_2Y, 3)
    assert result["10y3m"] == round(SR_10Y - SR_3M, 3)


def test_get_yield_spreads_partial_failure():
    """SR_10Y fails → both spreads are None because both need 10y."""
    SR_2Y, SR_3M = 2.62, 2.27

    def mock_get(url, timeout):
        if "SR_10Y" in url:
            raise ConnectionError("timeout")
        if "SR_2Y" in url:
            return _make_response(SR_2Y)
        if "SR_3M" in url:
            return _make_response(SR_3M)
        raise ValueError(f"Unexpected URL: {url}")

    with patch("adapters.data.ecb_sdw.requests.get", side_effect=mock_get):
        provider = EcbSdwProvider()
        result = provider.get_yield_spreads()

    assert result["10y2y"] is None
    assert result["10y3m"] is None


def test_get_yield_spreads_http_error():
    """HTTP 404 for all requests → both spreads are None."""
    resp = MagicMock()
    resp.status_code = 404
    resp.raise_for_status.side_effect = Exception("404 Client Error")

    with patch("adapters.data.ecb_sdw.requests.get", return_value=resp):
        provider = EcbSdwProvider()
        result = provider.get_yield_spreads()

    assert result["10y2y"] is None
    assert result["10y3m"] is None
