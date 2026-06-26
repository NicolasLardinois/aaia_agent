import asyncio
import logging

from agents.market_cockpit.commodity.energy_agent import EnergyAgent, _signal
from core.domain.models import Signal


def test_no_momentum_is_neutral():
    # Alle Returns ~0 → NEUTRAL
    assert _signal(wti_z=0.0, brent_z=0.0, gas_z=0.0) == Signal.NEUTRAL


def test_strong_positive_oil_momentum_is_bearish():
    # WTI/Brent stark gestiegen (z > +1.0) → Inflationsdruck → BEARISH für Risiko
    assert _signal(wti_z=1.5, brent_z=1.4, gas_z=0.2) == Signal.BEARISH


def test_strong_negative_oil_momentum_is_bearish():
    # Öl bricht ein (z < -1.0) → Nachfrageschwäche → BEARISH
    assert _signal(wti_z=-1.6, brent_z=-1.5, gas_z=-0.3) == Signal.BEARISH


def test_gas_spike_alone_is_bearish():
    # Gas-z extrem (>2.0), Öl neutral → EU-Energiekosten-Schock → BEARISH
    assert _signal(wti_z=0.1, brent_z=0.0, gas_z=2.4) == Signal.BEARISH


def test_zero_wti_does_not_fall_back_silently():
    # wti_z=0.0 ist ein valider Wert (kein Falsiness-Fallback)
    assert _signal(wti_z=0.0, brent_z=0.0, gas_z=0.0) == Signal.NEUTRAL


def test_all_none_is_neutral():
    assert _signal(wti_z=None, brent_z=None, gas_z=None) == Signal.NEUTRAL


# --- Logging: ein ausgefallener Preis-Call wird als warning sichtbar (Befund 2 / Bug #46) ---

class _RaisingMarket:
    """Spotpreis fällt aus (wirft), Historie liefert None (kein Crash)."""
    def get_current_price(self, ticker):
        raise RuntimeError("Quelle down")
    def get_price_history(self, ticker, period="1y"):
        return None


class _Bus:
    def publish(self, event):
        pass


def test_run_loggt_warnung_bei_ausgefallener_preisquelle(caplog):
    agent = EnergyAgent(_RaisingMarket(), _Bus())
    with caplog.at_level(logging.WARNING):
        snap = asyncio.run(agent.run())
    # Default greift weiter (kein Crash), aber der Ausfall ist jetzt sichtbar (nicht mehr still)
    assert snap.wti_usd is None
    assert "WTI" in caplog.text
