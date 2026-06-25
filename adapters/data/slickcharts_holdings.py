"""
Index-Holdings (Gewichtungen) via slickcharts.com.

MarketDataProvider-Decorator: ergänzt get_index_holdings mit echten Index-Gewichtungen
(S&P 500, Nasdaq-100, Dow Jones); alle übrigen Methoden werden an den Basis-Provider
(z. B. YahooFinanceProvider) delegiert.

Quelle slickcharts ist keyless und liefert Name + Gewichtung je Mitglied. Eine
Sektor-Zuordnung liefert sie NICHT → sector=None (der Agent meldet dann keinen
Top-Sektor). Die für das Konzentrations-Signal relevanten Größen (Top-Holding,
Top-10-Konzentration, HHI) sind vollständig.

Hinweis: ETF-Emittenten-Quellen (iShares-CSV, SPDR-XLSX) blocken Bot-Requests; die
FMP-Holdings-Endpunkte sind Legacy/kostenpflichtig — slickcharts ist die robuste,
freie Alternative für die großen US-Indizes.
"""
import html as _html
import logging
import re

import requests

from core.ports.data_provider import MarketDataProvider

_log = logging.getLogger(__name__)

_BASE = "https://www.slickcharts.com/{path}"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Index-/ETF-Ticker → slickcharts-Pfad (die Indizes, die slickcharts führt)
_PATH: dict[str, str] = {
    "^GSPC": "sp500",  "SPY": "sp500",  "IVV": "sp500", "VOO": "sp500",
    "^NDX":  "nasdaq100", "QQQ": "nasdaq100",
    "^DJI":  "dowjones",  "DIA": "dowjones",
}

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def _text(cell: str) -> str:
    return _html.unescape(re.sub(r"<.*?>", "", cell)).strip()


def _parse_slickcharts(page: str) -> list[dict]:
    """Rein: slickcharts-HTML → [{"name","weight_pct","sector":None}], absteigend nach Gewicht.
    Spalten je Zeile: [#, Company, Symbol, Weight%, Price]. Nicht-parsebare Zeilen
    (z. B. Kopfzeile) werden übersprungen."""
    out: list[dict] = []
    for row in _ROW.findall(page):
        cells = [_text(c) for c in _CELL.findall(row)]
        if len(cells) < 4:
            continue
        name = cells[1]
        try:
            weight = float(cells[3].replace("%", "").strip())
        except ValueError:
            continue
        if not name:
            continue
        out.append({"name": name, "weight_pct": weight, "sector": None})
    return out


class SlickchartsHoldingsMarket(MarketDataProvider):
    """Decorator über einen MarketDataProvider: get_index_holdings via slickcharts."""

    def __init__(self, base: MarketDataProvider):
        self._base = base

    # ── echt via slickcharts ────────────────────────────────────────────────
    def get_index_holdings(self, index_ticker: str) -> list:
        path = _PATH.get(index_ticker.upper())
        if path is None:
            return []   # Index nicht bei slickcharts → UNAVAILABLE
        try:
            resp = requests.get(_BASE.format(path=path), headers={"User-Agent": _UA}, timeout=15)
            resp.raise_for_status()
            return _parse_slickcharts(resp.text)
        except Exception as exc:
            _log.warning("slickcharts Holdings für %s nicht abrufbar (%s) — UNAVAILABLE", index_ticker, exc)
            return []

    # ── Delegation an base ──────────────────────────────────────────────────
    def get_current_price(self, ticker: str):
        return self._base.get_current_price(ticker)

    def get_price_history(self, ticker: str, period: str = "1y"):
        return self._base.get_price_history(ticker, period)

    def get_info(self, ticker: str) -> dict:
        return self._base.get_info(ticker)

    def get_index_constituents(self, index_ticker: str) -> list[str]:
        return self._base.get_index_constituents(index_ticker)

    def get_constituent_histories(self, index_ticker: str, period: str = "2y") -> dict:
        return self._base.get_constituent_histories(index_ticker, period)

    def get_index_fundamentals(self, index_ticker: str) -> dict:
        return self._base.get_index_fundamentals(index_ticker)
