import asyncio

from core.domain.events import ShortThesisReady
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider

# System-Prompt für die Short-These: prägnant, nüchtern, max. 6 Sätze; erklärt nur die
# deterministischen Engine-Befunde — kein Erfinden oder Ausschmücken.
SHORT_SYSTEM_PROMPT = """Du bist ein erfahrener Leerverkaufs-Analyst (Short-Seller).
Formuliere aus den strukturierten Engine-Befunden eine klare, nüchterne Short-These (max. 6 Sätze).
Erkläre die deterministischen Befunde — erfinde nichts dazu. Liegt keine belastbare Kern-These vor,
sag klar, dass und warum kein überzeugendes Short-Setup besteht."""

# System-Prompt für die XAI-Erklärung: ausführlich, warum genau diese Short-Aktion/Konfidenz —
# bleibt bei den gelieferten Fakten (Flags, Archetypen, Regime, Squeeze-Risiko).
SHORT_XAI_SYSTEM_PROMPT = """Du bist ein Finanzanalyst und erklärst eine Short-Einschätzung nachvollziehbar.
Erkläre ausführlich, warum die Engine zu dieser Short-Aktion und Konfidenz kommt — anhand der genannten
Flags/Archetypen/Regime/Squeeze. Bleib bei den gelieferten Fakten."""


def _assessment_block(sa) -> str:
    """Formatiert das ShortAssessment als lesbaren Text-Block für die LLM-Prompts."""
    # Größe/Stop sind Optional[float] (None möglich) → 'n/v' statt eines irreführenden
    # 'None%' im Prompt (analog zur 'n/v'-Konvention im ConflictAgent).
    size = f"{sa.suggested_size_pct}%" if sa.suggested_size_pct is not None else "n/v"
    stop = f"{sa.stop_pct}%" if sa.stop_pct is not None else "n/v"
    return (
        f"Short-Aktion: {sa.short_action.value} | Konfidenz: {sa.confidence:.0%}\n"
        f"Archetypen: {', '.join(sa.archetypes) or 'keine'}\n"
        f"Befunde (Flags): {'; '.join(sa.thesis_flags) or 'keine'}\n"
        f"Regime-Effekt: {sa.regime_effect} | Squeeze-Risiko: {sa.squeeze_risk} | "
        f"Hard-to-borrow: {sa.hard_to_borrow}\n"
        f"Größe: {size} | Stop: {stop}"
    )


class ShortThesisAgent:
    """Erzeugt aus dem deterministischen ShortAssessment eine Fließtext-These + XAI.
    Spiegelt die Long-Seite (judgment + xai_explanation); erklärt die Engine, erfindet nichts.

    Zwei sequenzielle LLM-Calls (Muster: ConflictAgent):
      1. These  — formuliert das Short-Setup aus den Engine-Befunden.
      2. XAI    — erklärt ausführlich, warum diese Einschätzung getroffen wurde;
                  die These wird im XAI-Prompt mitgeliefert (Kontext für das Modell).

    Defensiv: jeder Fehlerpfad (None-Assessment, LLM-Exception) → ("", "").
    """

    def __init__(self, llm: LLMProvider, bus: EventBus):
        self.llm = llm
        self.bus = bus

    async def run(self, ticker: str, short_assessment, asset_class: str) -> tuple[str, str]:
        """Gibt (short_thesis, short_xai) zurück. Bei None-Assessment oder Fehler: ("", "")."""
        # Null-Schutz: kein Assessment → kein LLM-Call, keine Exception
        if short_assessment is None:
            return "", ""
        try:
            block = _assessment_block(short_assessment)

            # Call 1: Short-These aus den Engine-Befunden formulieren
            thesis_prompt = (
                f"Titel: {ticker} | Anlageklasse: {asset_class}\n\n"
                f"ENGINE-BEFUNDE (Short):\n{block}\n\n"
                f"Formuliere die Short-These."
            )
            thesis = await asyncio.to_thread(self.llm.complete, thesis_prompt, SHORT_SYSTEM_PROMPT)

            # Call 2: XAI-Erklärung — enthält explizit die These als Kontext
            xai_prompt = (
                f"Titel: {ticker} | Short-Aktion: {short_assessment.short_action.value} | "
                f"Konfidenz: {short_assessment.confidence:.0%}\n\n"
                f"ENGINE-BEFUNDE (Short):\n{block}\n\n"
                f"SHORT-THESE DES ANALYSTEN:\n{thesis}\n\n"
                f"Erkläre ausführlich, warum diese Short-Einschätzung getroffen wurde."
            )
            xai = await asyncio.to_thread(self.llm.complete, xai_prompt, SHORT_XAI_SYSTEM_PROMPT)
        except Exception:
            # Jeder LLM-Fehler (Timeout, API-Fehler, …) → sicherer Default, kein Crash
            return "", ""

        # Event veröffentlichen (konsistent mit den übrigen Agenten; Daten fließen via Rückgabewert).
        # Bewusst SEPARAT umhüllt: ein Bus-Fehler darf die bereits berechneten (teuren)
        # LLM-Texte NICHT verwerfen — These/XAI werden trotzdem zurückgegeben.
        try:
            self.bus.publish(ShortThesisReady(
                source="short_thesis_agent",
                payload={"ticker": ticker},
            ))
        except Exception:
            pass
        return thesis, xai
