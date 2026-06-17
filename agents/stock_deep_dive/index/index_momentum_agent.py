import asyncio
import math

from core.domain.events import IndexMomentumReady
from core.domain.models import IndexMomentumSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.scoring import wilder_rsi

_WORLD_BENCHMARK = "URTH"   # iShares MSCI World ETF
_CROSS_WINDOW    = 5        # Handelstage für Kreuzungspunkt-Erkennung
_HISTORY_PERIOD  = "2y"     # MA200 braucht ≥2y für ein stabiles Cross-Fenster (P4.2)
_RSI_OVERBOUGHT  = 70.0
_RSI_OVERSOLD    = 30.0

_DEFAULT = IndexMomentumSnapshot(
    rsi_14=None, ma50=None, ma200=None,
    golden_cross=None, relative_strength=None, signal=Signal.NEUTRAL,
)


def _compute_rsi(prices, period: int = 14) -> float | None:
    """Wilder-Smoothing-RSI (delegiert an core.utils.scoring.wilder_rsi)."""
    return wilder_rsi(prices, period=period)


def _detect_crossover(ma50_series, ma200_series) -> bool | None:
    """True = Golden Cross, False = Death Cross, None = kein Kreuzungspunkt in letzten 5 Tagen."""
    try:
        diff   = ma50_series - ma200_series
        recent = diff.iloc[-(_CROSS_WINDOW + 1):]
        if len(recent) < 2:
            return None
        was_above = recent.iloc[0] > 0
        is_above  = recent.iloc[-1] > 0
        if not was_above and is_above:
            return True
        if was_above and not is_above:
            return False
        return None
    except Exception:
        return None


def _signal(ma50: float | None, ma200: float | None, rsi: float | None) -> Signal:
    """Signal aus dem Trend-STATUS (ma50 vs ma200) + RSI-Extreme statt nur Cross-Event.
    - Aufwärtstrend (ma50 > ma200) + RSI nicht überkauft → BULLISH.
    - Abwärtstrend (ma50 < ma200) + RSI nicht überverkauft → BEARISH.
    - Extreme dämpfen (überkauft im Up / überverkauft im Down) → NEUTRAL.
    - None oder NaN (< 50/200 Bars) → NEUTRAL.
    """
    if ma50 is None or ma200 is None:
        return Signal.NEUTRAL
    # NaN-Guard: rolling().mean().iloc[-1] liefert NaN bei zu wenig Bars
    if math.isnan(ma50) or math.isnan(ma200):
        return Signal.NEUTRAL
    uptrend = ma50 > ma200
    if uptrend:
        if rsi is not None and rsi > _RSI_OVERBOUGHT:
            return Signal.NEUTRAL
        return Signal.BULLISH
    # Abwärtstrend
    if rsi is not None and rsi < _RSI_OVERSOLD:
        return Signal.NEUTRAL
    return Signal.BEARISH


class IndexMomentumAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> IndexMomentumSnapshot:
        try:
            hist, bench = await asyncio.gather(
                asyncio.to_thread(self.market.get_price_history, ticker, _HISTORY_PERIOD),
                asyncio.to_thread(self.market.get_price_history, _WORLD_BENCHMARK, _HISTORY_PERIOD),
                return_exceptions=True,
            )
            if isinstance(hist, Exception):
                return _DEFAULT

            close    = hist["Close"]
            ma50_s   = close.rolling(50).mean()
            ma200_s  = close.rolling(200).mean()
            _ma50_raw  = float(ma50_s.iloc[-1])
            _ma200_raw = float(ma200_s.iloc[-1])
            # NaN (zu wenig Bars) → None, damit _signal korrekt NEUTRAL liefert
            ma50   = None if math.isnan(_ma50_raw)  else round(_ma50_raw,  2)
            ma200  = None if math.isnan(_ma200_raw) else round(_ma200_raw, 2)
            rsi      = _compute_rsi(close)
            golden   = _detect_crossover(ma50_s, ma200_s)

            rs = None
            if not isinstance(bench, Exception):
                bc = bench["Close"]
                ticker_ret = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
                bench_ret  = (bc.iloc[-1] - bc.iloc[0]) / bc.iloc[0]
                rs = round(float(ticker_ret - bench_ret) * 100, 2)

            result = IndexMomentumSnapshot(
                rsi_14=rsi, ma50=ma50, ma200=ma200,
                golden_cross=golden, relative_strength=rs,
                signal=_signal(ma50, ma200, rsi),
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(IndexMomentumReady(source="index_momentum_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> IndexMomentumSnapshot:
        return _DEFAULT
