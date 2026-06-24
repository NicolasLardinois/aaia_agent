import { useView } from "../../data/useView";
import { loadBigMac } from "../../data/cockpit";
import { BarChart } from "../../components/charts/BarChart";
import { DrilldownShell } from "./DrilldownShell";
import type { BigMacView } from "../../contract/cockpit";

// Big-Mac-Index (The Economist, halbjaehrlich Jan/Jul).
// Misst Ueberbewerung (+) bzw. Unterbewertung (-) einer Waehrung vs. USD
// auf Basis des Hamburger-Preisvergleichs. Beschraenkungen: setzt reale Kaufkraft-Parität voraus,
// ignoriert Handelsbarrieren, Subventionen, lokale Lohnkosten. Grobe Orientierung, kein Timing.

// Einschraenkungen des Big-Mac-Index (einklappbar, aber im DOM vorhanden — Spec §5.4).
const EINSCHRAENKUNGEN = [
  "Kaufkraftparitaet als Annahme: setzt voraus, dass gleiche Gueter gleich teuer sein sollten — gilt nur bedingt.",
  "Lokale Produktionskosten (Lohn, Subventionen, Steuern) verzerren den Vergleich systematisch.",
  "Kein Timing-Instrument: Unterbewertungen koennen jahrelang bestehen.",
  "Deckt nur Laender mit McDonald's ab — viele Schwellenlaender fehlen.",
];

export function BigMacWidget({ loader = loadBigMac }: { loader?: () => Promise<BigMacView> }) {
  const { data, loading, error } = useView(loader);

  return (
    <DrilldownShell title="Big-Mac-Index" view={data} loading={loading} error={error}>
      {data && (
        <div className="space-y-4">
          {/* Publikationsdatum: halbjährlich Jan/Jul — immer sichtbar (US7). */}
          <div className="text-sm text-slate-500">
            Stand: <span className="font-semibold text-slate-700">{data.publishedAt}</span>
            <span className="ml-2 text-slate-400">(The Economist, halbjaehrlich Jan/Jul)</span>
          </div>

          {/* Hinweis Bewertungsrichtung */}
          <p className="text-xs text-slate-500">
            + = über USD-Referenz (ueberbewertet) · – = unter USD-Referenz (unterbewertet)
          </p>

          {/* Balkendiagramm: Ueber-/Unterbewertung vs. USD (horizontale Balken, Farbe nach Vorzeichen).
              Analysiertes Land (analyzedIso2) ist hervorgehoben (highlight-Balken mit Rahmen). */}
          <BarChart
            bars={data.rows.map((r) => ({
              label: r.name,
              value: r.valuationPct,
              highlight: r.iso2 === data.analyzedIso2,
            }))}
            height={300}
          />

          {/* Einschraenkungen: einklappbar, aber standardmaessig offen (immer im DOM — Spec §5.4). */}
          <details open className="rounded-lg border border-slate-200 p-3 text-sm">
            <summary className="cursor-pointer font-medium text-slate-700">
              Einschraenkungen des Big-Mac-Index
            </summary>
            <ul className="mt-2 list-disc pl-4 space-y-1 text-slate-600">
              {EINSCHRAENKUNGEN.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </details>
        </div>
      )}
    </DrilldownShell>
  );
}
