import asyncio
from unittest.mock import MagicMock
from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent, _overall_signal
from core.domain.models import Signal


def test_overall_bearish_when_duration_and_spread_bearish():
    assert _overall_signal(Signal.BEARISH, Signal.NEUTRAL, Signal.BEARISH, Signal.NEUTRAL) == Signal.BEARISH


def test_overall_neutral_on_conflict():
    assert _overall_signal(Signal.BULLISH, Signal.NEUTRAL, Signal.BEARISH, Signal.NEUTRAL) == Signal.NEUTRAL


def test_chief_publishes_overall_in_payload():
    prov = MagicMock()
    prov.get_bond_data.return_value = {}
    macro = MagicMock()
    macro.get_economic_state.return_value = {}
    bus = MagicMock()
    asyncio.run(BondChiefAgent(prov, macro, bus).run("X", "government", "stable"))
    chief_calls = [c.args[0] for c in bus.publish.call_args_list
                   if type(c.args[0]).__name__ == "BondChiefReady"]
    assert chief_calls and "overall_signal" in chief_calls[-1].payload
