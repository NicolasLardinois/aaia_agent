"""Phase 2a: Mechanik-Overlay bei wrapper=FUTURE im BottomUpOrchestrator.

- Mit Provider → FuturesAssessment.available True am Ergebnis.
- Ohne Provider → unavailable (defensiv, kein Crash).
- Nicht-Future-Wrapper bleiben unberührt (futures_curve None).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.domain.models import FuturesCurveSnapshot
from core.domain.taxonomy import Underlying, Wrapper
from core.ports.futures_curve import FuturesCurveProvider
from orchestrators.bottom_up_orchestrator import BottomUpOrchestrator


class _FakeCurve(FuturesCurveProvider):
    async def get_curve(self, symbol):
        return FuturesCurveSnapshot(spot=100.0, front=100.0, next_=106.0,
                                    days_to_front_expiry=30, days_between_expiries=182,
                                    risk_free_rate=0.05, storage_cost=0.0, margin_quote=0.10)


def _orchestrator(futures_curve_provider=None) -> BottomUpOrchestrator:
    orch = BottomUpOrchestrator(
        fundamentals_provider=MagicMock(), macro_provider=MagicMock(),
        market_provider=MagicMock(), llm=MagicMock(), bus=MagicMock(),
        futures_curve_provider=futures_curve_provider,
    )
    orch.commodity_chief = MagicMock()
    orch.commodity_chief.run = AsyncMock(return_value=MagicMock())
    orch.commodity_chief.default = MagicMock(return_value=MagicMock())
    pm_result = MagicMock()
    pm_result.valuation_range = None
    orch.precious_metals_chief = MagicMock()
    orch.precious_metals_chief.run = AsyncMock(return_value=pm_result)
    orch.precious_metals_chief.default = MagicMock(return_value=pm_result)
    return orch


def test_commodity_future_attaches_assessment():
    orch = _orchestrator(futures_curve_provider=_FakeCurve())
    res = asyncio.run(orch.run("CL", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE))
    assert res.futures_curve is not None
    assert res.futures_curve.available is True
    assert res.wrapper == Wrapper.FUTURE


def test_commodity_without_provider_is_unavailable_not_crash():
    orch = _orchestrator(futures_curve_provider=None)
    res = asyncio.run(orch.run("CL", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE))
    assert res.futures_curve is not None
    assert res.futures_curve.available is False


def test_precious_metal_single_has_no_futures_layer():
    orch = _orchestrator(futures_curve_provider=_FakeCurve())
    res = asyncio.run(orch.run("GC", underlying=Underlying.PRECIOUS_METAL, wrapper=Wrapper.PHYSICAL_ETC))
    assert res.futures_curve is None
    assert res.wrapper == Wrapper.PHYSICAL_ETC
