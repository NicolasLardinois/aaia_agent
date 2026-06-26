"""Adapter-Test YahooPriceHistoryProvider (Backtester-Kursquelle).

Kein echtes Netz (conftest blockt `yfinance` global): geprüft wird der Port-Vertrag
und der defensive None-Pfad bei geblocktem yfinance.
"""
from datetime import datetime, timezone

from adapters.data.yahoo_price_history import YahooPriceHistoryProvider
from core.ports.price_history import PriceHistoryProvider


def test_implements_port():
    assert isinstance(YahooPriceHistoryProvider(), PriceHistoryProvider)


def test_blocked_network_price_is_none():
    # yfinance ist im Test geblockt → Exception → defensiv None (kein Crash).
    provider = YahooPriceHistoryProvider()
    px = provider.get_price_on_horizon("AAPL", datetime(2024, 1, 1, tzinfo=timezone.utc), 30)
    assert px is None
