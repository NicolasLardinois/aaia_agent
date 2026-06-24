import type { Direction, PositionJudgmentDTO } from "../contract/portfolio";
import type { LongVerdict, ShortVerdict } from "../contract/common";

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

// Das Urteil, das den Konflikt AUSLOEST (eine Quelle der Wahrheit fuer Note + Kartenkopf).
// null, wenn kein Konflikt. long: SELL (Long-Linse) sonst die gegenlaeufige Short-Linse (SHORT);
// short: COVER (Short-Linse) sonst die gegenlaeufige Long-Linse (BUY). So zeigt die UI immer das
// tatsaechlich gegenlaeufige Signal — nicht ein begleitendes HOLD/NONE.
export function conflictTrigger(
  direction: Direction,
  judgment: PositionJudgmentDTO,
): LongVerdict | ShortVerdict | null {
  if (!detectConflict(direction, judgment)) return null;
  if (direction === "long") {
    return judgment.longVerdict === "SELL" ? judgment.longVerdict : judgment.shortVerdict;
  }
  return judgment.shortVerdict === "COVER" ? judgment.shortVerdict : judgment.longVerdict;
}

// Kurzbegruendung fuer die UI/Inbox; null wenn kein Konflikt. Nutzt conflictTrigger,
// damit Note + Kartenkopf garantiert dasselbe auslösende Urteil nennen.
export function conflictNote(direction: Direction, judgment: PositionJudgmentDTO): string | null {
  const v = conflictTrigger(direction, judgment);
  if (v === null) return null;
  const halt = direction === "long" ? "Long" : "Short";
  return `${halt} gehalten, Urteil ${v} läuft gegen die Position.`;
}
