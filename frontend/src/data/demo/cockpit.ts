// Fachlich plausible Beispielwerte (Spec §1: Demo-Daten, nicht exakt). isDemo:true -> DemoBadge.
import type {
  MacroView, CommoditiesView, SentimentView, YieldCurveView,
  SectorsView, BuffettView, BigMacView,
} from "../../contract/cockpit";

export function demoMacro(): MacroView {
  return {
    isDemo: true,
    sourcesActive: 3, sourcesTotal: 3, failed: [],
    inflation: [
      // USA 3.2 % -> "erhoht" (3–4 %) -> BEARISH; Eurozone (EUR) 2.4 % -> Zielzone -> BULLISH;
      // CH 1.1 % -> ueber CH-Ziel-Untergrenze, in CH-Zielzone (0.5–2) -> BULLISH.
      // EUR = Euroraum-Aggregat (ECB-HICP), NICHT Deutschland.
      { region: "USA", cpiPct: 3.2, signal: "bearish", dataDate: "2026-05" },
      { region: "EUR", cpiPct: 2.4, signal: "bullish", dataDate: "2026-05" },
      { region: "CH",  cpiPct: 1.1, signal: "bullish", dataDate: "2026-05" },
    ],
  };
}

export function demoCommodities(): CommoditiesView {
  return {
    isDemo: true,
    sourcesActive: 2, sourcesTotal: 2, failed: [],
    commodities: [
      { name: "Rohoel (WTI)", ticker: "CL=F", signal: "bullish", note: "Angebotsdisziplin OPEC+, Nachfrage robust" },
      { name: "Kupfer",       ticker: "HG=F", signal: "bearish", note: "Konjunktursorgen China daempfen" },
      { name: "Erdgas",       ticker: "NG=F", signal: "neutral", note: "saisonal ausgeglichen" },
    ],
  };
}

export function demoSentiment(): SentimentView {
  return {
    isDemo: true,
    sourcesActive: 2, sourcesTotal: 2, failed: [],
    subSignals: [
      // VIX ~18 = moderat; Fear&Greed 62 = leichte Gier -> mild bearish (ueberhitzt).
      { name: "VIX", value: 18.2, signal: "neutral", note: "moderate Volatilitaet" },
      { name: "Fear & Greed", value: 62, signal: "bearish", note: "leichte Gier (ueberhitzt)" },
    ],
  };
}

export function demoYieldCurve(): YieldCurveView {
  return {
    isDemo: true,
    sourcesActive: 1, sourcesTotal: 1, failed: [],
    // Aufwaerts geneigte Kurve (nicht invertiert) -> kein Rezessions-Fruehsignal -> BULLISH.
    points: [
      { tenor: "3M",  yieldPct: 3.9 },
      { tenor: "2J",  yieldPct: 4.1 },
      { tenor: "10J", yieldPct: 4.5 },
      { tenor: "30J", yieldPct: 4.7 },
    ],
    // value = vorderes minus hinteres Tenor (in %-Punkten); positiv = nicht invertiert.
    spreads: [
      { pair: "10J-2J",  value: +0.4 },
      { pair: "10J-3M",  value: +0.6 },
      { pair: "30J-10J", value: +0.2 },
    ],
  };
}

export function demoSectors(): SectorsView {
  return {
    isDemo: true,
    // Bewusst eine Quelle ausgefallen -> UNAVAILABLE-Pfad demonstrieren (Spec §1/§5.4).
    sourcesActive: 2, sourcesTotal: 3,
    failed: [{ key: "Sektor-Momentum (Stub)", reason: "Datenquelle noch nicht angebunden" }],
    regime: "AUFSCHWUNG",
    sectors: [
      // Fruehzyklisch beguenstigt: zyklischer Konsum, Industrie, Technologie.
      { sector: "Technologie",        rotation: "favored", signal: "bullish" },
      { sector: "Zyklischer Konsum",  rotation: "favored", signal: "bullish" },
      { sector: "Industrie",          rotation: "favored", signal: "bullish" },
      { sector: "Versorger",          rotation: "avoid",   signal: "bearish" },
      { sector: "Basiskonsum",        rotation: "neutral", signal: "neutral" },
      // Ausgefallene Sub-Quelle -> signal null -> UNAVAILABLE (nicht 0, nicht neutral).
      { sector: "Energie",            rotation: "neutral", signal: null },
    ],
  };
}

export function demoBuffett(): BuffettView {
  // Plausible Groessenordnungen; history je Land fuer den 10-J-Drilldown.
  const usaHist = [150, 160, 175, 200, 210, 185, 195, 188, 192, 198].map((r, i) => ({ year: 2017 + i, ratioPct: r }));
  const cheHist = [180, 190, 205, 230, 240, 215, 222, 210, 218, 211].map((r, i) => ({ year: 2017 + i, ratioPct: r }));
  const deuHist = [48, 50, 55, 62, 64, 54, 58, 53, 56, 55].map((r, i) => ({ year: 2017 + i, ratioPct: r }));
  return {
    isDemo: true,
    sourcesActive: 2, sourcesTotal: 2, failed: [],
    globalMedian: 92,       // globaler Median ueber alle Laender (Referenz)
    analyzedIso3: "USA",    // hervorgehobenes Land
    countries: [
      // ratio>135 -> BEARISH (absoluter Fallback); USA z=+2.1 (>2 = Anomalie/auffaellig).
      { iso3: "USA", name: "USA",         ratioPct: 198, signal: "bearish", zScore: +2.1, year: null,   history: usaHist },
      { iso3: "CHE", name: "Schweiz",     ratioPct: 211, signal: "bearish", zScore: +0.6, year: 2024,   history: cheHist },
      { iso3: "DEU", name: "Deutschland", ratioPct: 55,  signal: "bullish", zScore: -0.9, year: 2024,   history: deuHist },
      { iso3: "JPN", name: "Japan",       ratioPct: 145, signal: "bearish", zScore: +1.6, year: 2024,   history: [] },
      { iso3: "GBR", name: "UK",          ratioPct: 100, signal: "neutral", zScore: -0.2, year: 2024,   history: [] },
    ],
  };
}

export function demoBigMac(): BigMacView {
  return {
    isDemo: true,
    sourcesActive: 1, sourcesTotal: 1, failed: [],
    publishedAt: "2026-01", // halbjaehrlich (Jan/Jul) — sichtbar im Widget
    analyzedIso2: "US",
    rows: [
      // + = ueberbewertet vs. USD, - = unterbewertet. CHF traditionell stark ueberbewertet.
      { iso2: "CH", name: "Schweiz",  valuationPct: +38.0 },
      { iso2: "NO", name: "Norwegen", valuationPct: +21.0 },
      { iso2: "US", name: "USA",      valuationPct: 0.0 },
      { iso2: "JP", name: "Japan",    valuationPct: -41.0 },
      { iso2: "IN", name: "Indien",   valuationPct: -52.0 },
    ],
  };
}
