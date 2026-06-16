from agents.market_cockpit.commodity_chief_agent_makro import _aggregate
from core.domain.models import Signal, SignalStatus


def test_energy_dominates_aggregate():
    # Energie BEARISH (höchstes Gewicht) schlägt drei neutrale → BEARISH
    items = [
        (Signal.BEARISH, 0.50, SignalStatus.AVAILABLE),   # energy
        (Signal.NEUTRAL, 0.20, SignalStatus.AVAILABLE),   # industrial
        (Signal.NEUTRAL, 0.15, SignalStatus.AVAILABLE),   # precious
        (Signal.NEUTRAL, 0.15, SignalStatus.AVAILABLE),   # agricultural
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.BEARISH


def test_unavailable_excluded_from_weight():
    # Energie UNAVAILABLE → industrial BULLISH bestimmt das Ergebnis
    items = [
        (Signal.NEUTRAL, 0.50, SignalStatus.UNAVAILABLE),
        (Signal.BULLISH, 0.20, SignalStatus.AVAILABLE),
        (Signal.NEUTRAL, 0.15, SignalStatus.AVAILABLE),
        (Signal.NEUTRAL, 0.15, SignalStatus.AVAILABLE),
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.BULLISH
