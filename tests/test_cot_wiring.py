"""TDD: CFTC-COT-Provider wird durch Orchestrator → Chief → COTAgent durchgereicht."""
from unittest.mock import MagicMock

from agents.stock_deep_dive.commodity_chief_agent_mikro import CommodityChiefAgentMikro
from orchestrators.bottom_up_orchestrator import BottomUpOrchestrator


def test_chief_injiziert_cot_provider_in_agent():
    prov = MagicMock()
    chief = CommodityChiefAgentMikro(MagicMock(), MagicMock(), cot_provider=prov)
    assert chief.cot_agent.provider is prov


def test_chief_ohne_provider_bleibt_none():
    chief = CommodityChiefAgentMikro(MagicMock(), MagicMock())
    assert chief.cot_agent.provider is None


def test_orchestrator_reicht_cot_provider_durch():
    prov = MagicMock()
    orch = BottomUpOrchestrator(
        fundamentals_provider=MagicMock(), macro_provider=MagicMock(),
        market_provider=MagicMock(), llm=MagicMock(), bus=MagicMock(),
        cot_provider=prov,
    )
    assert orch.commodity_chief.cot_agent.provider is prov
