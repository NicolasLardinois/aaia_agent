import { lazy, Suspense, useEffect, useState } from "react";

const ReactECharts = lazy(() => import("echarts-for-react"));

export interface MapPoint { iso3: string; name: string; value: number; signal: "bullish" | "bearish" | "neutral" | null }

const MAP_NAME = "world";

// Pure: baut die Choropleth-option. visualMap kontinuierlich gruen (niedrig/guenstig) ->
// rot (hoch/ueberbewertet), passend zur Signal-Farbkonvention. Separat testbar.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildMapOption(points: MapPoint[], mapName: string = MAP_NAME): any {
  const values = points.map((p) => p.value);
  return {
    tooltip: { trigger: "item", formatter: (p: { name: string; value: number }) => `${p.name}: ${p.value ?? "—"}` },
    visualMap: {
      min: Math.min(...values, 0),
      max: Math.max(...values, 100),
      calculable: true,
      // gruen = niedrig (guenstig), rot = hoch (ueberbewertet) — Buffett-Logik.
      inRange: { color: ["#16a34a", "#fde047", "#dc2626"] },
    },
    series: [{
      type: "map",
      map: mapName,
      nameProperty: "name",
      data: points.map((p) => ({ name: p.name, value: p.value })),
    }],
  };
}

// Lazy-Registrierung der Welt-GeoJSON. Fehlt sie (Download im Umsetzungs-Schritt
// gescheitert), zeigt das Component einen GRAZILEN FALLBACK statt zu crashen.
export function ChoroplethMap({ points, height = 360 }: { points: MapPoint[]; height?: number }) {
  const [status, setStatus] = useState<"loading" | "ready" | "missing">("loading");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const echarts = await import("echarts");
        const res = await fetch("/world.geo.json");
        if (!res.ok) throw new Error("geojson missing");
        const geo = await res.json();
        echarts.registerMap(MAP_NAME, geo);
        if (!cancelled) setStatus("ready");
      } catch {
        if (!cancelled) setStatus("missing"); // grazile Degradierung
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (status === "missing") {
    return <div className="rounded border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">Karte nicht verfügbar — bitte Tabelle nutzen.</div>;
  }
  if (status === "loading") {
    return <div className="text-sm text-slate-500">Karte lädt …</div>;
  }
  return (
    <Suspense fallback={<div className="text-sm text-slate-500">Karte lädt …</div>}>
      <ReactECharts option={buildMapOption(points)} style={{ height }} notMerge lazyUpdate />
    </Suspense>
  );
}
