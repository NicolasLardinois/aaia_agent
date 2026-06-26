import asyncio

from core.domain.events import IndustrialMetalsDataReady
from core.domain.models import IndustrialMetalsSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.ports.metal_spot import MetalSpotProvider
from core.utils.relative import zscore_vs_history

# Kupfer und Aluminium: CME-Futures, verfügbar über Yahoo Finance
TICKERS = {"copper": "HG=F", "aluminium": "ALI=F", "gold": "GC=F"}
# Zink und Nickel handeln an der LME — kein Yahoo-Ticker; sie kommen über den
# injizierten MetalSpotProvider (FMP-Adapter), nicht mehr aus hartkodiertem I/O.

_COPPER_GOLD_Z = 1.0   # |z| > 1.0 = signifikante Copper/Gold-Bewegung


_DEFAULT = IndustrialMetalsSnapshot(
    copper_usd=None, aluminium_usd=None, zinc_usd=None, nickel_usd=None, signal=Signal.NEUTRAL,
)


def _signal(copper_gold_z: float | None) -> Signal:
    """
    Dr. Copper als Frühindikator über die DYNAMIK des Copper/Gold-Ratios
    (dimensionslos, zins-/wachstumssensitiv), NICHT über ein statisches
    Kupfer-Niveau. Steigendes Ratio = Risk-on (BULLISH), fallendes = Risk-off (BEARISH).
    """
    if copper_gold_z is None:
        return Signal.NEUTRAL
    if copper_gold_z > _COPPER_GOLD_Z:
        return Signal.BULLISH
    if copper_gold_z < -_COPPER_GOLD_Z:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _copper_gold_z(copper_hist, gold_hist) -> float | None:
    """z-Score der 12M-Veränderung des Copper/Gold-Ratios."""
    if copper_hist is None or gold_hist is None:
        return None
    if isinstance(copper_hist, Exception) or isinstance(gold_hist, Exception):
        return None
    try:
        cu = copper_hist["Close"].dropna()
        au = gold_hist["Close"].dropna()
        ratio = (cu / au).dropna()
        if len(ratio) < 30:
            return None
        monthly = ratio.pct_change(21).dropna()
        if len(monthly) < 20:
            return None
        current = float((ratio.iloc[-1] - ratio.iloc[0]) / ratio.iloc[0])
        return zscore_vs_history(current, monthly.tolist(), robust=True, min_n=20)
    except Exception:
        return None


class IndustrialMetalsAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus,
                 metal_spot: MetalSpotProvider | None = None):
        self.provider   = provider
        self.bus        = bus
        # Optionaler Port für LME-Spotpreise (Zink/Nickel). Fehlt er, bleiben
        # diese beiden None — der Rest der Analyse läuft unverändert weiter.
        self.metal_spot = metal_spot

    async def _spot(self, symbol: str) -> float | None:
        if self.metal_spot is None:
            return None
        return await asyncio.to_thread(self.metal_spot.get_spot_price, symbol)

    async def run(self) -> IndustrialMetalsSnapshot:
        (copper, alu, zinc, nickel), (h_copper, h_gold) = await asyncio.gather(
            asyncio.gather(
                asyncio.to_thread(self.provider.get_current_price, TICKERS["copper"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["aluminium"]),
                self._spot("ZINC"),
                self._spot("NICKEL"),
                return_exceptions=True,
            ),
            asyncio.gather(
                asyncio.to_thread(self.provider.get_price_history, TICKERS["copper"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["gold"], "1y"),
                return_exceptions=True,
            ),
        )
        def _safe(v): return None if isinstance(v, Exception) else v
        copper = _safe(copper); alu = _safe(alu); zinc = _safe(zinc); nickel = _safe(nickel)

        cg_z = _copper_gold_z(h_copper, h_gold)

        result = IndustrialMetalsSnapshot(
            copper_usd=copper, aluminium_usd=alu, zinc_usd=zinc, nickel_usd=nickel,
            signal=_signal(cg_z),
        )
        self.bus.publish(IndustrialMetalsDataReady(source="industrial_metals_agent", payload={
            "copper": copper, "aluminium": alu, "zinc": zinc, "nickel": nickel,
        }))
        return result

    @staticmethod
    def default() -> IndustrialMetalsSnapshot:
        return _DEFAULT
