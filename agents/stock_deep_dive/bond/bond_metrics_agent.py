import asyncio
from core.domain.events import BondMetricsReady
from core.domain.models import BondMetricsSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider, MacroDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = BondMetricsSnapshot(
    bond_type="government", current_price=None, coupon=None, maturity_years=None,
    ytm=None, ytc=None, current_yield=None, real_yield=None,
    country=None, breakeven_inflation=None, issuer=None, sector=None,
    signal=Signal.NEUTRAL,
)


def _signal(ytm: float | None, real_yield: float | None) -> Signal:
    if ytm is None:
        return Signal.NEUTRAL
    if real_yield is not None:
        if real_yield > 2.0:
            return Signal.BULLISH   # attraktive Realrendite
        if real_yield < 0:
            return Signal.BEARISH   # negative Realrendite
    return Signal.NEUTRAL


class BondMetricsAgent:
    def __init__(self, provider: FundamentalsProvider, macro: MacroDataProvider, bus: EventBus):
        self.provider = provider
        self.macro    = macro
        self.bus      = bus

    async def run(self, ticker: str, bond_type: str = "government") -> BondMetricsSnapshot:
        data, state = await asyncio.gather(
            asyncio.to_thread(self.provider.get_bond_data, ticker),
            asyncio.to_thread(self.macro.get_economic_state),
            return_exceptions=True,
        )
        def _safe(v): return {} if isinstance(v, Exception) else (v or {})
        data  = _safe(data)
        state = _safe(state)

        ytm      = data.get("ytm")
        coupon   = data.get("coupon")
        price    = data.get("current_price")
        maturity = data.get("maturity_years")
        inflation = state.get("inflation")
        real_yield = round(ytm - inflation, 3) if ytm is not None and inflation is not None else None
        cur_yield  = round(coupon / price * 100, 3) if coupon is not None and price is not None and price > 0 else None

        result = BondMetricsSnapshot(
            bond_type=bond_type,
            current_price=price, coupon=coupon, maturity_years=maturity,
            ytm=ytm, ytc=data.get("ytc"), current_yield=cur_yield,
            real_yield=real_yield,
            country=data.get("country") if bond_type == "government" else None,
            breakeven_inflation=data.get("breakeven_inflation"),
            issuer=data.get("issuer") if bond_type == "corporate" else None,
            sector=data.get("sector") if bond_type == "corporate" else None,
            signal=_signal(ytm, real_yield),
        )
        self.bus.publish(BondMetricsReady(source="bond_metrics_agent", payload={"ticker": ticker, "ytm": ytm}))
        return result

    @staticmethod
    def default() -> BondMetricsSnapshot:
        return _DEFAULT
