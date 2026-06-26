import { useState } from "react";
import { useView } from "../../data/useView";
import { loadBuffett } from "../../data/cockpit";
import { sortRows, filterRows, vsMedianLabel, toMapPoints } from "../../lib/buffett";
import { zScoreFlag } from "../../lib/anomaly";
import { SignalBadge } from "../../components/SignalBadge";
import { ChoroplethMap } from "../../components/charts/ChoroplethMap";
import { LineCurve } from "../../components/charts/LineCurve";
import { Icon } from "../../components/icons";
import { DrilldownShell } from "./DrilldownShell";
import type { BuffettView, BuffettCountry } from "../../contract/cockpit";
import type { SortKey } from "../../lib/buffett";

// ---- Einschraenkungen (Pflicht laut frontend_notes.md / US6) ----
// Jede Einschraenkung begruendet, warum der Buffett-Indikator als alleiniges Signal nicht reicht.
const EINSCHRAENKUNGEN = [
  {
    titel: "Globalisierung",
    text: "Multinationale Konzerne erzielen Gewinne weltweit, die BIP-Basis unterschätzt die reale Ertragsbasis.",
  },
  {
    titel: "Zinskontext",
    text: "Bei niedrigen Zinsen (TINA) sind höhere Bewertungsquoten historisch normal — der Indikator ist zinssensitiv.",
  },
  {
    titel: "Kein Timing",
    text: "Hohe Quoten können jahrelang bestehen, bevor ein Kursrückgang einsetzt. Kein Market-Timing-Instrument.",
  },
  {
    titel: "Aktienrückkäufe",
    text: "Massive Rückkäufe (insb. USA) reduzieren den Streubesitz, treiben Kurse ohne BIP-Wachstum und verzerren die Quote.",
  },
];

// ---- Spalten-Sortierung ----
type SortDir = "asc" | "desc";

function SortButton({
  label,
  sortKey,
  current,
  dir,
  onToggle,
}: {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  dir: SortDir;
  onToggle: (k: SortKey) => void;
}) {
  const active = current === sortKey;
  return (
    <button
      onClick={() => onToggle(sortKey)}
      className={`inline-flex items-center gap-0.5 text-left text-xs font-semibold ${active ? "text-ink" : "text-muted hover:text-ink"}`}
    >
      {label}
      <Icon name={active ? (dir === "desc" ? "sort-desc" : "sort-asc") : "sort-none"} className="h-3.5 w-3.5" />
    </button>
  );
}

// ---- Einzelland-10-J-Drilldown ----
function CountryHistory({ country }: { country: BuffettCountry }) {
  if (country.history.length === 0) {
    return <p className="text-sm text-muted">Keine Verlaufsdaten verfügbar.</p>;
  }
  const series = [
    {
      name: `${country.name} — Buffett-Ratio`,
      points: country.history.map((h) => ({ x: String(h.year), y: h.ratioPct })),
    },
  ];
  return (
    <div className="mt-3">
      <p className="mb-1 text-sm font-semibold text-ink">10-J-Verlauf — {country.name}</p>
      <LineCurve series={series} height={200} />
    </div>
  );
}

// ---- Tabellenzeile ----
function BuffettRow({
  row,
  median,
  highlighted,
  selected,
  onClick,
}: {
  row: BuffettCountry;
  median: number;
  highlighted: boolean;
  selected: boolean;
  onClick: () => void;
}) {
  const flag = row.zScore !== null ? zScoreFlag(row.zScore) : "none";
  const { label: vsLabel } = vsMedianLabel(row.ratioPct, median);
  return (
    <>
      <tr
        onClick={onClick}
        className={`cursor-pointer border-b border-line transition-colors ${
          highlighted
            ? "bg-brand/10 font-semibold hover:bg-brand/[0.15]"
            : "hover:bg-surface-2"
        }`}
      >
        <td className="p-2 text-sm">{row.name}</td>
        <td className="p-2 text-right text-sm font-mono tnum">{row.ratioPct.toFixed(1)} %</td>
        <td className="p-2 text-sm">
          <SignalBadge signal={row.signal} />
        </td>
        <td className="p-2 text-right text-sm font-mono tnum">
          {row.zScore !== null ? (
            <span>
              {row.zScore > 0 ? "+" : ""}
              {row.zScore.toFixed(1)}
              {flag !== "none" && (
                <Icon
                  name="warning"
                  label={flag === "anomaly" ? "Anomalie (|Z|>2)" : "Auffällig (|Z|≥1.5)"}
                  className="ml-1 inline-block h-3.5 w-3.5 text-amber-600"
                />
              )}
            </span>
          ) : (
            <span className="text-muted">—</span>
          )}
        </td>
        <td className="p-2 text-center text-sm text-muted">
          {row.year === null ? "live" : row.year}
        </td>
        <td className="p-2 text-sm text-muted">{vsLabel}</td>
      </tr>
      {selected && (
        <tr>
          <td colSpan={6} className="bg-surface-2 p-3">
            <CountryHistory country={row} />
          </td>
        </tr>
      )}
    </>
  );
}

