import type { Underlying, Wrapper } from "../contract/common";
import { underlyingToVisual, wrapperToVisual } from "../lib/assets";
import { Icon } from "./icons";

// Zwei farbcodierte Etiketten (Konzept §5.2): Basiswert x Huelle.
export function UnderlyingWrapperBadge({ underlying, wrapper }: { underlying: Underlying; wrapper: Wrapper }) {
  const u = underlyingToVisual(underlying);
  const w = wrapperToVisual(wrapper);
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${u.colorClass}`}>
        <Icon name={u.icon} className="h-3.5 w-3.5" />{u.label}
      </span>
      <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${w.colorClass}`}>
        <Icon name={w.icon} className="h-3.5 w-3.5" />{w.label}
      </span>
    </span>
  );
}
