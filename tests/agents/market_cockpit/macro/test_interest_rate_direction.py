import asyncio
from unittest.mock import MagicMock

from agents.market_cockpit.macro.interest_rate_agent import InterestRateAgent
from core.domain.models import Signal


def _macro():
    m = MagicMock()
    m.get_economic_state.return_value = {"fed_rate": 5.0, "inflation": 3.0}
    m.get_policy_rate_history.return_value = [
        {"date": "2025-01-01", "rate": 4.0},
        {"date": "2026-05-01", "rate": 5.0},
    ]
    return m


def _ecb():
    e = MagicMock()
    e.get_interest_rate.return_value = 2.4
    e.get_balance_sheet_growth.return_value = None
    e.get_interest_rate_history.return_value = [
        {"date": "2025-01-01", "rate": 2.0},
        {"date": "2026-05-01", "rate": 2.4},
    ]
    return e


def _snb():
    s = MagicMock()
    s.get_interest_rate.return_value = 1.0
    s.get_balance_sheet_growth.return_value = None
    s.get_interest_rate_history.return_value = [
        {"date": "2025-01-01", "rate": 2.0},
        {"date": "2026-05-01", "rate": 1.0},
    ]
    return s


def test_directions_aus_historie():
    agent = InterestRateAgent(_macro(), _ecb(), _snb(), MagicMock())
    snap = asyncio.run(agent.run())
    assert snap.usa.rate_direction == "rising"
    assert snap.eurozone.rate_direction == "rising"
    assert snap.switzerland.rate_direction == "falling"


def test_ohne_historie_bleibt_stable():
    macro = _macro(); macro.get_policy_rate_history.return_value = []
    ecb = _ecb(); ecb.get_interest_rate_history.return_value = []
    snb = _snb(); snb.get_interest_rate_history.return_value = []
    agent = InterestRateAgent(macro, ecb, snb, MagicMock())
    snap = asyncio.run(agent.run())
    assert snap.usa.rate_direction == "stable"
    assert snap.eurozone.rate_direction == "stable"
    assert snap.switzerland.rate_direction == "stable"
