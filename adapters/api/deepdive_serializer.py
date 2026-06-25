"""Pure Serialisierung eines DeepDiveResult in den Frontend-Vertrag (DeepDiveView).

Kein I/O. snake_case-Schlüssel (API-Konvention wie cockpit_serializer); das Frontend
mappt auf seinen camelCase-Vertrag. UNAVAILABLE ≠ 0/neutral: fehlende Sub-Snapshots
werden zu null, nie zu einem erfundenen Signal/Wert (AGENTS.md §3 / Frontend §5.4).

PR-1-Umfang (Spec 2026-06-26 §6): Kern + Long/Short-Linse + Anomalie + Equity-Block.
Bond/Index/Commodity/Futures-Blöcke, die strukturierte Claude-XAI und die granulare
Quellen-Gesundheit (run-level failed-Gründe) folgen in eigenen Scheiben/PR-2.
"""
from typing import Any, Optional

from core.domain.models import DeepDiveResult, AnomalyReport, Recommendation, ShortAction
from core.domain.taxonomy import Underlying


# Recommendation → LongVerdict (Frontend kennt nur BUY/SELL/HOLD/NONE).
# BUY+ kollabiert auf BUY (Stärke trägt die Konfidenz); ein SHORT-Rec ist kein
# Long-Verdikt → NONE (die Short-Linse trägt die Short-Aussage).
_LONG_VERDICT: dict[Recommendation, str] = {
    Recommendation.BUY: "BUY",
    Recommendation.BUY_PLUS: "BUY",
    Recommendation.HOLD: "HOLD",
    Recommendation.SELL: "SELL",
    Recommendation.NONE: "NONE",
    Recommendation.SHORT: "NONE",
}

# ShortAction → ShortVerdict (SHORT/COVER/HOLD/NONE). SHORT+ kollabiert auf SHORT.
_SHORT_VERDICT: dict[ShortAction, str] = {
    ShortAction.SHORT: "SHORT",
    ShortAction.SHORT_PLUS: "SHORT",
    ShortAction.HOLD: "HOLD",
    ShortAction.COVER: "COVER",
    ShortAction.NONE: "NONE",
}

# Schwere-Rangordnung für die Anomalie-Zusammenführung (none<low<medium<high).
_SEVERITY_RANK: dict[str, int] = {"none": 0, "low": 1, "medium": 2, "high": 3}


def _signal_value(snapshot: Any) -> Optional[str]:
    """snapshot.signal.value, oder None wenn der Snapshot fehlt (UNAVAILABLE)."""
    return snapshot.signal.value if snapshot is not None else None


def _merge_anomaly(top_down: Optional[AnomalyReport],
                   bottom_up: Optional[AnomalyReport]) -> dict[str, Any]:
    """Vereinigt Top-Down- und Bottom-Up-Anomalie zu EINEM Frontend-Block.

    severity = höhere der beiden (Rangordnung), outliers = statistical-Vereinigung,
    conflicts = contradictions-Vereinigung. Fehlt beides → severity "none".
    """
    reports = [r for r in (top_down, bottom_up) if r is not None]
    if not reports:
        return {"severity": "none", "outliers": [], "conflicts": []}
    severity = max((r.severity for r in reports), key=lambda s: _SEVERITY_RANK.get(s, 0))
    outliers: list[str] = []
    conflicts: list[str] = []
    for r in reports:
        outliers.extend(r.statistical)
        conflicts.extend(r.contradictions)
    return {"severity": severity, "outliers": outliers, "conflicts": conflicts}


