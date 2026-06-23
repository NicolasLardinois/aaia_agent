from unittest.mock import MagicMock
from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent
from core.domain.portfolio import Position
from core.domain.models import RiskAffinity
from core.domain.taxonomy import Underlying, Wrapper


def _agent():
    return PortfolioMonitorAgent(memory=MagicMock(), portfolio_port=MagicMock())


def test_snapshot_listet_bond_affinitaeten():
    positions = [
        Position(ticker="TLT", shares=10, entry_price=90, direction="long",
                 underlying=Underlying.BOND, wrapper=Wrapper.SINGLE,
                 risk_affinity=RiskAffinity.NEUTRAL),
        Position(ticker="AAPL", shares=5, entry_price=100, direction="long",
                 underlying=Underlying.EQUITY, wrapper=Wrapper.SINGLE),
    ]
    snap = _agent()._evaluate_positions(
        positions, market_data={0: {"price": 90, "beta": 1.0, "returns": None},
                                1: {"price": 100, "beta": 1.0, "returns": None}})
    assert {"ticker": "TLT", "risk_affinity": "neutral"} in snap["bond_risk_affinities"]
    assert all(e["ticker"] != "AAPL" for e in snap["bond_risk_affinities"])
