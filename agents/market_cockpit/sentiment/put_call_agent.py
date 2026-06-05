import asyncio
from datetime import date, timedelta

import requests

from core.domain.events import PutCallDataReady
from core.domain.models import PutCallSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = PutCallSnapshot(ratio=None, signal=Signal.NEUTRAL)
_CBOE_BASE = "https://cdn.cboe.com/data/us/options/market_statistics/daily"


def _fetch_cboe_put_call() -> float | None:
    # CBOE veröffentlicht täglich eine CSV. Wir versuchen bis zu 5 Tage zurück
    # um Wochenenden und Feiertage abzudecken.
    for days_back in range(5):
        d = date.today() - timedelta(days=days_back)
        url = f"{_CBOE_BASE}/daily_OPTIONS_{d.strftime('%Y%m%d')}.csv"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                continue
            lines = resp.text.strip().split('\n')
            if len(lines) < 2:
                continue
            headers = [h.strip().upper() for h in lines[0].split(',')]
            # Suche nach "TOTAL ... PUT/CALL" Spalte, Fallback auf erste PUT/CALL-Spalte
            idx = next(
                (i for i, h in enumerate(headers) if "TOTAL" in h and "PUT/CALL" in h),
                None,
            )
            if idx is None:
                idx = next((i for i, h in enumerate(headers) if "PUT/CALL" in h), None)
            if idx is None:
                return None
            values = lines[-1].split(',')
            if idx >= len(values):
                return None
            return round(float(values[idx].strip()), 2)
        except Exception:
            continue
    return None


def _signal(ratio: float | None) -> Signal:
    if ratio is None:
        return Signal.NEUTRAL
    # Contrarian: hohes Ratio = viele Puts = Markt zu pessimistisch → BULLISH
    if ratio > 1.2:
        return Signal.BULLISH
    if ratio < 0.7:
        return Signal.BEARISH
    return Signal.NEUTRAL


class PutCallAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> PutCallSnapshot:
        ratio = await asyncio.to_thread(_fetch_cboe_put_call)

        result = PutCallSnapshot(ratio=ratio, signal=_signal(ratio))
        self.bus.publish(PutCallDataReady(source="put_call_agent", payload={"ratio": ratio}))
        return result

    @staticmethod
    def default() -> PutCallSnapshot:
        return _DEFAULT
