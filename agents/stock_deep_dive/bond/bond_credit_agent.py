import asyncio
from core.domain.events import BondCreditReady
from core.domain.models import BondCreditSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = BondCreditSnapshot(
    moodys=None, sp=None, fitch=None,
    category="investment_grade", trend="stable",
    default_probability=None, signal=Signal.NEUTRAL,
)

# Historische Ausfallraten je Rating-Klasse (Moody's, 1-Jahres-Horizont)
DEFAULT_RATES: dict[str, float] = {
    "Aaa": 0.0, "Aa": 0.01, "A": 0.02, "Baa": 0.18,
    "Ba": 1.2, "B": 4.3, "Caa": 14.0, "Ca": 30.0, "C": 50.0,
}

IG_RATINGS  = {"AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-",
               "Aaa", "Aa1", "Aa2", "Aa3", "A1", "A2", "A3", "Baa1", "Baa2", "Baa3"}
HY_RATINGS  = {"BB+", "BB", "BB-", "B+", "B", "B-",
               "Ba1", "Ba2", "Ba3", "B1", "B2", "B3"}
JUNK_RATINGS = {"CCC+", "CCC", "CCC-", "CC", "C", "D",
                "Caa1", "Caa2", "Caa3", "Ca", "C"}


def _category(rating: str | None) -> str:
    if rating is None:
        return "investment_grade"
    if rating in IG_RATINGS:
        return "investment_grade"
    if rating in HY_RATINGS:
        return "high_yield"
    return "junk"


def _default_prob(rating: str | None) -> float | None:
    if rating is None:
        return None
    for prefix, rate in DEFAULT_RATES.items():
        if rating.startswith(prefix[:2]):
            return rate
    return None


def _signal(trend: str) -> Signal:
    if trend == "upgrade":
        return Signal.BULLISH
    if trend == "downgrade":
        return Signal.BEARISH
    return Signal.NEUTRAL


class BondCreditAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self, ticker: str) -> BondCreditSnapshot:
        data = await asyncio.to_thread(self.provider.get_bond_data, ticker)
        if isinstance(data, Exception):
            data = {}

        moodys = data.get("rating_moodys")
        sp     = data.get("rating_sp")
        fitch  = data.get("rating_fitch")
        trend  = data.get("rating_trend", "stable")

        primary = sp or moodys or fitch
        result = BondCreditSnapshot(
            moodys=moodys, sp=sp, fitch=fitch,
            category=_category(primary),
            trend=trend,
            default_probability=_default_prob(moodys),
            signal=_signal(trend),
        )
        self.bus.publish(BondCreditReady(source="bond_credit_agent", payload={
            "ticker": ticker, "sp": sp, "trend": trend,
        }))
        return result

    @staticmethod
    def default() -> BondCreditSnapshot:
        return _DEFAULT
