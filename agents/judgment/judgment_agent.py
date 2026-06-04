import asyncio

from core.domain.events import DeepDiveResultReady
from core.domain.models import BottomUpResult, CockpitResult, DeepDiveResult, Signal
from core.domain.recommendation import derive_recommendation
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider

SYSTEM_PROMPT = """Du bist ein erfahrener Aktienanalyst.
Du kombinierst makroökonomischen Top-Down-Kontext mit Bottom-Up-Fundamentalanalyse.
Deine Urteile sind präzise, direkt und faktenbasiert. Maximal 4 Sätze."""


def _derive_alignment(signals: list[Signal]) -> str:
    valid = [s for s in signals if s is not None]
    bullish = valid.count(Signal.BULLISH)
    bearish = valid.count(Signal.BEARISH)
    if bullish >= 3 and bearish == 0:
        return "aligned_bullish"
    if bearish >= 3 and bullish == 0:
        return "aligned_bearish"
    if bullish > 0 and bearish > 0:
        return "contradicting"
    return "mixed"


def _dominant_signal(signals: list[Signal]) -> Signal:
    valid = [s for s in signals if s is not None]
    if not valid:
        return Signal.NEUTRAL
    bullish = valid.count(Signal.BULLISH)
    bearish = valid.count(Signal.BEARISH)
    if bullish > bearish:
        return Signal.BULLISH
    if bearish > bullish:
        return Signal.BEARISH
    return Signal.NEUTRAL


class JudgmentAgent:
    def __init__(self, llm: LLMProvider, bus: EventBus):
        self.llm = llm
        self.bus = bus

    async def run(
        self,
        ticker: str,
        top_down_context: str,
        bottom_up: BottomUpResult,
        cockpit: CockpitResult,
        market: str,
        in_portfolio: bool,
        top_down_available: bool,
    ) -> DeepDiveResult:
        fu  = bottom_up.fundamentals
        si  = bottom_up.short_interest
        ins = bottom_up.insider
        et  = bottom_up.earnings_trend
        mo  = bottom_up.moat
        vr  = bottom_up.valuation_range

        all_signals = [
            fu.signal  if fu  else None,
            si.signal  if si  else None,
            ins.signal if ins else None,
            et.signal  if et  else None,
            mo.signal  if mo  else None,
            vr.signal  if vr  else None,
        ]
        alignment      = _derive_alignment(all_signals)
        dominant_signal = _dominant_signal(all_signals)

        fu_line  = f"- Fundamentals: KGV={fu.pe_ratio}, Marge={fu.operating_margin}% → {fu.signal.value}" if fu  else "- Fundamentals: n/v"
        si_line  = f"- Short Interest: {si.short_float_pct}%, DTC={si.days_to_cover} → {si.signal.value}" if si  else "- Short Interest: n/v"
        ins_line = f"- Insider: {ins.net_direction} ({ins.recent_transactions} Tx) → {ins.signal.value}" if ins else "- Insider: n/v"
        et_line  = f"- Earnings: Beat={et.beat_rate}, Revision={et.estimate_revision} → {et.signal.value}" if et  else "- Earnings: n/v"
        mo_line  = f"- Burggraben: {mo.overall} (Score {mo.total_score}/10) → {mo.signal.value}" if mo  else "- Burggraben: n/v"
        vr_line  = f"- Bewertung: {vr.position} [{vr.combined_low:.0f}–{vr.combined_high:.0f}] → {vr.signal.value}" if vr  else "- Bewertung: n/v"

        prompt = f"""Aktie: {ticker} | Markt: {market} | Asset-Klasse: {bottom_up.asset_class}

TOP-DOWN KONTEXT:
{top_down_context}

BOTTOM-UP SIGNALE:
{fu_line}
{si_line}
{ins_line}
{et_line}
{mo_line}
{vr_line}

ALIGNMENT: {alignment}

Kombiniere Top-Down und Bottom-Up zu einem klaren Urteil. Gibt es Widersprüche?"""

        judgment = await asyncio.to_thread(self.llm.complete, prompt, SYSTEM_PROMPT)

        recommendation = derive_recommendation(
            alignment=alignment,
            signal=dominant_signal,
            asset_class=bottom_up.asset_class,
            in_portfolio=in_portfolio,
            market=market,
            cockpit=cockpit,
            top_down_available=top_down_available,
        )

        result = DeepDiveResult(
            ticker=ticker,
            asset_class=bottom_up.asset_class,
            top_down_context=top_down_context,
            top_down_available=top_down_available,
            bottom_up=bottom_up,
            judgment=judgment,
            alignment=alignment,
            recommendation=recommendation,
        )
        self.bus.publish(DeepDiveResultReady(source="judgment_agent", payload={
            "ticker": ticker, "alignment": alignment,
            "recommendation": recommendation.action.value,
        }))
        return result
