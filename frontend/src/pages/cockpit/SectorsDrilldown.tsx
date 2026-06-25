import { useView } from "../../data/useView";
import { loadSectors } from "../../data/cockpit";
import { SignalBadge } from "../../components/SignalBadge";
import { UnavailableField } from "../../components/UnavailableField";
import { DrilldownShell } from "./DrilldownShell";
import type { SectorsView, SectorRow } from "../../contract/cockpit";

// Rotation-Label: favored = frühzyklisch begünstigt, avoid = gemieden, neutral = ausgeglichen.
const ROTATION_LABEL: Record<SectorRow["rotation"], string> = {
  favored:  "favored ↑",
  neutral:  "neutral →",
  avoid:    "avoid ↓",
};

const ROTATION_COLOR: Record<SectorRow["rotation"], string> = {
  favored: "text-bull",
  neutral: "text-neutral",
  avoid:   "text-bear",
};

function SectorRowItem({ row }: { row: SectorRow }) {
  return (
    <li className="flex items-center justify-between rounded-lg border border-line p-3">
      <span className="font-medium">{row.sector}</span>
      <span className={`text-sm font-medium ${ROTATION_COLOR[row.rotation]}`}>
        {ROTATION_LABEL[row.rotation]}
      </span>
      {/* signal null -> UNAVAILABLE (gestreift-grau), niemals als neutral/0 darstellen (Spec §5.4). */}
      {row.signal !== null
        ? <SignalBadge signal={row.signal} />
        : <UnavailableField reason="Signal-Quelle nicht verfügbar" />}
    </li>
  );
}

// Loader-Prop ermöglicht stabilen Aufruf ohne Refetch-Loop.
export function SectorsDrilldown({ loader = loadSectors }: { loader?: () => Promise<SectorsView> }) {
  const { data, loading, error } = useView(loader);

  return (
    <DrilldownShell title="Sektor-Rotation" view={data} loading={loading} error={error}>
      {data && (
        <div className="space-y-4">
          {/* Regime-Kontext: Sektor-Empfehlung hängt direkt vom Markt-Regime ab (US8). */}
          <div className="rounded-lg bg-surface-2 p-3 text-sm">
            Aktuelles Regime: <span className="font-semibold">{data.regime}</span>
          </div>
          <ul className="space-y-2">
            {data.sectors.map((s) => (
              <SectorRowItem key={s.sector} row={s} />
            ))}
          </ul>
        </div>
      )}
    </DrilldownShell>
  );
}
