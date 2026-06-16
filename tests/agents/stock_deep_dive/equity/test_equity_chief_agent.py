import asyncio
from unittest.mock import MagicMock, patch

from agents.stock_deep_dive.equity_chief_agent import EquityChiefAgent, _aggregate_signal
from core.domain.models import (
    Signal, SignalStatus,
    FundamentalsSnapshot, QualitySnapshot, MoatSnapshot, MoatScore,
    EarningsTrendSnapshot, InsiderSnapshot, ShortInterestSnapshot,
    ValuationRangeSnapshot,
)


# ── gewichtete Gesamtbeurteilung ──────────────────────────────────────────

def test_aggregate_dominiert_von_bewertung_und_qualitaet():
    """Bullish Bewertung + bullish Qualität + bullish Moat → BULLISH gesamt."""
    sig, conf = _aggregate_signal(
        fundamentals_sig=Signal.BULLISH,
        quality_sig=Signal.BULLISH,
        valuation_sig=Signal.BULLISH,
        moat_sig=Signal.BULLISH,
        earnings_sig=Signal.NEUTRAL,
        insider_sig=Signal.NEUTRAL,
        short_sig=Signal.NEUTRAL,
    )
    assert sig == Signal.BULLISH
    assert conf > 0.0


def test_aggregate_konflikt_neutralisiert():
    """Bullish Bewertung gegen bearish Qualität (gleich gewichtet) → tendenziell NEUTRAL."""
    sig, _ = _aggregate_signal(
        fundamentals_sig=Signal.BULLISH,
        quality_sig=Signal.BEARISH,
        valuation_sig=Signal.NEUTRAL,
        moat_sig=Signal.NEUTRAL,
        earnings_sig=Signal.NEUTRAL,
        insider_sig=Signal.NEUTRAL,
        short_sig=Signal.NEUTRAL,
    )
    assert sig == Signal.NEUTRAL


# ── sector wird an fundamentals UND quality weitergereicht ─────────────────

def test_sector_an_fundamentals_und_quality_weitergereicht():
    fundamentals = MagicMock(); market = MagicMock(); llm = MagicMock(); bus = MagicMock()
    chief = EquityChiefAgent(fundamentals, market, llm, bus)

    chief.fundamentals_agent.run    = MagicMock(return_value=_afut(FundamentalsAgentDefault()))
    chief.quality_agent.run         = MagicMock(return_value=_afut(QualityAgentDefault()))
    chief.short_agent.run           = MagicMock(return_value=_afut(_short_default()))
    chief.insider_agent.run         = MagicMock(return_value=_afut(_insider_default()))
    chief.earnings_agent.run        = MagicMock(return_value=_afut(_earnings_default()))
    chief.moat_agent.run            = MagicMock(return_value=_afut(_moat_default()))
    chief.valuation_range_agent.run = MagicMock(return_value=_afut(_val_default()))

    asyncio.run(chief.run("AAPL", sector="Technology"))

    chief.fundamentals_agent.run.assert_called_once_with("AAPL", sector="Technology")
    chief.quality_agent.run.assert_called_once_with("AAPL", sector="Technology")
    chief.valuation_range_agent.run.assert_called_once_with("AAPL", "Technology")


# ── Helpers ───────────────────────────────────────────────────────────────

async def _acoro(value):
    return value

def _afut(value):
    return _acoro(value)

def _moat_default():
    z = MoatScore(score=0, evidence="")
    return MoatSnapshot(z, z, z, z, z, 0, "none", "", Signal.NEUTRAL)

def FundamentalsAgentDefault():
    from agents.stock_deep_dive.equity.fundamentals_agent import FundamentalsAgent
    return FundamentalsAgent.default()

def QualityAgentDefault():
    from agents.stock_deep_dive.equity.quality_agent import QualityAgent
    return QualityAgent.default()

def _short_default():
    return ShortInterestSnapshot(None, None, Signal.NEUTRAL)

def _insider_default():
    return InsiderSnapshot("neutral", 0, Signal.NEUTRAL)

def _earnings_default():
    return EarningsTrendSnapshot(None, "flat", Signal.NEUTRAL)

def _val_default():
    return ValuationRangeSnapshot([], 0.0, 0.0, None, "unknown", Signal.NEUTRAL)
