import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.earnings_trend_agent import EarningsTrendAgent, _signal
from core.domain.models import Signal


def _make_agent(history: list[dict]) -> EarningsTrendAgent:
    provider = MagicMock()
    provider.get_earnings_history.return_value = history
    return EarningsTrendAgent(provider, MagicMock())


def _quarters(actuals, estimates, revisions=None):
    revisions = revisions or [0] * len(actuals)
    return [
        {"actual": a, "estimate": e, "revision": r, "beat": a > e}
        for a, e, r in zip(actuals, estimates, revisions)
    ]


# ── SUE statt binärer Beat-Rate ───────────────────────────────────────────

def test_grosse_positive_surprise_ist_bullish():
    """Letzte Surprise weit über der Streuung (hoher SUE) + Up-Revision → BULLISH."""
    sig = _signal(sue=2.5, revision_label="up")
    assert sig == Signal.BULLISH


def test_kleine_surprise_trotz_beat_neutral():
    """Routine-Beat innerhalb der Streuung (SUE ~0.3) ohne Revisionsschub → NEUTRAL."""
    sig = _signal(sue=0.3, revision_label="flat")
    assert sig == Signal.NEUTRAL


# ── Revisions-Trend gewichtet statt ODER-Veto ─────────────────────────────

def test_down_revision_kippt_nicht_allein_bei_starkem_sue():
    """Starker positiver SUE + eine Down-Revision → NICHT automatisch BEARISH (kein Veto)."""
    sig = _signal(sue=2.5, revision_label="down")
    assert sig != Signal.BEARISH


def test_negative_surprise_und_down_revision_ist_bearish():
    sig = _signal(sue=-2.0, revision_label="down")
    assert sig == Signal.BEARISH


# ── End-to-End: SUE wird aus history berechnet ────────────────────────────

def test_run_berechnet_sue_aus_history():
    history = _quarters(
        actuals=[1.0, 0.95, 1.05, 1.40],
        estimates=[1.0, 1.0, 1.0, 1.0],
        revisions=[0, 0, 1, 1],     # jüngste zwei Up-Revisions
    )
    result = asyncio.run(_make_agent(history).run("X"))
    assert result.signal == Signal.BULLISH


def test_leere_history_neutral():
    result = asyncio.run(_make_agent([]).run("X"))
    assert result.signal == Signal.NEUTRAL
