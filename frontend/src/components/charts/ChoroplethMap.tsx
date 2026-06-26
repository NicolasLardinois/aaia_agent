import { lazy, Suspense, useEffect, useState } from "react";
import { CHART } from "../../lib/chartTheme";

const ReactECharts = lazy(() => import("echarts-for-react"));

export interface MapPoint { iso3: string; name: string; value: number; signal: "bullish" | "bearish" | "neutral" | null }

const MAP_NAME = "world";

// Ein Farbband der Buffett-Skala (ECharts-piecewise-Form: gte/lt sind die Grenzen).
export interface MapPiece { gte?: number; lt?: number; color: string; label: string }

// Finanz-verankerte FIXE Baender fuer den Buffett-Indikator (Boersenwert/BIP in %).
// WARUM fix statt datengetrieben: vorher max = Math.max(alle Werte) -> ein Ausreisser wie
// Hongkong (~1100 %, weil dort viele China-/Multi-Konzerne gelistet sind, deren Gewinne NICHT
// aus dem HK-BIP stammen) streckte die Gruen->Rot-Skala ueber 0..1100 und faerbte alles unter
// ~550 gruen — selbst USA (198 %) und Schweiz (211 %), die klar teuer sind. Mit fixen Baendern
// saettigt ein Ausreisser einfach im obersten Band (Dunkelrot), ohne die anderen Laender zu
// verzerren. Bandgrenzen nach Buffett-Konvention: ~100 % = fair (Marktkap ~ BIP), >150 % teuer,
// >200 % sehr teuer, <75 % guenstig. Lueckenlos: jeder Wert >= 0 trifft genau ein Band.
export const DEFAULT_BUFFETT_PIECES: MapPiece[] = [
  {            lt: 75,  color: "#15803d", label: "< 75 % · günstig" },
  { gte: 75,   lt: 100, color: "#4ade80", label: "75–100 %" },
  { gte: 100,  lt: 125, color: "#fde047", label: "100–125 % · fair" },
  { gte: 125,  lt: 150, color: "#fb923c", label: "125–150 %" },
  { gte: 150,  lt: 200, color: "#ef4444", label: "150–200 % · teuer" },
  { gte: 200,           color: "#991b1b", label: "> 200 % · sehr teuer" },
];

// Pure: Farbe fuer einen Wert nach den Baendern (separat testbar). Erster Treffer gewinnt.
export function bandColorFor(value: number, pieces: MapPiece[] = DEFAULT_BUFFETT_PIECES): string {
  for (const p of pieces) {
    if ((p.gte === undefined || value >= p.gte) && (p.lt === undefined || value < p.lt)) return p.color;
  }
  return pieces[pieces.length - 1].color; // Fallback (sollte bei lueckenlosen Baendern nie greifen)
}

// Pure: baut die Choropleth-option. PIECEWISE-visualMap mit fixen Baendern -> ausreisser-robust.
// roam:true erlaubt Pan/Zoom direkt in der Karte; zusammen mit dem SVG-Renderer (Komponente)
// bleibt sie beim Hineinzoomen scharf (Canvas wuerde rastern). Separat testbar.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildMapOption(points: MapPoint[], mapName: string = MAP_NAME, pieces: MapPiece[] = DEFAULT_BUFFETT_PIECES): any {
  return {
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(19,27,43,0.96)",
      borderWidth: 0,
      textStyle: { color: "#e7ecf5", fontSize: 12 },
      formatter: (p: { name: string; value: number }) =>
        `${p.name}: ${p.value != null && !Number.isNaN(p.value) ? p.value + " %" : "—"}`,
    },
    visualMap: {
      type: "piecewise",
      // Kopie der Baender (gte/lt/color/label sind genau die ECharts-piecewise-Felder).
      pieces: pieces.map((p) => ({ ...p })),
      orient: "horizontal",
      left: "center",
      bottom: 6,
      itemWidth: 16,
      itemHeight: 12,
      textStyle: { color: CHART.axisLabel, fontSize: 11 },
    },
    series: [{
      type: "map",
      map: mapName,
      nameProperty: "name",
      roam: true,                          // Pan + Mausrad-Zoom direkt in der Karte
      scaleLimit: { min: 1, max: 8 },      // sinnvolle Zoomgrenzen
      itemStyle: { borderColor: "rgba(138,147,163,0.45)", borderWidth: 0.4 },
      emphasis: { label: { show: false }, itemStyle: { areaColor: CHART.brand } },
      select: { disabled: true },
      data: points.map((p) => ({ name: p.name, value: p.value })),
    }],
  };
}

// Lazy-Registrierung der Welt-GeoJSON. Fehlt sie (Download im Umsetzungs-Schritt
// gescheitert), zeigt das Component einen GRAZILEN FALLBACK statt zu crashen.
export function ChoroplethMap({ points, height = 520 }: { points: MapPoint[]; height?: number }) {
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
    return <div className="rounded border border-dashed border-line p-6 text-center text-sm text-muted">Karte nicht verfügbar — bitte Tabelle nutzen.</div>;
  }
  if (status === "loading") {
    return <div className="text-sm text-muted">Karte lädt …</div>;
  }
  return (
    <Suspense fallback={<div className="text-sm text-muted">Karte lädt …</div>}>
      {/* SVG-Renderer: bleibt beim Hineinzoomen scharf (Vektoren statt Canvas-Raster). */}
      <ReactECharts
        option={buildMapOption(points)}
        style={{ height }}
        opts={{ renderer: "svg" }}
        notMerge
        lazyUpdate
      />
    </Suspense>
  );
}
