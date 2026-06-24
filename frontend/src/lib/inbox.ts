// frontend/src/lib/inbox.ts
import type { ConflictVerdict, ConflictDTO } from "../contract/inbox";
import type { Direction } from "../contract/portfolio";
import type { LongVerdict, ShortVerdict } from "../contract/common";

export interface VerdictSuggestion {
  verdict: ConflictVerdict;     // EXIT / HOLD / REVERSE (Default-Vorschlag, US29)
  rationale: string;            // fachliche Begruendung (Deutsch, ohne magische Zahl)
}

// Beratender Default-Vorschlag (US29). REVERSE nur, wenn das System ein AKTIVES Gegen-Setup
// sieht (long: neues SHORT; short: neues BUY) — sonst EXIT (raus) bzw. HOLD (kein Druck).
// Reihenfolge: REVERSE hat Vorrang vor EXIT — ein aktives Gegen-Setup ist staerker als ein
// bloss nicht-mehr-tragendes Signal. SHORT/BUY pruefe ich zuerst, bevor ich auf SELL/COVER falle.
export function suggestVerdict(
  direction: Direction,
  _heldVerdict: LongVerdict | ShortVerdict,
  newLong: LongVerdict,
  newShort: ShortVerdict,
): VerdictSuggestion {
  if (direction === "long") {
    // SHORT-Setup = aktiver Gegenhandlungsdruck: Richtung drehen ist staerker als bloss raus
    if (newShort === "SHORT") {
      return { verdict: "REVERSE", rationale: "Aktives Short-Setup gegen die Long-Position — Richtung drehen erwägen." };
    }
    // SELL = Long-These traegt nicht mehr, aber kein bestaetigtes Short-Setup vorhanden
    if (newLong === "SELL") {
      return { verdict: "EXIT", rationale: "Long-These trägt nicht mehr (SELL), aber kein bestätigtes Short — Ausstieg erwägen." };
    }
    // Kein echtes Gegensignal: vorerst halten
    return { verdict: "HOLD", rationale: "Kein tragfähiges Gegensignal — vorerst halten." };
  }
  // Short-Position (spiegelbildlich zur Long-Logik oben):
  // BUY-Setup = aktiver Gegenhandlungsdruck: Richtung drehen ist staerker als bloss eindecken
  if (newLong === "BUY") {
    return { verdict: "REVERSE", rationale: "Aktives Long-Setup gegen die Short-Position — Richtung drehen erwägen." };
  }
  // COVER = Short-These traegt nicht mehr, aber kein bestaetigtes Long-Setup vorhanden
  if (newShort === "COVER") {
    return { verdict: "EXIT", rationale: "Short-These trägt nicht mehr (COVER), aber kein bestätigtes Long — Eindecken erwägen." };
  }
  // Kein echtes Gegensignal: vorerst halten
  return { verdict: "HOLD", rationale: "Kein tragfaehiges Gegensignal — vorerst halten." };
}

// Anzahl OFFENER Konflikte fuer den Topbar-Badge (US28). Erledigte zaehlen NICHT mit.
// "Keine Konflikte" ist legitim 0 — kein UNAVAILABLE (Global Constraints).
export function openCount(conflicts: Pick<ConflictDTO, "status">[]): number {
  return conflicts.filter((c) => c.status === "offen").length;
}
