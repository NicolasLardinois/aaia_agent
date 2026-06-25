"""Pure-Serializer-Tests für den Deep-Dive-Echt-Anschluss (Spec 2026-06-26).

Spiegelt das Muster von test_cockpit_serializer: ein Fixture-Domänenobjekt rein,
ein snake_case-Dict raus (das Frontend mappt später auf camelCase, DeepDiveView).
Kein I/O. UNAVAILABLE ≠ 0/neutral: fehlende Sub-Snapshots → null, nie erfunden.

PR-1-Umfang: Kern + Long/Short-Linse + Anomalie + Equity-Block. Bond/Index/
Commodity/Futures-Blöcke und die strukturierte Claude-XAI folgen in eigenen Scheiben.
"""
from core.domain.models import (
    DeepDiveResult, BottomUpResult, InvestmentRecommendation, AnomalyReport,
    FundamentalsSnapshot, QualitySnapshot, ShortInterestSnapshot, InsiderSnapshot,
    EarningsTrendSnapshot, MoatSnapshot, MoatScore, ValuationRangeSnapshot, ValuationMethod,
    Recommendation, ShortAction, Signal,
)
from core.domain.taxonomy import Underlying, Wrapper
from adapters.api.deepdive_serializer import deepdive_to_dict


# ─────────────────────────────────────────────
# Fixtures: ein voll besetzter Equity-Deep-Dive (AAPL-artig)
# ─────────────────────────────────────────────

def _fundamentals() -> FundamentalsSnapshot:
    # Margen/Renditen/CAGR/WACC in PROZENT (Konvention des fundamentals_agent:
    # Schwellen op_margin>15, revenue_cagr>10 ⇒ Prozent, nicht Dezimal).
    return FundamentalsSnapshot(
        pe_ratio=30.5, forward_pe=28.2, shiller_cape=34.0, peg_ratio=None,
        ev_ebitda=22.4, ev_revenue=8.1, price_book=46.0, price_sales=8.3, price_fcf=30.0,
        dividend_yield=0.5, wacc=8.4, revenue_cagr_3y=8.0,
        operating_margin=30.1, gross_margin=45.2, debt_to_equity=1.5,
        signal=Signal.NEUTRAL,
    )


def _quality() -> QualitySnapshot:
    return QualitySnapshot(
        gross_margin=45.2, operating_margin=30.1, net_margin=25.0, fcf_margin=26.0,
        roe=150.0, roa=28.0, roic=49.8, debt_to_equity=1.5, net_debt_ebitda=0.4,
        interest_coverage=40.0, current_ratio=1.1, altman_z=6.1, signal=Signal.BULLISH,
    )


def _moat() -> MoatSnapshot:
    z = MoatScore(score=4, evidence="stark")
    return MoatSnapshot(
        intangible_assets=z, switching_costs=z, network_effects=z,
        cost_advantages=z, efficient_scale=z, total_score=18,
        overall="wide", llm_reasoning="Ökosystem-Lock-in", signal=Signal.BULLISH,
    )


def _valuation() -> ValuationRangeSnapshot:
    return ValuationRangeSnapshot(
        methods=[
            ValuationMethod(name="KGV-Multiple", low=170.0, high=210.0),
            ValuationMethod(name="EV/EBITDA-Multiple", low=180.0, high=220.0),
            ValuationMethod(name="DCF", low=160.0, high=205.0),
        ],
        combined_low=160.0, combined_high=220.0, current_price=232.1,
        position="overvalued", signal=Signal.BEARISH,
    )


