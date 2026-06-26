import type { LongVerdict, ShortVerdict } from "../../contract/common";
import { verdictToVisual, consistencyHint } from "../../lib/judgment";
import { formatConfidence } from "../../lib/format";

// "Urteil auf einen Blick" (Mangel #13/#11): hebt das wichtigste Ergebnis des Deep-Dive
// — das Long/Short-Urteil — in den Seitenkopf (die These zuerst, Details folgen im
// LongShortPanel darunter). Es erfindet NICHTS: Labels/Farben kommen aus verdictToVisual,
// der Gesamthinweis aus consistencyHint — exakt dieselbe Quelle wie das Detail-Panel.
interface Stance {
  verdict: LongVerdict | ShortVerdict;
  confidence: number; // 0..1
}

function Chip({ title, stance }: { title: string; stance: Stance }) {
  const v = verdictToVisual(stance.verdict);
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[11px] font-medium uppercase tracking-wide text-muted">{title}</span>
      <span className={`font-display text-base font-bold ${v.colorClass}`}>{v.label}</span>
      <span className="tnum text-xs text-muted">{formatConfidence(stance.confidence)}</span>
    </div>
  );
}

export function VerdictGlance({
  long,
  short,
}: {
  long: { verdict: LongVerdict; confidence: number };
  short: { verdict: ShortVerdict; confidence: number };
}) {
  const hint = consistencyHint(long.verdict, short.verdict);
  return (
    <div className="rounded-lg border border-line bg-surface-2 px-3 py-2">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted">
        Urteil auf einen Blick
      </div>
      <div className="flex flex-col gap-1">
        <Chip title="Long" stance={long} />
        <Chip title="Short" stance={short} />
      </div>
      {hint && <p className="mt-1.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}
