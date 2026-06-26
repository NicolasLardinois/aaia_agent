import asyncio
import logging
from core.domain.events import EnergyDataReady
from core.domain.models import EnergySnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.relative import zscore_vs_history
from core.utils.safe import safe_result

_log = logging.getLogger(__name__)

TICKERS = {"wti": "CL=F", "brent": "BZ=F", "natural_gas": "NG=F"}
_DEFAULT = EnergySnapshot(wti_usd=None, brent_usd=None, natural_gas_usd=None, signal=Signal.NEUTRAL)

# Schwellen auf der z-Score-Skala der 12M-Momentum-Verteilung.
_OIL_Z = 1.0   # |z| > 1.0 = signifikante Öl-Bewegung
_GAS_Z = 2.0   # Gas extrem volatil → höhere Schwelle


def _signal(wti_z: float | None, brent_z: float | None, gas_z: float | None) -> Signal:
    """
    Marktimplikation aus dem Öl-/Gas-MOMENTUM (z-Score der Veränderungsrate),
    NICHT aus dem nominalen Preisniveau. Konvention: starke Öl-Bewegung in beide
    Richtungen (Inflationsdruck bzw. Nachfrageschwäche) = BEARISH für Risiko-Assets.
    `is None`-Checks statt Falsiness (z=0.0 ist ein valider Wert).
    """
    oil = [z for z in (wti_z, brent_z) if z is not None]
    oil_z = sum(oil) / len(oil) if oil else None

    if oil_z is not None and abs(oil_z) > _OIL_Z:
        return Signal.BEARISH
    if gas_z is not None and abs(gas_z) > _GAS_Z:
        return Signal.BEARISH
    if oil_z is None and gas_z is None:
        return Signal.NEUTRAL
    return Signal.NEUTRAL


def _momentum_z(hist) -> float | None:
    """12M-Total-Return als z-Score gegen die rollierende Return-Historie."""
    if hist is None or isinstance(hist, Exception):
        return None
    try:
        close = hist["Close"].dropna()
        if len(close) < 30:
            return None
        # 21-Handelstage-Returns als Momentum-Verteilung; aktueller 12M-Return als Punkt
        monthly = close.pct_change(21).dropna()
        if len(monthly) < 20:
            return None
        current = float((close.iloc[-1] - close.iloc[0]) / close.iloc[0])
        return zscore_vs_history(current, monthly.tolist(), robust=True, min_n=20)
    except Exception:
        return None


class EnergyAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> EnergySnapshot:
        (wti, brent, gas), (h_wti, h_brent, h_gas) = await asyncio.gather(
            asyncio.gather(
                asyncio.to_thread(self.provider.get_current_price, TICKERS["wti"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["brent"]),
                asyncio.to_thread(self.provider.get_current_price, TICKERS["natural_gas"]),
                return_exceptions=True,
            ),
            asyncio.gather(
                asyncio.to_thread(self.provider.get_price_history, TICKERS["wti"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["brent"], "1y"),
                asyncio.to_thread(self.provider.get_price_history, TICKERS["natural_gas"], "1y"),
                return_exceptions=True,
            ),
        )
        # Ausgefallene Preisquelle -> None (geteilter Helfer statt lokalem _safe);
        # mit label+logger wird der Ausfall als warning sichtbar (nicht mehr still).
        wti = safe_result(wti, default=None, label=f"Energy WTI ({TICKERS['wti']})", logger=_log)
        brent = safe_result(brent, default=None, label=f"Energy Brent ({TICKERS['brent']})", logger=_log)
        gas = safe_result(gas, default=None, label=f"Energy Natural Gas ({TICKERS['natural_gas']})", logger=_log)

        result = EnergySnapshot(
            wti_usd=wti, brent_usd=brent, natural_gas_usd=gas,
            signal=_signal(_momentum_z(h_wti), _momentum_z(h_brent), _momentum_z(h_gas)),
        )
        self.bus.publish(EnergyDataReady(source="energy_agent", payload={
            "wti": wti, "brent": brent, "natural_gas": gas,
        }))
        return result

    @staticmethod
    def default() -> EnergySnapshot:
        return _DEFAULT
