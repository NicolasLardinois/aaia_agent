"""Tests für den World-Bank-Adapter (Marktkapitalisierung/BIP je Land).

Kein echtes Netzwerk-I/O (conftest blockt requests global): geprüft wird der
defensive Vertrag — bei blockiertem/fehlgeschlagenem Call liefert der Adapter {}.
"""
from adapters.data.world_bank import WorldBankMarketCapProvider
from core.ports.world_bank import MarketCapToGdpProvider


def test_implements_port():
    assert isinstance(WorldBankMarketCapProvider(), MarketCapToGdpProvider)


def test_blocked_network_returns_empty_dict():
    # requests ist im Test geblockt → except-Pfad → {} (kein Crash, keine Teildaten).
    provider = WorldBankMarketCapProvider()
    assert provider.get_market_cap_to_gdp() == {}
