import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from adapters.event_bus.redis_bus import InMemoryEventBus
from adapters.memory.supabase_memory import SupabaseMemory
from agents.backtester_chief_agent import BacktesterChiefAgent
from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent


async def main() -> None:
    print("=" * 50)
    print("  AAIA Background Runner")
    print("=" * 50)

    memory = SupabaseMemory()
    bus    = InMemoryEventBus()

    backtester = BacktesterChiefAgent(memory, bus)

    agents = [
        ("BacktesterChief", backtester.run),
        ("PortfolioMonitor", PortfolioMonitorAgent(memory).run),
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
