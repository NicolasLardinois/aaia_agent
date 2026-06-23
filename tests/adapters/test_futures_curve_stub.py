import pytest

from core.ports.futures_curve import FuturesCurveProvider
from adapters.data.futures_curve_stub import StubFuturesCurveProvider


@pytest.mark.asyncio
async def test_stub_returns_none():
    provider = StubFuturesCurveProvider()
    assert isinstance(provider, FuturesCurveProvider)
    assert await provider.get_curve("CL") is None
