"""TDD: Shiller-CAPE-Adapter (MultplShillerProvider) via multpl.com (S&P 500)."""
from unittest.mock import MagicMock, patch

from adapters.data.multpl_shiller import MultplShillerProvider, _parse_multpl_cape, _SP500

_GET = "adapters.data.multpl_shiller.requests.get"

_HTML = (
    "<html><body><div id='current'>Current Shiller PE Ratio "
    "<b>40.94</b> -0.02 (-0.05%) 4:00 PM EDT, Wed Jun 24</div>"
    "Mean: 17.39 Median: 16.05</body></html>"
)


def _resp(text):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def test_parse_multpl_cape_aktueller_wert():
    assert _parse_multpl_cape(_HTML) == 40.94


def test_parse_multpl_cape_ohne_treffer_none():
    assert _parse_multpl_cape("<html>kein Wert</html>") is None


def test_parse_multpl_cape_implausibel_none():
    bad = _HTML.replace("40.94", "999.0")
    assert _parse_multpl_cape(bad) is None


def test_get_shiller_cape_sp500():
    with patch(_GET, return_value=_resp(_HTML)):
        assert MultplShillerProvider().get_shiller_cape("^GSPC") == 40.94


def test_get_shiller_cape_nur_sp500_sonst_none():
    with patch(_GET) as m:
        assert MultplShillerProvider().get_shiller_cape("^NDX") is None
    m.assert_not_called()   # multpl ist S&P-500-spezifisch → kein Netzaufruf


def test_get_shiller_cape_netzfehler_none():
    with patch(_GET, side_effect=ConnectionError("boom")):
        assert MultplShillerProvider().get_shiller_cape("^GSPC") is None


def test_sp500_alias_set():
    assert "^GSPC" in _SP500 and "SPY" in _SP500
