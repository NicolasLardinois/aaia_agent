import type { DeepDiveView } from "../../contract/deepdive";
import { UnderlyingWrapperBadge } from "../UnderlyingWrapperBadge";
import { UnavailableField } from "../UnavailableField";
import { formatNumber } from "../../lib/format";

// Header (Konzept §4.5): beide Etiketten (underlying x wrapper) + Kurs/Markt + "vergleichen mit"-Einstieg.
export function DeepDiveHeader({ view, onCompare }: { view: DeepDiveView; onCompare?: () => void }) {
  return (
    <header className="space-y-2 border-b border-line pb-3">
      <h1 className="text-xl font-bold">{view.ticker} · {view.name}</h1>
      <UnderlyingWrapperBadge underlying={view.underlying} wrapper={view.wrapper} />
      <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
        <span>
          Kurs:{" "}
          {view.price === null
            ? <UnavailableField reason="Kurs nicht verfügbar" />
            : <span className="font-medium">{formatNumber(view.price)} {view.currency}</span>}
        </span>
        <span>· Markt: {view.market || "—"}</span>
        {onCompare && (
          <button type="button" onClick={onCompare} className="text-brand underline">
            ⤳ vergleichen mit
          </button>
        )}
      </div>
    </header>
  );
}
