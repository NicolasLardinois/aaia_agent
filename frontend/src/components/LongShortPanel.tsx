import { ConfidenceBar } from "./ConfidenceBar";
import { AutoHoldBadge, CashBiasBadge } from "./ThresholdBadges";
import { XaiPanel, type XaiContent } from "./XaiPanel";
import { verdictToVisual, consistencyHint } from "../lib/judgment";
import type { LongVerdict, ShortVerdict } from "../contract/common";

export interface VerdictLens {
  verdict: LongVerdict | ShortVerdict;
  confidence: number;
  rationale: string;
  xai?: XaiContent;
}

function Lens({ title, lens }: { title: string; lens: VerdictLens }) {
  const v = verdictToVisual(lens.verdict);
  return (
    <div className="flex-1 space-y-2 p-3">
      <div className="text-xs uppercase tracking-wide text-muted">{title}</div>
      <div className={`text-xl font-bold ${v.colorClass}`}>▶ {v.label}</div>
      <ConfidenceBar value={lens.confidence} />
      <div className="flex flex-wrap gap-1">
        <AutoHoldBadge confidence={lens.confidence} />
        <CashBiasBadge confidence={lens.confidence} />
      </div>
      <p className="text-sm text-muted">{lens.rationale}</p>
      {lens.xai && <XaiPanel xai={lens.xai} />}
    </div>
  );
}

// Long und Short STRIKT gleichwertig nebeneinander, nie ein Umschalter (Konzept §5.3).
export function LongShortPanel({ long, short }: { long: VerdictLens; short: VerdictLens }) {
  const hint = consistencyHint(long.verdict as LongVerdict, short.verdict as ShortVerdict);
  return (
    <div className="rounded-lg border border-line">
      <div className="flex divide-x divide-line">
        <Lens title="LONG-LINSE" lens={long} />
        <Lens title="SHORT-LINSE" lens={short} />
      </div>
      {hint && <div className="border-t border-line px-3 py-1.5 text-sm text-muted">{hint}</div>}
    </div>
  );
}
