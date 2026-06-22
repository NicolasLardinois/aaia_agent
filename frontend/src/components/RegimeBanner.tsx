import type { CockpitOverview } from "../lib/contract";
import { ConfidenceBar } from "./ConfidenceBar";
import { UnavailableField } from "./UnavailableField";

export function RegimeBanner({ overview }: { overview: CockpitOverview }) {
  return (
    <section className="rounded-lg border border-slate-200 p-4">
      <h2 className="text-xs uppercase tracking-wide text-slate-500">Marktregime</h2>
      {overview.macro_status === "unavailable" ? (
        <UnavailableField reason="Makro-Daten nicht verfügbar" />
      ) : (
        <div className="mt-1 flex items-center gap-4">
          <span className="text-2xl font-bold">{overview.regime}</span>
          <ConfidenceBar value={overview.regime_confidence} />
        </div>
      )}
    </section>
  );
}
