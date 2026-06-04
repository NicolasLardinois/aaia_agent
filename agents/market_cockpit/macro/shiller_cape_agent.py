import asyncio
from core.domain.events import ShillerCAPEDataReady
from core.domain.models import ShillerCAPESnapshot, ShillerCAPEDataPoint, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

# Historische Durchschnittswerte (langfristig)
HISTORICAL_AVG = {"usa": 17.0, "eurozone": 15.0, "switzerland": 18.0}

_NEUTRAL_USA = ShillerCAPEDataPoint(cape=None, historical_avg=HISTORICAL_AVG["usa"], deviation_pct=None, signal=Signal.NEUTRAL)
_NEUTRAL_EU  = ShillerCAPEDataPoint(cape=None, historical_avg=HISTORICAL_AVG["eurozone"], deviation_pct=None, signal=Signal.NEUTRAL)
_NEUTRAL_CH  = ShillerCAPEDataPoint(cape=None, historical_avg=HISTORICAL_AVG["switzerland"], deviation_pct=None, signal=Signal.NEUTRAL)
_DEFAULT = ShillerCAPESnapshot(usa=_NEUTRAL_USA, eurozone=_NEUTRAL_EU, switzerland=_NEUTRAL_CH)

# Shiller CAPE Ticker (Yahoo Finance)
# USA: ^SHILLER_PE_RATIO nicht direkt verfügbar → TODO: multpl.com oder FRED/Quandl
# EU/CH: TODO
CAPE_TICKERS = {
    "usa":        None,   # TODO: Datenquelle für S&P 500 CAPE
    "eurozone":   None,   # TODO: Datenquelle für Euro Stoxx 50 CAPE
    "switzerland": None,  # TODO: Datenquelle für SMI CAPE
}


def _signal(cape: float | None, avg: float) -> Signal:
    if cape is None:
        return Signal.NEUTRAL
    deviation = (cape - avg) / avg
    if deviation < 0:
        return Signal.BULLISH   # unterbewertet
    if deviation > 0.30:
        return Signal.BEARISH   # >30% über historischem Durchschnitt
    return Signal.NEUTRAL


def _deviation(cape: float | None, avg: float) -> float | None:
    if cape is None:
        return None
    return round((cape - avg) / avg * 100, 1)


class ShillerCAPEAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self) -> ShillerCAPESnapshot:
        # TODO: echte Datenquellen anbinden (multpl.com, Quandl, Bloomberg)
        usa_cape = None
        eu_cape  = None
        ch_cape  = None

        usa = ShillerCAPEDataPoint(
            cape=usa_cape, historical_avg=HISTORICAL_AVG["usa"],
            deviation_pct=_deviation(usa_cape, HISTORICAL_AVG["usa"]),
            signal=_signal(usa_cape, HISTORICAL_AVG["usa"]),
        )
        eu = ShillerCAPEDataPoint(
            cape=eu_cape, historical_avg=HISTORICAL_AVG["eurozone"],
            deviation_pct=_deviation(eu_cape, HISTORICAL_AVG["eurozone"]),
            signal=_signal(eu_cape, HISTORICAL_AVG["eurozone"]),
        )
        ch = ShillerCAPEDataPoint(
            cape=ch_cape, historical_avg=HISTORICAL_AVG["switzerland"],
            deviation_pct=_deviation(ch_cape, HISTORICAL_AVG["switzerland"]),
            signal=_signal(ch_cape, HISTORICAL_AVG["switzerland"]),
        )
        result = ShillerCAPESnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(ShillerCAPEDataReady(source="shiller_cape_agent", payload={
            "usa_cape": usa_cape, "eu_cape": eu_cape, "ch_cape": ch_cape,
        }))
        return result

    @staticmethod
    def default() -> ShillerCAPESnapshot:
        return _DEFAULT
