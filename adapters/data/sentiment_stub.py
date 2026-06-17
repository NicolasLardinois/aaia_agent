"""
Stub-Adapter für SentimentDataProvider.
Liefert None → FearGreedAgent gibt SignalStatus.UNAVAILABLE zurück.
Wird durch cnn_fear_greed.py ersetzt, sobald die echte CNN-API angebunden ist.

TODO: CNN Fear & Greed Adapter (adapters/data/cnn_fear_greed.py)
  URL: https://production.dataviz.cnn.io/index/fearandgreed/graphdata/
  Gibt {"score": float} zurück.
"""
from typing import Optional
from core.ports.data_provider import SentimentDataProvider


class SentimentStubProvider(SentimentDataProvider):
    def get_fear_greed(self) -> Optional[float]:
        return None  # TODO: CNN Fear & Greed API anbinden
