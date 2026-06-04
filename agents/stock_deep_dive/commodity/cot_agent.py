import asyncio

from core.domain.events import COTReady
from core.domain.models import COTSnapshot, Signal
from core.ports.event_bus import EventBus

_DEFAULT = COTSnapshot(
    net_speculative_long=None, net_speculative_pct_oi=None, signal=Signal.NEUTRAL,
)

# TODO: CFTC Commitment of Traders Report implementieren.
# Quelle: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
# Format: CSV wöchentlich (dienstags, veröffentlicht freitags)
# Signallogik: KONTRÄR — Spekulanten liegen am Extrempunkt oft falsch.


def _signal(pct_oi: float | None) -> Signal:
    if pct_oi is None:
        return Signal.NEUTRAL
    if pct_oi < -20:
        return Signal.BULLISH    # extreme Netto-Short → konträr bullish
    if pct_oi > 50:
        return Signal.BEARISH    # extreme Netto-Long → konträr bearish
    return Signal.NEUTRAL


class COTAgent:
    def __init__(self, bus: EventBus):
        self.bus = bus

    async def run(self, commodity: str) -> COTSnapshot:
        self.bus.publish(COTReady(source="cot_agent", payload={"commodity": commodity}))
        return _DEFAULT

    @staticmethod
    def default() -> COTSnapshot:
        return _DEFAULT
