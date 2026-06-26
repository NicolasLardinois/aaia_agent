import asyncio

from agents.market_cockpit.commodity.industrial_metals_agent import (
    IndustrialMetalsAgent,
    _signal,
)
from core.domain.models import Signal


def test_no_momentum_is_neutral():
    assert _signal(copper_gold_z=0.0) == Signal.NEUTRAL


def test_rising_copper_gold_ratio_is_bullish():
    # Dr. Copper steigt relativ zu Gold → Risk-on / Wachstum → BULLISH
    assert _signal(copper_gold_z=1.3) == Signal.BULLISH


def test_falling_copper_gold_ratio_is_bearish():
    # Kupfer fällt relativ zu Gold → Flucht in Sicherheit → BEARISH
    assert _signal(copper_gold_z=-1.3) == Signal.BEARISH


def test_none_is_neutral():
    assert _signal(copper_gold_z=None) == Signal.NEUTRAL


# --- run()-Verdrahtung: Zink/Nickel kommen jetzt über den injizierten Port ----

class _FakeMarket:
    """Minimaler MarketDataProvider-Stub: Kupfer/Alu-Preis, keine Historie."""
    def get_current_price(self, ticker):
        return 4.0
    def get_price_history(self, ticker, period="1y"):
        return None


class _FakeBus:
    def publish(self, event):
        pass


class _FakeMetalSpot:
    def __init__(self, prices):
        self._prices = prices
    def get_spot_price(self, symbol):
        return self._prices.get(symbol)


def test_run_uses_injected_metal_spot_for_zinc_nickel():
    # LME-Metalle (Zink/Nickel) kommen aus dem Port, nicht mehr aus hartkodiertem requests-I/O.
    agent = IndustrialMetalsAgent(
        _FakeMarket(), _FakeBus(),
        metal_spot=_FakeMetalSpot({"ZINC": 2500.0, "NICKEL": 18000.0}),
    )
    snap = asyncio.run(agent.run())
    assert snap.zinc_usd == 2500.0
    assert snap.nickel_usd == 18000.0


def test_run_without_metal_spot_yields_none_zinc_nickel():
    # Ohne injizierten Port bleiben Zink/Nickel None (kein I/O, kein Crash).
    agent = IndustrialMetalsAgent(_FakeMarket(), _FakeBus())
    snap = asyncio.run(agent.run())
    assert snap.zinc_usd is None
    assert snap.nickel_usd is None


def test_run_survives_metal_spot_exception():
    # Fällt der Port aus, liefert der Agent trotzdem ein Ergebnis (Zink/Nickel None).
    class _Boom:
        def get_spot_price(self, symbol):
            raise RuntimeError("FMP down")
    agent = IndustrialMetalsAgent(_FakeMarket(), _FakeBus(), metal_spot=_Boom())
    snap = asyncio.run(agent.run())
    assert snap.zinc_usd is None
    assert snap.nickel_usd is None


# --- Logging: ausgefallener Kupfer-Preis wird als warning sichtbar (Befund 2 / Bug #46) ---

def test_run_loggt_warnung_bei_ausgefallenem_kupferpreis(caplog):
    import logging

    class _RaisingMarket:
        def get_current_price(self, ticker):
            raise RuntimeError("Quelle down")
        def get_price_history(self, ticker, period="1y"):
            return None

    agent = IndustrialMetalsAgent(_RaisingMarket(), _FakeBus())
    with caplog.at_level(logging.WARNING):
        snap = asyncio.run(agent.run())
    assert snap.copper_usd is None
    assert "Copper" in caplog.text
