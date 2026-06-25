import asyncio
from unittest.mock import MagicMock

from agents.market_cockpit.macro.inflation_agent import InflationAgent, _signal, _cpi_trend
from core.domain.models import Signal


def _make_agent(*, eco=None, ext=None, ecb_cpi=None, ecb_core=None, ecb_ppi=None,
                ecb_10y=None, cpi_hist=None):
    macro = MagicMock()
    macro.get_economic_state.return_value = eco or {}
    macro.get_extended_state.return_value = ext or {}
    macro.get_cpi_history.return_value = cpi_hist if cpi_hist is not None else []
    ecb = MagicMock()
    ecb.get_cpi.return_value = ecb_cpi
    ecb.get_core_cpi.return_value = ecb_core
    ecb.get_ppi.return_value = ecb_ppi
    ecb.get_aaa_10y_yield.return_value = ecb_10y
    snb = MagicMock()
    snb.get_cpi.return_value = None
    snb.get_core_cpi.return_value = None
    return InflationAgent(macro=macro, ecb=ecb, snb=snb, bus=MagicMock())


def test_eu_real_rate_10y_aus_yield_minus_cpi():
    """EU Real Rate 10Y = ECB-AAA-10Y-Rendite − EU-HICP (2.94 − 2.0 = 0.94)."""
    agent = _make_agent(ecb_cpi=2.0, ecb_10y=2.94)
    result = asyncio.run(agent.run())
    assert result.eurozone.real_rate_10y == 0.94


def test_eu_hoher_realzins_drueckt_signal_bearish():
    """EU CPI im Ziel (2.0 → sonst BULLISH), aber Realzins 2.5% → Bewertungs-Gegenwind → BEARISH."""
    agent = _make_agent(ecb_cpi=2.0, ecb_10y=4.5)  # real = 2.5 > 2.0
    result = asyncio.run(agent.run())
    assert result.eurozone.real_rate_10y == 2.5
    assert result.eurozone.signal == Signal.BEARISH


def test_eu_real_rate_none_ohne_yield():
    agent = _make_agent(ecb_cpi=2.0, ecb_10y=None)
    result = asyncio.run(agent.run())
    assert result.eurozone.real_rate_10y is None


def test_usa_core_cpi_und_pce_aus_extended_state():
    """USA Core-CPI (CPILFESL) und PCE (PCEPI) werden aus extended_state befüllt."""
    agent = _make_agent(eco={"inflation": 2.5}, ext={"core_cpi": 2.9, "pce": 2.6})
    result = asyncio.run(agent.run())
    assert result.usa.core_cpi == 2.9
    assert result.usa.pce == 2.6


def test_usa_hohe_cpi_niedriger_core_entschaerft_via_run():
    """CPI 4.5% aber Core 2.2% → transiente Inflation → USA-Signal NEUTRAL (vorher BEARISH)."""
    agent = _make_agent(eco={"inflation": 4.5}, ext={"core_cpi": 2.2})
    result = asyncio.run(agent.run())
    assert result.usa.signal == Signal.NEUTRAL


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

def test_cpi_3_5_stable_is_bearish_no_gap():
    # 3.5% liegt jetzt in der "erhöht"-Klasse (lückenlos) → BEARISH bei stable
    assert _signal(3.5, trend="stable") == Signal.BEARISH

def test_cpi_3_5_falling_is_neutral():
    # 3.5% aber fallend (Δ über 3–6M negativ) → Momentum entschärft → NEUTRAL
    assert _signal(3.5, trend="falling") == Signal.NEUTRAL

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
    """2.5% CHF — erhöht für CH aber fallend-Klasse → NEUTRAL (2.5 > 2.0 high, < 3.0 bearish)."""
    assert _signal(2.5, region="ch") == Signal.BEARISH

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
    """CPI 0.5% (neutral, unter Ziel), PPI 5.0% → Pipeline-Inflation → BEARISH."""
    assert _signal(0.5, ppi=5.0) == Signal.BEARISH

