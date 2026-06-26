"""Tests für den FMP-Spotpreis-Adapter (LME-Metalle Zink/Nickel).

Kein echtes Netzwerk-I/O (conftest blockt requests global): geprüft wird der
defensive Vertrag — ohne API-Key liefert der Adapter None, statt zu rufen.
"""
from adapters.data.fmp_metal_spot import FmpMetalSpotProvider
from core.ports.metal_spot import MetalSpotProvider


def test_implements_port():
    assert isinstance(FmpMetalSpotProvider(api_key="x"), MetalSpotProvider)


def test_missing_key_returns_none_without_network():
    # Leerer Key → früher Ausstieg (None), kein requests-Call (Netzwerk ist geblockt).
    provider = FmpMetalSpotProvider(api_key="")
    assert provider.get_spot_price("ZINC") is None
