import asyncio

from core.domain.models import FundInfo
from core.ports.fund_info import FundInfoProvider
from adapters.data.fund_info_stub import StubFundInfoProvider


def test_unavailable_factory():
    fi = FundInfo.unavailable()
    assert fi.available is False
    assert fi.ter is None and fi.tracking_error is None


def test_of_derives_available_from_ter():
    # available ist kein frei setzbares Feld mehr: TER vorhanden → verfügbar, auch wenn der
    # Tracking-Error separat fehlt (Benchmark unbekannt) — §6.6.
    assert FundInfo.of(0.001, 0.02).available is True
    assert FundInfo.of(0.001, None).available is True
    # Ohne TER nicht "verfügbar" — die TER ist der Anker, auch wenn ein TE vorliegt.
    assert FundInfo.of(None, 0.02).available is False
    assert FundInfo.of(None, None).available is False


def test_stub_returns_none():
    # asyncio.run(...) statt @pytest.mark.asyncio — Projekt-Konvention (requirements-dev.txt:
    # kein pytest-asyncio-Plugin), sonst "async def functions are not natively supported".
    provider = StubFundInfoProvider()
    assert isinstance(provider, FundInfoProvider)
    assert asyncio.run(provider.get_fund_info("XLE")) is None
