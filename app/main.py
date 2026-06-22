"""
Verwendung:
  python -m app.main dashboard                              → Modus 1: Market Dashboard
  python -m app.main bottomup AAPL [asset_class] [sector]  → Modus 2: Bottom-Up Analyse
  python -m app.main judge AAPL [market]                   → Modus 3: Kombinations-Urteil
  python -m app.main conflicts                             → Modus 4: Offene Konflikte auflisten
  python -m app.main resolve <id> <held|closed>            → Modus 5: Konflikt-Entscheidung protokollieren (kein Trade)

asset_class:  equity | bond | commodity | precious_metal | etf  (default: equity)
market:       USA | CH | ISO-2 (DE/FR/IT/ES/NL/AT/BE/PT/FI/IE/GR/...)  (default: USA)
"""

import asyncio
import sys

from config.settings import FRED_API_KEY, ANTHROPIC_API_KEY, FINNHUB_API_KEY
from core.domain.models import PositionState, RiskAffinity
from core.domain.portfolio import PortfolioError
from adapters.persistence.json_portfolio import JsonPortfolioProvider
from adapters.data.fred_api import FredDataProvider
from adapters.data.yahoo_finance import YahooFinanceProvider
from adapters.data.finnhub import FinnhubProvider
from adapters.data.ecb_sdw import EcbSdwProvider
from adapters.data.fred_snb import FredSnbProvider
from adapters.event_bus.redis_bus import InMemoryEventBus
from adapters.llm.claude_adapter import ClaudeAdapter
from adapters.memory.supabase_memory import SupabaseMemory
from adapters.cache.result_cache import ResultCache
from adapters.persistence.supabase_conflict_store import SupabaseConflictStore
from orchestrators.top_down_orchestrator import TopDownOrchestrator
from orchestrators.bottom_up_orchestrator import BottomUpOrchestrator
from orchestrators.judgment_orchestrator import JudgmentOrchestrator


def _parse_risk_affinity(args: list[str], asset_class: str) -> "RiskAffinity | None":
    """Liest --risk-affinity aus der Argument-Liste.

    Für Anleihen (asset_class=='bond') ist der Parameter Pflicht;
    fehlt er oder ist er ungültig, wird mit Exit-Code 1 abgebrochen.
    Für alle anderen Asset-Klassen wird None zurückgegeben.
    """
    val = None
    if "--risk-affinity" in args:
        i = args.index("--risk-affinity")
        if i + 1 < len(args):
            val = args[i + 1]
    if asset_class != "bond":
        return None
    if val is None:
        print("Fehler: Anleihe-Analyse erfordert --risk-affinity {konservativ|neutral|risikofreudig}")
        sys.exit(1)
    try:
        return RiskAffinity(val)
    except ValueError:
        print(f"Fehler: ungültige --risk-affinity {val!r}. Erlaubt: konservativ|neutral|risikofreudig")
        sys.exit(1)


async def run_dashboard() -> None:
    print("\n=== MODUS 1: MARKET DASHBOARD ===\n")
    bus   = InMemoryEventBus()
    fred  = FredDataProvider(FRED_API_KEY)
    orch  = TopDownOrchestrator(
        macro=fred,
        ecb=EcbSdwProvider(),
        snb=FredSnbProvider(FRED_API_KEY),
        market=YahooFinanceProvider(),
        bus=bus,
    )
    result = await orch.run()
    ResultCache().save_cockpit(result)

    regime     = result.macro.regime
    confidence = result.macro.regime_confidence
    usa_yield  = result.yield_curve.yield_spreads.usa
    vix_val    = result.sentiment.vix.vix
    fg_label   = result.sentiment.fear_greed.label
    leading    = result.sectors.performance.leading_usa
    lagging    = result.sectors.performance.lagging_usa

    print(f"Regime:           {regime.value}  ({confidence:.0%} Konfidenz)")
    spread_str = f"{usa_yield.spread_10y2y:+.2f}" if usa_yield.spread_10y2y is not None else "n/v"
    print(f"Zinskurve (USA):  {spread_str}  {'⚠ INVERTIERT' if usa_yield.inverted else 'normal'}")
    print(f"VIX:              {vix_val:.1f}  Fear & Greed: {fg_label}" if vix_val else "VIX:              n/v")
    print(f"Führender Sektor: {leading or 'n/v'}")
    print(f"Schwächster:      {lagging or 'n/v'}")

    energy = result.commodities.energy
    metals = result.commodities.precious_metals
    print(f"WTI:              {energy.wti_usd or 'n/v'}  "
          f"Brent: {energy.brent_usd or 'n/v'}  "
          f"Gold: {metals.gold_usd or 'n/v'}")


