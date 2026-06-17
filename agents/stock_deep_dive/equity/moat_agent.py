import asyncio
import json

from core.domain.events import MoatReady
from core.domain.models import MoatSnapshot, MoatScore, Signal
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider

SYSTEM_PROMPT = """Du bist ein Experte für Wettbewerbsanalyse nach Warren Buffetts Burggraben-Konzept.
Analysiere das Unternehmen und bewerte jeden Burggraben-Typ mit:
  0 = keiner, 1 = schwach, 2 = stark

Antworte NUR mit validem JSON, kein Markdown, kein Text davor oder danach."""

PROMPT_TEMPLATE = """Unternehmen: {ticker}

Bewerte die folgenden Burggraben-Typen für dieses Unternehmen:
1. intangible_assets (Patente, Lizenzen, Markennamen)
2. switching_costs (Wechselkosten für Kunden)
3. network_effects (Netzwerkeffekte)
4. cost_advantages (Kostenvorteile, Skaleneffekte)
5. efficient_scale (Effiziente Skalierung in Nischenmärkten)

Antworte in diesem JSON-Format:
{{
  "intangible_assets": {{"score": 0-2, "evidence": "kurze Begründung"}},
  "switching_costs":   {{"score": 0-2, "evidence": "kurze Begründung"}},
  "network_effects":   {{"score": 0-2, "evidence": "kurze Begründung"}},
  "cost_advantages":   {{"score": 0-2, "evidence": "kurze Begründung"}},
  "efficient_scale":   {{"score": 0-2, "evidence": "kurze Begründung"}},
  "reasoning": "Gesamtbegründung in 2-3 Sätzen"
}}"""

_ZERO = MoatScore(score=0, evidence="n/a")
_DEFAULT = MoatSnapshot(
    intangible_assets=_ZERO, switching_costs=_ZERO, network_effects=_ZERO,
    cost_advantages=_ZERO, efficient_scale=_ZERO,
    total_score=0, overall="none", llm_reasoning="", signal=Signal.NEUTRAL,
)


def _overall(scores: list[MoatScore]) -> str:
    """Maximum-/Schwellen-pro-Kategorie statt linearer Summe.
    Eine dominante Quelle (Score 2) begründet allein 'wide'; eine 1er-Quelle 'narrow'."""
    max_score = max((s.score for s in scores), default=0)
    if max_score >= 2:
        return "wide"
    if max_score >= 1:
        return "narrow"
    return "none"


def _signal(overall: str) -> Signal:
    """Moat ist ein Qualitäts-/Prämien-Merkmal, kein Timing-Signal.
    Wide → BULLISH (rechtfertigt Bewertungsprämie); None/Narrow → NEUTRAL (nicht BEARISH)."""
    if overall == "wide":
        return Signal.BULLISH
    return Signal.NEUTRAL


class MoatAgent:
    def __init__(self, llm: LLMProvider, bus: EventBus):
        self.llm = llm
        self.bus = bus

    async def run(self, ticker: str) -> MoatSnapshot:
        prompt = PROMPT_TEMPLATE.format(ticker=ticker)
        raw = await asyncio.to_thread(self.llm.complete, prompt, SYSTEM_PROMPT)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.bus.publish(MoatReady(source="moat_agent", payload={"ticker": ticker, "error": "parse_failed"}))
            return _DEFAULT

        def _score(key: str) -> MoatScore:
            d = data.get(key, {})
            return MoatScore(score=int(d.get("score", 0)), evidence=d.get("evidence", ""))

        ia = _score("intangible_assets")
        sc = _score("switching_costs")
        ne = _score("network_effects")
        ca = _score("cost_advantages")
        es = _score("efficient_scale")
        all_scores = [ia, sc, ne, ca, es]
        total = ia.score + sc.score + ne.score + ca.score + es.score
        overall = _overall(all_scores)

        result = MoatSnapshot(
            intangible_assets=ia, switching_costs=sc, network_effects=ne,
            cost_advantages=ca, efficient_scale=es,
            total_score=total,
            overall=overall,
            llm_reasoning=data.get("reasoning", ""),
            signal=_signal(overall),
        )
        self.bus.publish(MoatReady(source="moat_agent", payload={
            "ticker": ticker, "total_score": total, "overall": result.overall,
        }))
        return result

    @staticmethod
    def default() -> MoatSnapshot:
        return _DEFAULT
