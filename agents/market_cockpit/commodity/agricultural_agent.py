import asyncio
import statistics
from core.domain.events import AgriculturalDataReady
from core.domain.models import AgriculturalSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

TICKERS = {
    "wheat":        "ZW=F",
    "corn":         "ZC=F",
    "soy":          "ZS=F",
    "coffee":       "KC=F",
    "sugar":        "SB=F",
    "cotton":       "CT=F",
    "orange_juice": "OJ=F",
}
_DEFAULT = AgriculturalSnapshot(
    wheat_usd=None, corn_usd=None, soy_usd=None, coffee_usd=None,
    sugar_usd=None, cotton_usd=None, orange_juice_usd=None, signal=Signal.NEUTRAL,
)


_BEARISH_THRESHOLD =  0.20   # +20% Jahresveränderung → Agrar-Inflation
_BULLISH_THRESHOLD = -0.20   # -20% Jahresveränderung → Preisentlastung


def _signal(changes: list[float]) -> Signal:
    """Median der 1J-Preisveränderungen aller Rohstoffe → Signal."""
    if not changes:
        return Signal.NEUTRAL
    med = statistics.median(changes)
    if med > _BEARISH_THRESHOLD:
        return Signal.BEARISH
    if med < _BULLISH_THRESHOLD:
        return Signal.BULLISH
    return Signal.NEUTRAL


def _yoy_change(hist) -> float | None:
    if isinstance(hist, Exception) or hist is None:
        return None
    try:
        close = hist["Close"].dropna()
        if len(close) < 2:
            return None
        return float((close.iloc[-1] - close.iloc[0]) / close.iloc[0])
    except Exception:
        return None


class AgriculturalAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> AgriculturalSnapshot:
        prices, histories = await asyncio.gather(
            asyncio.gather(
                asyncio.to_thread(self.provider.get_current_price, TICKERS["wheat"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["corn"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["soy"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["coffee"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["sugar"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["cotton"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["orange_juice"]),
                return_exceptions=True,
            ),
            asyncio.gather(
                asyncio.to_thread(self.provider.get_price_history, TICKERS["wheat"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["corn"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["soy"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["coffee"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["sugar"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["cotton"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["orange_juice"], "1y"),
                return_exceptions=True,
            ),
        )
        def _safe(v): return None if isinstance(v, Exception) else v
        wheat, corn, soy, coffee, sugar, cotton, oj = [_safe(v) for v in prices]

        changes = [c for c in (_yoy_change(h) for h in histories) if c is not None]

        result = AgriculturalSnapshot(
            wheat_usd=wheat, corn_usd=corn, soy_usd=soy, coffee_usd=coffee,
            sugar_usd=sugar, cotton_usd=cotton, orange_juice_usd=oj,
            signal=_signal(changes),
        )
        self.bus.publish(AgriculturalDataReady(source="agricultural_agent", payload={
            "wheat": wheat, "corn": corn, "soy": soy,
        }))
        return result

    @staticmethod
    def default() -> AgriculturalSnapshot:
        return _DEFAULT
