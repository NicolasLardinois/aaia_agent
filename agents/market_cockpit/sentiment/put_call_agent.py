import asyncio
from datetime import date

from core.domain.events import PutCallDataReady
from core.domain.models import PutCallSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.dated_history import DatedHistoryPort
from core.ports.event_bus import EventBus
from core.ports.put_call_source import PutCallSource
from core.utils.relative import zscore_vs_history

_DEFAULT = PutCallSnapshot(ratio=None, signal=Signal.NEUTRAL)

# Serien-Schlüssel der persistenten Tagesreihe (eine Reihe pro Indikator/Region).
_SERIES = "usa_put_call"
# Mindestlänge der Vergangenheits-Reihe für einen belastbaren z-Score
# (= zscore_vs_history min_n). Darunter: Warm-up → einmaliges Netz-Seeding,
# damit in der Aufbauphase kein Signal-Regress entsteht.
_MIN_HISTORY = 20


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
                 history: DatedHistoryPort | None = None,
                 source: PutCallSource | None = None):
        self.provider = provider
        self.bus      = bus
        # Persistente Tagesreihe (Datei/DB). Ohne sie (None) bleibt der Altpfad
        # erhalten: die Historie wird wie bisher pro Lauf neu aus dem Netz gezogen.
        self.history  = history
        # CBOE-Datenquelle über injizierten Port (Hexagonal, AGENTS.md §1) statt
        # hardcoded requests. None → kein Netz: ratio None, Seed leer (defensiv).
        self.source   = source

    async def run(self) -> PutCallSnapshot:
        ratio = await self._latest()

        history = await self._history_values(ratio)

        # z-Score gegen rollierende Historie; None wenn < min_n (→ NEUTRAL)
        ratio_z = zscore_vs_history(ratio, history) if ratio is not None and history else None

        result = PutCallSnapshot(ratio=ratio, signal=_signal(ratio_z))
        self.bus.publish(PutCallDataReady(source="put_call_agent", payload={"ratio": ratio}))
        return result

    async def _latest(self) -> float | None:
        """Aktueller Total-Put/Call-Wert über den injizierten Port; ohne Port → None."""
        if self.source is None:
            return None
        return await asyncio.to_thread(self.source.get_latest)

    async def _seed(self) -> list[float]:
        """Netz-Seed der Historie über den Port; ohne Port → leere Liste (kein Netz)."""
        if self.source is None:
            return []
        return await asyncio.to_thread(self.source.get_history)

    async def _history_values(self, ratio: float | None) -> list[float]:
        """Liefert die Vergangenheits-Reihe (heutiger Tag ausgeschlossen) für den z-Score.

        Mit persistenter Historie wird der heutige Wert protokolliert und die
        gespeicherte Reihe gelesen — das ersetzt das I/O-intensive Tages-Refetch
        (bisher N Einzelabrufe pro Lauf). Solange die persistente Reihe noch kürzer
        als `_MIN_HISTORY` ist, wird einmalig per Netz geseedet (Warm-up, kein
        Signal-Regress). Ohne persistente Historie (None) bleibt der Altpfad aktiv.
        """
        if self.history is None:
            return await self._seed()

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
        return await self._seed()

    @staticmethod
    def default() -> PutCallSnapshot:
        return _DEFAULT
