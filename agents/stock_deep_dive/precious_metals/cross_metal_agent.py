import asyncio

from core.domain.events import CrossMetalReady
from core.domain.models import CrossMetalSnapshot, Signal, SignalStatus
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.relative import percentile_rank

_DEFAULT = CrossMetalSnapshot(
    gold_silver_ratio=None, gold_platinum_ratio=None,
    signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)

_HIGH_PCT = 80.0   # ab hier "Ratio hoch" (zweites Metall relativ billig)
_LOW_PCT  = 20.0   # ab hier "Ratio niedrig" (erstes Metall relativ billig)


def _ratio_signal(pct: float, metal: str, high_favours: str) -> Signal:
    """pct = rollierendes Perzentil des aktuellen Ratios (Erstmetall/Zweitmetall).

    high_favours = "second": hohes Ratio → das ZWEITE Metall ist relativ billig.
    Richtung ist metallspezifisch: für das billige Metall bullish, fürs teure bearish.
    """
    m = metal.lower()
    if pct >= _HIGH_PCT:
        cheap, expensive = ("second", "first") if high_favours == "second" else ("first", "second")
    elif pct <= _LOW_PCT:
        cheap, expensive = ("first", "second") if high_favours == "second" else ("second", "first")
    else:
        return Signal.NEUTRAL
    # Mapping Position → konkretes Metall je Ratio bestimmt der Aufrufer; hier generisch:
    role = _role_of_metal(m)
    if role == cheap:
        return Signal.BULLISH
    if role == expensive:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _role_of_metal(metal: str) -> str | None:
    """Erstmetall ist immer Gold; Zweitmetall ist Silber bzw. Platin."""
    if metal == "gold":
        return "first"
    if metal in ("silver", "platinum"):
        return "second"
    return None


def _ratio_history(num: "object", den: "object") -> tuple[list[float], float | None]:
    import pandas as pd
    if num is None or den is None:
        return [], None
    n = num["Close"] if isinstance(num, pd.DataFrame) else num
    d = den["Close"] if isinstance(den, pd.DataFrame) else den
    aligned = (n.reset_index(drop=True) / d.reset_index(drop=True)).dropna()
    if len(aligned) < 30:
        return [], None
    hist = [round(float(x), 4) for x in aligned.iloc[:-1]]
    current = round(float(aligned.iloc[-1]), 4)
    return hist, current


class CrossMetalAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, metal: str = "gold") -> CrossMetalSnapshot:
        gold, silver, platinum = await asyncio.gather(
            asyncio.to_thread(self.provider.get_price_history, "GC=F", "2y"),
            asyncio.to_thread(self.provider.get_price_history, "SI=F", "2y"),
            asyncio.to_thread(self.provider.get_price_history, "PL=F", "2y"),
            return_exceptions=True,
        )
        gold     = None if isinstance(gold, Exception) else gold
        silver   = None if isinstance(silver, Exception) else silver
        platinum = None if isinstance(platinum, Exception) else platinum

        gs_hist, gs_cur = _ratio_history(gold, silver)
        gp_hist, gp_cur = _ratio_history(gold, platinum)

        m = metal.lower()
        if m == "silver" and gs_cur is not None:
            pct = percentile_rank(gs_cur, gs_hist)
            signal, status = _ratio_signal(pct, m, "second"), SignalStatus.AVAILABLE
        elif m == "platinum" and gp_cur is not None:
            pct = percentile_rank(gp_cur, gp_hist)
            signal, status = _ratio_signal(pct, m, "second"), SignalStatus.AVAILABLE
        elif m == "gold" and gs_cur is not None:
            pct = percentile_rank(gs_cur, gs_hist)
            signal, status = _ratio_signal(pct, m, "second"), SignalStatus.AVAILABLE
        else:
            signal, status = Signal.NEUTRAL, SignalStatus.UNAVAILABLE

        result = CrossMetalSnapshot(
            gold_silver_ratio=gs_cur,
            gold_platinum_ratio=gp_cur,
            signal=signal,
            status=status,
        )
        self.bus.publish(CrossMetalReady(source="cross_metal_agent", payload={
            "gold_silver_ratio": gs_cur, "gold_platinum_ratio": gp_cur,
        }))
        return result

    @staticmethod
    def default() -> CrossMetalSnapshot:
        return _DEFAULT
