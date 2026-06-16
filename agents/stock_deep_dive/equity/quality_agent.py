import asyncio

from core.domain.events import QualityReady
from core.domain.models import QualitySnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus
from core.utils.scoring import piotroski_f_score

_DEFAULT = QualitySnapshot(
    gross_margin=None, operating_margin=None, net_margin=None, fcf_margin=None,
    roe=None, roa=None, roic=None, debt_to_equity=None, net_debt_ebitda=None,
    interest_coverage=None, current_ratio=None, altman_z=None, signal=Signal.NEUTRAL,
)

# Sektoren, für die Altman-Z nicht definiert ist (keine sinnvolle Z-Anwendung).
_ALTMAN_EXCLUDED = {"Financials", "Financial Services", "Banks", "Insurance"}
# Manufacturing-nahe Sektoren → Original-Z (2,99/1,81); sonst Z'' (2,6/1,1).
_ALTMAN_MANUFACTURING = {"Industrials", "Materials", "Manufacturing", "Consumer Cyclical"}

# Default-Mindest-ROIC, falls WACC fehlt (konservativ).
_ROIC_DEFAULT_HURDLE = 12.0


def _altman_thresholds(sector: str) -> tuple[float, float] | None:
    """(safe, distress)-Schwellen je Unternehmenstyp. None = nicht anwenden (Financials)."""
    if sector in _ALTMAN_EXCLUDED:
        return None
    if sector in _ALTMAN_MANUFACTURING:
        return 2.99, 1.81          # Original Altman Z (1968)
    return 2.6, 1.1               # Z'' für Dienstleister / Nicht-Manufacturing


def _signal(roe, roic, wacc, net_debt_ebitda, altman_z,
            interest_coverage, fcf_margin, f_score, sector: str = "default") -> Signal:
    score = 0

    # ROIC − WACC-Spread (Wertschöpfung nur bei ROIC > WACC)
    if roic is not None:
        if wacc is not None:
            spread = roic - wacc
            score += 1 if spread > 2.0 else (-1 if spread < -2.0 else 0)
        else:
            score += 1 if roic > _ROIC_DEFAULT_HURDLE else (-1 if roic < 5 else 0)

    # ROE (Leverage-verzerrt → schwächer gewichtet, nur als Bestätigung)
    if roe is not None:
        score += 1 if roe > 15 else (-1 if roe < 5 else 0)

    # Net Debt / EBITDA (Standard-Schwellen, beibehalten)
    if net_debt_ebitda is not None:
        score += 1 if net_debt_ebitda < 2.0 else (-1 if net_debt_ebitda > 4.0 else 0)

    # Altman-Z nur bei anwendbarem Unternehmenstyp
    if altman_z is not None:
        thr = _altman_thresholds(sector)
        if thr is not None:
            safe, distress = thr
            score += 1 if altman_z > safe else (-1 if altman_z < distress else 0)

    # interest_coverage (zuvor ungenutzt)
    if interest_coverage is not None:
        score += 1 if interest_coverage > 5.0 else (-1 if interest_coverage < 1.5 else 0)

    # fcf_margin (zuvor ungenutzt)
    if fcf_margin is not None:
        score += 1 if fcf_margin > 10.0 else (-1 if fcf_margin < 0.0 else 0)

    # Piotroski F-Score als Gesamt-Qualitätsanker (kräftig gewichtet)
    if f_score is not None:
        if f_score >= 7:
            score += 2
        elif f_score <= 3:
            score -= 2

    return Signal.BULLISH if score >= 2 else (Signal.BEARISH if score <= -2 else Signal.NEUTRAL)


class QualityAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self, ticker: str, sector: str = "default") -> QualitySnapshot:
        data = await asyncio.to_thread(self.provider.get_fundamentals, ticker)
        if isinstance(data, Exception):
            data = {}

        roe            = data.get("roe")
        roa            = data.get("roa")
        roic           = data.get("roic")
        wacc           = data.get("wacc")
        gross_margin   = data.get("gross_margin")
        op_margin      = data.get("operating_margin")
        net_margin     = data.get("net_margin")
        fcf_margin     = data.get("fcf_margin")
        dte            = data.get("debt_to_equity")
        net_debt_ebitda = data.get("net_debt_ebitda")
        interest_cov   = data.get("interest_coverage")
        current_ratio  = data.get("current_ratio")
        altman_z       = data.get("altman_z")
        f_score        = piotroski_f_score(data)

        result = QualitySnapshot(
            gross_margin=gross_margin, operating_margin=op_margin,
            net_margin=net_margin, fcf_margin=fcf_margin,
            roe=roe, roa=roa, roic=roic,
            debt_to_equity=dte, net_debt_ebitda=net_debt_ebitda,
            interest_coverage=interest_cov, current_ratio=current_ratio,
            altman_z=altman_z,
            signal=_signal(roe, roic, wacc, net_debt_ebitda, altman_z,
                           interest_cov, fcf_margin, f_score, sector=sector),
        )
        self.bus.publish(QualityReady(source="quality_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> QualitySnapshot:
        return _DEFAULT
