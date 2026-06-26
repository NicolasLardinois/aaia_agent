import asyncio
import logging

from agents.market_cockpit.commodity.precious_metals_macro_agent import (
    PreciousMetalsMacroAgent,
    _signal,
)
from core.domain.models import Signal


def test_none_inputs_is_neutral():
    assert _signal(gs_pct=None, gold_z=None) == Signal.NEUTRAL


def test_high_gs_percentile_is_bearish():
    # GS-Ratio im oberen Extrem (>0.85 Perzentil) → Risikoaversion → BEARISH für Risiko
    assert _signal(gs_pct=0.92, gold_z=0.3) == Signal.BEARISH


def test_low_gs_percentile_is_bullish():
    # GS-Ratio im unteren Extrem (<0.15) → Risk-on → BULLISH
    assert _signal(gs_pct=0.08, gold_z=0.0) == Signal.BULLISH


def test_gold_momentum_spike_is_bearish():
    # Gold-z > +1.5 (Safe-Haven-Flucht) überschreibt neutrales GS → BEARISH
    assert _signal(gs_pct=0.50, gold_z=1.8) == Signal.BEARISH


def test_mid_percentile_no_momentum_is_neutral():
    assert _signal(gs_pct=0.50, gold_z=0.2) == Signal.NEUTRAL


# --- Logging: ausgefallener Gold-Preis wird als warning sichtbar (Befund 2 / Bug #46) ---

class _RaisingMarket:
    def get_current_price(self, ticker):
        raise RuntimeError("Quelle down")
    def get_price_history(self, ticker, period="1y"):
        return None


class _Bus:
    def publish(self, event):
        pass


def test_run_loggt_warnung_bei_ausgefallener_preisquelle(caplog):
    agent = PreciousMetalsMacroAgent(_RaisingMarket(), _Bus())
    with caplog.at_level(logging.WARNING):
        snap = asyncio.run(agent.run())
    assert snap.gold_usd is None
    assert "Gold" in caplog.text
