import { useState } from "react";
import { useView } from "../../data/useView";
import { loadBuffett } from "../../data/cockpit";
import { sortRows, filterRows, vsMedianLabel } from "../../lib/buffett";
import { zScoreFlag } from "../../lib/anomaly";
import { SignalBadge } from "../../components/SignalBadge";
import { ChoroplethMap } from "../../components/charts/ChoroplethMap";
import { LineCurve } from "../../components/charts/LineCurve";
import { DrilldownShell } from "./DrilldownShell";
import type { BuffettView, BuffettCountry } from "../../contract/cockpit";
import type { SortKey } from "../../lib/buffett";

// ---- Einschraenkungen (Pflicht laut frontend_notes.md / US6) ----
// Jede Einschraenkung begruendet, warum der Buffett-Indikator als alleiniges Signal nicht reicht.
const EINSCHRAENKUNGEN = [
  {
    titel: "Globalisierung",
    text: "Multinationale Konzerne erzielen Gewinne weltweit, die BIP-Basis unterschaetzt die reale Ertragsbasis.",
  },
  {
    titel: "Zinskontext",
    text: "Bei niedrigen Zinsen (TINA) sind hoehere Bewertungsquoten historisch normal — der Indikator ist zinssensitiv.",
  },
  {
    titel: "Kein Timing",
    text: "Hohe Quoten koennen jahrelang bestehen, bevor ein Kursrueckgang einsetzt. Kein Market-Timing-Instrument.",
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
      className={`text-left text-xs font-semibold ${active ? "text-slate-900" : "text-slate-500 hover:text-slate-700"}`}
    >
      {label} {active ? (dir === "desc" ? "↓" : "↑") : "↕"}
    </button>
  );
}

// ---- Einzelland-10-J-Drilldown ----
function CountryHistory({ country }: { country: BuffettCountry }) {
  if (country.history.length === 0) {
    return <p className="text-sm text-slate-500">Keine Verlaufsdaten verfuegbar.</p>;
  }
  const series = [
    {
      name: `${country.name} — Buffett-Ratio`,
      points: country.history.map((h) => ({ x: String(h.year), y: h.ratioPct })),
    },
  ];
  return (
    <div className="mt-3">
      <p className="mb-1 text-sm font-semibold text-slate-700">10-J-Verlauf — {country.name}</p>
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
        className={`cursor-pointer border-b transition-colors ${
          highlighted
            ? "bg-blue-50 font-semibold hover:bg-blue-100"
            : "hover:bg-slate-50"
        }`}
      >
        <td className="p-2 text-sm">{row.name}</td>
        <td className="p-2 text-right text-sm">{row.ratioPct.toFixed(1)} %</td>
        <td className="p-2 text-sm">
          <SignalBadge signal={row.signal} />
        </td>
        <td className="p-2 text-right text-sm">
          {row.zScore !== null ? (
            <span>
              {row.zScore > 0 ? "+" : ""}
              {row.zScore.toFixed(1)}
              {flag !== "none" && (
                <span className="ml-1 text-amber-600" title={flag === "anomaly" ? "Anomalie (|Z|>2)" : "Auffaellig (|Z|≥1.5)"}>
                  ⚠
                </span>
              )}
            </span>
          ) : (
            <span className="text-slate-400">—</span>
          )}
        </td>
        <td className="p-2 text-center text-sm text-slate-500">
          {row.year === null ? "live" : row.year}
        </td>
        <td className="p-2 text-sm text-slate-600">{vsLabel}</td>
      </tr>
      {selected && (
        <tr>
          <td colSpan={6} className="bg-slate-50 p-3">
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
          <p className="text-xs text-slate-500">
            Nur fuer <strong>Aktien, ETF und Index</strong> relevant — nicht fuer Anleihen, Rohstoffe oder Immobilien.
          </p>

          {/* Global-Median als Referenz */}
          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            Globaler Median (Referenz): <span className="font-semibold">{data.globalMedian} %</span>
            <span className="ml-2 text-slate-400 text-xs">(alle Laender im Datensatz)</span>
          </div>

          {/* Tab-Umschalter */}
          <div className="flex gap-2">
            <button
              onClick={() => setTab("tabelle")}
              className={`rounded-md px-3 py-1 text-sm font-medium ${
                tab === "tabelle"
                  ? "bg-slate-800 text-white"
                  : "border border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              Tabelle ▣
            </button>
            <button
              onClick={() => setTab("karte")}
              className={`rounded-md px-3 py-1 text-sm font-medium ${
                tab === "karte"
                  ? "bg-slate-800 text-white"
                  : "border border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              Karte ◻
            </button>
          </div>

          {/* ---- KARTEN-TAB ---- */}
          {tab === "karte" && (
            <ChoroplethMap
              points={data.countries.map((c) => ({
                iso3: c.iso3,
                name: c.name,
                value: c.ratioPct,
                signal: c.signal,
              }))}
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
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-left">
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
                <p className="text-sm text-slate-500">Kein Land erfuellt die aktiven Filter.</p>
              )}
            </>
          )}

          {/* Einschraenkungen (Pflicht, US6 / frontend_notes.md): aufklappbar, aber standardmaessig offen
              damit die Texte immer im DOM sichtbar sind (Spec: "im DOM vorhanden"). */}
          <details open className="rounded-lg border border-slate-200 p-3 text-sm">
            <summary className="cursor-pointer font-medium text-slate-700">
              Einschraenkungen des Buffett-Indikators
            </summary>
            <ul className="mt-3 space-y-2 text-slate-600">
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