def _bottom_up(**overrides) -> BottomUpResult:
    base = dict(
        ticker="AAPL", underlying=Underlying.EQUITY, wrapper=Wrapper.SINGLE,
        fundamentals=_fundamentals(), quality=_quality(),
        short_interest=ShortInterestSnapshot(short_float_pct=0.8, days_to_cover=1.2, signal=Signal.NEUTRAL),
        insider=InsiderSnapshot(net_direction="neutral", recent_transactions=3, signal=Signal.NEUTRAL),
        earnings_trend=EarningsTrendSnapshot(beat_rate=0.8, estimate_revision="up", signal=Signal.BULLISH),
        moat=_moat(), valuation_range=_valuation(),
        precious_metals=None, bond=None, index=None, commodity_deep=None,
    )
    base.update(overrides)
    return BottomUpResult(**base)


def _deepdive(**overrides) -> DeepDiveResult:
    base = dict(
        ticker="AAPL", underlying=Underlying.EQUITY, wrapper=Wrapper.SINGLE, market="NASDAQ",
        top_down_context="Aufschwung stützt Qualität.", top_down_available=True,
        judgment="Qualität top, Bewertung am oberen Rand.", alignment="mixed",
        recommendation=InvestmentRecommendation(
            action=Recommendation.HOLD, short_type=None, short_warning=None,
            confidence=0.58, reasoning="Qualität top, aber Bewertung hoch.",
        ),
        bottom_up=_bottom_up(),
        dominant_signal="neutral", confidence=0.58,
        xai_explanation="Wide Moat trägt, Bewertung bremst.",
        bottom_up_anomaly=AnomalyReport(
            has_anomalies=True, statistical=["ROIC im 98. Perzentil"],
            contradictions=["Qualität bullish vs. Bewertung bearish"],
            severity="low", summary="Qualität vs. Bewertung.", direction="neutral",
        ),
        short_action=ShortAction.NONE,
    )
    base.update(overrides)
    return DeepDiveResult(**base)


# ─────────────────────────────────────────────
# Kern-Felder + Linsen
# ─────────────────────────────────────────────

def test_core_fields_mapped():
    d = deepdive_to_dict(_deepdive())
    assert d["ticker"] == "AAPL"
    assert d["underlying"] == "equity"        # Underlying.EQUITY.value
    assert d["wrapper"] == "single"
    assert d["market"] == "NASDAQ"
    assert d["found"] is True                 # ein Result existiert
    # Preis/Währung aus der Equity-Bewertungs-Bandbreite (kein Top-Level-Feld im Modell).
    assert d["price"] == 232.1
    assert d["currency"] == "USD"


def test_long_lens_maps_recommendation():
    d = deepdive_to_dict(_deepdive())
    assert d["long"]["verdict"] == "HOLD"     # Recommendation.HOLD → LongVerdict HOLD
    assert d["long"]["confidence"] == 0.58
    assert d["long"]["rationale"] == "Qualität top, aber Bewertung hoch."


def test_long_buy_plus_collapses_to_buy():
    # Frontend-LongVerdict kennt kein "BUY+"; Stärke trägt die Konfidenz.
    rec = InvestmentRecommendation(action=Recommendation.BUY_PLUS, short_type=None,
                                   short_warning=None, confidence=0.8, reasoning="stark")
    d = deepdive_to_dict(_deepdive(recommendation=rec))
    assert d["long"]["verdict"] == "BUY"


def test_short_lens_maps_short_action():
    d = deepdive_to_dict(_deepdive(short_action=ShortAction.NONE))
    assert d["short"]["verdict"] == "NONE"


def test_short_plus_collapses_to_short():
    d = deepdive_to_dict(_deepdive(short_action=ShortAction.SHORT_PLUS))
    assert d["short"]["verdict"] == "SHORT"


# ─────────────────────────────────────────────
# Anomalie: top-down + bottom-up zusammengeführt
# ─────────────────────────────────────────────

def test_anomaly_from_bottom_up():
    d = deepdive_to_dict(_deepdive())
    a = d["anomaly"]
    assert a["severity"] == "low"
    assert a["outliers"] == ["ROIC im 98. Perzentil"]
    assert a["conflicts"] == ["Qualität bullish vs. Bewertung bearish"]


