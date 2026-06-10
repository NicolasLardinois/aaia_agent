from unittest.mock import MagicMock
from agents.anomaly_chief_agent import AnomalyChiefAgent
from core.domain.models import AnomalyReport


def test_anomaly_chief_td_failure_returns_empty_not_crash():
    bus = MagicMock()
    agent = AnomalyChiefAgent(bus)
    agent.td_anomaly_agent = MagicMock()
    agent.td_anomaly_agent.run.side_effect = Exception("cockpit attribute missing")
    agent.bu_anomaly_agent = MagicMock()
    agent.bu_anomaly_agent.run.return_value = AnomalyReport.empty()
    cockpit = MagicMock()
    bottom_up = MagicMock()
    bottom_up.asset_class = "equity"
    td, bu = agent.run(cockpit, bottom_up, [], [])
    assert td == AnomalyReport.empty()
    assert bu == AnomalyReport.empty()
