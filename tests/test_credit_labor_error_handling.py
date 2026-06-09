import asyncio
from unittest.mock import MagicMock
from agents.market_cockpit.macro.credit_agent import CreditAgent
from agents.market_cockpit.macro.labor_income_agent import LaborIncomeAgent


def test_credit_agent_returns_default_on_provider_failure():
    provider = MagicMock()
    provider.get_extended_state.side_effect = Exception("FRED down")
    bus = MagicMock()
    agent = CreditAgent(provider, bus)
    result = asyncio.run(agent.run())
    from agents.market_cockpit.macro.credit_agent import _DEFAULT
    assert result == _DEFAULT


def test_labor_agent_returns_default_on_provider_failure():
    provider = MagicMock()
    provider.get_extended_state.side_effect = Exception("FRED down")
    bus = MagicMock()
    agent = LaborIncomeAgent(provider, bus)
    result = asyncio.run(agent.run())
    from agents.market_cockpit.macro.labor_income_agent import _DEFAULT
    assert result == _DEFAULT
