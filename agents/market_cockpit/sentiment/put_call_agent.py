import asyncio
from datetime import date, timedelta

import requests

from core.domain.events import PutCallDataReady
from core.domain.models import PutCallSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.dated_history import DatedHistoryPort
from core.ports.event_bus import EventBus
from core.utils.relative import zscore_vs_history

_DEFAULT = PutCallSnapshot(ratio=None, signal=Signal.NEUTRAL)
_CBOE_BASE = "https://cdn.cboe.com/data/us/options/market_statistics/daily"

# Serien-Schlüssel der persistenten Tagesreihe (eine Reihe pro Indikator/Region).
_SERIES = "usa_put_call"
# Mindestlänge der Vergangenheits-Reihe für einen belastbaren z-Score
# (= zscore_vs_history min_n). Darunter: Warm-up → einmaliges Netz-Seeding,
# damit in der Aufbauphase kein Signal-Regress entsteht.
_MIN_HISTORY = 20


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
    def __init__(self, provider: MarketDataProvider, bus: EventBus,
                 history: DatedHistoryPort | None = None):
        self.provider = provider
        self.bus      = bus
        # Persistente Tagesreihe (Datei/DB). Ohne sie (None) bleibt der Altpfad
        # erhalten: die Historie wird wie bisher pro Lauf neu aus dem Netz gezogen.
        self.history  = history

    async def run(self) -> PutCallSnapshot:
        ratio = await asyncio.to_thread(_fetch_cboe_put_call)
        if isinstance(ratio, Exception):
            ratio = None

        history = await self._history_values(ratio)

        # z-Score gegen rollierende Historie; None wenn < min_n (→ NEUTRAL)
        ratio_z = zscore_vs_history(ratio, history) if ratio is not None and history else None

        result = PutCallSnapshot(ratio=ratio, signal=_signal(ratio_z))
        self.bus.publish(PutCallDataReady(source="put_call_agent", payload={"ratio": ratio}))
        return result

    async def _history_values(self, ratio: float | None) -> list[float]:
        """Liefert die Vergangenheits-Reihe (heutiger Tag ausgeschlossen) für den z-Score.

        Mit persistenter Historie wird der heutige Wert protokolliert und die
        gespeicherte Reihe gelesen — das ersetzt das I/O-intensive Tages-Refetch
        (bisher N Einzelabrufe pro Lauf). Solange die persistente Reihe noch kürzer
        als `_MIN_HISTORY` ist, wird einmalig per Netz geseedet (Warm-up, kein
        Signal-Regress). Ohne persistente Historie (None) bleibt der Altpfad aktiv.
        """
        if self.history is None:
            seed = await asyncio.to_thread(_fetch_cboe_put_call_history)
            return [] if isinstance(seed, Exception) else seed

        def _io() -> list[float]:
            today = date.today()
            # Vergangenheitswerte (heute ausgeschlossen): der z-Score vergleicht den
            # heutigen Wert GEGEN die Vergangenheit, nicht gegen sich selbst.
            past = [v for d, v in self.history.values(_SERIES) if d != today]
            if ratio is not None:
                self.history.append(_SERIES, today, ratio)  # für künftige Läufe protokollieren
            return past

        past = await asyncio.to_thread(_io)
        if len(past) >= _MIN_HISTORY:
            return past  # genug persistente Historie → kein Netz-I/O mehr (Steady State)
        # Warm-up: persistente Reihe noch zu kurz → einmalig per Netz seeden.
        seed = await asyncio.to_thread(_fetch_cboe_put_call_history)
        return [] if isinstance(seed, Exception) else seed

    @staticmethod
    def default() -> PutCallSnapshot:
        return _DEFAULT
