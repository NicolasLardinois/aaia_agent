from unittest.mock import MagicMock

from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent


def test_chief_reicht_macro_an_price_agent_weiter():
    macro = MagicMock()
    market = MagicMock()
    bus = MagicMock()
    chief = PreciousMetalsChiefAgent(macro, market, bus)
    # Der Price-Agent muss denselben Macro-Provider erhalten (fuer get_real_rate_history)
    assert chief.pm_price_agent.macro is macro
