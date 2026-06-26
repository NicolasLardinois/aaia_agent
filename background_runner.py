import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from config.settings import ANTHROPIC_API_KEY, require_keys
from adapters.event_bus.redis_bus import InMemoryEventBus
from adapters.memory.supabase_memory import SupabaseMemory
from adapters.data.yahoo_finance import YahooFinanceProvider
from adapters.persistence.json_portfolio import JsonPortfolioProvider
from adapters.persistence.supabase_conflict_store import SupabaseConflictStore
from adapters.cache.result_cache import ResultCache
from adapters.llm.claude_adapter import ClaudeAdapter
from agents.backtester_chief_agent import BacktesterChiefAgent
from adapters.data.yahoo_live_price import YahooLivePriceProvider
from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent, make_returns_provider
from agents.conflict.portfolio_conflict_scan import scan_portfolio_conflicts
from core.domain.models import PositionState
from orchestrators.judgment_orchestrator import JudgmentOrchestrator

# Standard-Markt für den proaktiven Scan: im Depot ist der Markt nicht zwingend
# hinterlegt, also nutzen wir "USA" als sinnvollen Default (Voll-Reuse, schlank).
_SCAN_MARKET = "USA"


def _build_scan_orchestrator(llm, bus, memory, port) -> JudgmentOrchestrator:
    """Orchestrator für den proaktiven Scan — bewusst OHNE conflict_store.

    WICHTIG: Der Scan ist der EINZIGE Recorder (er ruft record_conflict mit
    source="proactive"). Trüge der Orchestrator den Store, nähme er den Konflikt
    schon im run() als source="on_demand" auf; der spätere proaktive record würde
    dann via Dedupe (ticker, direction) verworfen → "proactive" erreichte die DB nie.
    """
    return JudgmentOrchestrator(llm, bus, memory, portfolio_port=port, conflict_store=None)


def _make_conflict_scan(memory: SupabaseMemory):
    """Baut den proaktiven Depot-Konflikt-Scan als (name, coroutine-fn) für die Agentenliste.

    judge_fn(ticker, direction) lädt die gecachten cockpit/bottom_up-Ergebnisse und ruft
    JudgmentOrchestrator.run im Voll-Reuse auf. Fehlt der Bottom-Up-Cache → None (übersprungen).
    Der eigentliche Scan (scan_portfolio_conflicts) ist defensiv: Fehler je Position überspringt nur diese.
    """
    cache  = ResultCache()
    store  = SupabaseConflictStore()
    port   = JsonPortfolioProvider()
    bus    = InMemoryEventBus()
    llm    = ClaudeAdapter(ANTHROPIC_API_KEY)
    orch   = _build_scan_orchestrator(llm, bus, memory, port)

    async def _judge_async(ticker: str, direction: str):
        # Voll-Reuse: gecachte Top-Down- und Bottom-Up-Ergebnisse laden.
        cockpit   = cache.load_cockpit()
        bottom_up = cache.load_bottom_up(ticker)
        if bottom_up is None:
            return None                       # keine frische Bottom-Up-Analyse → überspringen
        # current_position aus der gehaltenen Richtung ableiten.
        current_position = PositionState.LONG if direction == "long" else PositionState.SHORT
        return await orch.run(
            cockpit=cockpit,
            bottom_up=bottom_up,
            market=_SCAN_MARKET,
            current_position=current_position,
        )

    async def run():
        # orch.run ist async, scan_portfolio_conflicts ruft judge_fn aber synchron.
        # Brücke: Analysen vorab (async) je Position berechnen, defensiv puffern,
        # dann der getesteten Scan-Logik einen reinen Lookup als judge_fn geben.
        positions = port.get_positions()
        results: dict[str, object] = {}
        for p in positions:
            try:
                results[p.ticker] = await _judge_async(p.ticker, p.direction)
            except Exception:
                results[p.ticker] = None      # Fehler je Position → als "keine Daten" behandeln
        scan_portfolio_conflicts(positions, lambda ticker, _direction: results.get(ticker), store)

    return ("ConflictScan", run)


async def main() -> None:
    # Fail-fast: echte Pflicht-Keys (FRED + ANTHROPIC) verlangen, bevor Adapter aufgebaut werden.
    require_keys()
    print("=" * 50)
    print("  AAIA Background Runner")
    print("=" * 50)

    memory = SupabaseMemory()
    bus    = InMemoryEventBus()

    # Konflikt-Store defensiv aufbauen: schlägt der Store-Aufbau fehl (z. B. kein Supabase),
    # läuft der Backtester ohne Konflikt-Backtester weiter → kein Crash des Runners.
    try:
        conflict_store = SupabaseConflictStore()
    except Exception:
        conflict_store = None
    backtester = BacktesterChiefAgent(memory, bus, conflict_store=conflict_store)

    market = YahooFinanceProvider()
    agents = [
        ("BacktesterChief", backtester.run),
        ("PortfolioMonitor", PortfolioMonitorAgent(
            memory,
            portfolio_port=JsonPortfolioProvider(),
            market_provider=market,
            live_price=YahooLivePriceProvider(),   # Live-Kurs + FX (vormals hardcoded yfinance)
            returns_provider=make_returns_provider(market),
        ).run),
    ]
    # Proaktiver Konflikt-Scan: je gehaltener Position eine judge-Analyse → Konflikte in die Inbox.
    # Defensiv schon beim Bau (LLM-/Store-/Provider-Aufbau): ein Aufbau-Fehler darf den
    # restlichen Runner nicht verhindern — dann läuft der Scan diesmal einfach nicht.
    try:
        agents.append(_make_conflict_scan(memory))
    except Exception as e:
        print(f"[ConflictScan] Aufbau übersprungen: {e}")

    for name, run_fn in agents:
        print(f"\n[{name}] wird ausgeführt...")
        try:
            await run_fn()
        except Exception as e:
            print(f"[{name}] FEHLER: {e}")

    print("\n  Background Runner abgeschlossen.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
