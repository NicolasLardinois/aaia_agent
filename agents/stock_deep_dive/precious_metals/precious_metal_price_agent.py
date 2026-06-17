import asyncio

from core.domain.events import PreciousMetalDataReady
from core.domain.models import PreciousMetalSnapshot, Signal, SignalStatus
from core.ports.data_provider import MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus

METAL_TICKERS = {"gold": "GC=F", "silver": "SI=F", "platinum": "PL=F", "palladium": "PA=F"}

# S2F einheitlich definiert als: oberirdische Bestände / Jahresproduktion (Jahre).
# Quelle/Definition siehe supply_demand_agent (systemweit konsistent, Review D7).
STOCK_TO_FLOW = {"gold": 62.0, "silver": 22.0, "platinum": 0.4, "palladium": 0.5}

_DEFAULT = PreciousMetalSnapshot(
    metal="unknown", price_usd=None, performance={}, rsi=None, ma50=None, ma200=None,
    stock_to_flow=None, real_yield_correlation=None,
    signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)

_PERF_WINDOWS = {"1w": 5, "1m": 21, "3m": 63, "1y": 252, "5y": 252 * 5}


def _wilder_rsi(close: "object", period: int = 14) -> float | None:
    delta = close.diff().dropna()
    if len(delta) < period:
        return None
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def _performance(close: "object") -> dict[str, float]:
    out: dict[str, float] = {}
    now = float(close.iloc[-1])
    for label, n in _PERF_WINDOWS.items():
        if len(close) > n:
            past = float(close.iloc[-(n + 1)])
            if past != 0:
                out[label] = round((now - past) / abs(past) * 100, 2)
    return out


def _price_signal(price: float | None, ma200: float | None, rsi: float | None) -> Signal:
    if price is None or ma200 is None:
        return Signal.NEUTRAL
    if price > ma200 and (rsi is None or rsi < 70):
        return Signal.BULLISH
    if price < ma200:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _real_yield_correlation(close: "object", rr_history: list[dict]) -> float | None:
    """Pearson-Korrelation von Gold-Preis-Level und 10J-Realzins-Level (gleichgerichtete Tage).
    Gold und Realzins tendieren invers — negative Werte stützen das Edelmetall-Argument."""
    import pandas as pd
    if not rr_history or len(rr_history) < 30:
        return None
    rr = pd.Series(
        {pd.Timestamp(r["date"]): float(r["real_rate_10y"]) for r in rr_history}
    ).sort_index()
    px = close.copy()
    px.index = pd.to_datetime(px.index).tz_localize(None)
    joined = pd.concat([px.rename("px"), rr.rename("rr")], axis=1).dropna()
    if len(joined) < 30:
        return None
    corr = joined["px"].corr(joined["rr"])
    return None if corr != corr else round(float(corr), 3)


class PreciousMetalPriceAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus, macro: MacroDataProvider | None = None):
        self.provider = provider
        self.bus = bus
        self.macro = macro

    async def run(self, metal: str) -> PreciousMetalSnapshot:
        ticker = METAL_TICKERS.get(metal.lower())
        if not ticker:
            return _DEFAULT

        price, hist = await asyncio.gather(
            asyncio.to_thread(self.provider.get_current_price, ticker),
            asyncio.to_thread(self.provider.get_price_history, ticker, "5y"),
            return_exceptions=True,
        )
        price = None if isinstance(price, Exception) else price
        hist  = None if isinstance(hist, Exception) else hist
        if hist is None or "Close" not in getattr(hist, "columns", []):
            return PreciousMetalSnapshot(
                metal=metal, price_usd=price, performance={}, rsi=None, ma50=None, ma200=None,
                stock_to_flow=STOCK_TO_FLOW.get(metal.lower()),
                real_yield_correlation=None, signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
            )

        close = hist["Close"].dropna()
        rsi   = _wilder_rsi(close)
        ma50  = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else None
        ma200 = round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None
        perf  = _performance(close)
        ref_price = price if price is not None else float(close.iloc[-1])

        rr_corr = None
        macro_src = self.macro if self.macro is not None else (
            self.provider if hasattr(self.provider, "get_real_rate_history") else None
        )
        if macro_src is not None:
            rr_hist = await asyncio.to_thread(macro_src.get_real_rate_history, 5)
            rr_corr = _real_yield_correlation(close, rr_hist)

        result = PreciousMetalSnapshot(
            metal=metal, price_usd=price, performance=perf, rsi=rsi, ma50=ma50, ma200=ma200,
            stock_to_flow=STOCK_TO_FLOW.get(metal.lower()),
            real_yield_correlation=rr_corr,
            signal=_price_signal(ref_price, ma200, rsi),
            status=SignalStatus.AVAILABLE,
        )
        self.bus.publish(PreciousMetalDataReady(source="precious_metal_price_agent", payload={
            "metal": metal, "price_usd": price,
        }))
        return result

    @staticmethod
    def default(metal: str = "gold") -> PreciousMetalSnapshot:
        return PreciousMetalSnapshot(
            metal=metal, price_usd=None, performance={}, rsi=None, ma50=None, ma200=None,
            stock_to_flow=STOCK_TO_FLOW.get(metal, None),
            real_yield_correlation=None, signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
        )
