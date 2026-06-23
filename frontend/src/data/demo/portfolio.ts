// Fachlich plausible Beispielwerte (Spec §1: Demo, nicht exakt). isDemo:true -> DemoBadge.
// Positionen long+short quer ueber underlying x wrapper inkl. Konflikt-Fall (XLE long + SELL).
// Exposure/net_beta/Klumpen/Hedges werden AUS den Positionen berechnet -> Tabelle & Panel
// sind garantiert konsistent (keine handgesetzten Aggregate, die auseinanderdriften).
import type { PortfolioView, PositionDTO, ConcentrationLimits } from "../../contract/portfolio";
import { grossExposure, netExposure, netBeta } from "../../lib/exposure";
import { detectKlumpen } from "../../lib/klumpen";
import { hedgeSuggestions } from "../../lib/hedge";

// Limits fuer die Demo: Sektor bewusst auf 0.25, damit die Tech-Konzentration (27 %) als
// Klumpen erscheint (vgl. Wireframe §4.8 "Tech … Limit 30 %"). underlying/geography = Default.
const DEMO_LIMITS: ConcentrationLimits = { sector: 0.25, underlying: 0.60, geography: 0.70 };

const POSITIONS: PositionDTO[] = [
  {
    ticker: "AAPL", name: "Apple Inc.", underlying: "equity", wrapper: "single",
    direction: "long", sizePctNav: 12, entryPrice: 185.2, currency: "USD",
    sector: "Technologie", geography: "USA", beta: 1.25,
    judgment: { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.52 },
  },
  {
    ticker: "MSFT", name: "Microsoft Corp.", underlying: "equity", wrapper: "single",
    direction: "long", sizePctNav: 15, entryPrice: 410.0, currency: "USD",
    sector: "Technologie", geography: "USA", beta: 1.10,
    judgment: { longVerdict: "BUY", shortVerdict: "NONE", confidence: 0.55 },
  },
  {
    ticker: "GC=F", name: "Gold", underlying: "precious_metal", wrapper: "future",
    direction: "long", sizePctNav: 6, entryPrice: 2310, currency: "USD",
    sector: "Edelmetall", geography: "Global", beta: null, // kein Aktienmarkt-Beta -> nicht im net_beta
    judgment: { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.47 },
  },
  {
    ticker: "TLT", name: "20+ Jahre US-Staatsanleihen", underlying: "bond", wrapper: "fund",
    direction: "long", sizePctNav: 10, entryPrice: 88.4, currency: "USD",
    sector: "Anleihen", geography: "USA", beta: null, // Bond -> nicht im net_beta
    judgment: { longVerdict: "BUY", shortVerdict: "NONE", confidence: 0.60 },
  },
  {
    ticker: "TSLA", name: "Tesla Inc.", underlying: "equity", wrapper: "single",
    direction: "short", sizePctNav: 5, entryPrice: 240.0, currency: "USD",
    sector: "Zyklischer Konsum", geography: "USA", beta: 1.80,
    // Urteil STUETZT den Short (Short-Verdikt SHORT) -> KEIN Konflikt
    judgment: { longVerdict: "NONE", shortVerdict: "SHORT", confidence: 0.61 },
  },
  {
    ticker: "XLE", name: "Energy Select Sector SPDR", underlying: "equity_index", wrapper: "fund",
    direction: "long", sizePctNav: 9, entryPrice: 88.4, currency: "USD",
    sector: "Energie", geography: "USA", beta: 1.05,
    // KONFLIKT: long gehalten, Long-Verdikt SELL laeuft gegen die Position (speist Inbox/Slice 4)
    judgment: { longVerdict: "SELL", shortVerdict: "NONE", confidence: 0.58 },
  },
];

export function demoPortfolio(): PortfolioView {
  const exposure = {
    grossPct: Number(grossExposure(POSITIONS).toFixed(2)),
    netPct: Number(netExposure(POSITIONS).toFixed(2)),
    netBeta: Number(netBeta(POSITIONS).toFixed(2)),
    annualizedVolPct: 13.8,            // datierte Portfolio-Vola (Demo, PR #11)
    volAsOf: "2026-06-20",
  };
  const klumpen = detectKlumpen(POSITIONS, DEMO_LIMITS);
  const hedges = hedgeSuggestions(exposure, klumpen);
  return {
    isDemo: true,
    sourcesActive: 3, sourcesTotal: 4,
    // bewusst eine ausgefallene Quelle -> UNAVAILABLE-Pfad sichtbar (Spec §1/§5.4)
    failed: [{ key: "Beta-Feed (Stub)", reason: "Marktbeta-Quelle teilweise noch nicht angebunden" }],
    navCurrency: "USD",
    positions: POSITIONS,
    exposure,
    klumpen,
    hedges,
    limits: DEMO_LIMITS,
  };
}
