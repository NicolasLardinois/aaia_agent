import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent
from core.domain.models import Signal


def test_chief_reicht_macro_an_price_agent_weiter():
    macro = MagicMock()
    market = MagicMock()
    bus = MagicMock()
    chief = PreciousMetalsChiefAgent(macro, market, bus)
    # Der Price-Agent muss denselben Macro-Provider erhalten (fuer get_real_rate_history)
    assert chief.pm_price_agent.macro is macro


# ── COT-Signal aus echtem COTAgent statt hart verdrahtetem NEUTRAL ───────────

class _FakeCot:
    """Minimaler COTProvider-Doppelgänger für die Verdrahtungstests."""
    def __init__(self, history):
        self._history = history

    def get_cot_history(self, commodity, years=3):
        return self._history


def _bearish_cot_history(n=30):
    """Streng steigende Managed-Money-Netto-Reihe; letzter Wert = Maximum →
    Perzentil-Rang ≈ 100 → COT-Index hoch → konträr BEARISH (extreme Long-Positionierung)."""
    return [{"managed_money_net": float(i), "open_interest": 1000.0} for i in range(n)]


def test_cot_signal_wird_aus_cot_agent_uebernommen():
    """Mit injiziertem COT-Provider liefert der Chief das ECHTE COT-Signal,
    nicht mehr das hart verdrahtete NEUTRAL."""
    chief = PreciousMetalsChiefAgent(
        MagicMock(), MagicMock(), MagicMock(), cot_provider=_FakeCot(_bearish_cot_history())
    )
    result = asyncio.run(chief.run("GC=F"))
    assert result.cot_signal == Signal.BEARISH


def test_ohne_cot_provider_bleibt_cot_signal_neutral():
    """Ohne COT-Provider (None) → COTAgent UNAVAILABLE → cot_signal NEUTRAL
    (rückwärtskompatibel, kein Regress)."""
    chief = PreciousMetalsChiefAgent(MagicMock(), MagicMock(), MagicMock())
    result = asyncio.run(chief.run("GC=F"))
    assert result.cot_signal == Signal.NEUTRAL
