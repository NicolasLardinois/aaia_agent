import { sourcesLabel } from "../lib/display";

export function DataHealthIndicator({ active, total }: { active: number; total: number }) {
  const allUp = active === total;
  return (
    <span className={`text-sm ${allUp ? "text-muted" : "text-amber-600"}`}>
      {sourcesLabel(active, total)}
    </span>
  );
}
