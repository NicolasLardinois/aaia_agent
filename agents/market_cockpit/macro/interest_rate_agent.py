import asyncio
from core.domain.events import InterestRateDataReady
from core.domain.models import InterestRateSnapshot, InterestRateDataPoint, Signal
from core.ports.data_provider import MacroDataProvider, EcbDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus

_NEUTRAL = InterestRateDataPoint(
    policy_rate=None, rate_direction="stable",
    balance_sheet_growth=None, real_rate=None, signal=Signal.NEUTRAL,
)
_DEFAULT = InterestRateSnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)

_RATE_HISTORY: dict[str, list[float]] = {"usa": [], "eu": [], "ch": []}


def _direction(rate: float | None, history: list[float]) -> str:
    if rate is None or len(history) < 2:
        return "stable"
    if rate > history[-2]:
        return "rising"
    if rate < history[-2]:
        return "falling"
    return "stable"


def _signal(rate: float | None, direction: str, real_rate: float | None) -> Signal:
    if rate is None:
        return Signal.NEUTRAL
    if direction == "falling" and (real_rate is None or real_rate < 0):
        return Signal.BULLISH   # expansive Geldpolitik
    if direction == "rising" and real_rate is not None and real_rate > 2.0:
        return Signal.BEARISH   # restriktive Geldpolitik
    return Signal.NEUTRAL


class InterestRateAgent:
    def __init__(self, macro: MacroDataProvider, ecb: EcbDataProvider, snb: SnbDataProvider, bus: EventBus):
        self.macro = macro
        self.ecb   = ecb
        self.snb   = snb
        self.bus   = bus

    async def run(self) -> InterestRateSnapshot:
        state, ecb_rate, ecb_bs, snb_rate, snb_bs = await asyncio.gather(
            asyncio.to_thread(self.macro.get_economic_state),
            asyncio.to_thread(self.ecb.get_interest_rate),
            asyncio.to_thread(self.ecb.get_balance_sheet_growth),
            asyncio.to_thread(self.snb.get_interest_rate),
            asyncio.to_thread(self.snb.get_balance_sheet_growth),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v

        state    = _safe(state)    or {}
        ecb_rate = _safe(ecb_rate)
        ecb_bs   = _safe(ecb_bs)
        snb_rate = _safe(snb_rate)
        snb_bs   = _safe(snb_bs)

        fed_rate = state.get("fed_rate")
        usa_cpi  = state.get("inflation")
        usa_real = round(fed_rate - usa_cpi, 3) if fed_rate is not None and usa_cpi is not None else None

        if fed_rate is not None:
            _RATE_HISTORY["usa"].append(fed_rate)
        if ecb_rate is not None:
            _RATE_HISTORY["eu"].append(ecb_rate)
        if snb_rate is not None:
            _RATE_HISTORY["ch"].append(snb_rate)

        usa_dir = _direction(fed_rate, _RATE_HISTORY["usa"])
        eu_dir  = _direction(ecb_rate, _RATE_HISTORY["eu"])
        ch_dir  = _direction(snb_rate, _RATE_HISTORY["ch"])

        usa = InterestRateDataPoint(
            policy_rate=fed_rate, rate_direction=usa_dir,
            balance_sheet_growth=None,   # TODO: FRED WALCL
            real_rate=usa_real, signal=_signal(fed_rate, usa_dir, usa_real),
        )
        eu = InterestRateDataPoint(
            policy_rate=ecb_rate, rate_direction=eu_dir,
            balance_sheet_growth=ecb_bs,
            real_rate=None, signal=_signal(ecb_rate, eu_dir, None),
        )
        ch = InterestRateDataPoint(
            policy_rate=snb_rate, rate_direction=ch_dir,
            balance_sheet_growth=snb_bs,
            real_rate=None, signal=_signal(snb_rate, ch_dir, None),
        )
        result = InterestRateSnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(InterestRateDataReady(source="interest_rate_agent", payload={
            "usa_rate": fed_rate, "eu_rate": ecb_rate, "ch_rate": snb_rate,
        }))
        return result

    @staticmethod
    def default() -> InterestRateSnapshot:
        return _DEFAULT
