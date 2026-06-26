from abc import ABC, abstractmethod


class MetalSpotProvider(ABC):
    """Port für Spot-/Kassapreise von Metallen, die NICHT über den regulären
    Markt-Provider (Yahoo) verfügbar sind — konkret die LME-Metalle Zink/Nickel.

    Synchron gehalten (wie `MarketDataProvider.get_current_price`): der Agent
    wickelt den Aufruf in `asyncio.to_thread(...)`, da es blockierendes I/O ist.
    """

    @abstractmethod
    def get_spot_price(self, symbol: str) -> float | None:
        """Letzter Spotpreis in USD oder None, wenn nicht verfügbar/fehlerhaft."""
        ...
