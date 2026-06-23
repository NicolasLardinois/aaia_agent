from agents.anomaly_chief_agent import AnomalyChiefAgent
from agents.judgment_chief_agent import JudgmentChiefAgent
from agents.backtester_chief_agent import BacktesterChiefAgent
from agents.conflict.conflict_agent import ConflictAgent
from agents.short_thesis.short_thesis_agent import ShortThesisAgent
from core.domain.conflict_inbox import record_conflict
from core.domain.models import AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult, PositionState
from core.domain.recommendation import FULL_ANALYSIS_MARKETS
from core.domain.taxonomy import legacy_asset_class, legacy_to_taxonomy
from core.domain.top_down_context import derive_top_down_context
from core.ports.conflict_store import ConflictStorePort
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider
from core.ports.memory_port import MemoryPort
from core.ports.portfolio_port import PortfolioPort


class JudgmentOrchestrator:
    """
    Modus 3 — Kombinations-Urteil.
    Koordiniert 3 ChiefAgents: Anomalie-Erkennung, Urteil, Backtesting-Kontext.
    """

    def __init__(self, llm: LLMProvider, bus: EventBus, memory: MemoryPort,
                 portfolio_port: PortfolioPort | None = None,
                 conflict_store: ConflictStorePort | None = None):
        self.memory              = memory
        self.anomaly_chief       = AnomalyChiefAgent(bus)
        self.judgment_chief      = JudgmentChiefAgent(llm, bus, portfolio_port)
        self.backtester_chief    = BacktesterChiefAgent(memory, bus)
        self.conflict_agent      = ConflictAgent(llm, bus)
        self.short_thesis_agent  = ShortThesisAgent(llm, bus)
        # Konflikt-Inbox: None erlaubt (bestehende Bauten ohne Store bleiben kompatibel)
        self.conflict_store      = conflict_store

    async def run(
        self,
        cockpit: CockpitResult,
        bottom_up: BottomUpResult,
        market: str,
        current_position: PositionState = PositionState.NONE,
        sector: str = "default",
    ) -> DeepDiveResult:
        top_down_available = cockpit is not None and market in FULL_ANALYSIS_MARKETS
        top_down_context = (
            derive_top_down_context(
                cockpit,
                sector=sector,
                market=market,
                underlying=bottom_up.underlying,
            )
            if top_down_available
            else f"Kein vollständiger Top-Down-Kontext verfügbar (Markt: {market})."
        )

        ticker_history = self.memory.load_history(bottom_up.ticker, days=90)
        global_history = self.memory.load_global_history(days=90)

        td_anomaly, bu_anomaly = self.anomaly_chief.run(
            cockpit, bottom_up, ticker_history, global_history, market=market
        )
        backtester_context = self.backtester_chief.load_context()

        try:
            result = await self.judgment_chief.run(
                ticker=bottom_up.ticker,
                top_down_context=top_down_context,
                bottom_up=bottom_up,
                cockpit=cockpit,
                market=market,
                current_position=current_position,
                top_down_available=top_down_available,
                top_down_anomaly=td_anomaly,
                bottom_up_anomaly=bu_anomaly,
                backtester_context=backtester_context,
            )
        except Exception:
            # underlying/wrapper defensiv auflösen: BottomUpResult trägt die Felder direkt;
            # Test-Doubles (SimpleNamespace) können legacy asset_class-String tragen → Fallback.
            if hasattr(bottom_up, "underlying") and hasattr(bottom_up, "wrapper"):
                from core.domain.taxonomy import Underlying, Wrapper as _W
                _und = bottom_up.underlying
                _wrp = bottom_up.wrapper
                if isinstance(_und, Underlying) and isinstance(_wrp, _W):
                    _legacy_ac = legacy_asset_class(_und, _wrp)
                else:
                    _legacy_ac = getattr(bottom_up, "asset_class", "equity")
            else:
                _legacy_ac = getattr(bottom_up, "asset_class", "equity")
            result = JudgmentChiefAgent.default(
                ticker=bottom_up.ticker,
                asset_class=_legacy_ac,
                market=market,
            )

        result.top_down_anomaly = td_anomaly
        result.bottom_up_anomaly = bu_anomaly

        if result.conflict:
            try:
                result.conflict_resolution = await self.conflict_agent.run(
                    ticker=bottom_up.ticker, current_position=current_position,
                    recommendation=result.recommendation, short_assessment=result.short_assessment,
                    conflict_reason=result.conflict_reason,
                    top_down_anomaly=td_anomaly, bottom_up_anomaly=bu_anomaly,
                    backtester_context=backtester_context)
            except Exception:
                result.conflict_resolution = None

            # On-demand Aufnahme in die Konflikt-Inbox (defensiv: Store-Fehler darf nie crashen)
            if self.conflict_store is not None and result.conflict_resolution is not None:
                try:
                    record_conflict(
                        self.conflict_store,
                        bottom_up.ticker,
                        current_position.value,
                        result.conflict_resolution.verdict,
                        result.conflict_resolution.reasoning,
                        "on_demand",
                    )
                except Exception:
                    pass  # Inbox ist nie kritisch — Analyse läuft weiter

        # Short-These + XAI: immer erzeugen, solange short_assessment vorhanden (null-sicher)
        if result.short_assessment is not None:
            try:
                result.short_thesis, result.short_xai = await self.short_thesis_agent.run(
                    bottom_up.ticker, result.short_assessment,
                    # Legacy-String für ShortThesisAgent: abgeleitet aus underlying/wrapper
                    # (Phase-2: ShortThesisAgent direkt auf underlying/wrapper umstellen)
                    legacy_asset_class(result.underlying, result.wrapper))
            except Exception:
                result.short_thesis, result.short_xai = "", ""

        self.memory.save_analysis(result, cockpit, price=None)
        return result