def test_anomaly_merges_top_down_and_takes_higher_severity():
    # Beide Anomalie-Quellen werden vereinigt; die höhere Schwere gewinnt
    # (none<low<medium<high), Listen werden zusammengefügt.
    td = AnomalyReport(has_anomalies=True, statistical=["Kurs +3σ"], contradictions=[],
                       severity="medium", summary="Kursausreißer", direction="bearish")
    d = deepdive_to_dict(_deepdive(top_down_anomaly=td))
    a = d["anomaly"]
    assert a["severity"] == "medium"                       # max(medium, low)
    assert "Kurs +3σ" in a["outliers"]
    assert "ROIC im 98. Perzentil" in a["outliers"]


def test_anomaly_absent_is_none_severity():
    d = deepdive_to_dict(_deepdive(bottom_up_anomaly=None, top_down_anomaly=None))
    a = d["anomaly"]
    assert a["severity"] == "none"
    assert a["outliers"] == []
    assert a["conflicts"] == []


# ─────────────────────────────────────────────
# Equity-Block: Bewertung / Qualität / Signale / Fundamentaldaten
# ─────────────────────────────────────────────

def test_equity_valuation_block():
    d = deepdive_to_dict(_deepdive())
    v = d["equity"]["valuation"]
    assert [m["name"] for m in v["methods"]] == ["KGV-Multiple", "EV/EBITDA-Multiple", "DCF"]
    assert v["methods"][0]["low"] == 170.0
    assert v["current_price"] == 232.1
    assert v["pe_ratio"] == 30.5            # aus fundamentals.pe_ratio
    assert v["ev_ebitda"] == 22.4


def test_equity_quality_block_units_passthrough():
    # Prozent bleibt Prozent (kein ×100) — Einheit des Backends ist bereits %.
    d = deepdive_to_dict(_deepdive())
    q = d["equity"]["quality"]
    assert q["gross_margin_pct"] == 45.2
    assert q["operating_margin_pct"] == 30.1
    assert q["roic_pct"] == 49.8
    assert q["altman_z"] == 6.1


def test_equity_signals_block():
    d = deepdive_to_dict(_deepdive())
    s = d["equity"]["signals"]
    assert s["short_interest_pct"] == 0.8
    assert s["insider_signal"] == "neutral"
    assert s["earnings_trend"] == "bullish"
    assert s["moat"] == "wide"             # MoatSnapshot.overall


def test_equity_fundamentals_block_passthrough():
    d = deepdive_to_dict(_deepdive())
    f = d["equity"]["fundamentals"]
    assert f["forward_pe"] == 28.2
    assert f["shiller_cape"] == 34.0
    assert f["peg_ratio"] is None          # UNAVAILABLE → null, nicht 0
    assert f["dividend_yield_pct"] == 0.5
    assert f["wacc_pct"] == 8.4
    assert f["revenue_cagr_3y_pct"] == 8.0
    assert f["debt_to_equity"] == 1.5


def test_equity_signal_none_when_snapshot_missing():
    # Fehlender Sub-Snapshot ⇒ Signal null (UNAVAILABLE), nicht "neutral" erfunden.
    d = deepdive_to_dict(_deepdive(bottom_up=_bottom_up(earnings_trend=None, short_interest=None)))
    s = d["equity"]["signals"]
    assert s["earnings_trend"] is None
    assert s["short_interest_pct"] is None


def test_non_equity_underlying_omits_equity_block():
    # Bond-Underlying ⇒ kein Equity-Block (kommt in eigener Scheibe).
    bu = _bottom_up(underlying=Underlying.BOND, wrapper=Wrapper.SINGLE,
                    fundamentals=None, quality=None, valuation_range=None,
                    moat=None, short_interest=None, insider=None, earnings_trend=None)
    d = deepdive_to_dict(_deepdive(underlying=Underlying.BOND, wrapper=Wrapper.SINGLE, bottom_up=bu))
    assert "equity" not in d
