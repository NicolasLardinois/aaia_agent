import { formatConfidence } from "../lib/format";

export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="flex items-center gap-2">
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 w-32 rounded bg-slate-200"
      >
        <div className="h-2 rounded bg-slate-600" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm tabular-nums">{formatConfidence(value)}</span>
    </div>
  );
}
