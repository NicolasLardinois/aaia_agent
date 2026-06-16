import asyncio
from core.domain.events import BondDurationReady
from core.domain.models import BondDurationSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus
from core.utils.bond_math import (
    ytm as _ytm, macaulay_duration, modified_duration, convexity,
    effective_duration, dv01, price_change_estimate, bond_price,
)

_DEFAULT = BondDurationSnapshot(
    macaulay_duration=None, modified_duration=None, convexity=None, dv01=None,
    signal=Signal.NEUTRAL,
)

# angenommene Yield-Bewegung je Richtung (50 bp) für die Signal-Schätzung
_DY = {"rising": 0.005, "falling": -0.005, "stable": 0.0}


def _coupon_rate(data: dict) -> float | None:
    if data.get("coupon_rate") is not None:
        return data["coupon_rate"]
    coupon, face = data.get("coupon"), data.get("face", 100.0)
    return coupon / face if coupon is not None and face else None


def _signal(mod_dur, conv, rate_direction) -> Signal:
    if mod_dur is None or conv is None:
        return Signal.NEUTRAL
    dy = _DY.get(rate_direction, 0.0)
    if dy == 0.0:
        return Signal.NEUTRAL
    est = price_change_estimate(mod_dur, conv, dy)  # ΔP/P
    if est < -0.01:   # erwarteter Kursverlust > 1 %
        return Signal.BEARISH
    if est > 0.01:
        return Signal.BULLISH
    return Signal.NEUTRAL


class BondDurationAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str, rate_direction: str = "stable") -> BondDurationSnapshot:
        data = await asyncio.to_thread(self.provider.get_bond_data, ticker)
        if isinstance(data, Exception):
            data = {}

        price = data.get("current_price")
        face = data.get("face", 100.0)
        freq = data.get("frequency", 2)
        maturity = data.get("maturity_years")
        crate = _coupon_rate(data)
        accrued = data.get("accrued_interest", 0.0)

        mac = mod = conv = dv = None
        if price and crate is not None and maturity:
            y = _ytm(price, face, crate, maturity, freq)
            mac = round(macaulay_duration(price, face, crate, maturity, freq), 4)
            # Effective Duration bei Optionalität (Call/Put) numerisch, sonst Modified
            if data.get("is_callable") or data.get("is_putable"):
                dyc = 0.0025
                pu = bond_price(y + dyc, face, crate, maturity, freq)
                pd = bond_price(y - dyc, face, crate, maturity, freq)
                mod = round(effective_duration(pu, pd, price, dyc), 4)
            else:
                mod = round(modified_duration(mac, y, freq), 4)
            conv = round(convexity(price, face, crate, maturity, freq), 3)
            dirty = price + (accrued or 0.0)
            dv = round(dv01(mod, dirty), 4)

        result = BondDurationSnapshot(
            macaulay_duration=mac, modified_duration=mod, convexity=conv, dv01=dv,
            signal=_signal(mod, conv, rate_direction),
        )
        self.bus.publish(BondDurationReady(source="bond_duration_agent",
                                           payload={"ticker": ticker, "modified_duration": mod}))
        return result

    @staticmethod
    def default() -> BondDurationSnapshot:
        return _DEFAULT
