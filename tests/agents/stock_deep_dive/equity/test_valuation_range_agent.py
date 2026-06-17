import asyncio
import statistics
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.valuation_range_agent import ValuationRangeAgent, _combine_methods
from core.domain.models import ValuationMethod, Signal
from core.utils.valuation_math import two_stage_dcf, capm_wacc


def _make_agent(data: dict) -> ValuationRangeAgent:
    fundamentals = MagicMock()
    fundamentals.get_fundamentals.return_value = data
    market = MagicMock()
    market.get_current_price.return_value = data.get("current_price", 100.0)
    bus = MagicMock()
    return ValuationRangeAgent(fundamentals, market, bus)


def test_dcf_does_not_crash_when_wacc_equals_terminal_growth():
    agent = _make_agent({
        "current_price": 100.0,
        "fcf_per_share": 5.0,
        "wacc": 0.025,
        "revenue_cagr_3y": 10,
        "eps_trailing": 8.0,
    })
    result = asyncio.run(agent.run("AAPL"))
    assert result is not None


def test_terminal_growth_is_higher_for_tech_than_default():
    from agents.stock_deep_dive.equity.valuation_range_agent import _TERMINAL_GROWTH
    assert _TERMINAL_GROWTH["Technology"] > _TERMINAL_GROWTH["default"]
    assert _TERMINAL_GROWTH["Healthcare"] > _TERMINAL_GROWTH["default"]


def test_terminal_growth_used_in_dcf():
    """Tech-DCF verwendet 3.0% statt 2.5% — ergibt anderen Wert als default."""
    base_data = {
        "current_price": 100.0,
        "fcf_per_share": 5.0,
        "wacc": 0.09,
        "revenue_cagr_3y": 10,
    }
    tech_agent   = _make_agent({**base_data})
    default_agent = _make_agent({**base_data})

    import agents.stock_deep_dive.equity.valuation_range_agent as m
    original = m._TERMINAL_GROWTH.copy()
    try:
        tech_result    = asyncio.run(tech_agent.run("AAPL", sector="Technology"))
        default_result = asyncio.run(default_agent.run("AAPL", sector="default"))
    finally:
        m._TERMINAL_GROWTH.clear()
        m._TERMINAL_GROWTH.update(original)

    # Bei höherer terminal growth → grösserer Divisor (wacc - tg wird kleiner) → höherer DCF-Wert
    dcf_tech    = next((m for m in tech_result.methods    if m.name == "DCF"), None)
    dcf_default = next((m for m in default_result.methods if m.name == "DCF"), None)
    if dcf_tech and dcf_default:
        assert dcf_tech.high > dcf_default.high, "Tech DCF soll höher sein als default"


def test_band_aggregation_uses_median_not_extreme():
    methods = [
        ValuationMethod(name="KGV",       low=90.0,  high=130.0),
        ValuationMethod(name="EV/EBITDA", low=85.0,  high=120.0),
        ValuationMethod(name="DCF",       low=95.0,  high=125.0),
    ]
    low, high = _combine_methods(methods)
    assert low  == 90.0,  f"Expected median low 90.0, got {low}"
    assert high == 125.0, f"Expected median high 125.0, got {high}"


def test_dcf_uses_two_stage_not_gordon():
    """2-Stufen-DCF mit CAPM-WACC: bei fcf0=10, growth=10%, tg=0.025, wacc=0.10 (CAPM).
    Prüft, dass WACC aus CAPM kommt (rf+beta*erp=0.04+1.0*0.06=0.10) und
    das Szenario-Band gespreizt wird (low 0.7× < high 1.3×).
    revenue_cagr_3y=10 damit growth != 0 (sonst low==high by design, kein Band)."""
    fundamentals = MagicMock()
    fundamentals.get_fundamentals.return_value = {
        "current_price": 100.0,
        "fcf_per_share": 10.0,
        "revenue_cagr_3y": 10,  # 10% → growth=0.10 → Band 0.07..0.13
        "beta": 1.0, "risk_free_rate": 0.04, "erp": 0.06,
        "cost_of_debt": 0.05, "tax_rate": 0.21,
        "equity_weight": 1.0, "debt_weight": 0.0,
        "eps": 8.0, "pe_ratio": 15.0,
    }
    market = MagicMock(); market.get_current_price.return_value = 100.0
    bus = MagicMock()
    agent = ValuationRangeAgent(fundamentals, market, bus)
    result = asyncio.run(agent.run("AAPL", sector="default"))
    dcf = next((m for m in result.methods if m.name == "DCF"), None)
    assert dcf is not None
    # WACC = 0.04 + 1.0*0.06 = 0.10 (CAPM, all-equity). 2-Stufen-DCF mit fcf0=10, tg=0.025
    # liefert endlichen, positiven Wert; Szenario-Band sorgt für low < high.
    assert dcf.low > 0 and dcf.high > dcf.low


