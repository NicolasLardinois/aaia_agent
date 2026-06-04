import asyncio
from unittest.mock import MagicMock, AsyncMock
from agents.anomaly_chief_agent import AnomalyChiefAgent
from core.domain.models import AnomalyReport


def _make_cockpit():
    cockpit = MagicMock()
    cockpit.sentiment.vix.vix = 18.0
    cockpit.sentiment.vix.signal = MagicMock()
    cockpit.sentiment.fear_greed.value = 50.0
    cockpit.sentiment.fear_greed.signal = MagicMock()
    cockpit.sentiment.put_call.signal = MagicMock()
    cockpit.yield_curve.yield_spreads.usa.spread_10y2y = 1.0
    cockpit.yield_curve.yield_spreads.usa.signal = MagicMock()
    cockpit.macro.regime_confidence = 0.75
    cockpit.macro.inflation.usa.cpi = 3.0
    cockpit.macro.inflation.usa.signal = MagicMock()
    cockpit.macro.gdp.usa.signal = MagicMock()
    cockpit.commodities.energy.signal = MagicMock()
    cockpit.commodities.industrial_metals.signal = MagicMock()
    return cockpit

def _make_bottom_up():
    bu = MagicMock()
    bu.asset_class = "equity"
    bu.fundamentals = None
    bu.short_interest = None
    bu.insider = None
    bu.earnings_trend.signal = MagicMock()
    bu.moat.signal = MagicMock()
    bu.valuation_range.signal = MagicMock()
    bu.quality.signal = MagicMock()
    return bu


def test_anomaly_chief_returns_two_reports():
    bus = MagicMock()
    chief = AnomalyChiefAgent(bus)
    td, bu = chief.run(_make_cockpit(), _make_bottom_up(), [], [])
    assert isinstance(td, AnomalyReport)
    assert isinstance(bu, AnomalyReport)
    bus.publish.assert_called_once()


def test_anomaly_chief_no_cockpit():
    bus = MagicMock()
    chief = AnomalyChiefAgent(bus)
    td, bu = chief.run(None, _make_bottom_up(), [], [])
    assert td.has_anomalies is False
    assert isinstance(bu, AnomalyReport)


# ─────────────────────────────────────────────
# Task 15: JudgmentChiefAgent
# ─────────────────────────────────────────────

from agents.judgment_chief_agent import JudgmentChiefAgent
from core.domain.models import DeepDiveResult, Recommendation, InvestmentRecommendation, Signal


def _make_deep_dive_result():
    return DeepDiveResult(
        ticker="AAPL", asset_class="equity", market="USA",
        top_down_context="neutral", top_down_available=True,
        judgment="Hold", alignment="mixed",
        recommendation=InvestmentRecommendation(
            action=Recommendation.HOLD, short_type=None, short_warning=None,
            confidence=0.65, reasoning="neutral",
        ),
        dominant_signal="neutral", confidence=0.65, xai_explanation="",
    )


def test_judgment_chief_returns_result():
    bus = MagicMock()
    llm = MagicMock()
    bottom_up = MagicMock()
    bottom_up.ticker = "AAPL"
    bottom_up.asset_class = "equity"

    chief = JudgmentChiefAgent(llm, bus)
    chief.judgment_agent.run = AsyncMock(return_value=_make_deep_dive_result())

    result = asyncio.run(chief.run(
        ticker="AAPL",
        top_down_context="neutral macro",
        bottom_up=bottom_up,
        cockpit=None,
        market="USA",
        in_portfolio=False,
        top_down_available=False,
        top_down_anomaly=AnomalyReport.empty(),
        bottom_up_anomaly=AnomalyReport.empty(),
        backtester_context={},
    ))
    assert isinstance(result, DeepDiveResult)
    bus.publish.assert_called_once()


# ─────────────────────────────────────────────
# Task 16: BacktesterChiefAgent
# ─────────────────────────────────────────────

from agents.backtester_chief_agent import BacktesterChiefAgent


def test_backtester_chief_load_context_empty():
    bus = MagicMock()
    memory = MagicMock()
    memory.load_latest_backtester_report = MagicMock(return_value={})
    chief = BacktesterChiefAgent(memory, bus)
    ctx = chief.load_context()
    assert isinstance(ctx, dict)


def test_backtester_chief_run_calls_all_agents():
    bus = MagicMock()
    memory = MagicMock()
    memory.load_global_history = MagicMock(return_value=[])
    chief = BacktesterChiefAgent(memory, bus)
    chief.td_backtester.run   = AsyncMock(return_value=None)
    chief.bu_backtester.run   = AsyncMock(return_value=None)
    chief.j_backtester.run    = AsyncMock(return_value=None)

    asyncio.run(chief.run())
    chief.td_backtester.run.assert_called_once()
    chief.bu_backtester.run.assert_called_once()
    chief.j_backtester.run.assert_called_once()
    bus.publish.assert_called_once()