async def run_bottom_up(
    ticker: str,
    asset_class: str = "equity",
    sector: str = "default",
    bond_type: str = "government",
    rate_direction: str = "stable",
    risk_affinity: "RiskAffinity | None" = None,
) -> None:
    print(f"\n=== MODUS 2: BOTTOM-UP ANALYSE — {ticker.upper()} ===\n")
    bus  = InMemoryEventBus()
    llm  = ClaudeAdapter(ANTHROPIC_API_KEY)
    orch = BottomUpOrchestrator(
        fundamentals_provider=FinnhubProvider(FINNHUB_API_KEY),
        macro_provider=FredDataProvider(FRED_API_KEY),
        market_provider=YahooFinanceProvider(),
        llm=llm,
        bus=bus,
    )
    result = await orch.run(
        ticker.upper(), asset_class=asset_class, sector=sector,
        bond_type=bond_type, rate_direction=rate_direction,
        risk_affinity=risk_affinity,
    )
    ResultCache().save_bottom_up(result)

    fu  = result.fundamentals
    qu  = result.quality
    si  = result.short_interest
    ins = result.insider
    et  = result.earnings_trend
    mo  = result.moat
    vr  = result.valuation_range
    bo  = result.bond

    if fu:
        print(f"Fundamentals:   KGV={fu.pe_ratio}  Marge={fu.operating_margin}%  → {fu.signal.value}")
    if qu:
        print(f"Qualität:       ROE={qu.roe}%  ROIC={qu.roic}%  Altman-Z={qu.altman_z}  → {qu.signal.value}")
    if si:
        print(f"Short Interest: {si.short_float_pct}%  DTC={si.days_to_cover}  → {si.signal.value}")
    if ins:
        print(f"Insider:        {ins.net_direction}  ({ins.recent_transactions} Transaktionen)  → {ins.signal.value}")
    if et:
        print(f"Earnings:       Beat={et.beat_rate}  Revision={et.estimate_revision}  → {et.signal.value}")
    if mo:
        print(f"Burggraben:     {mo.overall}  (Score {mo.total_score}/10)  → {mo.signal.value}")
    if vr:
        print(f"Bewertung:      {vr.position}  [{vr.combined_low:.0f}–{vr.combined_high:.0f}]  → {vr.signal.value}")
    if bo:
        print(f"Bond Metrics:   YTM={bo.metrics.ytm}  Duration={bo.duration.modified_duration}  → {bo.metrics.signal.value}")
        print(f"Bond Rating:    {bo.credit.moodys}/{bo.credit.sp}/{bo.credit.fitch}  Trend={bo.credit.trend}  → {bo.credit.signal.value}")


def run_conflicts(store) -> None:
    """Listet alle offenen Konflikte aus dem Store.

    Kein Trade wird ausgeführt — reine Anzeige-Funktion.
    """
    items = store.load_open()
    if not items:
        print("Keine offenen Konflikte.")
        return
    print(f"\nOFFENE KONFLIKTE ({len(items)}):")
    for c in items:
        print(f"  #{c.id}  {c.ticker} ({c.direction})  {c.verdict} — {c.reason}")
    print("\n→ entscheiden mit:  python -m app.main resolve <id> <held|closed>")


def run_resolve(store, conflict_id: str, decision: str) -> None:
    """Protokolliert die Nutzer-Entscheidung zu einem Konflikt.

    Erlaubte Entscheidungen: 'held' (Position gehalten) oder 'closed' (Position geschlossen).
    Bei ungültiger Entscheidung wird nichts geschrieben — kein Trade ausgeführt.
    """
    if decision not in ("held", "closed"):
        print("Nutzung: resolve <id> <held|closed>")
        return
    store.resolve(int(conflict_id), decision)
    print(f"✓ Konflikt #{conflict_id} als '{decision}' protokolliert (kein Trade ausgeführt).")