def test_dcf_skipped_without_fcf():
    fundamentals = MagicMock()
    fundamentals.get_fundamentals.return_value = {"current_price": 100.0, "eps": 5.0, "pe_ratio": 15.0}
    market = MagicMock(); market.get_current_price.return_value = 100.0
    agent = ValuationRangeAgent(fundamentals, market, MagicMock())
    result = asyncio.run(agent.run("AAPL"))
    assert all(m.name != "DCF" for m in result.methods)


# ── Fix 1: >0-Guards für EPS, EBITDA, FCF ────────────────────────────────────

def test_kgv_skipped_when_eps_negative():
    """Bei eps=-2.0 darf KGV-Multiple NICHT in die Kombination einfliessen —
    sonst entstehen negative/invertierte Bänder."""
    agent = _make_agent({
        "current_price": 50.0,
        "eps": -2.0,
        "pe_ratio": 20.0,
        "fcf_per_share": 3.0,
        "revenue_cagr_3y": 5,
    })
    result = asyncio.run(agent.run("AAPL"))
    assert all(m.name != "KGV-Multiple" for m in result.methods), (
        f"KGV-Multiple darf bei negativem EPS nicht erscheinen, methods={result.methods}"
    )
    # Sicherstellen: keine negativen Bänder im Ergebnis
    for m in result.methods:
        assert m.low >= 0, f"Methode {m.name} hat negatives low={m.low}"
        assert m.high >= 0, f"Methode {m.name} hat negatives high={m.high}"


def test_ebitda_skipped_when_ebitda_negative():
    """Bei ebitda_per_share=-3.0 darf EV/EBITDA-Multiple NICHT einfliessen."""
    agent = _make_agent({
        "current_price": 50.0,
        "eps": 2.0,
        "pe_ratio": 20.0,
        "ebitda_per_share": -3.0,
        "fcf_per_share": 3.0,
        "revenue_cagr_3y": 5,
    })
    result = asyncio.run(agent.run("AAPL"))
    assert all(m.name != "EV/EBITDA-Multiple" for m in result.methods), (
        f"EV/EBITDA-Multiple darf bei negativem EBITDA nicht erscheinen, methods={result.methods}"
    )
    for m in result.methods:
        assert m.low >= 0, f"Methode {m.name} hat negatives low={m.low}"


def test_dcf_skipped_when_fcf_negative():
    """Bei fcf_per_share=-5.0 darf DCF NICHT einfliessen."""
    agent = _make_agent({
        "current_price": 50.0,
        "eps": 2.0,
        "pe_ratio": 20.0,
        "fcf_per_share": -5.0,
        "revenue_cagr_3y": 5,
    })
    result = asyncio.run(agent.run("AAPL"))
    assert all(m.name != "DCF" for m in result.methods), (
        f"DCF darf bei negativem FCF nicht erscheinen, methods={result.methods}"
    )
    for m in result.methods:
        assert m.low >= 0, f"Methode {m.name} hat negatives low={m.low}"


def test_kgv_skipped_when_eps_zero():
    """eps=0 darf auch nicht zu KGV-Multiple führen (Division-by-zero-ähnlich)."""
    agent = _make_agent({
        "current_price": 50.0,
        "eps": 0.0,
        "pe_ratio": 20.0,
    })
    result = asyncio.run(agent.run("AAPL"))
    assert all(m.name != "KGV-Multiple" for m in result.methods)


# ── Fix 2: Trennschärfer DCF-Test (zwei-Stufen vs. Gordon) ───────────────────

