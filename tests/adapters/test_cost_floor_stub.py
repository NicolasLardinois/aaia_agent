"""Phase 3: Stub-Kostenboden liefert None (UNAVAILABLE), bis echte Quelle steht."""
import asyncio

from adapters.data.cost_floor_stub import StubCostFloorProvider
from core.ports.cost_floor import CostFloorProvider
from core.domain.taxonomy import Underlying


def test_stub_is_a_cost_floor_provider():
    assert isinstance(StubCostFloorProvider(), CostFloorProvider)


def test_stub_returns_none():
    stub = StubCostFloorProvider()
    assert asyncio.run(stub.get_cost_floor(Underlying.COMMODITY, "CL")) is None
    assert asyncio.run(stub.get_cost_floor(Underlying.PRECIOUS_METAL, "GC")) is None
