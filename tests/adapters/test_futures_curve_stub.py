import asyncio

from core.ports.futures_curve import FuturesCurveProvider
from adapters.data.futures_curve_stub import StubFuturesCurveProvider


def test_stub_returns_none():
    # Projektkonvention: Coroutine synchron über asyncio.run() ausführen — das Repo
    # verzichtet bewusst auf pytest-asyncio (requirements-dev.txt), das in der CI fehlt.
    provider = StubFuturesCurveProvider()
    assert isinstance(provider, FuturesCurveProvider)
    assert asyncio.run(provider.get_curve("CL")) is None
