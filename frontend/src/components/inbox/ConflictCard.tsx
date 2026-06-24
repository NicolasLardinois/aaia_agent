// ConflictCard.tsx
// Eine beratende Konflikt-Karte (US29/US30, Konzept §2.5, Wireframe §4.9).
// Zeigt: Ticker + Richtungs-Kipp, Verdikt-Optionen (Default hervorgehoben), Begruendung,
// Querlinks (Portfolio / Deep-Dive) + Protokoll-Aktionen (KEINE Trade-Ausfuehrung).
import { Link } from "react-router-dom";
import type { ConflictDTO, ConflictDecision, ConflictVerdict } from "../../contract/inbox";
import { UnderlyingWrapperBadge } from "../UnderlyingWrapperBadge";
import { ConfidenceBar } from "../ConfidenceBar";
import { verdictToVisual } from "../../lib/judgment";

export interface ConflictCardProps {
  conflict: ConflictDTO;
  // US30: nur im Offen-Tab gesetzt. Erledigen markiert + protokolliert (KEINE Trade-Ausfuehrung).
  onResolve?: (id: string, decision: ConflictDecision) => void;
  // im Erledigt-Tab gesetzt: die protokollierte Entscheidung (Audit-Trail).
  loggedDecision?: ConflictDecision;
}

// Alle drei Verdikt-Optionen in fixer Reihenfolge (US29: Default hervorgehoben).
const VERDIKT_OPTIONEN: ConflictVerdict[] = ["EXIT", "HOLD", "REVERSE"];

// Beschreibt jedes Verdikt mit einer kurzen, beratenden Bezeichnung (keine Trade-Sprache).
const VERDIKT_LABEL: Record<ConflictVerdict, string> = {
  EXIT: "EXIT — aussteigen",
  HOLD: "HOLD — halten",
  REVERSE: "REVERSE — Richtung drehen",
};

// Kipp-Text: welches neue Urteil laeuft gegen die Position? Long-Seite: newLongVerdict;
// Short-Seite: newShortVerdict zeigt den Druck. Einfaerbung via verdictToVisual.
function relevantesUrteils(conflict: ConflictDTO): { label: string; colorClass: string } {
  if (conflict.direction === "long") {
    return verdictToVisual(conflict.newLongVerdict);
  }
  // Short-Position: neues Long-Urteil zeigt den Gegenwind
  return verdictToVisual(conflict.newLongVerdict);
}

export function ConflictCard({ conflict, onResolve, loggedDecision }: ConflictCardProps) {
  const { ticker, name, direction, confidence, conflictNote, suggestedVerdict, suggestedRationale } = conflict;
  const richtungsKurzel = direction === "long" ? "L" : "S";
  const neuesUrteil = relevantesUrteils(conflict);

  // Erledigt-Modus: kein onResolve + kein loggedDecision -> trotzdem kein Render (beides optional)
  const istErledigt = loggedDecision !== undefined;

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      {/* Kopfzeile: Badge, Ticker, Name, Richtung, Kipp-Text */}
      <div className="mb-3 flex flex-wrap items-start gap-2">
        <UnderlyingWrapperBadge underlying={conflict.underlying} wrapper={conflict.wrapper} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {/* Ticker verlinkt auf Deep-Dive (Konzept §3 Querverlinkung) */}
            <Link
              to={`/deep-dive/${ticker}`}
              className="text-base font-bold text-slate-900 hover:underline dark:text-slate-100"
            >
              {ticker}
            </Link>
            <span className="text-sm text-slate-500">
              {richtungsKurzel === "L" ? "LONG" : "SHORT"} gehalten
            </span>
            <span className="text-sm">
              → neues Urteil:{" "}
              <span className={`font-semibold ${neuesUrteil.colorClass}`}>
                {conflict.direction === "long" ? conflict.newLongVerdict : conflict.newShortVerdict}
              </span>{" "}
              <span className="text-slate-400">({Math.round(confidence * 100)} %)</span>
            </span>
          </div>
          <p className="mt-0.5 text-sm text-slate-500">{name}</p>
        </div>
      </div>

      {/* Konfidenz-Balken */}
      <div className="mb-3">
        <ConfidenceBar value={confidence} />
      </div>

      {/* Konflikt-Begruendung (warum dies ein Konflikt ist) */}
      <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">{conflictNote}</p>

      {/* Verdikt-Reihe: EXIT / HOLD / REVERSE (US29: Default hervorgehoben) */}
      <div className="mb-3">
        <p className="mb-1 text-xs font-medium text-slate-500 uppercase tracking-wide">
          Beratendes Verdikt (Vorschlag):
        </p>
        <div className="flex flex-wrap gap-2">
          {VERDIKT_OPTIONEN.map((v) => {
            const istDefault = v === suggestedVerdict;
            return (
              <span
                key={v}
                role="button"
                aria-pressed={istDefault ? "true" : "false"}
                title={VERDIKT_LABEL[v]}
                className={[
                  "rounded px-3 py-1 text-sm font-medium cursor-default select-none",
                  istDefault
                    ? "ring-2 ring-offset-1 ring-slate-900 bg-slate-900 text-white dark:ring-slate-200 dark:bg-slate-200 dark:text-slate-900 font-bold"
                    : "border border-slate-300 text-slate-500 dark:border-slate-600",
                ].join(" ")}
              >
                {v}
                {istDefault && <span className="ml-1 text-xs opacity-75">✓ Vorschlag</span>}
              </span>
            );
          })}
        </div>
        {/* Fachliche Begruendung des Default-Vorschlags */}
        <p className="mt-1.5 text-xs text-slate-500 italic">{suggestedRationale}</p>
      </div>

      {/* Querlinks (Konzept §3) */}
      <div className="mb-3 flex gap-3 text-xs">
        <Link to={`/deep-dive/${ticker}`} className="text-blue-600 hover:underline dark:text-blue-400">
          ↗ Deep-Dive
        </Link>
        <Link to="/portfolio" className="text-blue-600 hover:underline dark:text-blue-400">
          ↗ Portfolio
        </Link>
      </div>

      {/* Aktionen oder Audit-Label */}
      {istErledigt ? (
        /* Erledigt-Tab: Audit-Label anstelle der Aktions-Buttons */
        <div className="rounded bg-slate-100 px-3 py-2 text-sm text-slate-700 dark:bg-slate-700 dark:text-slate-300">
          <span className="font-medium">Erledigt: {loggedDecision}</span>
        </div>
      ) : onResolve ? (
        /* Offen-Tab: Protokoll-Aktionen (KEINE Trade-Ausfuehrung, US30) */
        <div className="flex flex-wrap gap-2">
          <p className="w-full text-xs text-slate-400 mb-1">
            Entscheidung protokollieren (kein Trade — nur Notiz):
          </p>
          <button
            type="button"
            onClick={() => onResolve(conflict.id, "gefolgt")}
            className="rounded bg-green-100 px-3 py-1.5 text-sm font-medium text-green-800 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-300"
          >
            Gefolgt
          </button>
          <button
            type="button"
            onClick={() => onResolve(conflict.id, "ignoriert")}
            className="rounded bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-800 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-300"
          >
            Ignoriert
          </button>
          <button
            type="button"
            onClick={() => onResolve(conflict.id, "vertagt")}
            className="rounded bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300"
          >
            Vertagt
          </button>
        </div>
      ) : null}
    </article>
  );
}
