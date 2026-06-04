import asyncio

from core.domain.events import DeepDiveResultReady
from core.domain.models import (
    AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult, Signal,
)
from core.domain.recommendation import compute_confidence, derive_recommendation
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider

SYSTEM_PROMPT = """Du bist ein erfahrener Aktienanalyst.
Du kombinierst makroökonomischen Top-Down-Kontext mit Bottom-Up-Fundamentalanalyse.
Deine Urteile sind präzise, direkt und faktenbasiert. Maximal 4 Sätze."""

XAI_SYSTEM_PROMPT = """Du bist ein erfahrener Finanzanalyst und erklärst Anlageentscheidungen.
Schreibe eine ausführliche, nachvollziehbare Begründung für die getroffene Empfehlung.
Struktur (alle 5 Punkte ausführen):
(1) Top-Down-Analyse: welche makroökonomischen Signale waren entscheidend und warum
(2) Bottom-Up-Analyse: welche Kennzahlen haben die Entscheidung beeinflusst
(3) Widersprüche: wo lagen sie und wie wurden sie aufgelöst
(4) Konfidenz: warum diese Stufe — was macht die Lage unsicher oder klar
(5) Kipppunkte: welche Entwicklungen würden die Einschätzung ändern
Kein Fachjargon. Direkt, klar und für einen informierten Anleger verständlich."""


def _derive_alignment(signals: list[Signal]) -> str:
    valid   = [s for s in signals if s is not None]
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
    valid   = [s for s in signals if s is not None]
    if not valid:
        return Signal.NEUTRAL
    bullish = valid.count(Signal.BULLISH)
    bearish = valid.count(Signal.BEARISH)
    if bullish > bearish:
        return Signal.BULLISH
    if bearish > bullish:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _backtester_summary(context: dict) -> str:
    if not context:
        return "Noch kein Backtesting-Report verfügbar (System läuft erst seit Kurzem)."
    acc = context.get("accuracy_30d")
    if acc is not None:
        return f"System-Treffsicherheit (30 Tage): {acc:.0%}"
    notes = context.get("notes", "")
    return notes or "Backtesting-Daten vorhanden."


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
        top_down_anomaly: AnomalyReport,
        bottom_up_anomaly: AnomalyReport,
        backtester_context: dict,
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
        alignment        = _derive_alignment(all_signals)
        dominant_sig     = _dominant_signal(all_signals)

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

TOP-DOWN ANOMALIEN:
{top_down_anomaly.summary}

BOTTOM-UP ANOMALIEN:
{bottom_up_anomaly.summary}

SYSTEM-TREFFSICHERHEIT:
{_backtester_summary(backtester_context)}

Kombiniere Top-Down und Bottom-Up zu einem klaren Urteil. Gibt es Widersprüche?"""

        # LLM-Call 1: Urteil
        judgment = await asyncio.to_thread(self.llm.complete, prompt, SYSTEM_PROMPT)

        # Confidence berechnen
        regime_conf = cockpit.macro.regime_confidence if cockpit else 0.5
        confidence = compute_confidence(
            alignment=alignment,
            regime_confidence=regime_conf,
            td_anomaly=top_down_anomaly,
            bu_anomaly=bottom_up_anomaly,
        )

        # Empfehlung ableiten
        recommendation = derive_recommendation(
            alignment=alignment,
            signal=dominant_sig,
            asset_class=bottom_up.asset_class,
            in_portfolio=in_portfolio,
            market=market,
            cockpit=cockpit,
            top_down_available=top_down_available,
            confidence=confidence,
        )

        # LLM-Call 2: XAI-Erklärung
        xai_prompt = f"""Aktie: {ticker} | Empfehlung: {recommendation.action.value} | Konfidenz: {confidence:.0%}

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

ANOMALIEN:
{top_down_anomaly.summary}
{bottom_up_anomaly.summary}

URTEIL DES ANALYSTEN:
{judgment}

Erkläre ausführlich warum diese Empfehlung getroffen wurde."""

        xai_explanation = await asyncio.to_thread(
            self.llm.complete, xai_prompt, XAI_SYSTEM_PROMPT
        )

        result = DeepDiveResult(
            ticker=ticker,
            asset_class=bottom_up.asset_class,
            market=market,
            top_down_context=top_down_context,
            top_down_available=top_down_available,
            bottom_up=bottom_up,
            judgment=judgment,
            alignment=alignment,
            recommendation=recommendation,
            dominant_signal=dominant_sig.value,
            confidence=confidence,
            xai_explanation=xai_explanation,
        )

        self.bus.publish(DeepDiveResultReady(source="judgment_agent", payload={
            "ticker": ticker,
            "alignment": alignment,
            "recommendation": recommendation.action.value,
            "confidence": confidence,
        }))

        return result