def test_dcf_uses_two_stage_not_gordon_discriminating():
    """Diskriminierender Test: 2-Stufen-DCF (wacc=0.10 via CAPM) muss von
    Gordon-Einstufer (wacc=0.09) unterscheidbar sein.

    Testdaten: fcf0=10, revenue_cagr_3y=20 (→ growth=0.20 in DCF),
    tg=0.025 (default-Sektor), WACC via CAPM = rf+beta*erp = 0.04+1.0*0.05 = 0.09
    (deliberat gleich altem hard-coded Gordon-WACC für maximale Diskriminierung).

    2-Stufen-DCF: growth=0.20*0.7=0.14 (low) und 0.20*1.3=0.26 (high), years=5, tg=0.025
      → dcf_low  ≈ two_stage_dcf(10, 0.14, 0.025, 0.09, 5) ≈ 155
      → dcf_high ≈ two_stage_dcf(10, 0.26, 0.025, 0.09, 5) ≈ 213

    Gordon-Einstufer mit wacc=0.09: 10*(1+0)/( 0.09 - 0) → undefined / explosive,
    mit g=0: 10/0.09 ≈ 111 (für g_term=0) — liegt unter dem 2-Stufen-Low.
    Mit g=0.20: 10*1.20/(0.09-0.20) → negativ — clearly wrong.

    Schranken: dcf.low > 140 und dcf.high > 190 schliessen Gordon aus.
    """
    # Erwartete Werte vorausberechnen:
    expected_low  = two_stage_dcf(fcf0=10.0, growth=0.20 * 0.7, terminal_growth=0.025,
                                   wacc=0.09, years=5)
    expected_high = two_stage_dcf(fcf0=10.0, growth=0.20 * 1.3, terminal_growth=0.025,
                                   wacc=0.09, years=5)
    # Gordon-Einstufer-Referenz mit gleichem g_term (wäre 10*1.025/(0.09-0.025) ≈ 157.7)
    # → unterscheidet sich von 2-Stufen because Stufe-1 cashflows FEHLEN beim Gordon.
    # Mit growth=0.20 im Gordon: 10*1.20/(0.09-0.025) ≈ 184.6 — ebenfalls im Bereich,
    # aber high müsste bei growth*1.3=0.26 explodieren (0.09-0.026<0 wäre negativ).
    # Schranke: dcf.high muss > 200 sein (Gordon mit tg=0.025, g=0.26 → negativ → schlägt fehl).

    fundamentals = MagicMock()
    fundamentals.get_fundamentals.return_value = {
        "current_price": 100.0,
        "fcf_per_share": 10.0,
        "revenue_cagr_3y": 20,
        "beta": 1.0, "risk_free_rate": 0.04, "erp": 0.05,
        "cost_of_debt": 0.05, "tax_rate": 0.21,
        "equity_weight": 1.0, "debt_weight": 0.0,
        # kein EPS/EBITDA → nur DCF in den methods
    }
    market = MagicMock(); market.get_current_price.return_value = 100.0
    bus = MagicMock()
    agent = ValuationRangeAgent(fundamentals, market, bus)
    result = asyncio.run(agent.run("AAPL", sector="default"))

    dcf = next((m for m in result.methods if m.name == "DCF"), None)
    assert dcf is not None, "DCF muss in den Methoden erscheinen"

    # 2-Stufen sollte expected_low und expected_high liefern (±1 Rundung)
    assert abs(dcf.low - round(expected_low, 2)) <= 0.02, (
        f"DCF low {dcf.low} weicht von 2-Stufen-Erwartung {expected_low:.2f} ab"
    )
    assert abs(dcf.high - round(expected_high, 2)) <= 0.02, (
        f"DCF high {dcf.high} weicht von 2-Stufen-Erwartung {expected_high:.2f} ab"
    )

    # Diskriminierende Schranken: dcf.high > 200 schlägt Gordon-Einstufer fehl
    # (Gordon mit g_term=0.025 und fcf*(1+growth_high=0.26)/(0.09-0.025) ≈ 12.6/0.065≈193,
    # ohne Stufe-1-PV; 2-Stufen addiert Stufe-1-PV obendrauf → höher).
    assert dcf.high > 200.0, (
        f"2-Stufen-DCF high {dcf.high} soll > 200; Gordon-Einstufer würde dies nicht erfüllen"
    )
    assert dcf.low > 120.0, (
        f"2-Stufen-DCF low {dcf.low} soll > 120; Gordon-Einstufer (nur TV) wäre tiefer"
    )


# ── Fix 3: CAGR=0 nicht zu 5% hochbiegen ─────────────────────────────────────

def test_cagr_zero_used_as_zero_not_five_percent():
    """revenue_cagr_3y=0 (falsy) darf nicht still zu 5% werden.
    Erwartung: DCF mit growth=0 vs. growth=0.05 liefert unterschiedliche Werte."""
    base = {
        "current_price": 100.0,
        "fcf_per_share": 10.0,
        "revenue_cagr_3y": 0,  # 0% Wachstum — darf NICHT zu 5% gemacht werden
        "beta": 1.0, "risk_free_rate": 0.04, "erp": 0.05,
        "cost_of_debt": 0.05, "tax_rate": 0.21,
        "equity_weight": 1.0, "debt_weight": 0.0,
    }
    agent = _make_agent(base)
    result = asyncio.run(agent.run("AAPL", sector="default"))

    dcf = next((m for m in result.methods if m.name == "DCF"), None)
    assert dcf is not None, "DCF soll auch bei growth=0 erscheinen"

    # Erwarteter Wert bei growth=0 (korrekt):
    wacc_val = capm_wacc(rf=0.04, beta=1.0, erp=0.05,
                          cost_of_debt=0.05, tax_rate=0.21,
                          equity_weight=1.0, debt_weight=0.0)
    expected_low  = two_stage_dcf(fcf0=10.0, growth=0.0 * 0.7, terminal_growth=0.025,
                                   wacc=wacc_val, years=5)
    expected_high = two_stage_dcf(fcf0=10.0, growth=0.0 * 1.3, terminal_growth=0.025,
                                   wacc=wacc_val, years=5)

    # Falscher Wert (bei `or 5` → growth=0.05):
    wrong_low  = two_stage_dcf(fcf0=10.0, growth=0.05 * 0.7, terminal_growth=0.025,
                                wacc=wacc_val, years=5)

    # Wenn der Bug vorhanden ist, würde dcf.low nahe wrong_low sein, nicht expected_low
    assert abs(dcf.low - round(expected_low, 2)) <= 0.02, (
        f"CAGR=0 Bug: dcf.low={dcf.low} muss ≈{expected_low:.2f} sein (growth=0), "
        f"nicht ≈{wrong_low:.2f} (growth=0.05)"
    )
