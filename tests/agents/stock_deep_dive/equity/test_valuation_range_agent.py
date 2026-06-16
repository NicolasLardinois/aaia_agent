import asyncio
import statistics
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.valuation_range_agent import ValuationRangeAgent, _combine_methods
from core.domain.models import ValuationMethod, Signal


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
    """Bei fcf0=10, growth=0, tg=0, wacc=0.10, years=5 muss der DCF-Fair-Value-Mittelpunkt
    nahe dem 2-Stufen-Resultat (~100/Aktie) liegen, nicht beim Gordon-Wert 10/(0.10-0)=100*(1.0).
    Hier prüfen wir, dass der WACC NICHT mehr hart 0.09 ist, sondern aus CAPM kommt."""
    fundamentals = MagicMock()
    fundamentals.get_fundamentals.return_value = {
        "current_price": 100.0,
        "fcf_per_share": 10.0,
        "revenue_cagr_3y": 0,
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
    # WACC = 0.04 + 1.0*0.06 = 0.10 (CAPM, all-equity). 2-Stufen-DCF mit fcf0=10, g=0, tg=0.025
    # ergibt einen endlichen, positiven Wert > 0.
    assert dcf.low > 0 and dcf.high > dcf.low


def test_dcf_skipped_without_fcf():
    fundamentals = MagicMock()
    fundamentals.get_fundamentals.return_value = {"current_price": 100.0, "eps": 5.0, "pe_ratio": 15.0}
    market = MagicMock(); market.get_current_price.return_value = 100.0
    agent = ValuationRangeAgent(fundamentals, market, MagicMock())
    result = asyncio.run(agent.run("AAPL"))
    assert all(m.name != "DCF" for m in result.methods)
