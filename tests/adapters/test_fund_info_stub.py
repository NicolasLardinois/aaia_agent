import pytest

from core.domain.models import FundInfo
from core.ports.fund_info import FundInfoProvider
from adapters.data.fund_info_stub import StubFundInfoProvider


def test_unavailable_factory():
    fi = FundInfo.unavailable()
    assert fi.available is False
    assert fi.ter is None and fi.tracking_error is None


@pytest.mark.asyncio
async def test_stub_returns_none():
    provider = StubFundInfoProvider()
    assert isinstance(provider, FundInfoProvider)
    assert await provider.get_fund_info("XLE") is None
