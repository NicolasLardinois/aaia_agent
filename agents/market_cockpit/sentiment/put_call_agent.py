import asyncio
from datetime import date, timedelta

import requests

from core.domain.events import PutCallDataReady
from core.domain.models import PutCallSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.relative import zscore_vs_history

_DEFAULT = PutCallSnapshot(ratio=None, signal=Signal.NEUTRAL)
_CBOE_BASE = "https://cdn.cboe.com/data/us/options/market_statistics/daily"


def _fetch_cboe_put_call() -> float | None:
    # CBOE veröffentlicht täglich eine CSV mit der TOTAL PUT/CALL-Spalte.
    # Wir versuchen bis zu 5 Tage zurück um Wochenenden/Feiertage abzudecken.
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
            # Strikt auf "TOTAL ... PUT/CALL" Spalte beschränken (konsistente Serie)
            idx = next(
                (i for i, h in enumerate(headers) if "TOTAL" in h and "PUT/CALL" in h),
                None,
            )
            if idx is None:
                return None
            values = lines[-1].split(',')
            if idx >= len(values):
                return None
            return round(float(values[idx].strip()), 2)
        except Exception:
            continue
    return None


def _fetch_cboe_put_call_history(n_days: int = 90) -> list[float]:
    """Holt bis zu n_days tägliche CBOE-Total-P/C-Werte für die z-Score-Berechnung."""
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
            lines = resp.text.strip().split('\n')
            if len(lines) < 2:
                continue
            headers = [h.strip().upper() for h in lines[0].split(',')]
            idx = next(
                (i for i, h in enumerate(headers) if "TOTAL" in h and "PUT/CALL" in h),
                None,
            )
            if idx is None:
                continue
            values = lines[-1].split(',')
            if idx >= len(values):
                continue
            history.append(round(float(values[idx].strip()), 2))
        except Exception:
            continue
    return history


_Z = 1.0


def _signal(ratio_z: float | None) -> Signal:
    """
    Contrarian, relativ kalibriert: hohes P/C relativ zum rollierenden Mittel
    (z > +1) = Pessimismus → BULLISH; niedriges (z < -1) = Sorglosigkeit → BEARISH.
    Feste CBOE-Total-P/C-Serie; z-Score statt fixer 1.2/0.7 (säkularer Drift).
    """
    if ratio_z is None:
        return Signal.NEUTRAL
    if ratio_z > _Z:
        return Signal.BULLISH
    if ratio_z < -_Z:
        return Signal.BEARISH
    return Signal.NEUTRAL


class PutCallAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> PutCallSnapshot:
        ratio, history = await asyncio.gather(
            asyncio.to_thread(_fetch_cboe_put_call),
            asyncio.to_thread(_fetch_cboe_put_call_history),
            return_exceptions=True,
        )
        if isinstance(ratio, Exception):
            ratio = None
        if isinstance(history, Exception):
            history = []

        # z-Score gegen rollierende Historie; None wenn < min_n (→ NEUTRAL)
        ratio_z = zscore_vs_history(ratio, history) if ratio is not None and history else None

        result = PutCallSnapshot(ratio=ratio, signal=_signal(ratio_z))
        self.bus.publish(PutCallDataReady(source="put_call_agent", payload={"ratio": ratio}))
        return result

    @staticmethod
    def default() -> PutCallSnapshot:
        return _DEFAULT
