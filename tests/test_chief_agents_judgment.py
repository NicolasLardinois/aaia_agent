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
    cockpit.macro.buffett_indicator.countries = {}
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
from core.domain.models import DeepDiveResult, PositionState, Recommendation, InvestmentRecommendation, ShortAction, Signal


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
        current_position=PositionState.NONE,
        top_down_available=False,
        top_down_anomaly=AnomalyReport.empty(),
        bottom_up_anomaly=AnomalyReport.empty(),
        backtester_context={},
    ))
    assert isinstance(result, DeepDiveResult)
    bus.publish.assert_called_once()


def test_judgment_chief_short_action_hold_when_short():
    bus = MagicMock()
    llm = MagicMock()
    bottom_up = MagicMock()
    bottom_up.ticker = "TSLA"
    bottom_up.asset_class = "equity"

    deep_dive_short = DeepDiveResult(
        ticker="TSLA", asset_class="equity", market="USA",
        top_down_context="neutral", top_down_available=True,
        judgment="Hold", alignment="mixed",
        recommendation=InvestmentRecommendation(
            action=Recommendation.NONE, short_type=None, short_warning=None,
            confidence=0.65, reasoning="short gehalten",
        ),
        dominant_signal="neutral", confidence=0.65, xai_explanation="",
        short_action=ShortAction.HOLD,
    )

    chief = JudgmentChiefAgent(llm, bus)
    chief.judgment_agent.run = AsyncMock(return_value=deep_dive_short)

    result = asyncio.run(chief.run(
        ticker="TSLA",
        top_down_context="neutral macro",
        bottom_up=bottom_up,
        cockpit=None,
        market="USA",
        current_position=PositionState.SHORT,
        top_down_available=False,
        top_down_anomaly=AnomalyReport.empty(),
        bottom_up_anomaly=AnomalyReport.empty(),
        backtester_context={},
    ))
    assert result.short_action == ShortAction.HOLD


def test_judgment_chief_short_action_none_when_none():
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
        current_position=PositionState.NONE,
        top_down_available=False,
        top_down_anomaly=AnomalyReport.empty(),
        bottom_up_anomaly=AnomalyReport.empty(),
        backtester_context={},
    ))
    assert result.short_action == ShortAction.NONE


# ─────────────────────────────────────────────
# Task 16: BacktesterChiefAgent
# ─────────────────────────────────────────────

from agents.backtester_chief_agent import BacktesterChiefAgent

# ─────────────────────────────────────────────
# Task 2: _short_position_pnl_pct (P&L-Helfer)
# ─────────────────────────────────────────────

from types import SimpleNamespace as NS
from core.domain.portfolio import PortfolioError
from agents.judgment.judgment_agent import _short_position_pnl_pct


def _port(positions):
    return NS(get_positions=lambda: positions)


def _bu_price(cur):
    return NS(valuation_range=NS(current_price=cur))


def test_pnl_short_in_profit():
    port = _port([NS(ticker="AAPL", direction="short", entry_price=100.0)])
    assert _short_position_pnl_pct(port, "AAPL", PositionState.SHORT, _bu_price(90.0)) == 10.0


def test_pnl_none_when_not_short():
    port = _port([NS(ticker="AAPL", direction="short", entry_price=100.0)])
    assert _short_position_pnl_pct(port, "AAPL", PositionState.NONE, _bu_price(90.0)) is None


def test_pnl_none_when_no_port():
    assert _short_position_pnl_pct(None, "AAPL", PositionState.SHORT, _bu_price(90.0)) is None


def test_pnl_none_when_ticker_absent():
    port = _port([NS(ticker="MSFT", direction="short", entry_price=100.0)])
    assert _short_position_pnl_pct(port, "AAPL", PositionState.SHORT, _bu_price(90.0)) is None


def test_pnl_none_when_no_current_price():
    port = _port([NS(ticker="AAPL", direction="short", entry_price=100.0)])
    assert _short_position_pnl_pct(port, "AAPL", PositionState.SHORT, NS(valuation_range=None)) is None


def test_pnl_none_on_portfolio_error():
    def _raise():
        raise PortfolioError("bad")
    assert _short_position_pnl_pct(NS(get_positions=_raise), "AAPL", PositionState.SHORT, _bu_price(90.0)) is None


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


# ─────────────────────────────────────────────
# Task 3: PortfolioPort-Verdrahtung durch die Kette
# ─────────────────────────────────────────────

def test_portfolio_port_wired_chief_to_agent():
    from agents.judgment_chief_agent import JudgmentChiefAgent
    sentinel = object()
    chief = JudgmentChiefAgent(NS(), NS(), portfolio_port=sentinel)
    assert chief.judgment_agent.portfolio_port is sentinel


def test_portfolio_port_wired_orchestrator_to_agent():
    from orchestrators.judgment_orchestrator import JudgmentOrchestrator
    sentinel = object()
    orch = JudgmentOrchestrator(NS(), NS(), NS(), portfolio_port=sentinel)
    assert orch.judgment_chief.judgment_agent.portfolio_port is sentinel
