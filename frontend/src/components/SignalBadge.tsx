import type { Signal } from "../lib/contract";
import { signalToVisual } from "../lib/display";

export function SignalBadge({ signal }: { signal: Signal | null }) {
  const { label, colorClass } = signalToVisual(signal);
  return <span className={`font-semibold ${colorClass}`}>{label}</span>;
}
