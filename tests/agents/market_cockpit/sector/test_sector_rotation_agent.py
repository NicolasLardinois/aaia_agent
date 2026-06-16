from agents.market_cockpit.sector.sector_rotation_agent import ROTATION_MAP, _alignment
from core.domain.models import MarketRegime, Signal


def test_gold_removed_from_depression():
    assert "Gold" not in ROTATION_MAP[MarketRegime.DEPRESSION]["recommended"]


def test_alignment_uses_top_n():
    rec = ["Technology", "ConsumerDisc", "Financials"]
    avoid = ["Utilities"]
    # 2 von 3 Top-Sektoren empfohlen → aligned
    al, sig = _alignment(["Technology", "Financials", "Energy"], rec, avoid)
    assert al == "aligned" and sig == Signal.BULLISH


def test_alignment_contradicting_when_top_in_avoid():
    al, sig = _alignment(["Utilities", "ConsumerStap", "Healthcare"], ["Technology"], ["Utilities", "ConsumerStap"])
    assert al == "contradicting" and sig == Signal.BEARISH
