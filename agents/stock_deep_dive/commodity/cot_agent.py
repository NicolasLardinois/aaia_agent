from core.domain.events import COTReady
from core.domain.models import COTSnapshot, Signal, SignalStatus
from core.ports.data_provider import COTProvider
from core.ports.event_bus import EventBus
from core.utils.relative import percentile_rank
import asyncio

_DEFAULT = COTSnapshot(
    net_speculative_long=None, net_speculative_pct_oi=None,
    signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)

_HIGH = 80.0
_LOW  = 20.0
_MIN_HISTORY = 2  # mind. 2 Einträge (aktuell + 1 hist.) für sinnvollen Perzentil


def _cot_signal(cot_index: float) -> Signal:
    # konträr: extreme Long-Positionierung der Spekulanten → bearish
    if cot_index >= _HIGH:
        return Signal.BEARISH
    if cot_index <= _LOW:
        return Signal.BULLISH
    return Signal.NEUTRAL


class COTAgent:
    def __init__(self, provider: COTProvider | None, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, commodity: str) -> COTSnapshot:
        if self.provider is None:
            self.bus.publish(COTReady(source="cot_agent", payload={"commodity": commodity}))
            return _DEFAULT
        history = await asyncio.to_thread(self.provider.get_cot_history, commodity, 3)
        if not history or len(history) < _MIN_HISTORY:
            self.bus.publish(COTReady(source="cot_agent", payload={"commodity": commodity}))
            return _DEFAULT

        nets = [float(h["managed_money_net"]) for h in history]
        current = nets[-1]
        cot_index = percentile_rank(current, nets[:-1])
        last = history[-1]
        oi = float(last.get("open_interest") or 0)
        pct_oi = round(current / oi * 100, 2) if oi else None

        result = COTSnapshot(
            net_speculative_long=round(current, 1),
            net_speculative_pct_oi=pct_oi,
            signal=_cot_signal(cot_index),
            status=SignalStatus.AVAILABLE,
        )
        self.bus.publish(COTReady(source="cot_agent", payload={"commodity": commodity}))
        return result

    @staticmethod
    def default() -> COTSnapshot:
        return _DEFAULT
