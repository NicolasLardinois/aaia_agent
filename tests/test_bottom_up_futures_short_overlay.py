"""Phase 3: Short-Overlay bei wrapper=FUTURE & Rohstoff/Edelmetall + Single-Fetch der Kurve."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from core.domain.models import FuturesCurveSnapshot
from core.domain.taxonomy import Underlying, Wrapper
from core.ports.futures_curve import FuturesCurveProvider
from orchestrators.bottom_up_orchestrator import BottomUpOrchestrator


def _snap():
    return FuturesCurveSnapshot(spot=140.0, front=100.0, next_=106.0,
                                days_to_front_expiry=30, days_between_expiries=182,
                                risk_free_rate=0.05, storage_cost=0.0, margin_quote=0.10)


def _orchestrator(futures_curve_provider=None, cost_floor_provider=None):
    orch = BottomUpOrchestrator(
        fundamentals_provider=MagicMock(), macro_provider=MagicMock(),
        market_provider=MagicMock(), llm=MagicMock(), bus=MagicMock(),
        futures_curve_provider=futures_curve_provider, cost_floor_provider=cost_floor_provider,
    )
    orch.commodity_chief = MagicMock()
    orch.commodity_chief.run = AsyncMock(return_value=MagicMock())
    pm_result = MagicMock(); pm_result.valuation_range = None
    orch.precious_metals_chief = MagicMock()
    orch.precious_metals_chief.run = AsyncMock(return_value=pm_result)
    return orch


def test_commodity_future_attaches_futures_short():
    provider = MagicMock(spec=FuturesCurveProvider)
    provider.get_curve = AsyncMock(return_value=_snap())
    orch = _orchestrator(futures_curve_provider=provider)
    res = asyncio.run(orch.run("CL", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE))
    assert res.futures_short is not None
    assert res.futures_short.available is True


def test_single_fetch_curve_called_once():
    provider = MagicMock(spec=FuturesCurveProvider)
    provider.get_curve = AsyncMock(return_value=_snap())
    orch = _orchestrator(futures_curve_provider=provider)
    asyncio.run(orch.run("CL", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE))
    # Long- UND Short-Overlay teilen denselben Snapshot ⇒ genau EIN Provider-Aufruf.
    assert provider.get_curve.call_count == 1


def test_non_future_commodity_has_no_futures_short():
    provider = MagicMock(spec=FuturesCurveProvider)
    provider.get_curve = AsyncMock(return_value=_snap())
    orch = _orchestrator(futures_curve_provider=provider)
    res = asyncio.run(orch.run("DBC", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUND))
    assert res.futures_short is None


def test_cost_floor_provider_exception_does_not_crash():
    provider = MagicMock(spec=FuturesCurveProvider)
    provider.get_curve = AsyncMock(return_value=_snap())
    floor = MagicMock()
    floor.get_cost_floor = AsyncMock(side_effect=RuntimeError("boom"))
    orch = _orchestrator(futures_curve_provider=provider, cost_floor_provider=floor)
    res = asyncio.run(orch.run("CL", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE))
    assert res.futures_short is not None
    assert res.futures_short.floor_applied is False


def test_precious_metal_future_attaches_futures_short():
    provider = MagicMock(spec=FuturesCurveProvider)
    provider.get_curve = AsyncMock(return_value=_snap())
    orch = _orchestrator(futures_curve_provider=provider)
    res = asyncio.run(orch.run("GC", underlying=Underlying.PRECIOUS_METAL, wrapper=Wrapper.FUTURE))
    assert res.futures_short is not None
    assert res.futures_short.available is True
