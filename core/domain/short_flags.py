from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class ShortFlag:
    name: str
    kind: str                  # "kern" | "verstaerker"
    archetype: Optional[str]   # nur kern
    weight: float
    fires: Callable
    detail: Callable


def _q(bu):   return getattr(bu, "quality", None)
def _et(bu):  return getattr(bu, "earnings_trend", None)
def _fu(bu):  return getattr(bu, "fundamentals", None)
def _vr(bu):  return getattr(bu, "valuation_range", None)
def _mo(bu):  return getattr(bu, "moat", None)
def _in(bu):  return getattr(bu, "insider", None)


def _lt(v, t):
    return v is not None and v < t


SHORT_FLAGS = [
    ShortFlag("altman_distress", "kern", "distress", 0.0,
              lambda bu: _q(bu) is not None and _lt(_q(bu).altman_z, 1.8),
              lambda bu: f"Altman-Z {_q(bu).altman_z:.1f} (Konkurszone)"),
    ShortFlag("coverage_weak", "kern", "distress", 0.0,
              lambda bu: _q(bu) is not None and _lt(_q(bu).interest_coverage, 1.0),
              lambda bu: f"Zinsdeckung {_q(bu).interest_coverage:.1f} (<1)"),
    ShortFlag("cash_burn_levered", "kern", "distress", 0.0,
              lambda bu: _q(bu) is not None and _lt(_q(bu).fcf_margin, 0.0)
                         and (_q(bu).debt_to_equity is not None and _q(bu).debt_to_equity > 1.0),
              lambda bu: f"negativer FCF + hohe Verschuldung (D/E {_q(bu).debt_to_equity:.1f})"),
    ShortFlag("liquidity_strain", "kern", "distress", 0.0,
              lambda bu: _q(bu) is not None and _lt(_q(bu).current_ratio, 1.0),
              lambda bu: f"Current Ratio {_q(bu).current_ratio:.2f} (<1)"),
    ShortFlag("earnings_collapse", "kern", "broken_growth", 0.0,
              lambda bu: _et(bu) is not None and (
                  getattr(_et(bu), "estimate_revision", None) == "down"
                  or _lt(getattr(_et(bu), "beat_rate", None), 0.4)),
              lambda bu: "Earnings kippen (Revision down / Beat-Rate niedrig)"),
    ShortFlag("growth_collapse", "kern", "secular_decline", 0.0,
              lambda bu: _fu(bu) is not None and _lt(getattr(_fu(bu), "revenue_cagr_3y", None), -5.0),
              lambda bu: f"Umsatz-CAGR(3J) {_fu(bu).revenue_cagr_3y:.1f}% (schrumpft)"),
    ShortFlag("valuation_extreme", "verstaerker", None, 0.05,
              lambda bu: (_vr(bu) is not None and getattr(_vr(bu), "position", None) == "overvalued")
                         or (_fu(bu) is not None and (getattr(_fu(bu), "peg_ratio", None) or 0) > 2.5),
              lambda bu: "Bewertung extrem (overvalued / PEG>2.5)"),
    ShortFlag("weak_moat", "verstaerker", None, 0.03,
              lambda bu: _mo(bu) is not None and (getattr(_mo(bu), "total_score", None) is not None)
                         and _mo(bu).total_score <= 3,
              lambda bu: f"schwacher Burggraben (Score {_mo(bu).total_score}/10)"),
    ShortFlag("insider_selling", "verstaerker", None, 0.04,
              lambda bu: _in(bu) is not None and "sell" in (getattr(_in(bu), "net_direction", "") or "").lower(),
              lambda bu: "Insider-Verkäufe"),
]
