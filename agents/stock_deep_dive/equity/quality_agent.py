import asyncio
from core.domain.events import QualityReady
from core.domain.models import QualitySnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = QualitySnapshot(
    gross_margin=None, operating_margin=None, net_margin=None, fcf_margin=None,
    roe=None, roa=None, roic=None, debt_to_equity=None, net_debt_ebitda=None,
    interest_coverage=None, current_ratio=None, altman_z=None, signal=Signal.NEUTRAL,
)


def _signal(roe: float | None, roic: float | None, net_debt_ebitda: float | None,
            altman_z: float | None) -> Signal:
    score = 0
    if roe is not None:
        score += 1 if roe > 15 else (-1 if roe < 5 else 0)
    if roic is not None:
        score += 1 if roic > 12 else (-1 if roic < 5 else 0)
    if net_debt_ebitda is not None:
        score += 1 if net_debt_ebitda < 2.0 else (-1 if net_debt_ebitda > 4.0 else 0)
    if altman_z is not None:
        score += 1 if altman_z > 2.99 else (-1 if altman_z < 1.81 else 0)
    return Signal.BULLISH if score >= 2 else (Signal.BEARISH if score <= -2 else Signal.NEUTRAL)


class QualityAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self, ticker: str) -> QualitySnapshot:
        data = await asyncio.to_thread(self.provider.get_fundamentals, ticker)
        if isinstance(data, Exception):
            data = {}

        roe            = data.get("roe")
        roa            = data.get("roa")
        roic           = data.get("roic")
        gross_margin   = data.get("gross_margin")
        op_margin      = data.get("operating_margin")
        net_margin     = data.get("net_margin")
        fcf_margin     = data.get("fcf_margin")
        dte            = data.get("debt_to_equity")
        net_debt_ebitda = data.get("net_debt_ebitda")
        interest_cov   = data.get("interest_coverage")
        current_ratio  = data.get("current_ratio")
        altman_z       = data.get("altman_z")

        result = QualitySnapshot(
            gross_margin=gross_margin, operating_margin=op_margin,
            net_margin=net_margin, fcf_margin=fcf_margin,
            roe=roe, roa=roa, roic=roic,
            debt_to_equity=dte, net_debt_ebitda=net_debt_ebitda,
            interest_coverage=interest_cov, current_ratio=current_ratio,
            altman_z=altman_z,
            signal=_signal(roe, roic, net_debt_ebitda, altman_z),
        )
        self.bus.publish(QualityReady(source="quality_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> QualitySnapshot:
        return _DEFAULT
