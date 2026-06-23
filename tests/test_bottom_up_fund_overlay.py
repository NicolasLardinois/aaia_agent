"""Phase 2b: Info-Overlay bei wrapper=FUND im BottomUpOrchestrator.

Die Fonds-Info-Schicht (§6.6) hängt am *Wrapper*, nicht am Basiswert: JEDER ETF/Fonds
(Aktien-, Anleihe-, Rohstoff-, Edelmetall-Hülle) bekommt sie, sobald wrapper=FUND ist.

- Fonds-Hülle → FundInfo am Ergebnis (Index- UND Nicht-Index-Pfad).
- Nicht-Fonds-Hülle (SINGLE/Future) → keine Fund-Info.
- Provider fehlt / wirft / liefert None → unavailable (defensiv, kein Crash).
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


class _RaisingFund(FundInfoProvider):
    async def get_fund_info(self, symbol):
        raise RuntimeError("Quelle kaputt")


class _NoneFund(FundInfoProvider):
    async def get_fund_info(self, symbol):
        return None


def _orch(fund_info_provider=None):
    orch = BottomUpOrchestrator(
        fundamentals_provider=MagicMock(), macro_provider=MagicMock(),
        market_provider=MagicMock(), llm=MagicMock(), bus=MagicMock(),
        fund_info_provider=fund_info_provider,
    )
    # Alle Chiefs durch schnelle Mocks ersetzen — der Test prüft nur das Fund-Overlay,
    # nicht die Engine-Logik dahinter.
    stub = MagicMock()
    for chief in ("index_chief", "equity_chief", "bond_chief",
                  "commodity_chief", "precious_metals_chief"):
        m = MagicMock()
        m.run = AsyncMock(return_value=stub)
        m.default = MagicMock(return_value=stub)
        setattr(orch, chief, m)
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


def test_fund_wrapper_on_non_index_attaches_info():
    """Auch Nicht-Index-ETFs (z. B. Edelmetall-ETF GLD) sind Fonds-Hüllen und bekommen die
    Info-Schicht — die Schicht hängt am Wrapper, nicht nur am Index-Pfad."""
    res = asyncio.run(_orch(_FakeFund()).run("GLD", underlying=Underlying.PRECIOUS_METAL, wrapper=Wrapper.FUND))
    assert res.fund_info is not None
    assert res.fund_info.available is True


def test_non_fund_wrapper_on_non_index_has_no_info():
    """Gegenprobe: Edelmetall ohne Fonds-Hülle (Direktbesitz/Future) → keine Schicht."""
    res = asyncio.run(_orch(_FakeFund()).run("XAU", underlying=Underlying.PRECIOUS_METAL, wrapper=Wrapper.SINGLE))
    assert res.fund_info is None


def test_fund_provider_error_is_unavailable():
    """Defensiv: Provider wirft → unavailable statt Crash."""
    res = asyncio.run(_orch(_RaisingFund()).run("XLE", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND))
    assert res.fund_info is not None
    assert res.fund_info.available is False


def test_fund_provider_none_is_unavailable():
    """Provider liefert None (keine Daten) → unavailable."""
    res = asyncio.run(_orch(_NoneFund()).run("XLE", underlying=Underlying.EQUITY_INDEX, wrapper=Wrapper.FUND))
    assert res.fund_info is not None
    assert res.fund_info.available is False
