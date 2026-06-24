// Inbox-Vertrag (Spec §2): beschreibt die KUENFTIGE API-Form. Demo + Echt liefern denselben
// Vertrag, InboxView extends DemoMeta. Die Inbox ist BERATEND — Aktionen fuehren KEINE Trades
// aus, sie markieren erledigt + protokollieren die Entscheidung (US30, Konzept §2.5).
import type { DemoMeta, Underlying, Wrapper, LongVerdict, ShortVerdict } from "./common";
import type { Direction } from "./portfolio";

// Beratendes Verdikt pro Konflikt (US29): aussteigen / halten / Richtung drehen.
export type ConflictVerdict = "EXIT" | "HOLD" | "REVERSE";

// Abarbeitungs-Status (US30): offen -> erledigt. "erledigt" traegt immer eine Entscheidung.
export type ConflictStatus = "offen" | "erledigt";

// Protokollierte Entscheidung beim Erledigen (US30): dem Verdikt gefolgt / ignoriert / vertagt.
export type ConflictDecision = "gefolgt" | "ignoriert" | "vertagt";

export interface ConflictDTO {
  id: string;                   // stabile ID (Ticker+Richtung reicht in der Demo)
  ticker: string;
  name: string;
  underlying: Underlying;
  wrapper: Wrapper;
  direction: Direction;         // gehaltene Positionsrichtung (long/short)
  heldVerdict: LongVerdict | ShortVerdict;  // Urteil, das die These STUETZTE, als die Position eroeffnet wurde
  newLongVerdict: LongVerdict;  // aktuelles AAIA-Long-Urteil
  newShortVerdict: ShortVerdict;// aktuelles AAIA-Short-Urteil
  confidence: number;           // 0..1 — Konfidenz des kippenden Urteils
  conflictNote: string;         // Kurzbegruendung, WARUM dies ein Konflikt ist (aus lib/conflict)
  suggestedVerdict: ConflictVerdict; // beratender Default-Vorschlag (US29), hervorgehoben
  suggestedRationale: string;   // fachliche Begruendung des Vorschlags
  status: ConflictStatus;       // initial immer "offen"
}

export interface InboxView extends DemoMeta {
  conflicts: ConflictDTO[];
}
