import { Link } from "react-router-dom";
import type { PositionDTO } from "../../contract/portfolio";
import type { LongVerdict, ShortVerdict } from "../../contract/common";
import { UnderlyingWrapperBadge } from "../UnderlyingWrapperBadge";
import { ConfidenceBar } from "../ConfidenceBar";
import { verdictToVisual } from "../../lib/judgment";
import { detectConflict, conflictNote } from "../../lib/conflict";

// Das fuer die Positionsrichtung relevante Urteil: long -> Long-Linse, short -> Short-Linse.
// Sauber typisiert (LongVerdict | ShortVerdict) -> kein Cast bei verdictToVisual noetig.
function relevantVerdict(p: PositionDTO): LongVerdict | ShortVerdict {
  return p.direction === "long" ? p.judgment.longVerdict : p.judgment.shortVerdict;
}

function Row({ p }: { p: PositionDTO }) {
  const conflict = detectConflict(p.direction, p.judgment);
  const note = conflictNote(p.direction, p.judgment);
  const v = verdictToVisual(relevantVerdict(p));
  const signedSize = p.direction === "long" ? `+${p.sizePctNav} %` : `−${p.sizePctNav} %`;
  return (
    <tr
      className={conflict ? "bg-amber-50 dark:bg-amber-950/30" : ""}
      title={note ?? undefined}
    >
      <td className="py-2 pr-4">
        <Link to={`/deep-dive/${p.ticker}`} className="font-medium text-brand underline">{p.ticker}</Link>
        <div className="text-xs text-muted">{p.name}</div>
      </td>
      {/* L/S als Kuerzel: "L" (long) / "S" (short) — damit das Verdikt-Label (SHORT/SELL)
          im DOM eindeutig und per getByText("SHORT") testbar bleibt. */}
      <td className={`py-2 pr-4 font-medium ${p.direction === "short" ? "text-bear" : "text-bull"}`}>
        {p.direction === "long" ? "L" : "S"}
      </td>
      <td className="py-2 pr-4"><UnderlyingWrapperBadge underlying={p.underlying} wrapper={p.wrapper} /></td>
      <td className="py-2 pr-4 tabular-nums">{signedSize}</td>
      <td className="py-2 pr-4 tabular-nums">{p.entryPrice} {p.currency}</td>
      <td className="py-2 pr-4">
        <div className="flex flex-col gap-1">
          <span className={`font-semibold ${v.colorClass}`}>{v.label}</span>
          <ConfidenceBar value={p.judgment.confidence} />
          {conflict && (
            <span className="inline-block rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
              ⚠ Urteil gegen Position
            </span>
          )}
        </div>
      </td>
    </tr>
  );
}

// Positionstabelle (US23, Wireframe §4.8): alle Positionen long+short mit beiden Etiketten,
// Richtung, Groesse, Einstand, AAIA-Urteil + Konflikt-Markierung. Ticker -> Deep-Dive.
export function PositionsTable({ positions }: { positions: PositionDTO[] }) {
  if (positions.length === 0) {
    return <p className="text-muted">Keine Positionen erfasst.</p>;
  }
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="text-xs uppercase text-muted">
          <th className="py-1 pr-4">Titel</th>
          <th className="py-1 pr-4">L/S</th>
          <th className="py-1 pr-4">underlying×wrapper</th>
          <th className="py-1 pr-4">Größe</th>
          <th className="py-1 pr-4">Einstand</th>
          <th className="py-1 pr-4">AAIA-Urteil</th>
        </tr>
      </thead>
      <tbody>{positions.map((p) => <Row key={`${p.ticker}-${p.direction}`} p={p} />)}</tbody>
    </table>
  );
}
