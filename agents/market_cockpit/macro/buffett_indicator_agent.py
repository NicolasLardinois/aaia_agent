import asyncio

from core.domain.events import BuffettIndicatorReady
from core.domain.models import BuffettCountryPoint, BuffettIndicatorSnapshot, Signal
from core.domain.top_down_context import buffett_corridor
from core.ports.data_provider import MacroDataProvider
from core.ports.event_bus import EventBus
from core.ports.world_bank import MarketCapToGdpProvider

_Z_HIGH = 1.5
_Z_LOW  = -1.5

# Die Weltbank-Rohdaten (Marktkap./BIP je Land) kommen über den injizierten
# MarketCapToGdpProvider (World-Bank-Adapter), nicht mehr aus hartkodiertem I/O.

_DEFAULT = BuffettIndicatorSnapshot(countries={}, signal=Signal.NEUTRAL)


def _signal(ratio: float | None, code: str) -> Signal:
    """Absolut-Fallback für Länder ohne ausreichende Historie (z-Score nicht bildbar).

    Nutzt den LÄNDERSPEZIFISCHEN Korridor (z. B. CH 150–260, DE 40–70) statt der
    früheren globalen 75/135%-Schwelle — sonst würde die strukturell hohe CH-Bewertung
    dauerhaft fälschlich als „teuer" und die niedrige DE-Bewertung als „günstig" gewertet.
    Unbekannte Länder fallen auf den Default-Korridor (75/135) zurück."""
    if ratio is None:
        return Signal.NEUTRAL
    low, high = buffett_corridor(code)
    if ratio < low:
        return Signal.BULLISH
    if ratio > high:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _signal_from_z(z: float | None) -> Signal:
    """
    Klassifizierung über den z-Score zur LANDESHISTORIE (Abweichung vom landeseigenen
    Mittel), NICHT über eine globale 75/135%-Schwelle. CH (strukturell 200–250%) und DE
    (50–60%) werden so korrekt relativ bewertet.
    """
    if z is None:
        return Signal.NEUTRAL
    if z >= _Z_HIGH:
        return Signal.BEARISH
    if z <= _Z_LOW:
        return Signal.BULLISH
    return Signal.NEUTRAL


def _z_score(current: float | None, history: list[float]) -> float | None:
    """Stichproben-Z-Score; mindestens 8 Datenpunkte nötig."""
    if current is None or len(history) < 8:
        return None
    mean = sum(history) / len(history)
    variance = sum((x - mean) ** 2 for x in history) / (len(history) - 1)
    std = variance ** 0.5
    if std == 0:
        return None
    return round((current - mean) / std, 2)


def _median(values: list[float]) -> float | None:
    clean = sorted(v for v in values if v is not None)
    n = len(clean)
    if n == 0:
        return None
    mid = n // 2
    return round(clean[mid] if n % 2 else (clean[mid - 1] + clean[mid]) / 2, 1)


class BuffettIndicatorAgent:
    def __init__(self, macro: MacroDataProvider, bus: EventBus,
                 world_bank: MarketCapToGdpProvider | None = None):
        self.macro = macro
        self.bus   = bus
        # Optionaler Port für die Weltbank-Länderdaten. Fehlt er (None), entstehen
        # keine Weltbank-Länder — nur USA aus FRED (netzfreier Replay/Backtest).
        self._world_bank = world_bank

    async def _fetch_wb(self) -> dict:
        if self._world_bank is None:
            return {}
        return await asyncio.to_thread(self._world_bank.get_market_cap_to_gdp)

    async def run(self) -> BuffettIndicatorSnapshot:
        fred_data, wb_data, fred_history = await asyncio.gather(
            asyncio.to_thread(self.macro.get_buffett_data),
            self._fetch_wb(),
            asyncio.to_thread(self.macro.get_buffett_history, 10),
            return_exceptions=True,
        )
        if isinstance(fred_data, Exception):
            fred_data = {}
        if isinstance(wb_data, Exception):
            wb_data = {}
        if isinstance(fred_history, Exception):
            fred_history = []

        # Alle Weltbank-Länder mit eigenem Z-Score
        countries: dict[str, BuffettCountryPoint] = {}
        all_ratios: list[float] = []

        for code, (ratio, year, history, name) in wb_data.items():
            values = [v for _, v in history]   # nur die Werte für den z-Score
            z = _z_score(ratio, values)
            # z-Score-Pfad primär; Fallback auf landesspezifischen Korridor ohne ausreichende Historie
            sig = _signal_from_z(z) if z is not None else _signal(ratio, code)
            countries[code] = BuffettCountryPoint(
                ratio_pct=ratio, signal=sig, year=year, z_score=z, name=name, history=history,
            )
            all_ratios.append(ratio)

        # Globaler Median über alle vorhandenen Länderwerte
        global_median = _median(all_ratios)

        # USA: FRED überschreibt Weltbank (Echtzeit, monatlich, beste Qualität)
        market_cap = fred_data.get("market_cap_bn")
        gdp        = fred_data.get("gdp_bn")
        usa_ratio  = None
        if market_cap is not None and gdp is not None and gdp > 0:
            usa_ratio = round(market_cap / gdp * 100, 1)
        usa_z = _z_score(usa_ratio, fred_history)
        usa_sig = _signal_from_z(usa_z) if usa_z is not None else _signal(usa_ratio, "USA")
        countries["USA"] = BuffettCountryPoint(
            ratio_pct=usa_ratio, signal=usa_sig, year=None, z_score=usa_z, name="United States",
        )

        usa_signal = countries["USA"].signal
        result = BuffettIndicatorSnapshot(
            countries=countries,
            signal=usa_signal,
            global_median=global_median,
        )
        self.bus.publish(BuffettIndicatorReady(source="buffett_indicator_agent", payload={
            "usa_ratio_pct":  usa_ratio,
            "usa_z_score":    usa_z,
            "global_median":  global_median,
            "countries_count": len(countries),
        }))
        return result

    @staticmethod
    def default() -> BuffettIndicatorSnapshot:
        return _DEFAULT
