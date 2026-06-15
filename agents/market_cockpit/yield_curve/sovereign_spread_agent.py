import asyncio
from core.domain.events import SovereignSpreadDataReady
from core.domain.models import SovereignSpreadSnapshot, Signal
from core.ports.data_provider import EcbDataProvider
from core.ports.event_bus import EventBus
from adapters.data.ecb_sdw import EUROZONE_COUNTRIES

_DEFAULT = SovereignSpreadSnapshot(btp_bund=None, oat_bund=None, bonos_bund=None, signal=Signal.NEUTRAL)

# Länder die für den Stress-Signal relevant sind (grosse/mittlere Volkswirtschaften)
# Mini-Länder (MT, CY, EE, LV, LT) werden gespeichert aber nicht für Signal gewertet
_STRESS_COUNTRIES = {
    "IT", "ES", "PT", "GR", "FR", "BE", "IE", "AT",
    "NL", "HR", "SK", "SI", "LU", "FI",
}


def _signal(spreads: dict[str, float | None]) -> Signal:
    """BEARISH wenn max Spread > 300bp (Krise) oder 3+ Länder > 200bp (systemisch)."""
    values = [v for k, v in spreads.items()
              if v is not None and k.split("_")[0] in _STRESS_COUNTRIES]
    if not values:
        return Signal.NEUTRAL
    if max(values) > 300:
        return Signal.BEARISH
    if sum(1 for v in values if v > 200) >= 3:
        return Signal.BEARISH
    return Signal.NEUTRAL


class SovereignSpreadAgent:
    def __init__(self, ecb: EcbDataProvider, bus: EventBus):
        self.ecb = ecb
        self.bus = bus

    async def run(self) -> SovereignSpreadSnapshot:
        try:
            yields = await asyncio.to_thread(self.ecb.get_sovereign_yields)
        except Exception:
            yields = {}

        de = yields.get("DE_10y")

        def _spread(country_key: str) -> float | None:
            v = yields.get(country_key)
            if v is None or de is None:
                return None
            return round((v - de) * 100, 1)

        # Berechne alle Spreads vs Bund
        spreads_by_country = {
            f"{c}_10y": _spread(f"{c}_10y")
            for c in EUROZONE_COUNTRIES if c != "DE"
        }

        # Backward-compatible Felder
        btp_bund   = spreads_by_country.get("IT_10y")
        oat_bund   = spreads_by_country.get("FR_10y")
        bonos_bund = spreads_by_country.get("ES_10y")

        result = SovereignSpreadSnapshot(
            btp_bund=btp_bund,
            oat_bund=oat_bund,
            bonos_bund=bonos_bund,
            signal=_signal(spreads_by_country),
            spreads_by_country=spreads_by_country,
        )
        self.bus.publish(SovereignSpreadDataReady(source="sovereign_spread_agent", payload={
            "btp_bund": btp_bund, "oat_bund": oat_bund,
            "max_spread": max((v for v in spreads_by_country.values() if v is not None), default=None),
        }))
        return result

    @staticmethod
    def default() -> SovereignSpreadSnapshot:
        return _DEFAULT
