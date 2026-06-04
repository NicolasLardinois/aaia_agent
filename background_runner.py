import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from adapters.memory.supabase_memory import SupabaseMemory
from agents.backtester.bottom_up_backtester_agent import BottomUpBacktesterAgent
from agents.backtester.judgment_backtester_agent import JudgmentBacktesterAgent
from agents.backtester.top_down_backtester_agent import TopDownBacktesterAgent
from agents.portfolio.portfolio_monitor_agent import PortfolioMonitorAgent


async def main() -> None:
    print("=" * 50)
    print("  AAIA Background Runner")
    print("=" * 50)

    memory = SupabaseMemory()

    agents = [
        ("TopDownBacktester",  TopDownBacktesterAgent(memory).run),
        ("BottomUpBacktester", BottomUpBacktesterAgent(memory).run),
        ("JudgmentBacktester", JudgmentBacktesterAgent(memory).run),
        ("PortfolioMonitor",   PortfolioMonitorAgent(memory).run),
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
