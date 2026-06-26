import asyncio
from datetime import date
from typing import Optional
from core.domain.events import InterestRateDataReady
from core.domain.models import InterestRateSnapshot, InterestRateDataPoint, Signal
from core.ports.data_provider import MacroDataProvider, EcbDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus
from core.ports.dated_history import DatedHistoryPort
from core.utils.real_nominal import to_real
from core.utils.safe import safe_result
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory

_NEUTRAL = InterestRateDataPoint(
    policy_rate=None, rate_direction="stable",
    balance_sheet_growth=None, real_rate=None, signal=Signal.NEUTRAL,
)
_DEFAULT = InterestRateSnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)


def _months_back(d: date, months: int) -> date:
    """Datum `months` Monate zurück (ohne externe Abhängigkeit wie dateutil)."""
    m = d.month - 1 - months
    year = d.year + m // 12
    month = m % 12 + 1
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days_in_month = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(d.day, days_in_month))


def _direction(current: Optional[float], history: Optional[DatedHistoryPort], series: str,
               months_back: int = 3, today: Optional[date] = None) -> str:
    """Richtung aus DATIERTER Historie: aktueller Wert vs. Wert vor `months_back` Monaten.
    `today` injizierbar für deterministische Tests; nutzt die Multi-Serie-Port-API."""
    if current is None or history is None:
        return "stable"
    ref_date = _months_back(today or date.today(), months_back)
    prev = history.value_on_or_before(series, ref_date)
    if prev is None:
        return "stable"
    if current > prev:
        return "rising"
    if current < prev:
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
        state, ext, ecb_rate, ecb_bs, snb_rate, snb_bs = await asyncio.gather(
            asyncio.to_thread(self.macro.get_economic_state),
            asyncio.to_thread(self.macro.get_extended_state),
            asyncio.to_thread(self.ecb.get_interest_rate),
            asyncio.to_thread(self.ecb.get_balance_sheet_growth),
            asyncio.to_thread(self.snb.get_interest_rate),
            asyncio.to_thread(self.snb.get_balance_sheet_growth),
            return_exceptions=True,
        )
        # Teilergebnisse aus gather(return_exceptions=True) defensiv entpacken
        # (geteilter Helfer statt lokalem _safe): Exception -> None. Die separaten
        # Helfer _safe_real / _safe_hist unten bleiben unberuehrt (andere Semantik).
        state    = safe_result(state, default=None)    or {}
        ext      = safe_result(ext, default=None)      or {}
        ecb_rate = safe_result(ecb_rate, default=None)
        ecb_bs   = safe_result(ecb_bs, default=None)
        snb_rate = safe_result(snb_rate, default=None)
        snb_bs   = safe_result(snb_bs, default=None)

        fed_rate = state.get("fed_rate")
        usa_cpi  = state.get("inflation")
        # Realzinsen für alle Regionen: to_real(nominal, cpi)
        def _safe_real(rate, cpi):
            if rate is None or cpi is None:
                return None
            try:
                return round(to_real(rate, cpi), 3)
            except Exception:
                return None

        usa_real = _safe_real(fed_rate, usa_cpi)
        # EU/CH: Realzinsen aus ECB/SNB CPI (keine Historien-Abhängigkeit für Richtung)
        eu_real  = _safe_real(ecb_rate, state.get("eu_cpi"))   # TODO: ECB CPI via ext
        ch_real  = _safe_real(snb_rate, state.get("ch_cpi"))   # TODO: SNB CPI via ext

        usa_hist, eu_hist, ch_hist = await asyncio.gather(
            asyncio.to_thread(self.macro.get_policy_rate_history, 2),
            asyncio.to_thread(self.ecb.get_interest_rate_history, 2),
            asyncio.to_thread(self.snb.get_interest_rate_history, 2),
            return_exceptions=True,
        )
        def _safe_hist(h): return [] if isinstance(h, Exception) or not h else h

        def _to_pairs(hist):
            pairs = []
            for r in hist:
                try:
                    pairs.append((date.fromisoformat(r["date"]), float(r["rate"])))
                except Exception:
                    continue
            return pairs

        history = InMemoryDatedHistory({
            "fed_rate": _to_pairs(_safe_hist(usa_hist)),
            "ecb_rate": _to_pairs(_safe_hist(eu_hist)),
            "snb_rate": _to_pairs(_safe_hist(ch_hist)),
        })
        _today = date.today()

        usa_dir = _direction(fed_rate, history=history, series="fed_rate", today=_today)
        eu_dir  = _direction(ecb_rate, history=history, series="ecb_rate", today=_today)
        ch_dir  = _direction(snb_rate, history=history, series="snb_rate", today=_today)

        usa = InterestRateDataPoint(
            policy_rate=fed_rate, rate_direction=usa_dir,
            balance_sheet_growth=ext.get("balance_sheet_growth"),   # FRED WALCL (YoY %)
            real_rate=usa_real, signal=_signal(fed_rate, usa_dir, usa_real),
        )
        eu = InterestRateDataPoint(
            policy_rate=ecb_rate, rate_direction=eu_dir,
            balance_sheet_growth=ecb_bs,
            real_rate=eu_real, signal=_signal(ecb_rate, eu_dir, eu_real),
        )
        ch = InterestRateDataPoint(
            policy_rate=snb_rate, rate_direction=ch_dir,
            balance_sheet_growth=snb_bs,
            real_rate=ch_real, signal=_signal(snb_rate, ch_dir, ch_real),
        )
        result = InterestRateSnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(InterestRateDataReady(source="interest_rate_agent", payload={
            "usa_rate": fed_rate, "eu_rate": ecb_rate, "ch_rate": snb_rate,
        }))
        return result

    @staticmethod
    def default() -> InterestRateSnapshot:
        return _DEFAULT
