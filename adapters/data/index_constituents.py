"""
Index-Konstituenten + deren Kurshistorien für die Marktbreite (Index-Breadth).

MarketDataProvider-Decorator:
- get_index_constituents: Mitglieds-Symbole von slickcharts.com (S&P 500/Nasdaq-100/Dow)
- get_constituent_histories: Tages-Schlusskurse je Mitglied via yfinance (Batch-Download)
übrige Methoden an den Basis-Provider (YahooFinanceProvider) delegiert.

Beides keyless. Hinweis: Der Batch-Download umfasst alle Indexmitglieder (S&P 500 ≈ 500
Ticker) — das ist bewusst vollständig (gleichgewichtete Marktbreite) und entsprechend
latenzintensiv; Teilausfälle einzelner Ticker degradieren sauber (der Breadth-Agent
überspringt Reihen < 200 Punkten).
"""
import html as _html
import logging
import re

import requests
import yfinance as yf

from core.ports.data_provider import MarketDataProvider

_log = logging.getLogger(__name__)

_BASE = "https://www.slickcharts.com/{path}"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_PATH: dict[str, str] = {
    "^GSPC": "sp500", "SPY": "sp500", "IVV": "sp500", "VOO": "sp500",
    "^NDX": "nasdaq100", "QQQ": "nasdaq100",
    "^DJI": "dowjones", "DIA": "dowjones",
}

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def _text(cell: str) -> str:
    return _html.unescape(re.sub(r"<.*?>", "", cell)).strip()


def _parse_slickcharts_symbols(page: str) -> list[str]:
    """Rein: slickcharts-HTML → Liste der Mitglieds-Symbole (Spalte 3: Symbol)."""
    out: list[str] = []
    for row in _ROW.findall(page):
        cells = [_text(c) for c in _CELL.findall(row)]
        if len(cells) < 3:
            continue
        sym = cells[2]
        if sym:
            out.append(sym)
    return out


def _download_closes(symbols: list[str], period: str) -> dict:
    """Tages-Schlusskurse je Symbol via yfinance-Batch. Teilausfälle werden übersprungen."""
    data = yf.download(symbols, period=period, progress=False,
                       group_by="ticker", threads=True, auto_adjust=True)
    out: dict = {}
    for sym in symbols:
        try:
            close = data[sym]["Close"].dropna()
        except Exception:
            continue
        if len(close):
            out[sym] = close
    return out


class ConstituentMarketProvider(MarketDataProvider):
    """Decorator: ergänzt Konstituenten + Kurshistorien für die Marktbreite."""

    def __init__(self, base: MarketDataProvider):
        self._base = base

    def get_index_constituents(self, index_ticker: str) -> list[str]:
        path = _PATH.get(index_ticker.upper())
        if path is None:
            return self._base.get_index_constituents(index_ticker)
        try:
            resp = requests.get(_BASE.format(path=path), headers={"User-Agent": _UA}, timeout=15)
            resp.raise_for_status()
            return _parse_slickcharts_symbols(resp.text)
        except Exception as exc:
            _log.warning("slickcharts Konstituenten für %s nicht abrufbar (%s)", index_ticker, exc)
            return []

    def get_constituent_histories(self, index_ticker: str, period: str = "2y") -> dict:
        symbols = self.get_index_constituents(index_ticker)
        if not symbols:
            return {}
        try:
            return _download_closes(symbols, period)
        except Exception as exc:
            _log.warning("Konstituenten-Historien für %s nicht abrufbar (%s)", index_ticker, exc)
            return {}

    # ── Delegation an base ──────────────────────────────────────────────────
    def get_current_price(self, ticker: str):
        return self._base.get_current_price(ticker)

    def get_price_history(self, ticker: str, period: str = "1y"):
        return self._base.get_price_history(ticker, period)

    def get_info(self, ticker: str) -> dict:
        return self._base.get_info(ticker)

    def get_index_fundamentals(self, index_ticker: str) -> dict:
        return self._base.get_index_fundamentals(index_ticker)

    def get_index_holdings(self, index_ticker: str) -> list:
        return self._base.get_index_holdings(index_ticker)
