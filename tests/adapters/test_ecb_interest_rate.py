from unittest.mock import MagicMock, patch

from adapters.data.ecb_sdw import EcbSdwProvider

_CSV = (
    "KEY,FREQ,TIME_PERIOD,OBS_VALUE\r\n"
    "FM...,B,2026-04-01,2.15\r\n"
    "FM...,B,2026-06-17,2.4\r\n"
)


def _resp(text, status=200):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def test_get_interest_rate_returns_latest():
    p = EcbSdwProvider()
    with patch("adapters.data.ecb_sdw.requests.get", return_value=_resp(_CSV)):
        assert p.get_interest_rate() == 2.4


def test_get_interest_rate_history_maps_rows():
    p = EcbSdwProvider()
    with patch("adapters.data.ecb_sdw.requests.get", return_value=_resp(_CSV)):
        assert p.get_interest_rate_history(2) == [
            {"date": "2026-04-01", "rate": 2.15},
            {"date": "2026-06-17", "rate": 2.4},
        ]


def test_get_interest_rate_none_on_failure():
    p = EcbSdwProvider()
    with patch("adapters.data.ecb_sdw.requests.get", side_effect=Exception("net")):
        assert p.get_interest_rate() is None
        assert p.get_interest_rate_history(2) == []
