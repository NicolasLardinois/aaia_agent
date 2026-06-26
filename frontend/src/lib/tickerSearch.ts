// Fuzzy-Ticker-Suche: bildet eine freie Eingabe ("appl", "apple", "öl", "s&p")
// auf das passende Instrument aus dem TICKER_UNIVERSE ab. Reine Funktionen, kein I/O —
// damit leicht testbar (Bug #10: bisher fiel jede nicht-exakte Eingabe auf "nicht gefunden").
//
// Strategie (vom besten zum schwaechsten Signal):
//   exakt > Prefix > Teilstring > Subsequenz > Levenshtein (Tippfehler-Toleranz).
// Gematcht wird gegen Symbol, Name UND alle Aliasse; das Feld mit dem besten Score gewinnt.
// Ein kleiner Feld-Bonus (Symbol > Name > Alias) bricht Gleichstaende deterministisch.

import { TICKER_UNIVERSE, type TickerEntry } from "../data/tickerUniverse";

export interface TickerHit {
  entry: TickerEntry;
  score: number;
}

/** Normalisiert fuer den Vergleich: Kleinschreibung, Umlaute → ae/oe/ue/ss, nur a–z0–9. */
function norm(s: string): string {
  return s
    .toLowerCase()
    .replace(/ä/g, "ae")
    .replace(/ö/g, "oe")
    .replace(/ü/g, "ue")
    .replace(/ß/g, "ss")
    .replace(/[^a-z0-9]/g, "");
}

/** Klassische Levenshtein-Distanz (Anzahl Einfuegen/Loeschen/Ersetzen). */
function levenshtein(a: string, b: string): number {
  if (a === b) return 0;
  if (a.length === 0) return b.length;
  if (b.length === 0) return a.length;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  let curr = new Array<number>(b.length + 1);
  for (let i = 1; i <= a.length; i++) {
    curr[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      curr[j] = Math.min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost);
    }
    [prev, curr] = [curr, prev];
  }
  return prev[b.length];
}

/** Ist q eine (nicht zwingend zusammenhaengende) Teilfolge von t? z. B. "msft" in "microsoft". */
function isSubsequence(q: string, t: string): boolean {
  let i = 0;
  for (let j = 0; j < t.length && i < q.length; j++) {
    if (q[i] === t[j]) i++;
  }
  return i === q.length;
}

/** Score eines einzelnen Feldes (Symbol/Name/Alias) gegen die normalisierte Anfrage. 0 = kein Treffer. */
function fieldScore(q: string, target: string): number {
  const t = norm(target);
  if (!t || !q) return 0;
  if (t === q) return 100;
  if (t.startsWith(q)) return 85;
  if (t.includes(q)) return 65;
  if (q.length >= 3 && isSubsequence(q, t)) return 45;
  if (q.length >= 3) {
    const d = levenshtein(q, t);
    // Toleranz waechst mit der Laenge: ~1/4 der laengeren Zeichenkette, mind. 1 Fehler.
    const tolerance = Math.max(1, Math.floor(Math.max(q.length, t.length) * 0.25));
    if (d <= tolerance) return Math.max(20, 40 - d * 8);
  }
  return 0;
}

function entryScore(q: string, entry: TickerEntry): number {
  // Feld-Bonus bricht Gleichstaende: exaktes Symbol (100+3) schlaegt exakten Namen (100+2).
  const symbol = fieldScore(q, entry.ticker);
  const name = fieldScore(q, entry.name);
  let best = Math.max(symbol > 0 ? symbol + 3 : 0, name > 0 ? name + 2 : 0);
  for (const alias of entry.aliases) {
    const a = fieldScore(q, alias);
    if (a > 0) best = Math.max(best, a + 1);
  }
  return best;
}

/** Liefert die besten Treffer (Score absteigend), begrenzt auf `limit`. Leere Eingabe → []. */
export function searchTickers(query: string, limit = 8, universe: TickerEntry[] = TICKER_UNIVERSE): TickerHit[] {
  const q = norm(query);
  if (!q) return [];
  return universe
    .map((entry) => ({ entry, score: entryScore(q, entry) }))
    .filter((hit) => hit.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

/** Bestes einzelnes Symbol fuer eine Eingabe — oder null, wenn nichts hinreichend passt. */
export function resolveTicker(query: string, universe: TickerEntry[] = TICKER_UNIVERSE): string | null {
  const hits = searchTickers(query, 1, universe);
  return hits.length > 0 ? hits[0].entry.ticker : null;
}
