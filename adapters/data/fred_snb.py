"""Schweizer Zinskurven-Spreads via FRED OECD-Serien."""
from fredapi import Fred


class FredSnbProvider:
    """Schweizer Zinskurven-Spreads via FRED OECD-Serien."""

    def __init__(self, api_key: str):
        self.fred = Fred(api_key=api_key)

    def get_yield_spreads(self) -> dict[str, float | None]:
        """Gibt Zinskurven-Spreads für die Schweiz zurück.

        Returns:
            {"10y3m": float | None}
            10y3m = 10-Jahres minus 3-Monats Spread
        """
        rate_10y = self._fetch_series("IRLTLT01CHM156N")
        rate_3m = self._fetch_series("IR3TIB01CHM156N")

        if rate_10y is None or rate_3m is None:
            spread = None
        else:
            spread = round(rate_10y - rate_3m, 3)

        return {"10y3m": spread}

    def _fetch_series(self, series_id: str) -> float | None:
        """Fetcht letzte Beobachtung einer FRED-Serie. Bei Fehler → None."""
        try:
            series = self.fred.get_series(series_id, observation_start="2020-01-01")
            return float(series.dropna().iloc[-1])
        except Exception:
            return None
