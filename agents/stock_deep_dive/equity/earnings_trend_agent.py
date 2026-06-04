import asyncio

from core.domain.events import EarningsTrendReady
from core.domain.models import EarningsTrendSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = EarningsTrendSnapshot(beat_rate=None, estimate_revision="flat", signal=Signal.NEUTRAL)


class EarningsTrendAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> EarningsTrendSnapshot:
        history = await asyncio.to_thread(self.provider.get_earnings_history, ticker)
        if not history:
            self.bus.publish(EarningsTrendReady(source="earnings_trend_agent", payload={"ticker": ticker}))
            return _DEFAULT
        beats = sum(1 for q in history if q.get("beat") is True)
        beat_rate = beats / len(history)
        revisions = [q.get("revision", 0) for q in history[-2:]]
        avg_rev = sum(revisions) / len(revisions) if revisions else 0
        revision_label = "up" if avg_rev > 0 else ("down" if avg_rev < 0 else "flat")
        signal = (
            Signal.BULLISH if beat_rate >= 0.75 and revision_label == "up"
            else Signal.BEARISH if beat_rate <= 0.25 or revision_label == "down"
            else Signal.NEUTRAL
        )
        result = EarningsTrendSnapshot(beat_rate=beat_rate, estimate_revision=revision_label, signal=signal)
        self.bus.publish(EarningsTrendReady(source="earnings_trend_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> EarningsTrendSnapshot:
        return _DEFAULT
