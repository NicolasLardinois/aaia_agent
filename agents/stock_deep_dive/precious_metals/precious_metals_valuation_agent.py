import asyncio

from core.domain.events import ValuationRangeReady
from core.domain.models import ValuationRangeSnapshot, ValuationMethod, Signal
from core.ports.data_provider import MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = ValuationRangeSnapshot(
    methods=[], combined_low=0.0, combined_high=0.0,
    current_price=None, position="unknown", signal=Signal.NEUTRAL,
)

# Historische inflationsbereinigte Goldpreise (Basis 2024 USD)
GOLD_INFLATION_ADJ_AVG = 1_200.0   # konservativer historischer Durchschnitt


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
        ticker_map = {"gold": "GC=F", "silver": "SI=F", "platinum": "PL=F", "palladium": "PA=F"}
        ticker = ticker_map.get(metal.lower(), "GC=F")

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

        # Methode 1: Realzins-Modell (nur Gold/Silber)
        real_rate = macro_data.get("real_rate_10y")
        if real_rate is not None and metal.lower() in ("gold", "silver"):
            # Inverse Beziehung: je tiefer Realzins, desto höher Gold-Fairer-Wert
            base = current_price or 2000
            adjustment = (0 - real_rate) * 150   # grobe Daumenregel
            methods.append(ValuationMethod(
                name="Realzins-Modell",
                low=round(base + adjustment * 0.7, 0),
                high=round(base + adjustment * 1.3, 0),
            ))

        # Methode 2: Inflationsbereinigt (Gold)
        if metal.lower() == "gold":
            methods.append(ValuationMethod(
                name="Inflationsbereinigt (historisch)",
                low=round(GOLD_INFLATION_ADJ_AVG * 0.85, 0),
                high=round(GOLD_INFLATION_ADJ_AVG * 1.40, 0),
            ))

        # Methode 3: Stock-to-Flow Kontext
        # S2F gibt kein direktes Kursziel — dient als Knappheits-Anker
        # Wenn S2F hoch und stabil → untere Bandbreite stützt sich auf Produktionskosten
        if metal.lower() == "gold":
            methods.append(ValuationMethod(
                name="S2F Produktionskosten-Boden",
                low=1_050.0,   # All-in Sustaining Cost (AISC) günstigster Produzent
                high=1_800.0,  # AISC teuerster Produzent — Angebotsgrenze
            ))

        if not methods or current_price is None:
            return _DEFAULT

        combined_low  = min(m.low  for m in methods)
        combined_high = max(m.high for m in methods)
        position, signal = _position(current_price, combined_low, combined_high)

        result = ValuationRangeSnapshot(
            methods=methods,
            combined_low=combined_low,
            combined_high=combined_high,
            current_price=current_price,
            position=position,
            signal=signal,
        )
        self.bus.publish(ValuationRangeReady(source="precious_metals_valuation_agent", payload={
            "metal": metal, "position": position,
        }))
        return result

    @staticmethod
    def default() -> ValuationRangeSnapshot:
        return _DEFAULT
