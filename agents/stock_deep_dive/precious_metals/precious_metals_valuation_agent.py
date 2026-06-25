import asyncio

from core.domain.events import PreciousMetalsValuationReady
from core.domain.models import ValuationRangeSnapshot, ValuationMethod, Signal
from core.ports.data_provider import MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.valuation_math import real_rate_anchor, weighted_median_range

_DEFAULT = ValuationRangeSnapshot(
    methods=[], combined_low=0.0, combined_high=0.0,
    current_price=None, position="unknown", signal=Signal.NEUTRAL,
)

# Preis-UNABHÄNGIGE Realzins-Regression je Metall (injizierte, empirisch kalibrierte
# Konstanten — KEINE Ableitung aus dem aktuellen Preis). real_rate in Prozent (z. B. 1.5).
#   fair = intercept + slope * real_rate   (slope < 0: inverse Realzins-Beziehung)
# Datenannahme: ersetzbar durch echte Provider-Regression ohne Signaturänderung.
_REAL_RATE_MODEL: dict[str, dict[str, float]] = {
    "gold":   {"intercept": 2400.0, "slope": -250.0, "band_pct": 0.12},
    "silver": {"intercept":   28.0, "slope":   -4.0, "band_pct": 0.18},
}

# Aktuelle AISC-Produktionskosten-Bänder (2024/25), nur Gold (USD/oz).
_AISC_FLOOR: dict[str, tuple[float, float]] = {
    "gold": (1250.0, 1450.0),
}

# Methoden-Gewichte für die Kombination (Realzins ist der dominante Gold-Treiber).
_METHOD_WEIGHTS: dict[str, float] = {
    "Realzins-Modell": 2.0,
    "AISC-Produktionskosten-Boden": 1.0,
}


def _position(price: float, low: float, high: float) -> tuple[str, Signal]:
    if price < low * 0.95:
        return "undervalued", Signal.BULLISH
    if price > high * 1.05:
        return "overvalued", Signal.BEARISH
    return "fair", Signal.NEUTRAL


class PreciousMetalsValuationAgent:
    def __init__(self, macro: MacroDataProvider, market: MarketDataProvider, bus: EventBus):
        self.macro = macro
        self.market = market
        self.bus = bus

    async def run(self, metal: str = "gold") -> ValuationRangeSnapshot:
        metal = metal.lower()
        ticker_map = {"gold": "GC=F", "silver": "SI=F", "platinum": "PL=F", "palladium": "PA=F"}
        ticker = ticker_map.get(metal, "GC=F")

        current_price, macro_data = await asyncio.gather(
            asyncio.to_thread(self.market.get_current_price, ticker),
            asyncio.to_thread(self.macro.get_extended_state),
            return_exceptions=True,
        )
        if isinstance(current_price, Exception):
            current_price = None
        if isinstance(macro_data, Exception):
            macro_data = {}

        methods: list[ValuationMethod] = []

        # Methode 1: preis-UNABHÄNGIGER Realzins-Anker (Gold/Silber)
        real_rate = macro_data.get("real_rate_10y")
        model = _REAL_RATE_MODEL.get(metal)
        if real_rate is not None and model is not None:
            anchor = real_rate_anchor(
                real_rate=real_rate,
                intercept=model["intercept"],
                slope=model["slope"],
                band_pct=model["band_pct"],
            )
            # None = kein sinnvoller Anker (fair <= 0, z. B. extrem hoher Realzins) → Methode überspringen.
            if anchor is not None:
                low, high = anchor
                methods.append(ValuationMethod(
                    name="Realzins-Modell", low=round(low, 0), high=round(high, 0),
                ))

        # Methode 2: AISC-Produktionskosten-Boden (aktuelle Daten)
        floor = _AISC_FLOOR.get(metal)
        if floor is not None:
            methods.append(ValuationMethod(
                name="AISC-Produktionskosten-Boden", low=floor[0], high=floor[1],
            ))

        if not methods or current_price is None:
            return _DEFAULT

        weighted = [
            (m.low, m.high, _METHOD_WEIGHTS.get(m.name, 1.0)) for m in methods
        ]
        combined_low, combined_high = weighted_median_range(weighted)
        position, signal = _position(current_price, combined_low, combined_high)

        result = ValuationRangeSnapshot(
            methods=methods,
            combined_low=combined_low,
            combined_high=combined_high,
            current_price=current_price,
            position=position,
            signal=signal,
        )
        self.bus.publish(PreciousMetalsValuationReady(
            source="precious_metals_valuation_agent", payload={"metal": metal, "position": position},
        ))
        return result

    @staticmethod
    def default() -> ValuationRangeSnapshot:
        return _DEFAULT
