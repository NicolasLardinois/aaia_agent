import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.fundamentals_agent import FundamentalsAgent, _score
from core.domain.models import Signal


def _make_agent(data: dict) -> FundamentalsAgent:
    provider = MagicMock()
    provider.get_fundamentals.return_value = data
    return FundamentalsAgent(provider, MagicMock())


# ── CAPE entfernt ─────────────────────────────────────────────────────────

def test_score_signatur_ohne_shiller():
    """_score nimmt kein shiller-Argument mehr (CAPE auf Einzelaktie entfernt)."""
    import inspect
    params = inspect.signature(_score).parameters
    assert "shiller" not in params
    assert "shiller_cape" not in params


def test_shiller_cape_bleibt_im_snapshot_aber_ohne_signalwirkung():
    """Snapshot trägt shiller_cape weiter (Backward-Compat), aber es beeinflusst das Signal nicht."""
    with_cape    = asyncio.run(_make_agent({"pe_ratio": 18.0, "shiller_cape": 5.0}).run("X"))
    without_cape = asyncio.run(_make_agent({"pe_ratio": 18.0, "shiller_cape": None}).run("X"))
    assert with_cape.signal == without_cape.signal


# ── negatives / None EPS neutralisieren ───────────────────────────────────

def test_negatives_eps_pe_neutral_nicht_bullish():
    """Negatives P/E (Verlust) darf NICHT bullish gewertet werden."""
    sig = _score(pe=-12.0, forward_pe=None, peg=None, ev_ebitda=None,
                 price_fcf=None, price_book=None, revenue_cagr=None,
                 op_margin=None, debt_equity=None, sector="default")
    assert sig == Signal.NEUTRAL


# ── sektor-relativ ────────────────────────────────────────────────────────

def test_pe_billig_im_sektor_ist_bullish():
    """P/E 11 ist bei Financials (Sektor-Band 10–16) eher günstig → BULLISH-Tendenz."""
    sig = _score(pe=11.0, forward_pe=None, peg=None, ev_ebitda=None,
                 price_fcf=None, price_book=None, revenue_cagr=None,
                 op_margin=None, debt_equity=None, sector="Financials")
    assert sig in (Signal.BULLISH, Signal.NEUTRAL)


def test_pe_teuer_im_sektor_ist_bearish_tendenz():
    """P/E 40 bei Financials (Band 10–16) ist klar teuer."""
    sig = _score(pe=40.0, forward_pe=None, peg=None, ev_ebitda=None,
                 price_fcf=None, price_book=None, revenue_cagr=None,
                 op_margin=None, debt_equity=None, sector="Financials")
    assert sig in (Signal.BEARISH, Signal.NEUTRAL)


# ── PEG mit Growth-Basis-Check ────────────────────────────────────────────

def test_peg_ohne_growth_basis_neutral():
    """PEG aus trivialem/negativem g ist sinnlos → kein Beitrag."""
    sig = _score(pe=20.0, forward_pe=None, peg=0.2, ev_ebitda=None,
                 price_fcf=None, price_book=None, revenue_cagr=-5.0,
                 op_margin=None, debt_equity=None, sector="default")
    # revenue_cagr < 0 → PEG darf nicht bullish ziehen
    assert sig != Signal.BULLISH


# ── ungenutzte Multiples aktiviert ────────────────────────────────────────

def test_price_fcf_und_price_book_fliessen_ein():
    """Sehr niedriges P/FCF und P/B verschieben das Signal in Richtung BULLISH."""
    cheap = _score(pe=15.0, forward_pe=None, peg=None, ev_ebitda=None,
                   price_fcf=6.0, price_book=0.8, revenue_cagr=None,
                   op_margin=None, debt_equity=None, sector="default")
    pricey = _score(pe=15.0, forward_pe=None, peg=None, ev_ebitda=None,
                    price_fcf=40.0, price_book=8.0, revenue_cagr=None,
                    op_margin=None, debt_equity=None, sector="default")
    order = {Signal.BEARISH: -1, Signal.NEUTRAL: 0, Signal.BULLISH: 1}
    assert order[cheap] >= order[pricey]


# ── symmetrische Aggregationsschwellen ────────────────────────────────────

def test_aggregation_symmetrisch():
    """Spiegelbildlich gleich starke Bull-/Bear-Inputs ergeben spiegelbildliche Signale."""
    bull = _score(pe=11.0, forward_pe=10.0, peg=None, ev_ebitda=6.0,
                  price_fcf=6.0, price_book=0.8, revenue_cagr=None,
                  op_margin=None, debt_equity=None, sector="default")
    bear = _score(pe=40.0, forward_pe=45.0, peg=None, ev_ebitda=30.0,
                  price_fcf=45.0, price_book=9.0, revenue_cagr=None,
                  op_margin=None, debt_equity=None, sector="default")
    assert bull == Signal.BULLISH
    assert bear == Signal.BEARISH
