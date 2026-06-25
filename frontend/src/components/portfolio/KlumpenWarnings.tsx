import type { KlumpenWarningDTO, KlumpenDimension } from "../../contract/portfolio";

// Deutsche Dimensions-Bezeichnung (Wireframe §4.8: Sektor / Asset-Klasse / Geographie).
const DIM_LABEL: Record<KlumpenDimension, string> = {
  sector: "Sektor", underlying: "Asset-Klasse", geography: "Geographie",
};

// Klumpen-Warnungen (US25): Konzentration je Dimension mit Limit-Bezug. Leere Liste = Entwarnung.
export function KlumpenWarnings({ klumpen }: { klumpen: KlumpenWarningDTO[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold">⚠ Klumpen-Warnungen</h3>
      {klumpen.length === 0 ? (
        <p className="mt-1 rounded bg-bull/10 p-2 text-sm text-bull">
          Keine Konzentration über den Limits.
        </p>
      ) : (
        <ul className="mt-1 space-y-1 text-sm">
          {klumpen.map((k) => (
            <li key={`${k.dimension}-${k.name}`} className="rounded bg-amber-50 px-2 py-1 text-amber-800">
              <span className="font-medium">{DIM_LABEL[k.dimension]}:</span> {k.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
