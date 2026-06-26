// Kursverlauf-Mathematik (Mangel #6: Kurschart im Deep-Dive). Rein, keine I/O.
export interface PricePoint { date: string; close: number; }

export interface PriceChange {
  absolute: number;                    // letzter - erster Schlusskurs (in Kurswaehrung)
  pct: number;                         // relative Veraenderung in % ueber die Periode
  direction: "up" | "down" | "flat";   // Vorzeichen -> Farbwahl (gruen/rot/grau)
}

// Periodenveraenderung = erster vs. letzter Schlusskurs. Leere/einzelne Reihe -> neutraler
// Nullwert (kein Crash, keine Division durch 0 — Datenrealitaet: Reihe kann fehlen).
export function periodChange(points: PricePoint[]): PriceChange {
  if (points.length < 2) return { absolute: 0, pct: 0, direction: "flat" };
  const first = points[0].close;
  const last = points[points.length - 1].close;
  const absolute = Number((last - first).toFixed(2));
  const pct = first === 0 ? 0 : Number(((absolute / first) * 100).toFixed(1));
  const direction = absolute > 0 ? "up" : absolute < 0 ? "down" : "flat";
  return { absolute, pct, direction };
}
