// Such-Universum: die Instrumente, die die App per Suche kennt und oeffnen kann.
// Reine Daten (kein I/O). Jede Zeile hat ein kanonisches Symbol (fuer die Navigation),
// einen Namen und Aliasse (umgangssprachliche Begriffe, deutsche/englische Synonyme),
// damit die Fuzzy-Suche auch "apple", "oel" oder "s&p" auf den richtigen Ticker fuehrt.
// WICHTIG: Jeder Eintrag ist als Demo-Deep-Dive ladbar (siehe data/demo/deepdive.ts) —
// die Suche schlaegt also nie etwas vor, das anschliessend "nicht gefunden" zeigt.

export type AssetKind = "Aktie" | "Index" | "Anleihe" | "Rohstoff" | "Edelmetall";

export interface TickerEntry {
  /** Kanonisches Symbol — exakt so, wie es der Deep-Dive-Loader erwartet (z. B. "GC=F"). */
  ticker: string;
  /** Anzeigename. */
  name: string;
  /** Anlageklasse (fuer das Etikett im Vorschlags-Dropdown). */
  kind: AssetKind;
  /** Zusaetzliche Suchbegriffe (Synonyme, Marken, deutsche Begriffe). */
  aliases: string[];
}

export const TICKER_UNIVERSE: TickerEntry[] = [
  // Aktien
  { ticker: "AAPL", name: "Apple Inc.", kind: "Aktie", aliases: ["apple", "iphone", "mac"] },
  { ticker: "MSFT", name: "Microsoft Corp.", kind: "Aktie", aliases: ["microsoft", "windows", "azure"] },
  { ticker: "NVDA", name: "NVIDIA Corp.", kind: "Aktie", aliases: ["nvidia", "gpu", "grafikkarte"] },
  { ticker: "GOOGL", name: "Alphabet Inc. (Google)", kind: "Aktie", aliases: ["google", "alphabet"] },
  { ticker: "AMZN", name: "Amazon.com Inc.", kind: "Aktie", aliases: ["amazon"] },
  { ticker: "TSLA", name: "Tesla Inc.", kind: "Aktie", aliases: ["tesla", "elon"] },
  { ticker: "META", name: "Meta Platforms Inc.", kind: "Aktie", aliases: ["meta", "facebook", "instagram"] },
  // Index
  { ticker: "SPY", name: "S&P 500 ETF", kind: "Index", aliases: ["s&p", "sp500", "s&p 500", "us-aktien", "standard and poors"] },
  // Anleihe
  { ticker: "TLT", name: "20+ Jahre US-Staatsanleihen", kind: "Anleihe", aliases: ["treasury", "staatsanleihe", "anleihe", "us-anleihen", "bonds"] },
  // Edelmetall / Rohstoff
  { ticker: "GC=F", name: "Gold (Future)", kind: "Edelmetall", aliases: ["gold", "goldfuture", "goldpreis"] },
  { ticker: "4GLD", name: "Xetra-Gold (physisch)", kind: "Edelmetall", aliases: ["gold physisch", "xetra-gold", "xetra gold"] },
  { ticker: "CL=F", name: "Rohöl WTI (Future)", kind: "Rohstoff", aliases: ["öl", "oel", "oil", "rohöl", "wti", "crude"] },
];
