"""CBOE-Adapter für die Total-Put/Call-Tagesreihe (Sentiment).

Kapselt das blockierende `requests`-I/O, das früher direkt im Agenten stand
(`_fetch_cboe_put_call` / `_fetch_cboe_put_call_history`). CBOE veröffentlicht
täglich eine CSV mit der Spalte "TOTAL … PUT/CALL". Defensiver Vertrag
(AGENTS.md §2/§3): ein fehlgeschlagener Tag wird übersprungen, ein komplett
blockierter Abruf liefert `None` (aktuell) bzw. `[]` (Historie).
"""
from datetime import date, timedelta

import requests

from core.ports.put_call_source import PutCallSource

_CBOE_BASE = "https://cdn.cboe.com/data/us/options/market_statistics/daily"


def _total_put_call_from_csv(text: str) -> float | None:
    """Liest die TOTAL-PUT/CALL-Spalte aus dem CBOE-Tages-CSV (strikt: nur die
    Spalte, deren Header sowohl 'TOTAL' als auch 'PUT/CALL' enthält → konsistente Serie)."""
    lines = text.strip().split('\n')
    if len(lines) < 2:
        return None
    headers = [h.strip().upper() for h in lines[0].split(',')]
    idx = next(
        (i for i, h in enumerate(headers) if "TOTAL" in h and "PUT/CALL" in h),
        None,
    )
    if idx is None:
        return None
    values = lines[-1].split(',')
    if idx >= len(values):
        return None
    try:
        return round(float(values[idx].strip()), 2)
    except ValueError:
        return None


class CboePutCallProvider(PutCallSource):
    def get_latest(self) -> float | None:
        # Bis zu 5 Tage zurück, um Wochenenden/Feiertage abzudecken.
        for days_back in range(5):
            d = date.today() - timedelta(days=days_back)
            url = f"{_CBOE_BASE}/daily_OPTIONS_{d.strftime('%Y%m%d')}.csv"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                val = _total_put_call_from_csv(resp.text)
                if val is not None:
                    return val
            except Exception:
                continue
        return None

    def get_history(self, n_days: int = 90) -> list[float]:
        history: list[float] = []
        for days_back in range(1, n_days + 5):
            if len(history) >= n_days:
                break
            d = date.today() - timedelta(days=days_back)
            url = f"{_CBOE_BASE}/daily_OPTIONS_{d.strftime('%Y%m%d')}.csv"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                val = _total_put_call_from_csv(resp.text)
                if val is not None:
                    history.append(val)
            except Exception:
                continue
        return history
