import asyncio
from core.domain.events import BondMetricsReady
from core.domain.models import BondMetricsSnapshot, Signal, SignalStatus
from core.ports.data_provider import FundamentalsProvider, MacroDataProvider
from core.ports.event_bus import EventBus
from core.utils.bond_math import ytm as _ytm, yield_to_worst
from core.utils.real_nominal import to_real

_DEFAULT = BondMetricsSnapshot(
    bond_type="government", current_price=None, coupon=None, maturity_years=None,
    ytm=None, ytc=None, current_yield=None, real_yield=None,
    country=None, breakeven_inflation=None, issuer=None, sector=None,
    signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)


def _coupon_rate(data: dict) -> float | None:
    """Kuponsatz als Dezimal: direkt aus coupon_rate, sonst coupon/face."""
    if data.get("coupon_rate") is not None:
        return data["coupon_rate"]
    coupon, face = data.get("coupon"), data.get("face", 100.0)
    return coupon / face if coupon is not None and face else None


def _signal(real_yield: float | None) -> Signal:
    if real_yield is None:
        return Signal.NEUTRAL
    if real_yield > 2.0:
        return Signal.BULLISH
    if real_yield < 0:
        return Signal.BEARISH
    return Signal.NEUTRAL


class BondMetricsAgent:
    def __init__(self, provider: FundamentalsProvider, macro: MacroDataProvider, bus: EventBus):
        self.provider = provider
        self.macro = macro
        self.bus = bus

    async def run(self, ticker: str, bond_type: str = "government") -> BondMetricsSnapshot:
        data, state = await asyncio.gather(
            asyncio.to_thread(self.provider.get_bond_data, ticker),
            asyncio.to_thread(self.macro.get_economic_state),
            return_exceptions=True,
        )
        def _safe(v): return {} if isinstance(v, Exception) else (v or {})
        data, state = _safe(data), _safe(state)

        price = data.get("current_price")
        face = data.get("face", 100.0)
        freq = data.get("frequency", 2)
        maturity = data.get("maturity_years")
        crate = _coupon_rate(data)

        # Preisbasis-Konvention: current_price ist der Clean-Kurs (quotiert).
        # YTM/YTC werden auf dem Dirty-Preis (clean + accrued_interest) gerechnet.
        # Current Yield bleibt auf dem Clean-Preis (Marktkonvention).
        accrued = data.get("accrued_interest", 0.0) or 0.0
        dirty = price + accrued if price else None

        # YTM selbst berechnen (kein Durchreichen mehr)
        ytm_val = None
        if dirty and crate is not None and maturity:
            try:
                ytm_val = round(_ytm(dirty, face, crate, maturity, freq), 5)
            except (ValueError, ZeroDivisionError):
                ytm_val = None

        # YTC für callable Bonds (Bewertung bis zum Call-Datum/-Preis)
        ytc_val = None
        call_price, ytc_years = data.get("call_price"), data.get("years_to_call")
        if dirty and crate is not None and call_price and ytc_years:
            try:
                ytc_val = round(_ytm(dirty, call_price, crate, ytc_years, freq), 5)
            except (ValueError, ZeroDivisionError):
                ytc_val = None

        ytw = yield_to_worst(ytm_val, ytc_val)

        # Realrendite ex-ante: Breakeven bevorzugt, sonst realisierte Inflation
        infl = state.get("breakeven_inflation")
        if infl is None:
            infl = data.get("breakeven_inflation")
        if infl is None:
            infl = state.get("inflation")
        # ytw/infl sind Dezimal → in Prozentpunkte umrechnen; to_real liefert Prozentpunkte.
        # Guard gegen inflation == -100 % (to_real wirft ValueError bei Division durch 0).
        real_yield = None
        if ytw is not None and infl is not None:
            try:
                real_yield = round(to_real(ytw * 100.0, infl * 100.0), 3)
            except ValueError:
                real_yield = None

        # Current Yield (Clean-Konvention), in % ausgegeben (Snapshot-Konvention)
        cur_yield = round(crate * face / price * 100, 3) if crate is not None and price else None

        result = BondMetricsSnapshot(
            bond_type=bond_type,
            current_price=price, coupon=crate, maturity_years=maturity,
            ytm=ytm_val, ytc=ytc_val, current_yield=cur_yield,
            real_yield=real_yield, ytw=ytw,
            country=data.get("country") if bond_type == "government" else None,
            breakeven_inflation=infl,
            issuer=data.get("issuer") if bond_type == "corporate" else None,
            sector=data.get("sector") if bond_type == "corporate" else None,
            signal=_signal(real_yield),
            # Signal speist sich aus der Realrendite; ohne sie ist die Komponente
            # uninformativ → UNAVAILABLE (§3.4), nicht als neutrale Stimme zählen.
            status=SignalStatus.AVAILABLE if real_yield is not None else SignalStatus.UNAVAILABLE,
        )
        self.bus.publish(BondMetricsReady(source="bond_metrics_agent",
                                          payload={"ticker": ticker, "ytm": ytm_val, "ytw": ytw}))
        return result

    @staticmethod
    def default() -> BondMetricsSnapshot:
        return _DEFAULT
