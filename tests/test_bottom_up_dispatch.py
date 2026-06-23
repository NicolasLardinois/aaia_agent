"""TDD Task 7: BottomUpOrchestrator.run() nimmt underlying/wrapper und verzweigt korrekt.

Testet:
- XLE (EQUITY_INDEX/FUND) → index_chief, NICHT equity_chief
- AAPL (EQUITY/SINGLE) → equity_chief
- Gold (PRECIOUS_METAL/FUTURE) → precious_metals_chief
- Bond (BOND/SINGLE) → bond_chief
- Rohstoff (COMMODITY/FUTURE) → commodity_chief
- Legacy-Compat: str "equity" → legacy_to_taxonomy → run() korrekt
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.domain.taxonomy import Underlying, Wrapper
from core.domain.models import BottomUpResult
from orchestrators.bottom_up_orchestrator import BottomUpOrchestrator


def _minimal_result(ticker: str, underlying: Underlying, wrapper: Wrapper) -> BottomUpResult:
    """Minimales BottomUpResult für Mocks."""
    return BottomUpResult(
        ticker=ticker,
        underlying=underlying,
        wrapper=wrapper,
        fundamentals=None, quality=None, short_interest=None, insider=None,
        earnings_trend=None, moat=None, valuation_range=None,
        precious_metals=None, bond=None, index=None, commodity_deep=None,
    )


def _orchestrator_mit_gemockten_chiefs() -> BottomUpOrchestrator:
    """Erzeugt einen BottomUpOrchestrator mit allen Chiefs als AsyncMock.

    Alle Chiefs haben eine `.run`-Methode als AsyncMock und eine `default()`-Klassenmethode.
    Der Rückgabewert von `.run` ist ein MagicMock (ausreichend für Dispatch-Tests).
    """
    # Ports (werden nur im Konstruktor übergeben, hier nicht benötigt)
    dummy_fund  = MagicMock()
    dummy_macro = MagicMock()
    dummy_mkt   = MagicMock()
    dummy_llm   = MagicMock()
    dummy_bus   = MagicMock()

    orch = BottomUpOrchestrator(
        fundamentals_provider=dummy_fund,
        macro_provider=dummy_macro,
        market_provider=dummy_mkt,
        llm=dummy_llm,
        bus=dummy_bus,
    )

    # Equity Chief
    orch.equity_chief = MagicMock()
    orch.equity_chief.run = AsyncMock(return_value=MagicMock(
        fundamentals=None, quality=None, short_interest=None,
        insider=None, earnings_trend=None, moat=None, valuation_range=None, momentum=None,
    ))
    orch.equity_chief.default = MagicMock(return_value=orch.equity_chief.run.return_value)

    # Bond Chief
    orch.bond_chief = MagicMock()
    orch.bond_chief.run = AsyncMock(return_value=MagicMock())
    orch.bond_chief.default = MagicMock(return_value=MagicMock(
        metrics=MagicMock(), duration=MagicMock(), credit=MagicMock()
    ))

    # Index Chief
    idx_result = MagicMock()
    orch.index_chief = MagicMock()
    orch.index_chief.run = AsyncMock(return_value=idx_result)
    orch.index_chief.default = MagicMock(return_value=idx_result)

    # Commodity Chief
    orch.commodity_chief = MagicMock()
    orch.commodity_chief.run = AsyncMock(return_value=MagicMock())
    orch.commodity_chief.default = MagicMock(return_value=MagicMock())

    # Precious Metals Chief
    pm_result = MagicMock()
    pm_result.valuation_range = None
    orch.precious_metals_chief = MagicMock()
    orch.precious_metals_chief.run = AsyncMock(return_value=pm_result)
    orch.precious_metals_chief.default = MagicMock(return_value=pm_result)

    return orch


# ── Test 1: EQUITY_INDEX/FUND → index_chief (der XLE-Bug-Fix) ─────────────
def test_dispatch_equity_index_fund_routet_zu_index_chief():
    """XLE (ETF auf Energie-Sektor): underlying=EQUITY_INDEX, wrapper=FUND → index_chief.run.

    Testet den zentralen Dispatch-Bug: vorher fiel 'etf' in die Equity-Engine.
    Jetzt muss EQUITY_INDEX explizit zur Index-Engine routen.
    """
    orch = _orchestrator_mit_gemockten_chiefs()
    asyncio.run(orch.run("XLE", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND))
    orch.index_chief.run.assert_awaited_once()
    orch.equity_chief.run.assert_not_awaited()


# ── Test 2: EQUITY/SINGLE → equity_chief ──────────────────────────────────
def test_dispatch_equity_single_routet_zu_equity_chief():
    """AAPL (Einzelaktie): underlying=EQUITY → equity_chief."""
    orch = _orchestrator_mit_gemockten_chiefs()
    asyncio.run(orch.run("AAPL", underlying=Underlying.EQUITY, wrapper=Wrapper.SINGLE))
    orch.equity_chief.run.assert_awaited_once()
    orch.index_chief.run.assert_not_awaited()


# ── Test 3: PRECIOUS_METAL → precious_metals_chief ─────────────────────────
def test_dispatch_precious_metal_routet_zu_pm_chief():
    """GC=F (Gold-Future): underlying=PRECIOUS_METAL → precious_metals_chief."""
    orch = _orchestrator_mit_gemockten_chiefs()
    asyncio.run(orch.run("GC=F", underlying=Underlying.PRECIOUS_METAL, wrapper=Wrapper.FUTURE))
    orch.precious_metals_chief.run.assert_awaited_once()
    orch.equity_chief.run.assert_not_awaited()


# ── Test 4: COMMODITY → commodity_chief ────────────────────────────────────
def test_dispatch_commodity_routet_zu_commodity_chief():
    """CL=F (WTI-Crude-Future): underlying=COMMODITY → commodity_chief."""
    orch = _orchestrator_mit_gemockten_chiefs()
    asyncio.run(orch.run("CL=F", underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE))
    orch.commodity_chief.run.assert_awaited_once()
    orch.equity_chief.run.assert_not_awaited()


# ── Test 5: BOND → bond_chief ──────────────────────────────────────────────
def test_dispatch_bond_routet_zu_bond_chief():
    """TLT (US-Treasuries-ETF als Bond): underlying=BOND → bond_chief."""
    orch = _orchestrator_mit_gemockten_chiefs()
    asyncio.run(orch.run("TLT", underlying=Underlying.BOND, wrapper=Wrapper.SINGLE))
    orch.bond_chief.run.assert_awaited_once()
    orch.equity_chief.run.assert_not_awaited()


# ── Test 6: EQUITY_INDEX/SINGLE → index_chief (direkter Index) ─────────────
def test_dispatch_equity_index_single_routet_zu_index_chief():
    """SPX (direkter Aktienindex): underlying=EQUITY_INDEX, wrapper=SINGLE → index_chief."""
    orch = _orchestrator_mit_gemockten_chiefs()
    asyncio.run(orch.run("^GSPC", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.SINGLE))
    orch.index_chief.run.assert_awaited_once()
    orch.equity_chief.run.assert_not_awaited()
