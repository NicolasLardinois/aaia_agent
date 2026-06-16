import asyncio
from core.domain.events import BondCreditReady
from core.domain.models import BondCreditSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus
from core.utils.credit import (
    default_probability, is_investment_grade, credit_triangle_spread,
)

_DEFAULT = BondCreditSnapshot(
    moodys=None, sp=None, fitch=None,
    category="investment_grade", trend="stable",
    default_probability=None, signal=Signal.NEUTRAL,
)


def _category(rating: str | None) -> str:
    if rating is None:
        return "unrated"
    return "investment_grade" if is_investment_grade(rating) else "high_yield"


def _default_prob(rating: str | None) -> float | None:
    return default_probability(rating)  # Dezimal, exakter Lookup


def _signal(trend: str) -> Signal:
    if trend == "upgrade":
        return Signal.BULLISH
    if trend == "downgrade":
        return Signal.BEARISH
    return Signal.NEUTRAL


class BondCreditAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> BondCreditSnapshot:
        data = await asyncio.to_thread(self.provider.get_bond_data, ticker)
        if isinstance(data, Exception):
            data = {}

        sp = data.get("rating_sp")
        moodys = data.get("rating_moodys")
        fitch = data.get("rating_fitch")
        trend = data.get("rating_trend", "stable")

        # PD aus DEMSELBEN primären Rating wie die Kategorie ableiten
        primary = sp or moodys or fitch
        pd = _default_prob(primary)

        # Credit Triangle: erwarteter Spread aus PD und LGD (Dezimal)
        recovery = data.get("recovery_rate", 0.40)
        lgd = 1.0 - recovery
        tri_spread = credit_triangle_spread(pd, lgd) if pd is not None else None

        result = BondCreditSnapshot(
            moodys=moodys, sp=sp, fitch=fitch,
            category=_category(primary),
            trend=trend,
            default_probability=pd,
            signal=_signal(trend),
        )
        self.bus.publish(BondCreditReady(source="bond_credit_agent", payload={
            "ticker": ticker, "sp": sp, "trend": trend,
            "pd": pd, "triangle_spread_bps": round(tri_spread * 10000, 1) if tri_spread is not None else None,
        }))
        return result

    @staticmethod
    def default() -> BondCreditSnapshot:
        return _DEFAULT
