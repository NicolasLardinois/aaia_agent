import asyncio

from core.domain.events import EarningsTrendReady
from core.domain.models import EarningsTrendSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus
from core.utils.scoring import standardized_unexpected_earnings

_DEFAULT = EarningsTrendSnapshot(beat_rate=None, estimate_revision="flat", signal=Signal.NEUTRAL)

# SUE-Schwelle für „signifikante" Überraschung (in Std-Einheiten).
_SUE_STRONG = 1.0


def _signal(sue: float | None, revision_label: str) -> Signal:
    """Gewichtetes Scoring: SUE (Magnitude) + Revisions-Momentum, kein ODER-Veto.
    Revisionen werden höher gewichtet als die rohe Surprise (PEAD-Literatur)."""
    score = 0.0

    if sue is not None:
        if sue > _SUE_STRONG:
            score += 1.0
        elif sue < -_SUE_STRONG:
            score -= 1.0

    # Revisions-Momentum stärker gewichtet (1.5) als SUE — aber additiv, kein Veto
    if revision_label == "up":
        score += 1.5
    elif revision_label == "down":
        score -= 1.5

    if score >= 1.0:
        return Signal.BULLISH
    if score <= -1.0:
        return Signal.BEARISH
    return Signal.NEUTRAL


class EarningsTrendAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> EarningsTrendSnapshot:
        history = await asyncio.to_thread(self.provider.get_earnings_history, ticker)
        if not history:
            self.bus.publish(EarningsTrendReady(source="earnings_trend_agent", payload={"ticker": ticker}))
            return _DEFAULT

        # Beat-Rate weiterhin als deskriptive Kennzahl im Snapshot (nicht mehr signal-tragend)
        beats = sum(1 for q in history if q.get("beat") is True)
        beat_rate = beats / len(history)

        sue = standardized_unexpected_earnings(history)

        revisions = [q.get("revision", 0) for q in history[-3:]]
        avg_rev = sum(revisions) / len(revisions) if revisions else 0
        revision_label = "up" if avg_rev > 0 else ("down" if avg_rev < 0 else "flat")

        result = EarningsTrendSnapshot(
            beat_rate=beat_rate,
            estimate_revision=revision_label,
            signal=_signal(sue, revision_label),
        )
        self.bus.publish(EarningsTrendReady(source="earnings_trend_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> EarningsTrendSnapshot:
        return _DEFAULT