async def run_judgment(ticker: str, market: str = "USA") -> None:
    try:
        current_position = JsonPortfolioProvider().position_state_for(ticker)
    except PortfolioError as e:
        print(f"⚠ Portfolio-Daten ungültig ({e}) — current_position=NONE.")
        current_position = PositionState.NONE
    print(f"\n=== MODUS 3: KOMBINATIONS-URTEIL — {ticker.upper()} ===\n")
    cache     = ResultCache()
    cockpit   = cache.load_cockpit()
    bottom_up = cache.load_bottom_up(ticker.upper())

    if cockpit is None:
        print("Kein Dashboard-Cache → führe zuerst 'dashboard' aus.")
        sys.exit(1)
    if bottom_up is None:
        print(f"Kein Bottom-Up-Cache für {ticker.upper()} → führe zuerst 'bottomup {ticker}' aus.")
        sys.exit(1)

    bus    = InMemoryEventBus()
    llm    = ClaudeAdapter(ANTHROPIC_API_KEY)
    memory = SupabaseMemory()
    # Konflikt-Store: persistiert erkannte Konflikte on-demand in der DB
    orch   = JudgmentOrchestrator(llm, bus, memory, portfolio_port=JsonPortfolioProvider(),
                                  conflict_store=SupabaseConflictStore())
    result = await orch.run(
        cockpit=cockpit,
        bottom_up=bottom_up,
        market=market,
        current_position=current_position,
    )

    print(f"TOP-DOWN:\n{result.top_down_context}\n")
    print(f"ALIGNMENT:      {result.alignment}")
    print(f"EMPFEHLUNG:     {result.recommendation.action.value}  "
          f"(Konfidenz {result.recommendation.confidence:.0%})")
    if result.recommendation.short_warning:
        print(f"\n{result.recommendation.short_warning}")
    print(f"SHORT-AKTION:   {result.short_action.value}")
    if result.short_assessment:
        sa = result.short_assessment
        print(f"  Short-Konfidenz: {sa.confidence:.0%}"
              + (f" | Typ: {', '.join(sa.archetypes)}" if sa.archetypes else ""))
    if result.conflict:
        print(f"⚠️  KONFLIKT: {result.conflict_reason}")
    if result.conflict_resolution:
        cr = result.conflict_resolution
        print(f"🔀 KONFLIKT-URTEIL: {cr.verdict}\n{cr.reasoning}")
    print(f"\nURTEIL:\n{result.judgment}")
    if result.short_thesis:
        print(f"\nSHORT-THESE:\n{result.short_thesis}")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] == "dashboard":
        asyncio.run(run_dashboard())
    elif args[0] == "bottomup" and len(args) >= 2:
        # --risk-affinity <wert> herausziehen, damit es das Positions-Parsing nicht stört
        pos = list(args)
        if "--risk-affinity" in pos:
            i = pos.index("--risk-affinity")
            del pos[i:i + 2]
        asset_class    = pos[2] if len(pos) >= 3 else "equity"
        sector         = pos[3] if len(pos) >= 4 else "default"
        bond_type      = pos[4] if len(pos) >= 5 else "government"
        rate_direction = pos[5] if len(pos) >= 6 else "stable"
        risk_affinity  = _parse_risk_affinity(args, asset_class)
        asyncio.run(run_bottom_up(pos[1], asset_class=asset_class, sector=sector,
                                  bond_type=bond_type, rate_direction=rate_direction,
                                  risk_affinity=risk_affinity))
    elif args[0] == "judge" and len(args) >= 2:
        market = args[2] if len(args) >= 3 else "USA"
        asyncio.run(run_judgment(args[1], market=market))
    elif args[0] == "conflicts":
        run_conflicts(SupabaseConflictStore())
    elif args[0] == "resolve" and len(args) >= 3:
        run_resolve(SupabaseConflictStore(), args[1], args[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
