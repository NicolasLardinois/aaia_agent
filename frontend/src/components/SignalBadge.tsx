import type { Signal } from "../lib/contract";
import { signalToVisual } from "../lib/display";

// Signal als kleine Ablesung: farbiger Punkt (bg-current = Signalfarbe) + Label.
export function SignalBadge({ signal }: { signal: Signal | null }) {
  const { label, colorClass } = signalToVisual(signal);
  return (
    <span className={`inline-flex items-center gap-1.5 font-semibold ${colorClass}`}>
      <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-current opacity-80" />
      {label}
    </span>
  );
}
