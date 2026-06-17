from unittest.mock import MagicMock, patch

from adapters.data.fred_snb import FredSnbProvider

_CSV = (
    '"CubeId";"snboffzisa"\r\n'
    '"PublishingDate";"2026-05-21 09:00"\r\n'
    "\r\n"
    '"Date";"D0";"Value"\r\n'
    '"2026-02";"UG0";"1.0"\r\n'
    '"2026-02";"LZ";"1.75"\r\n'
    '"2026-04";"LZ";"2.15"\r\n'
)


def _provider():
    return FredSnbProvider.__new__(FredSnbProvider)


def _resp(text):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def test_get_interest_rate_latest_lz():
    p = _provider()
    with patch("adapters.data.fred_snb.requests.get", return_value=_resp(_CSV)):
        assert p.get_interest_rate() == 2.15


def test_get_interest_rate_history_only_lz_iso_dates():
    p = _provider()
    with patch("adapters.data.fred_snb.requests.get", return_value=_resp(_CSV)):
        assert p.get_interest_rate_history(2) == [
            {"date": "2026-02-01", "rate": 1.75},
            {"date": "2026-04-01", "rate": 2.15},
        ]


def test_get_interest_rate_none_on_failure():
    p = _provider()
    with patch("adapters.data.fred_snb.requests.get", side_effect=Exception("net")):
        assert p.get_interest_rate() is None
        assert p.get_interest_rate_history(2) == []
