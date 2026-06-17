from unittest.mock import MagicMock
from agents.anomaly_chief_agent import AnomalyChiefAgent
from core.domain.models import AnomalyReport


def test_chief_returns_two_reports_and_publishes():
    bus = MagicMock()
    chief = AnomalyChiefAgent(bus)
    cockpit = None  # → td_anomaly = empty
    bu = MagicMock()
    bu.asset_class = "bond"
    bu.fundamentals = None
    bu.short_interest = None
    bu.insider = None
    bu.earnings_trend.signal = None
    bu.moat.signal = None
    bu.valuation_range.signal = None
    bu.quality.signal = None
    td, bu_report = chief.run(cockpit, bu, [], [], market="USA")
    assert isinstance(td, AnomalyReport)
    assert isinstance(bu_report, AnomalyReport)
    assert bus.publish.called


def test_chief_swallows_subagent_exception():
    bus = MagicMock()
    chief = AnomalyChiefAgent(bus)
    chief.bu_anomaly_agent.run = MagicMock(side_effect=RuntimeError("boom"))
    td, bu_report = chief.run(None, MagicMock(), [], [], market="USA")
    assert bu_report.severity == "none"  # Fallback auf empty()
