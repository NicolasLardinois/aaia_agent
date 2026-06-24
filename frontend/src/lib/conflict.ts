import type { Direction, PositionJudgmentDTO } from "../contract/portfolio";

// Konflikt = AAIA-Urteil laeuft GEGEN die gehaltene Positionsrichtung (Konzept §2.5).
// long-Position: Long-Linse SELL ODER Short-Linse SHORT (beides gegen den Bestand).
// short-Position: Short-Linse COVER ODER Long-Linse BUY (beides gegen die Short-These).
// HOLD/NONE sind KEIN Konflikt (kein gegenlaeufiges Handlungssignal).
// EXPORTIERT, damit Slice 4 (Inbox) dieselbe Logik nutzt (eine Quelle der Wahrheit).
export function detectConflict(direction: Direction, judgment: PositionJudgmentDTO): boolean {
  if (direction === "long") {
    return judgment.longVerdict === "SELL" || judgment.shortVerdict === "SHORT";
  }
  return judgment.shortVerdict === "COVER" || judgment.longVerdict === "BUY";
}

// Kurzbegruendung fuer die UI/Inbox; null wenn kein Konflikt.
export function conflictNote(direction: Direction, judgment: PositionJudgmentDTO): string | null {
  if (!detectConflict(direction, judgment)) return null;
  if (direction === "long") {
    const v = judgment.longVerdict === "SELL" ? judgment.longVerdict : judgment.shortVerdict;
    return `Long gehalten, Urteil ${v} läuft gegen die Position.`;
  }
  const v = judgment.shortVerdict === "COVER" ? judgment.shortVerdict : judgment.longVerdict;
  return `Short gehalten, Urteil ${v} läuft gegen die Position.`;
}