// ---- Hauptkomponente ----
export function BuffettWidget({ loader = loadBuffett }: { loader?: () => Promise<BuffettView> }) {
  const { data, loading, error } = useView(loader);

  // Tab: Tabelle (default) oder Karte
  const [tab, setTab] = useState<"tabelle" | "karte">("tabelle");
  // Sortierung
  const [sortKey, setSortKey] = useState<SortKey>("ratioPct");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  // Filter
  const [onlyZOutlier, setOnlyZOutlier] = useState(false);
  const [onlyBearish, setOnlyBearish] = useState(false);
  // Ausgewaehltes Land fuer 10-J-Drilldown
  const [selectedIso3, setSelectedIso3] = useState<string | null>(null);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  function toggleRow(iso3: string) {
    setSelectedIso3((prev) => (prev === iso3 ? null : iso3));
  }

  return (
    <DrilldownShell title="Buffett-Indikator" view={data} loading={loading} error={error}>
      {data && (
        <div className="space-y-4">
          {/* Asset-Filter-Hinweis (Pflicht, US5) */}
          <p className="text-xs text-muted">
            Nur für <strong>Aktien, ETF und Index</strong> relevant — nicht für Anleihen, Rohstoffe oder Immobilien.
          </p>

          {/* Global-Median als Referenz */}
          <div className="rounded-lg bg-surface-2 p-3 text-sm">
            Globaler Median (Referenz): <span className="font-semibold font-mono tnum">{data.globalMedian} %</span>
            <span className="ml-2 text-muted text-xs">(alle Länder im Datensatz)</span>
          </div>

          {/* Tab-Umschalter */}
          <div className="flex gap-2">
            <button
              onClick={() => setTab("tabelle")}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-sm font-medium ${
                tab === "tabelle"
                  ? "bg-brand text-brand-ink"
                  : "border border-line text-muted hover:bg-surface-2"
              }`}
            >
              <Icon name="view-table" className="h-4 w-4" /> Tabelle
            </button>
            <button
              onClick={() => setTab("karte")}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-sm font-medium ${
                tab === "karte"
                  ? "bg-brand text-brand-ink"
                  : "border border-line text-muted hover:bg-surface-2"
              }`}
            >
              <Icon name="view-map" className="h-4 w-4" /> Karte
            </button>
          </div>

          {/* ---- KARTEN-TAB ---- */}
          {/* toMapPoints: iso3 -> englischer GeoJSON-Name (world.geo.json joiniert per name-Property).
              Demo-Daten haben deutsche Namen; ohne Mapping bleibt die Karte grau (kein Match). */}
          {tab === "karte" && (
            <ChoroplethMap
              points={toMapPoints(data.countries)}
              height={380}
            />
          )}

          {/* ---- TABELLEN-TAB ---- */}
          {tab === "tabelle" && (
            <>
              {/* Filter-Leiste */}
              <div className="flex flex-wrap gap-4 text-sm">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={onlyZOutlier}
                    onChange={(e) => setOnlyZOutlier(e.target.checked)}
                  />
                  Nur Z-Ausreißer (|Z|≥1.5)
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={onlyBearish}
                    onChange={(e) => setOnlyBearish(e.target.checked)}
                  />
                  Nur BEARISH
                </label>
              </div>

              {/* Tabelle */}
              <div className="overflow-x-auto rounded-lg border border-line">
                <table className="w-full text-sm">
                  <thead className="bg-surface-2 text-left">
                    <tr>
                      <th className="p-2">
                        <SortButton label="Land" sortKey="name" current={sortKey} dir={sortDir} onToggle={toggleSort} />
                      </th>
                      <th className="p-2 text-right">
                        <SortButton label="Ratio %" sortKey="ratioPct" current={sortKey} dir={sortDir} onToggle={toggleSort} />
                      </th>
                      <th className="p-2">Signal</th>
                      <th className="p-2 text-right">
                        <SortButton label="Z-Score" sortKey="zScore" current={sortKey} dir={sortDir} onToggle={toggleSort} />
                      </th>
                      <th className="p-2 text-center">Jahr</th>
                      <th className="p-2">vs. Median</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortRows(
                      filterRows(data.countries, { onlyZOutlier, onlyBearish }),
                      sortKey,
                      sortDir,
                    ).map((row) => (
                      <BuffettRow
                        key={row.iso3}
                        row={row}
                        median={data.globalMedian}
                        highlighted={row.iso3 === data.analyzedIso3}
                        selected={selectedIso3 === row.iso3}
                        onClick={() => toggleRow(row.iso3)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              {filterRows(data.countries, { onlyZOutlier, onlyBearish }).length === 0 && (
                <p className="text-sm text-muted">Kein Land erfüllt die aktiven Filter.</p>
              )}
            </>
          )}

          {/* Einschraenkungen (Pflicht, US6 / frontend_notes.md): aufklappbar, aber standardmaessig offen
              damit die Texte immer im DOM sichtbar sind (Spec: "im DOM vorhanden"). */}
          <details open className="rounded-lg border border-line p-3 text-sm">
            <summary className="cursor-pointer font-medium text-ink">
              Einschraenkungen des Buffett-Indikators
            </summary>
            <ul className="mt-3 space-y-2 text-muted">
              {EINSCHRAENKUNGEN.map((e) => (
                <li key={e.titel}>
                  <strong>{e.titel}:</strong> {e.text}
                </li>
              ))}
            </ul>
          </details>
        </div>
      )}
    </DrilldownShell>
  );
}
