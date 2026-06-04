import asyncio
from datetime import datetime

from core.domain.events import SeasonalityReady
from core.domain.models import SeasonalitySnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = SeasonalitySnapshot(
    current_month_bias="neutral",
    avg_return_this_month=None,
    positive_years_pct=None,
    signal=Signal.NEUTRAL,
)


def _signal(avg_return: float | None, pos_pct: float | None) -> Signal:
    if avg_return is None:
        return Signal.NEUTRAL
    if avg_return > 2.0 and (pos_pct is None or pos_pct > 60):
        return Signal.BULLISH
    if avg_return < -2.0 and (pos_pct is None or pos_pct < 40):
        return Signal.BEARISH
    return Signal.NEUTRAL


def _bias(avg: float | None) -> str:
    if avg is None:
        return "neutral"
    return "bullish" if avg > 1.0 else ("bearish" if avg < -1.0 else "neutral")


class SeasonalityAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> SeasonalitySnapshot:
        try:
            hist = await asyncio.to_thread(self.market.get_price_history, ticker, "10y")
            if isinstance(hist, Exception) or hist is None:
                return _DEFAULT

            close = hist["Close"]
            current_month = datetime.utcnow().month

            monthly = close.resample("ME").last()
            monthly_returns = monthly.pct_change().dropna() * 100

            same_month = monthly_returns[monthly_returns.index.month == current_month]
            if len(same_month) < 3:
                return _DEFAULT

            avg_ret  = round(float(same_month.mean()), 2)
            pos_pct  = round(float((same_month > 0).sum() / len(same_month) * 100), 1)

            result = SeasonalitySnapshot(
                current_month_bias=_bias(avg_ret),
                avg_return_this_month=avg_ret,
                positive_years_pct=pos_pct,
                signal=_signal(avg_ret, pos_pct),
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(SeasonalityReady(source="seasonality_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> SeasonalitySnapshot:
        return _DEFAULT
