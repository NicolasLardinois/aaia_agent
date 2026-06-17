import asyncio
import statistics as _stats
from datetime import datetime, timezone

from core.domain.events import SeasonalityReady
from core.domain.models import SeasonalitySnapshot, Signal, SignalStatus
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = SeasonalitySnapshot(
    current_month_bias="neutral", avg_return_this_month=None, positive_years_pct=None,
    signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)

_MIN_N = 15          # mind. 15 Jahresbeobachtungen für den Monat
_T_CRITICAL = 2.0    # ~95 % zweiseitig bei df>30; konservativ


def _t_stat(returns: list[float]) -> float:
    n = len(returns)
    if n < 2:
        return 0.0
    mean = _stats.fmean(returns)
    try:
        sd = _stats.stdev(returns)  # Stichproben-Std (n-1) für t-Test korrekt
    except _stats.StatisticsError:
        return 0.0
    if sd == 0:
        # Alle Werte identisch: kein Rauschen → mean-Vorzeichen entscheidet (t → ±∞)
        return float("inf") if mean > 0 else (float("-inf") if mean < 0 else 0.0)
    return mean / (sd / (n ** 0.5))


def _significant(returns: list[float]) -> bool:
    return len(returns) >= _MIN_N and abs(_t_stat(returns)) >= _T_CRITICAL


def _signal(returns: list[float]) -> Signal:
    if not _significant(returns):
        return Signal.NEUTRAL
    median = _stats.median(returns)
    if median > 0:
        return Signal.BULLISH
    if median < 0:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _bias(median: float | None) -> str:
    if median is None:
        return "neutral"
    return "bullish" if median > 1.0 else ("bearish" if median < -1.0 else "neutral")


class SeasonalityAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus = bus

    async def run(self, ticker: str) -> SeasonalitySnapshot:
        hist = await asyncio.to_thread(self.market.get_price_history, ticker, "20y")
        if hist is None or "Close" not in getattr(hist, "columns", []):
            self.bus.publish(SeasonalityReady(source="seasonality_agent", payload={"ticker": ticker}))
            return _DEFAULT

        close = hist["Close"].dropna()  # nominal; reale CPI-Deflation als Folge-Task
        try:
            monthly = close.resample("ME").last()
        except TypeError:
            # Index ist kein DatetimeIndex → keine Saisonalitätsberechnung möglich
            self.bus.publish(SeasonalityReady(source="seasonality_agent", payload={"ticker": ticker}))
            return _DEFAULT
        monthly_returns = monthly.pct_change().dropna() * 100
        current_month = datetime.now(timezone.utc).month
        same_month = monthly_returns[monthly_returns.index.month == current_month]
        returns = [float(x) for x in same_month]

        if len(returns) < _MIN_N:
            self.bus.publish(SeasonalityReady(source="seasonality_agent", payload={"ticker": ticker}))
            return _DEFAULT

        median = round(_stats.median(returns), 2)
        pos_pct = round(sum(1 for r in returns if r > 0) / len(returns) * 100, 1)
        result = SeasonalitySnapshot(
            current_month_bias=_bias(median),
            avg_return_this_month=median,   # Median statt arithm. Mittel
            positive_years_pct=pos_pct,
            signal=_signal(returns),
            status=SignalStatus.AVAILABLE,
        )
        self.bus.publish(SeasonalityReady(source="seasonality_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> SeasonalitySnapshot:
        return _DEFAULT
