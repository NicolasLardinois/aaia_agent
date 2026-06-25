"""
Shiller-CAPE (zyklisch bereinigtes KGV) des S&P 500 via multpl.com.

multpl.com publiziert die autoritative Shiller-PE-Reihe (Robert Shillers Methodik:
Preis / 10-Jahres-Durchschnitt der inflationsbereinigten Gewinne) keyless.
Wir holen den aktuellen Wert direkt, statt eine 10J-Real-EPS-Reihe selbst zu
rekonstruieren (methodisch fehleranfällig). multpl ist S&P-500-spezifisch → nur für
S&P-500-Ticker; andere Indizes liefern None.
"""
import html as _html
import logging
import re

import requests

from core.ports.data_provider import ShillerCapeProvider

_log = logging.getLogger(__name__)

_URL = "https://www.multpl.com/shiller-pe"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# S&P-500-Ticker/-ETFs, für die multpl gilt
_SP500 = {"^GSPC", "^SP500TR", "SPY", "IVV", "VOO", "SPX"}

_CAPE_RE = re.compile(r"Current Shiller PE Ratio\s*:?\s*([0-9]+\.[0-9]+)")

# Plausibilität: CAPE historisch ~5..45; großzügiger Garbage-Filter
_CAP = (1.0, 100.0)


def _parse_multpl_cape(page: str) -> float | None:
    """Rein: aktuelle Shiller-CAPE aus dem multpl-HTML. None bei fehlendem/implausiblem Wert."""
    text = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", page)))
    m = _CAPE_RE.search(text)
    if not m:
        return None
    val = float(m.group(1))
    if not (_CAP[0] <= val <= _CAP[1]):
        return None
    return round(val, 2)


class MultplShillerProvider(ShillerCapeProvider):
    """Aktuelle S&P-500-Shiller-CAPE von multpl.com."""

    def get_shiller_cape(self, ticker: str) -> float | None:
        if ticker.upper() not in _SP500:
            return None   # multpl ist S&P-500-spezifisch
        try:
            resp = requests.get(_URL, headers={"User-Agent": _UA}, timeout=15)
            resp.raise_for_status()
            return _parse_multpl_cape(resp.text)
        except Exception as exc:
            _log.warning("multpl Shiller-CAPE für %s nicht abrufbar (%s) — None", ticker, exc)
            return None