def _equity_block(bottom_up) -> dict[str, Any]:
    """Equity-Block (Bewertung/Qualität/Signale/Fundamentaldaten).

    Einheiten: Margen/ROIC/Rendite/CAGR/WACC sind im Backend bereits PROZENT
    (Schwellen im fundamentals_agent: op_margin>15, revenue_cagr>10) → 1:1
    durchgereicht, KEIN ×100. debt_to_equity = Ratio, Multiples = Pass-through.
    Fehlende Sub-Snapshots → null (UNAVAILABLE), nie 0/neutral.
    """
    f = bottom_up.fundamentals
    q = bottom_up.quality
    vr = bottom_up.valuation_range
    si = bottom_up.short_interest
    moat = bottom_up.moat

    valuation = {
        "methods": [{"name": m.name, "low": m.low, "high": m.high} for m in vr.methods] if vr else [],
        "current_price": vr.current_price if vr else None,
        "pe_ratio": f.pe_ratio if f else None,
        "ev_ebitda": f.ev_ebitda if f else None,
    }
    quality = {
        "gross_margin_pct": q.gross_margin if q else None,
        "operating_margin_pct": q.operating_margin if q else None,
        "roic_pct": q.roic if q else None,
        "altman_z": q.altman_z if q else None,
        # sector steuert frontseitig die Altman-Z-Schwellen; im QualitySnapshot (noch)
        # nicht geführt → "" bis PR-2 die Sektor-Quelle durchreicht (Logbuch-Folge).
        "sector": "",
    }
    signals = {
        "short_interest_pct": si.short_float_pct if si else None,
        "insider_signal": _signal_value(bottom_up.insider),
        "earnings_trend": _signal_value(bottom_up.earnings_trend),
        "moat": moat.overall if moat else None,
    }
    fundamentals = {
        "forward_pe": f.forward_pe if f else None,
        "shiller_cape": f.shiller_cape if f else None,
        "peg_ratio": f.peg_ratio if f else None,
        "ev_revenue": f.ev_revenue if f else None,
        "price_book": f.price_book if f else None,
        "price_sales": f.price_sales if f else None,
        "price_fcf": f.price_fcf if f else None,
        "dividend_yield_pct": f.dividend_yield if f else None,
        "wacc_pct": f.wacc if f else None,
        "revenue_cagr_3y_pct": f.revenue_cagr_3y if f else None,
        "debt_to_equity": f.debt_to_equity if f else None,
    }
    return {"valuation": valuation, "quality": quality, "signals": signals, "fundamentals": fundamentals}


def _price_currency(bottom_up) -> tuple[Optional[float], str]:
    """Preis/Währung — im DeepDiveResult kein Top-Level-Feld; aus der Equity-
    Bewertungs-Bandbreite gezogen (current_price + Methoden-Währung, Default USD).
    Andere Underlyings liefern Preis/Währung in PR-2 aus ihren Block-Snapshots.
    """
    if bottom_up is not None and bottom_up.valuation_range is not None:
        vr = bottom_up.valuation_range
        currency = vr.methods[0].currency if vr.methods else "USD"
        return vr.current_price, currency
    return None, "USD"


def deepdive_to_dict(result: DeepDiveResult) -> dict[str, Any]:
    bu = result.bottom_up
    price, currency = _price_currency(bu)
    out: dict[str, Any] = {
        "ticker": result.ticker,
        # name: im DeepDiveResult (noch) nicht geführt → Ticker als Fallback, bis PR-2
        # den Anzeigenamen aus dem Daten-Adapter durchreicht (Logbuch-Folge).
        "name": result.ticker,
        "underlying": result.underlying.value,
        "wrapper": result.wrapper.value,
        "price": price,
        "currency": currency,
        "market": result.market,
        "found": True,                     # ein DeepDiveResult existiert ⇒ Titel gefunden
        "long": {
            "verdict": _LONG_VERDICT.get(result.recommendation.action, "NONE"),
            "confidence": result.recommendation.confidence,
            "rationale": result.recommendation.reasoning,
        },
        "short": {
            "verdict": _SHORT_VERDICT.get(result.short_action, "NONE"),
            "confidence": result.short_assessment.confidence if result.short_assessment else 0.0,
            "rationale": result.short_thesis,
        },
        "anomaly": _merge_anomaly(result.top_down_anomaly, result.bottom_up_anomaly),
    }
    # Equity-Block nur beim Equity-Underlying (andere Blöcke folgen in eigenen Scheiben).
    if result.underlying == Underlying.EQUITY and bu is not None:
        out["equity"] = _equity_block(bu)
    return out
