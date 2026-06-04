import asyncio

from core.domain.events import IndexMomentumReady
from core.domain.models import IndexMomentumSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_WORLD_BENCHMARK = "URTH"   # iShares MSCI World ETF

_DEFAULT = IndexMomentumSnapshot(
    rsi_14=None, ma50=None, ma200=None,
    golden_cross=None, relative_strength=None, signal=Signal.NEUTRAL,
)


def _compute_rsi(prices, period: int = 14) -> float | None:
    try:
        delta = prices.diff().dropna()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss.replace(0, float("nan"))
        rsi   = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 2)
    except Exception:
        return None


def _signal(golden_cross: bool | None, rsi: float | None) -> Signal:
    if golden_cross is None:
        return Signal.NEUTRAL
    if golden_cross and (rsi is None or rsi < 70):
        return Signal.BULLISH
    if not golden_cross and (rsi is None or rsi > 30):
        return Signal.BEARISH
    return Signal.NEUTRAL


class IndexMomentumAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> IndexMomentumSnapshot:
        try:
            hist, bench = await asyncio.gather(
                asyncio.to_thread(self.market.get_price_history, ticker, "1y"),
                asyncio.to_thread(self.market.get_price_history, _WORLD_BENCHMARK, "1y"),
                return_exceptions=True,
            )
            if isinstance(hist, Exception):
                return _DEFAULT

            close = hist["Close"]
            ma50  = round(float(close.rolling(50).mean().iloc[-1]), 2)
            ma200 = round(float(close.rolling(200).mean().iloc[-1]), 2)
            rsi   = _compute_rsi(close)
            golden = bool(ma50 > ma200)

            rs = None
            if not isinstance(bench, Exception):
                bc = bench["Close"]
                ticker_ret = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
                bench_ret  = (bc.iloc[-1] - bc.iloc[0]) / bc.iloc[0]
                rs = round(float(ticker_ret - bench_ret) * 100, 2)

            result = IndexMomentumSnapshot(
                rsi_14=rsi, ma50=ma50, ma200=ma200,
                golden_cross=golden, relative_strength=rs,
                signal=_signal(golden, rsi),
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(IndexMomentumReady(source="index_momentum_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> IndexMomentumSnapshot:
        return _DEFAULT
