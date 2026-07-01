from datetime import date

from adapters.data.caching_data_provider import (
    CachingEcbProvider,
    CachingMarketProvider,
    wrap_providers,
)
from adapters.persistence.composite_snapshot_store import CompositeSnapshotStore
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory
from core.domain.run_context import RunContext


class _E:  # minimaler ECB-Doppelgänger (Duck-Typing reicht dem Decorator)
    def __getattr__(self, name):
        return lambda *a, **k: None


class _M:
    def __getattr__(self, name):
        return lambda *a, **k: None


def test_wrap_providers_liefert_beide_caching_decorators(tmp_path):
    run = RunContext(as_of=date(2026, 7, 1))
    store = CompositeSnapshotStore(InMemoryDatedHistory(), str(tmp_path / "b.json"))
    ecb, market = wrap_providers(_E(), _M(), run, store)
    assert isinstance(ecb, CachingEcbProvider)
    assert isinstance(market, CachingMarketProvider)


def test_settings_hat_ttl_konstante():
    import config.settings as settings
    assert isinstance(settings.SNAPSHOT_TTL_DAYS, int)
    assert settings.SNAPSHOT_TTL_DAYS >= 1
