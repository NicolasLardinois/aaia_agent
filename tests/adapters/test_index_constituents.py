"""TDD: Index-Konstituenten + Kurshistorien (ConstituentMarketProvider)."""
from unittest.mock import MagicMock, patch

import pandas as pd

from adapters.data.index_constituents import (
    ConstituentMarketProvider,
    _parse_slickcharts_symbols,
    _PATH,
)

_GET = "adapters.data.index_constituents.requests.get"
_DL = "adapters.data.index_constituents._download_closes"

_HTML = """
<table>
<tr><th>#</th><th>Company</th><th>Symbol</th><th>Weight</th><th>Price</th></tr>
<tr><td>1</td><td><a>NVIDIA Corp</a></td><td><a href="/symbol/NVDA">NVDA</a></td><td>7.07%</td><td>195.61</td></tr>
<tr><td>2</td><td><a>Apple Inc</a></td><td><a href="/symbol/AAPL">AAPL</a></td><td>6.02%</td><td>274.61</td></tr>
<tr><td>3</td><td><a>Berkshire</a></td><td><a href="/symbol/BRK.B">BRK.B</a></td><td>1.50%</td><td>500.00</td></tr>
</table>
"""


def _resp(text):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


# ── _parse_slickcharts_symbols (rein) ───────────────────────────────────────
def test_parse_symbols():
    assert _parse_slickcharts_symbols(_HTML) == ["NVDA", "AAPL", "BRK.B"]


def test_parse_symbols_leer():
    assert _parse_slickcharts_symbols("<html>nichts</html>") == []


# ── Mapping ─────────────────────────────────────────────────────────────────
def test_mapping():
    assert _PATH["^GSPC"] == "sp500"
    assert _PATH["^NDX"] == "nasdaq100"


# ── get_index_constituents ──────────────────────────────────────────────────
def test_get_index_constituents_sp500():
    base = MagicMock()
    with patch(_GET, return_value=_resp(_HTML)) as m:
        out = ConstituentMarketProvider(base).get_index_constituents("^GSPC")
    assert out == ["NVDA", "AAPL", "BRK.B"]
    assert "sp500" in m.call_args.args[0]


def test_get_index_constituents_unbekannt_delegiert_an_base():
    base = MagicMock()
    base.get_index_constituents.return_value = ["X"]
    with patch(_GET) as m:
        out = ConstituentMarketProvider(base).get_index_constituents("AAPL")
    assert out == ["X"]
    m.assert_not_called()


# ── get_constituent_histories ───────────────────────────────────────────────
def test_get_constituent_histories_baut_dict():
    base = MagicMock()
    closes = {"NVDA": pd.Series([1.0, 2.0]), "AAPL": pd.Series([3.0, 4.0])}
    prov = ConstituentMarketProvider(base)
    with patch.object(prov, "get_index_constituents", return_value=["NVDA", "AAPL"]), \
         patch(_DL, return_value=closes) as dl:
        out = prov.get_constituent_histories("^GSPC", "2y")
    assert set(out) == {"NVDA", "AAPL"}
    dl.assert_called_once_with(["NVDA", "AAPL"], "2y")


def test_get_constituent_histories_ohne_konstituenten_leer():
    base = MagicMock()
    prov = ConstituentMarketProvider(base)
    with patch.object(prov, "get_index_constituents", return_value=[]):
        assert prov.get_constituent_histories("XYZ", "2y") == {}


# ── Delegation ──────────────────────────────────────────────────────────────
def test_delegiert_uebrige_methoden():
    base = MagicMock()
    base.get_current_price.return_value = 9.0
    dec = ConstituentMarketProvider(base)
    assert dec.get_current_price("AAPL") == 9.0
    dec.get_info("AAPL")
    base.get_info.assert_called_once_with("AAPL")
