import asyncio

from core.domain.events import DeepDiveResultReady
from core.domain.models import (
    AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult, PositionState, Signal,
)
from core.domain.recommendation import compute_confidence, derive_recommendation, detect_conflict
from core.domain.short_assessment import derive_short_assessment
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


# Gewichte nach prädiktiver Kraft (Index-aligned zu all_signals in run()):
# [Fundamentals, ShortInterest, Insider, Earnings, Moat, Valuation]
_ALIGNMENT_WEIGHTS = [1.0, 0.5, 0.5, 1.0, 0.75, 1.5]
_ALIGNMENT_THRESHOLD = 0.60


def _derive_alignment(signals: list[Signal]) -> str:
    weights = _ALIGNMENT_WEIGHTS[:len(signals)]
    if len(weights) < len(signals):
        weights = weights + [1.0] * (len(signals) - len(weights))

    bull_w = sum(w for s, w in zip(signals, weights)
                 if s is not None and s == Signal.BULLISH)
    bear_w = sum(w for s, w in zip(signals, weights)
                 if s is not None and s == Signal.BEARISH)
    directional = bull_w + bear_w
    if directional == 0:
        return "mixed"

    if bull_w / directional > _ALIGNMENT_THRESHOLD:
        return "aligned_bullish"
    if bear_w / directional > _ALIGNMENT_THRESHOLD:
        return "aligned_bearish"
    if bull_w > 0 and bear_w > 0:
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


def _bottom_up_signals(bottom_up) -> list[Signal | None]:
    """Bottom-Up-Signale für Alignment + dominantes Signal sammeln.

    Equity liefert seine Signale aus den Sub-Bausteinen (Fundamentals … Bewertung).
    Eine Anleihe trägt diese Bausteine nicht — ihr bereits aggregiertes Gesamtsignal
    steckt im `BondResult.overall_signal` (PR #19). Ohne den letzten Slot bliebe jede
    Anleihe-Empfehlung NEUTRAL, weil alle sechs Equity-Bausteine `None` sind.
    Die ersten sechs Positionen bleiben index-gleich zu `_ALIGNMENT_WEIGHTS`.
    """
    fu  = bottom_up.fundamentals
    si  = bottom_up.short_interest
    ins = bottom_up.insider
    et  = bottom_up.earnings_trend
    mo  = bottom_up.moat
    vr  = bottom_up.valuation_range
    bond = getattr(bottom_up, "bond", None)   # defensiv: Test-Doubles tragen evtl. kein Bond-Feld
    return [
        fu.signal  if fu  else None,
        si.signal  if si  else None,
        ins.signal if ins else None,
        et.signal  if et  else None,
        mo.signal  if mo  else None,
        vr.signal  if vr  else None,
        bond.overall_signal if bond else None,
    ]


def _backtester_summary(context: dict) -> str:
    if not context:
        return "Noch kein Backtesting-Report verfügbar (System läuft erst seit Kurzem)."
    hr = context.get("hit_rate")
    n = context.get("sample_size")
    lo = context.get("hit_rate_ci_low")
    hi = context.get("hit_rate_ci_high")
    if hr is not None and lo is not None and hi is not None and n:
        return (f"System-Treffsicherheit (fixes Forward-Window, marktbereinigt): "
                f"{hr:.0%} [{lo:.0%}–{hi:.0%}] aus N={n}")
    if hr is not None:
        return f"System-Treffsicherheit (marktbereinigt): {hr:.0%}"
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
        current_position: PositionState,
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

        all_signals = _bottom_up_signals(bottom_up)
        alignment        = _derive_alignment(all_signals)
        dominant_sig     = _dominant_signal(all_signals)

        fu_line  = f"- Fundamentals: KGV={fu.pe_ratio}, Marge={fu.operating_margin}% → {fu.signal.value}" if fu  else "- Fundamentals: n/v"
        si_line  = f"- Short Interest: {si.short_float_pct}%, DTC={si.days_to_cover} → {si.signal.value}" if si  else "- Short Interest: n/v"
        ins_line = f"- Insider: {ins.net_direction} ({ins.recent_transactions} Tx) → {ins.signal.value}" if ins else "- Insider: n/v"
        et_line  = f"- Earnings: Beat={et.beat_rate}, Revision={et.estimate_revision} → {et.signal.value}" if et  else "- Earnings: n/v"
        mo_line  = f"- Burggraben: {mo.overall} (Score {mo.total_score}/10) → {mo.signal.value}" if mo  else "- Burggraben: n/v"
        vr_line  = f"- Bewertung: {vr.position} [{vr.combined_low:.0f}–{vr.combined_high:.0f}] → {vr.signal.value}" if vr  else "- Bewertung: n/v"
        # Anleihen tragen keine Equity-Bausteine; ihr aggregiertes Gesamtsignal (PR #19)
        # gehört in den Prompt, sonst sähe der LLM nur "n/v" trotz bullishem Alignment.
        bond = getattr(bottom_up, "bond", None)
        bond_line = (
            f"- Anleihe-Gesamtsignal: {bond.overall_signal.value} "
            f"(Credit-Band: {bond.credit_band.value if bond.credit_band else 'n/v'}, "
            f"Risikoaffinität: {bond.risk_affinity.value if bond.risk_affinity else 'n/v'})"
        ) if bond else None
        bottom_up_block = "\n".join(
            ln for ln in [fu_line, si_line, ins_line, et_line, mo_line, vr_line, bond_line] if ln)

        prompt = f"""Aktie: {ticker} | Markt: {market} | Asset-Klasse: {bottom_up.asset_class}

TOP-DOWN KONTEXT:
{top_down_context}

BOTTOM-UP SIGNALE:
{bottom_up_block}

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
            calibration=backtester_context.get("calibration") if backtester_context else None,
        )

        # Empfehlung ableiten
        recommendation = derive_recommendation(
            alignment=alignment,
            signal=dominant_sig,
            asset_class=bottom_up.asset_class,
            current_position=current_position,
            market=market,
            cockpit=cockpit,
            top_down_available=top_down_available,
            confidence=confidence,
        )
        short_assessment = derive_short_assessment(
            bottom_up, cockpit, current_position, top_down_available,
            bottom_up_anomaly, top_down_anomaly)
        conflict, conflict_reason = detect_conflict(
            current_position, alignment, dominant_sig, short_assessment, confidence)

        # LLM-Call 2: XAI-Erklärung
        xai_prompt = f"""Aktie: {ticker} | Empfehlung: {recommendation.action.value} | Konfidenz: {confidence:.0%}

TOP-DOWN KONTEXT:
{top_down_context}

BOTTOM-UP SIGNALE:
{bottom_up_block}

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
            short_action=short_assessment.short_action,
            short_assessment=short_assessment,
            conflict=conflict,
            conflict_reason=conflict_reason,
        )

        self.bus.publish(DeepDiveResultReady(source="judgment_agent", payload={
            "ticker": ticker,
            "alignment": alignment,
            "recommendation": recommendation.action.value,
            "confidence": confidence,
        }))

        return result
