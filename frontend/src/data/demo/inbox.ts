// frontend/src/data/demo/inbox.ts
// Demo-Fixture fuer die Konflikt-Inbox (Spec §1, Slice 4). isDemo:true -> DemoBadge.
// Verwendet detectConflict/conflictNote (lib/conflict) + suggestVerdict (lib/inbox) als
// einzige Quelle der Wahrheit — keine Duplikat-Konfliktlogik hier.
//
// Positionen: 3 echte Konflikte + 1 Kontroll-Position (kein Konflikt, wird gefiltert).
// Konsistent zum Portfolio-Demo: XLE long+SELL (conflict.ts kennt diesen Fall).
import type { InboxView, ConflictDTO } from "../../contract/inbox";
import type { Direction, PositionJudgmentDTO } from "../../contract/portfolio";
import type { LongVerdict, ShortVerdict, Underlying, Wrapper } from "../../contract/common";
import { detectConflict, conflictNote } from "../../lib/conflict";
import { suggestVerdict } from "../../lib/inbox";

// Beschreibt eine Quell-Position (Ticker, gehaltenes Urteil, aktuelles Urteil).
// Wird durch detectConflict gefiltert; nur echte Konflikte erscheinen in der Inbox.
interface SourcePosition {
  ticker: string;
  name: string;
  underlying: Underlying;
  wrapper: Wrapper;
  direction: Direction;
  heldVerdict: LongVerdict | ShortVerdict;  // stuetzte die These bei Eroeffnung
  newLong: LongVerdict;                     // aktuelles AAIA-Long-Urteil
  newShort: ShortVerdict;                   // aktuelles AAIA-Short-Urteil
  confidence: number;                       // Konfidenz des kippenden Urteils
}

// Quell-Positionen (mix aus Portfolio-Demo-Tickers fuer Konsistenz).
// MSFT ist bewusst als Nicht-Konflikt dabei (detectConflict=false -> herausgefiltert).
const SOURCE_POSITIONS: SourcePosition[] = [
  {
    // XLE: long gehalten, Long-Urteil SELL laeuft gegen die Position.
    // suggestVerdict: EXIT (SELL ohne SHORT -> keine Richtungsumkehr, nur raus).
    // Konsistent zum Portfolio-Demo (portfolio.ts XLE-Kommentar).
    ticker: "XLE", name: "Energy Select Sector SPDR",
    underlying: "equity_index", wrapper: "fund",
    direction: "long", heldVerdict: "BUY",
    newLong: "SELL", newShort: "NONE", confidence: 0.58,
  },
  {
    // GC=F: long gehalten, Short-Urteil SHORT aktiv (aktives Gegen-Setup).
    // suggestVerdict: REVERSE (SHORT vorhanden -> Richtung drehen ist staerker als EXIT).
    ticker: "GC=F", name: "Gold",
    underlying: "precious_metal", wrapper: "future",
    direction: "long", heldVerdict: "BUY",
    newLong: "HOLD", newShort: "SHORT", confidence: 0.55,
  },
  {
    // TSLA: short gehalten, Long-Urteil BUY aktiv (aktives Gegen-Setup).
    // suggestVerdict: REVERSE (BUY hat Vorrang vor COVER -> Richtung drehen).
    // Hinweis: im Portfolio-Demo stuetzt SHORT das TSLA-Short; in der Inbox hat sich das Bild
    // gedreht (neues BUY-Setup) — zwei Demo-Momentaufnahmen, beide fachlich konsistent.
    ticker: "TSLA", name: "Tesla Inc.",
    underlying: "equity", wrapper: "single",
    direction: "short", heldVerdict: "SHORT",
    newLong: "BUY", newShort: "COVER", confidence: 0.62,
  },
  {
    // MSFT: long gehalten, Long-Urteil BUY -> KEIN Konflikt. Wird gefiltert.
    // Dokumentiert, dass detectConflict als Tor wirkt (eine Quelle der Wahrheit).
    ticker: "MSFT", name: "Microsoft Corp.",
    underlying: "equity", wrapper: "single",
    direction: "long", heldVerdict: "BUY",
    newLong: "BUY", newShort: "NONE", confidence: 0.55,
  },
];

// Baut ein ConflictDTO aus einer SourcePosition, falls detectConflict zutrifft.
function toConflictDTO(pos: SourcePosition): ConflictDTO | null {
  const judgment: PositionJudgmentDTO = {
    longVerdict: pos.newLong,
    shortVerdict: pos.newShort,
    confidence: pos.confidence,
  };
  if (!detectConflict(pos.direction, judgment)) return null;
  const note = conflictNote(pos.direction, judgment);
  const suggestion = suggestVerdict(pos.direction, pos.heldVerdict, pos.newLong, pos.newShort);
  return {
    id: `${pos.ticker}-${pos.direction}`,
    ticker: pos.ticker,
    name: pos.name,
    underlying: pos.underlying,
    wrapper: pos.wrapper,
    direction: pos.direction,
    heldVerdict: pos.heldVerdict,
    newLongVerdict: pos.newLong,
    newShortVerdict: pos.newShort,
    confidence: pos.confidence,
    conflictNote: note ?? "",  // conflictNote ist nur null bei Nicht-Konflikten; hier immer gesetzt
    suggestedVerdict: suggestion.verdict,
    suggestedRationale: suggestion.rationale,
    status: "offen",           // Initialzustand: alle Konflikte offen (US30)
  };
}

export function demoInbox(): InboxView {
  const conflicts = SOURCE_POSITIONS
    .map(toConflictDTO)
    .filter((c): c is ConflictDTO => c !== null);
  return { isDemo: true, conflicts };
}
