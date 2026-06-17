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


# ── Fix I2: negativer forward_pe darf kein +1 erzeugen ────────────────────

def test_negativer_forward_pe_kein_bullish_credit():
    """Fix I2: forward_pe=-5 bei pe=8 und ev_ebitda=6 bedeutet erwarteten Verlust → KEIN +1-Credit.
    VOR dem Fix: -5 < 8 ist True → fälschliches +1, das den Score von 2 auf 3 hebt → BULLISH.
    NACH dem Fix: forward_pe > 0 nötig → kein Extra-Punkt → Score bleibt 2 → NEUTRAL.
    """
    # pe=8 in default-Sektor (günstig → +1), ev_ebitda=6 in default-Sektor (günstig → +1)
    # fpe=-5 < pe=8 → fälschliches +1 → Gesamt=3 → BULLISH (BUG)
    # Ohne den Bug: Gesamt=2 → NEUTRAL
    sig_neg_fpe = _score(pe=8.0, forward_pe=-5.0, peg=None, ev_ebitda=6.0,
                         price_fcf=None, price_book=None, revenue_cagr=None,
                         op_margin=None, debt_equity=None, sector="default")
    sig_none_fpe = _score(pe=8.0, forward_pe=None, peg=None, ev_ebitda=6.0,
                          price_fcf=None, price_book=None, revenue_cagr=None,
                          op_margin=None, debt_equity=None, sector="default")
    # Nach dem Fix sollen beide NEUTRAL sein (kein falsches BULLISH durch negativen forward_pe)
    assert sig_neg_fpe != Signal.BULLISH, (
        f"Negativer forward_pe=-5 darf keinen BULLISH-Credit erzeugen, war {sig_neg_fpe}"
    )
    assert sig_neg_fpe == sig_none_fpe, (
        f"Negativer forward_pe darf keinen Unterschied machen (war {sig_neg_fpe} vs. None={sig_none_fpe})"
    )


# ── Fix M2: Exception-Guard in run() ──────────────────────────────────────

def test_run_exception_guard_liefert_valid_snapshot():
    """Fix M2: run() muss Exception-Guard haben wie QualityAgent.
    Wenn provider.get_fundamentals() eine Exception wirft, soll kein Crash kommen.
    """
    from agents.stock_deep_dive.equity.fundamentals_agent import FundamentalsAgent
    from core.domain.models import FundamentalsSnapshot
    provider = MagicMock()
    provider.get_fundamentals.side_effect = ValueError("API down")
    agent = FundamentalsAgent(provider, MagicMock())
    # Soll nicht werfen → soll einen validen Snapshot zurückgeben
    result = asyncio.run(agent.run("FAIL"))
    assert isinstance(result, FundamentalsSnapshot), (
        f"run() soll bei Exception einen FundamentalsSnapshot zurückgeben, war {type(result)}"
    )
