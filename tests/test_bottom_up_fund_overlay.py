"""Phase 2b: Info-Overlay bei wrapper=FUND im BottomUpOrchestrator (Index-Pfad).

- Fonds-Hülle → FundInfo am Ergebnis.
- Direkt-Index (SINGLE) → keine Fund-Info.
- Ohne Provider → unavailable (defensiv, kein Crash).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from core.domain.models import FundInfo
from core.domain.taxonomy import Underlying, Wrapper
from core.ports.fund_info import FundInfoProvider
from orchestrators.bottom_up_orchestrator import BottomUpOrchestrator


class _FakeFund(FundInfoProvider):
    async def get_fund_info(self, symbol):
        return FundInfo(ter=0.001, tracking_error=0.02, available=True)


def _orch(fund_info_provider=None):
    orch = BottomUpOrchestrator(
        fundamentals_provider=MagicMock(), macro_provider=MagicMock(),
        market_provider=MagicMock(), llm=MagicMock(), bus=MagicMock(),
        fund_info_provider=fund_info_provider,
    )
    idx = MagicMock()
    orch.index_chief = MagicMock()
    orch.index_chief.run = AsyncMock(return_value=idx)
    orch.index_chief.default = MagicMock(return_value=idx)
    return orch


def test_fund_wrapper_attaches_info():
    res = asyncio.run(_orch(_FakeFund()).run("XLE", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND))
    assert res.fund_info is not None
    assert res.fund_info.available is True


def test_index_single_has_no_fund_info():
    res = asyncio.run(_orch(_FakeFund()).run("^GSPC", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.SINGLE))
    assert res.fund_info is None


def test_fund_without_provider_is_unavailable():
    res = asyncio.run(_orch(None).run("XLE", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND))
    assert res.fund_info is not None
    assert res.fund_info.available is False
