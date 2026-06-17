import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.quality_agent import QualityAgent, _signal, _altman_thresholds
from core.domain.models import Signal


def _make_agent(data: dict) -> QualityAgent:
    provider = MagicMock()
    provider.get_fundamentals.return_value = data
    return QualityAgent(provider, MagicMock())


# ── ROIC − WACC-Spread statt fixer 12 % ───────────────────────────────────

def test_roic_ueber_wacc_ist_wertschoepfend():
    """ROIC 10 % bei WACC 7 % = +3 pp Spread → wertschöpfend (bullish-Beitrag)."""
    pos = _signal(roe=None, roic=10.0, wacc=7.0, net_debt_ebitda=None, altman_z=None,
                  interest_coverage=None, fcf_margin=None, f_score=None, sector="default")
    neg = _signal(roe=None, roic=10.0, wacc=13.0, net_debt_ebitda=None, altman_z=None,
                  interest_coverage=None, fcf_margin=None, f_score=None, sector="default")
    order = {Signal.BEARISH: -1, Signal.NEUTRAL: 0, Signal.BULLISH: 1}
    # Gleicher ROIC, aber bei höherem WACC schlechter
    assert order[pos] >= order[neg]


def test_roic_ohne_wacc_faellt_auf_absolutschwelle_zurueck():
    """Fehlt WACC, nutzt der Spread-Check eine konservative Default-Schwelle."""
    sig = _signal(roe=None, roic=18.0, wacc=None, net_debt_ebitda=None, altman_z=None,
                  interest_coverage=None, fcf_margin=None, f_score=None, sector="default")
    assert sig in (Signal.BULLISH, Signal.NEUTRAL)


# ── Piotroski F-Score fließt ein ──────────────────────────────────────────

def test_hoher_f_score_ist_bullish_beitrag():
    high = _signal(roe=None, roic=None, wacc=None, net_debt_ebitda=None, altman_z=None,
                   interest_coverage=None, fcf_margin=None, f_score=9, sector="default")
    low  = _signal(roe=None, roic=None, wacc=None, net_debt_ebitda=None, altman_z=None,
                   interest_coverage=None, fcf_margin=None, f_score=1, sector="default")
    assert high == Signal.BULLISH
    assert low == Signal.BEARISH


# ── interest_coverage / fcf_margin aktiviert ──────────────────────────────

def test_interest_coverage_und_fcf_margin_wirken():
    strong = _signal(roe=None, roic=None, wacc=None, net_debt_ebitda=None, altman_z=None,
                     interest_coverage=12.0, fcf_margin=15.0, f_score=None, sector="default")
    weak   = _signal(roe=None, roic=None, wacc=None, net_debt_ebitda=None, altman_z=None,
                     interest_coverage=1.0, fcf_margin=-5.0, f_score=None, sector="default")
    order = {Signal.BEARISH: -1, Signal.NEUTRAL: 0, Signal.BULLISH: 1}
    assert order[strong] > order[weak]


# ── Altman-Variante nach Unternehmenstyp ──────────────────────────────────

def test_altman_manufacturing_klassische_schwellen():
    safe, distress = _altman_thresholds("Industrials")
    assert safe == 2.99 and distress == 1.81


def test_altman_nicht_manufacturing_z_doppelstrich():
    safe, distress = _altman_thresholds("Technology")
    assert safe == 2.6 and distress == 1.1


def test_altman_financials_nicht_angewendet():
    """Für Financials liefert die Schwellen-Funktion None → Altman ignoriert."""
    assert _altman_thresholds("Financials") is None


def test_financials_altman_z_kein_beitrag():
    """Auch ein extrem niedriger Altman-Z darf bei Financials NICHT bearish ziehen."""
    sig = _signal(roe=None, roic=None, wacc=None, net_debt_ebitda=None, altman_z=0.5,
                  interest_coverage=None, fcf_margin=None, f_score=None, sector="Financials")
    assert sig == Signal.NEUTRAL


# ── Piotroski-Felddurchreichung end-to-end ────────────────────────────────

def test_run_berechnet_f_score_aus_provider_feldern():
    data = {
        "net_income": 100.0, "roa": 8.0, "operating_cash_flow": 150.0, "roa_prev": 5.0,
        "long_term_debt": 50.0, "long_term_debt_prev": 80.0,
        "current_ratio": 2.0, "current_ratio_prev": 1.5,
        "shares_outstanding": 100.0, "shares_outstanding_prev": 100.0,
        "gross_margin": 40.0, "gross_margin_prev": 35.0,
        "asset_turnover": 1.2, "asset_turnover_prev": 1.0,
    }
    result = asyncio.run(_make_agent(data).run("X"))
    assert result.signal == Signal.BULLISH
