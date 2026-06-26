import asyncio
import logging

from agents.market_cockpit.commodity.agricultural_agent import AgriculturalAgent, _signal
from core.domain.models import Signal


def test_all_near_zero_z_is_neutral():
    assert _signal([0.2, -0.1, 0.0, 0.3, -0.2, 0.1, 0.0]) == Signal.NEUTRAL


def test_median_z_above_threshold_is_bearish():
    # Median-z > +1.0 → Agrar-Inflation → BEARISH
    assert _signal([1.4, 1.2, 1.6, 1.1, 1.3, 0.2, 1.5]) == Signal.BEARISH


def test_median_z_below_threshold_is_bullish():
    # Median-z < -1.0 → Preisentlastung → BULLISH
    assert _signal([-1.4, -1.2, -1.6, -1.1, -1.3, -0.2, -1.5]) == Signal.BULLISH


def test_single_outlier_does_not_flip_median():
    assert _signal([3.0, 0.1, -0.1, 0.0, 0.2, 0.1, 0.0]) == Signal.NEUTRAL


def test_empty_returns_neutral():
    assert _signal([]) == Signal.NEUTRAL


def test_moderate_positive_z_below_1_is_neutral():
    # z=0.5 überschreitet den alten ±20%-Schwelle bei %-Werten, aber nicht die z-Score-Schwelle 1.0
    # → mit z-Score-Logik: NEUTRAL
    assert _signal([0.5, 0.6, 0.4, 0.55, 0.45, 0.5, 0.5]) == Signal.NEUTRAL


# --- Logging: ausgefallener Agrar-Preis wird als warning sichtbar (Befund 2 / Bug #46) ---

class _RaisingMarket:
    def get_current_price(self, ticker):
        raise RuntimeError("Quelle down")
    def get_price_history(self, ticker, period="1y"):
        return None


class _Bus:
    def publish(self, event):
        pass


def test_run_loggt_warnung_bei_ausgefallener_preisquelle(caplog):
    agent = AgriculturalAgent(_RaisingMarket(), _Bus())
    with caplog.at_level(logging.WARNING):
        snap = asyncio.run(agent.run())
    assert snap.wheat_usd is None
    assert "Wheat" in caplog.text
