"""TDD: Index-Holdings via slickcharts (SlickchartsHoldingsMarket-Decorator)."""
from unittest.mock import MagicMock, patch

from adapters.data.slickcharts_holdings import (
    SlickchartsHoldingsMarket,
    _parse_slickcharts,
    _PATH,
)

_GET = "adapters.data.slickcharts_holdings.requests.get"

_HTML = """
<table class="table table-hover table-borderless table-sm">
<tr><th>#</th><th>Company</th><th>Symbol</th><th>Weight</th><th>Price</th></tr>
<tr><td>1</td><td><a href="/symbol/NVDA">NVIDIA Corp</a></td><td><a>NVDA</a></td><td>7.07%</td><td>195.61</td></tr>
<tr><td>2</td><td><a href="/symbol/AAPL">Apple Inc</a></td><td><a>AAPL</a></td><td>6.02%</td><td>274.61</td></tr>
<tr><td>3</td><td><a>Microsoft Corp</a></td><td><a>MSFT</a></td><td>3.90%</td><td>351.81</td></tr>
</table>
"""


def _resp(text):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


# ── _parse_slickcharts (rein) ───────────────────────────────────────────────
def test_parse_liefert_name_und_gewicht():
    out = _parse_slickcharts(_HTML)
    assert out[0] == {"name": "NVIDIA Corp", "weight_pct": 7.07, "sector": None}
    assert out[1]["name"] == "Apple Inc" and out[1]["weight_pct"] == 6.02
    assert len(out) == 3   # Kopfzeile übersprungen


def test_parse_leer_ohne_tabelle():
    assert _parse_slickcharts("<html><body>kein content</body></html>") == []


# ── Mapping ─────────────────────────────────────────────────────────────────
def test_mapping_indizes():
    assert _PATH["^GSPC"] == "sp500"
    assert _PATH["^NDX"] == "nasdaq100"
    assert _PATH["^DJI"] == "dowjones"


# ── Decorator get_index_holdings ────────────────────────────────────────────
def test_get_index_holdings_sp500():
    base = MagicMock()
    with patch(_GET, return_value=_resp(_HTML)) as m:
        out = SlickchartsHoldingsMarket(base).get_index_holdings("^GSPC")
    assert out[0]["name"] == "NVIDIA Corp"
    assert "sp500" in m.call_args.args[0]


def test_get_index_holdings_unbekannt_leer():
    base = MagicMock()
    with patch(_GET) as m:
        assert SlickchartsHoldingsMarket(base).get_index_holdings("XYZ") == []
    m.assert_not_called()


def test_get_index_holdings_netzfehler_leer():
    base = MagicMock()
    with patch(_GET, side_effect=ConnectionError("boom")):
        assert SlickchartsHoldingsMarket(base).get_index_holdings("^GSPC") == []


# ── Decorator delegiert übrige MarketDataProvider-Methoden an base ──────────
def test_decorator_delegiert_an_base():
    base = MagicMock()
    base.get_current_price.return_value = 123.0
    base.get_index_constituents.return_value = ["AAPL"]
    dec = SlickchartsHoldingsMarket(base)
    assert dec.get_current_price("AAPL") == 123.0
    assert dec.get_index_constituents("^GSPC") == ["AAPL"]
    dec.get_price_history("AAPL", "1y")
    base.get_price_history.assert_called_once_with("AAPL", "1y")
