import type { Underlying, Wrapper } from "../contract/common";
import { underlyingToVisual, wrapperToVisual } from "../lib/assets";

// Zwei farbcodierte Etiketten (Konzept §5.2): Basiswert x Huelle.
export function UnderlyingWrapperBadge({ underlying, wrapper }: { underlying: Underlying; wrapper: Wrapper }) {
  const u = underlyingToVisual(underlying);
  const w = wrapperToVisual(wrapper);
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${u.colorClass}`}>
        <span aria-hidden>{u.icon}</span>{u.label}
      </span>
      <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${w.colorClass}`}>
        <span aria-hidden>{w.icon}</span>{w.label}
      </span>
    </span>
  );
}
