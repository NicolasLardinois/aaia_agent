import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from adapters.event_bus.redis_bus import InMemoryEventBus
from adapters.memory.supabase_memory import SupabaseMemory
from adapters.data.yahoo_finance import YahooFinanceProvider
from adapters.persistence.json_portfolio import JsonPortfolioProvider
from agents.backtester_chief_agent import BacktesterChiefAgent
from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent, make_returns_provider


async def main() -> None:
    print("=" * 50)
    print("  AAIA Background Runner")
    print("=" * 50)

    memory = SupabaseMemory()
    bus    = InMemoryEventBus()

    backtester = BacktesterChiefAgent(memory, bus)

    market = YahooFinanceProvider()
    agents = [
        ("BacktesterChief", backtester.run),
        ("PortfolioMonitor", PortfolioMonitorAgent(
            memory,
            portfolio_port=JsonPortfolioProvider(),
            market_provider=market,
            returns_provider=make_returns_provider(market),
        ).run),
    ]

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
