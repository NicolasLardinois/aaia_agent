from agents.market_cockpit.macro.inflation_agent import _signal
from core.domain.models import Signal


# ── USA/EU Basis-Schwellen (unverändert) ─────────────────────────────────

def test_cpi_none_is_neutral():
    assert _signal(None) == Signal.NEUTRAL

def test_cpi_deflation_is_bearish():
    assert _signal(-0.5) == Signal.BEARISH

def test_cpi_zero_is_neutral():
    assert _signal(0.0) == Signal.NEUTRAL

def test_cpi_0_5_is_neutral():
    assert _signal(0.5) == Signal.NEUTRAL

def test_cpi_1_is_bullish():
    assert _signal(1.0) == Signal.BULLISH

def test_cpi_2_is_bullish():
    assert _signal(2.0) == Signal.BULLISH

def test_cpi_3_is_bullish():
    assert _signal(3.0) == Signal.BULLISH

def test_cpi_3_5_is_neutral():
    assert _signal(3.5) == Signal.NEUTRAL

def test_cpi_4_exact_is_bearish():
    assert _signal(4.0) == Signal.BEARISH

def test_cpi_5_is_bearish():
    assert _signal(5.0) == Signal.BEARISH


# ── Schweiz-spezifische Schwellen ─────────────────────────────────────────

def test_ch_0_9_is_bullish():
    """0.9% CHF-Inflation liegt im CH-Zielbereich (0.5–2%) → BULLISH."""
    assert _signal(0.9, region="ch") == Signal.BULLISH

def test_ch_0_3_is_neutral():
    """0.3% CHF — unter CH-Zielbereich aber keine Deflation → NEUTRAL."""
    assert _signal(0.3, region="ch") == Signal.NEUTRAL

def test_ch_2_5_is_neutral():
    """2.5% CHF — erhöht für CH → NEUTRAL."""
    assert _signal(2.5, region="ch") == Signal.NEUTRAL

def test_ch_3_5_is_bearish():
    """3.5% CHF — klar zu hoch für CH → BEARISH."""
    assert _signal(3.5, region="ch") == Signal.BEARISH


# ── Core CPI: abschwächen bei transientem BEARISH ─────────────────────────

def test_high_cpi_low_core_cpi_downgrades_to_neutral():
    """CPI 4.5% aber Core 2.2% → Inflation durch Energie/Lebensmittel, nicht strukturell."""
    assert _signal(4.5, core_cpi=2.2) == Signal.NEUTRAL

def test_high_cpi_high_core_cpi_stays_bearish():
    """CPI 4.5%, Core 4.0% → strukturelle Inflation → bleibt BEARISH."""
    assert _signal(4.5, core_cpi=4.0) == Signal.BEARISH


# ── PPI: verstärken bei Pipeline-Inflation ────────────────────────────────

def test_neutral_cpi_high_ppi_upgrades_to_bearish():
    """CPI 3.5% (neutral), PPI 5.0% → mehr Inflation in der Pipeline → BEARISH."""
    assert _signal(3.5, ppi=5.0) == Signal.BEARISH

def test_neutral_cpi_low_ppi_stays_neutral():
    """CPI 3.5%, PPI 2.0% → keine Pipeline-Inflation → bleibt NEUTRAL."""
    assert _signal(3.5, ppi=2.0) == Signal.NEUTRAL
