from agents.market_cockpit.commodity.energy_agent import _signal
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
