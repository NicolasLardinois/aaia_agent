from agents.market_cockpit.macro.inflation_agent import _signal
from core.domain.models import Signal


def test_cpi_none_is_neutral():
    assert _signal(None) == Signal.NEUTRAL

def test_cpi_deflation_is_bearish():
    assert _signal(-0.5) == Signal.BEARISH

def test_cpi_zero_is_neutral():
    assert _signal(0.0) == Signal.NEUTRAL

def test_cpi_0_5_is_neutral():
    """Unter Zielbereich aber keine Deflation → NEUTRAL."""
    assert _signal(0.5) == Signal.NEUTRAL

def test_cpi_1_is_bullish():
    assert _signal(1.0) == Signal.BULLISH

def test_cpi_2_is_bullish():
    assert _signal(2.0) == Signal.BULLISH

def test_cpi_3_is_bullish():
    assert _signal(3.0) == Signal.BULLISH

def test_cpi_3_5_is_neutral():
    """CPI 3.5% — erhöht aber nicht kritisch → NEUTRAL."""
    assert _signal(3.5) == Signal.NEUTRAL

def test_cpi_4_exact_is_bearish():
    """CPI exakt 4.0% — war NEUTRAL wegen '> 4.0' statt '>= 4.0'."""
    assert _signal(4.0) == Signal.BEARISH

def test_cpi_5_is_bearish():
    assert _signal(5.0) == Signal.BEARISH
