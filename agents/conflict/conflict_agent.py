import asyncio

from core.domain.events import ConflictResolutionReady
from core.domain.models import ConflictResolution
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider

SYSTEM_PROMPT = """Du bist ein Risk-Reconciliation-Spezialist. Eine bestehende Position
widerspricht der aktuellen Analyse. Wäge nüchtern ab, ob die ursprüngliche These gekippt ist.
Antworte in der ERSTEN Zeile mit GENAU einem von: `VERDICT: EXIT`, `VERDICT: HOLD`, `VERDICT: REVERSE`.
Danach eine kurze, klare Begründung (max. 5 Sätze).
EXIT = Ausstieg empfohlen (SELL bei Long / COVER bei Short); HOLD = These hält trotz Gegenwind;
REVERSE = Ausstieg + Gegenposition (aggressiv)."""

_VALID = {"EXIT", "HOLD", "REVERSE"}


def _parse_verdict(text: str) -> str:
    """Verdikt ausschließlich aus der `VERDICT:`-Zeile lesen.
    Bewusst KEIN Stichwort-Scan im Fließtext — Verneinungen/Erwähnungen wie
    „kein Exit" oder „nicht aussteigen" würden sonst fälschlich EXIT liefern.
    Fehlt eine gültige Zeile → konservativer Default HOLD (siehe Spec)."""
    for line in (text or "").splitlines():
        s = line.strip().upper()
        if s.startswith("VERDICT:"):
            parts = s.split(":", 1)
            tok = parts[1].strip().split()[0] if len(parts) > 1 and parts[1].strip() else ""
            if tok in _VALID:
                return tok
    return "HOLD"


class ConflictAgent:
    def __init__(self, llm: LLMProvider, bus: EventBus):
        self.llm = llm
        self.bus = bus

    async def run(self, ticker, current_position, recommendation, short_assessment,
                  conflict_reason, top_down_anomaly, bottom_up_anomaly, backtester_context):
        track = ""
        if backtester_context:
            hr = backtester_context.get("hit_rate")
            if hr is not None:
                track = f"\nSYSTEM-TRACK-RECORD (Kontext): historische Treffsicherheit {hr:.0%}"

        if recommendation is not None:
            long_line = f"LONG-LESART: {recommendation.action.value} — {recommendation.reasoning}"
        else:
            long_line = "LONG-LESART: n/v"
        if short_assessment:
            sa = short_assessment
            short_line = (f"SHORT-LESART: {sa.short_action.value}, Konfidenz {sa.confidence:.0%}, "
                          f"Typ {', '.join(sa.archetypes) or 'n/v'}; "
                          f"Gründe: {'; '.join(sa.thesis_flags) or 'n/v'}")
        else:
            short_line = "SHORT-LESART: n/v"

        # Anomalie-Summaries defensiv (None → "keine"); der Orchestrator umhüllt zwar
        # mit try/except, aber so geht bei fehlenden Daten das Urteil nicht still verloren.
        td_sum = getattr(top_down_anomaly, "summary", None) or "keine"
        bu_sum = getattr(bottom_up_anomaly, "summary", None) or "keine"

        prompt = f"""Titel: {ticker} | Gehaltene Position: {current_position.value}
KONFLIKT: {conflict_reason}

{long_line}
{short_line}

ANOMALIEN:
{td_sum}
{bu_sum}{track}

Hat sich die gehaltene These wirklich gedreht? Verdikt + Begründung."""

        text = await asyncio.to_thread(self.llm.complete, prompt, SYSTEM_PROMPT)
        resolution = ConflictResolution(verdict=_parse_verdict(text), reasoning=text)
        # Konsistenz mit den übrigen Agenten: Fertig-Event veröffentlichen
        # (Daten fließen via Rückgabewert/result; das Event ist für spätere Listener).
        self.bus.publish(ConflictResolutionReady(
            source="conflict_agent",
            payload={"ticker": ticker, "verdict": resolution.verdict},
        ))
        return resolution
