import asyncio
import statistics
from core.domain.events import AgriculturalDataReady
from core.domain.models import AgriculturalSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.relative import zscore_vs_history

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

_Z_THRESHOLD = 1.0   # Median-z der Jahresveränderungen


def _signal(z_changes: list[float]) -> Signal:
    """
    Median der z-Normierten Jahresveränderungen aller Agrar-Rohstoffe.
    Hohe Agrarpreise (Median-z > +1) = Inflationsdruck → BEARISH;
    Preisentlastung (Median-z < -1) = BULLISH. z-Score statt fixer ±20%
    macht die Schwelle volatilitäts-adjustiert.
    """
    if not z_changes:
        return Signal.NEUTRAL
    med = statistics.median(z_changes)
    if med > _Z_THRESHOLD:
        return Signal.BEARISH
    if med < -_Z_THRESHOLD:
        return Signal.BULLISH
    return Signal.NEUTRAL


def _yoy_change_z(hist) -> float | None:
    """Geglättete (5-Tage) Jahresveränderung als z-Score gegen die Return-Historie."""
    if isinstance(hist, Exception) or hist is None:
        return None
    try:
        close = hist["Close"].dropna()
        if len(close) < 30:
            return None
        start = float(close.iloc[:5].mean())
        end   = float(close.iloc[-5:].mean())
        if start <= 0:
            return None
        current = (end - start) / start
        monthly = close.pct_change(21).dropna()
        if len(monthly) < 20:
            return None
        return zscore_vs_history(current, monthly.tolist(), robust=True, min_n=20)
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

        changes = [z for z in (_yoy_change_z(h) for h in histories) if z is not None]

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