def test_neutral_cpi_low_ppi_stays_neutral():
    """CPI 0.5% (neutral), PPI 2.0% → keine Pipeline-Inflation → bleibt NEUTRAL."""
    assert _signal(0.5, ppi=2.0) == Signal.NEUTRAL


# ── Realzins-Gegenwind ────────────────────────────────────────────────────

def test_cpi_2_with_high_real_rate_is_bearish():
    # CPI im Ziel, aber Realzins >2% → Bewertungs-Gegenwind → BEARISH
    assert _signal(2.0, real_rate_10y=2.5) == Signal.BEARISH

def test_cpi_2_with_normal_real_rate_stays_bullish():
    assert _signal(2.0, real_rate_10y=0.5) == Signal.BULLISH


# ── Trend-Modifikator: "rising" verschärft (symmetrisch zu "falling") ──────

def test_cpi_high_low_core_but_rising_resharpens_to_bearish():
    """CPI 4.5% (>Ziel), Core 2.2% (≤high) → sonst NEUTRAL (transitorisch), aber
    Inflation BESCHLEUNIGT → 'transitorisch'-These untergraben → zurück auf BEARISH."""
    assert _signal(4.5, core_cpi=2.2, trend="rising") == Signal.BEARISH


def test_cpi_high_low_core_falling_stays_neutral():
    """Gegenprobe: gleiche Lage, aber fallend → bleibt entschärft NEUTRAL."""
    assert _signal(4.5, core_cpi=2.2, trend="falling") == Signal.NEUTRAL


def test_cpi_in_band_rising_stays_bullish():
    """CPI 2.5% im Ziel (BULLISH). Steigender Trend allein kippt ein gesundes
    LEVEL nicht — Trend verschärft nur den core-entschärften Sonderfall."""
    assert _signal(2.5, trend="rising") == Signal.BULLISH


def test_cpi_high_rising_no_core_stays_bearish():
    """Erhöhte CPI ohne Core-Rabatt ist bereits BEARISH; rising lässt das unverändert."""
    assert _signal(4.5, trend="rising") == Signal.BEARISH


# ── _cpi_trend: Klassifizierung der YoY-CPI-Historie ──────────────────────

def test_cpi_trend_rising():
    """YoY-CPI steigt klar über das Fenster (Δ Halbmittel ≥ 0.3pp) → 'rising'."""
    assert _cpi_trend([2.0, 2.2, 2.5, 2.9, 3.2, 3.5]) == "rising"


def test_cpi_trend_falling():
    assert _cpi_trend([5.0, 4.6, 4.0, 3.5, 3.0, 2.5]) == "falling"


def test_cpi_trend_stable_within_deadband():
    """Δ Halbmittel < 0.3pp → Rauschen → 'stable' (kein Flip-Flop)."""
    assert _cpi_trend([2.0, 2.05, 2.1, 2.1, 2.15, 2.2]) == "stable"


def test_cpi_trend_empty_is_stable():
    assert _cpi_trend([]) == "stable"


def test_cpi_trend_single_is_stable():
    assert _cpi_trend([2.5]) == "stable"


# ── run()-Wiring: USA-CPI-Trend aus get_cpi_history ───────────────────────

def test_usa_cpi_trend_aus_history_resharpens_via_run():
    """CPI 4.5% + Core 2.2% → ohne Trend NEUTRAL; mit steigender History → BEARISH."""
    agent = _make_agent(eco={"inflation": 4.5}, ext={"core_cpi": 2.2},
                        cpi_hist=[2.0, 2.5, 3.0, 3.5, 4.0, 4.5])
    result = asyncio.run(agent.run())
    assert result.usa.signal == Signal.BEARISH


def test_usa_ohne_cpi_history_bleibt_neutral_via_run():
    """Ohne History (Default []) → Trend 'stable' → core-entschärftes NEUTRAL bleibt."""
    agent = _make_agent(eco={"inflation": 4.5}, ext={"core_cpi": 2.2})
    result = asyncio.run(agent.run())
    assert result.usa.signal == Signal.NEUTRAL
