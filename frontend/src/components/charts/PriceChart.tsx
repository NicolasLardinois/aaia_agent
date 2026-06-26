import { ChartContainer } from "./ChartContainer";
import { CHART, themedGrid, themedAxis, themedTooltip, areaGradient } from "../../lib/chartTheme";
import { periodChange, type PricePoint } from "../../lib/priceSeries";

// Kurschart (Mangel #6: "Kurschart im Deep-Dive"). Flaechen-Linie ueber die Zeit, gefaerbt
// nach der Periodenrichtung (gruen rauf / rot runter / grau seitwaerts — Finanzkonvention).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildPriceOption(points: PricePoint[], color: string): any {
  return {
    tooltip: themedTooltip("axis"),
    grid: themedGrid(),
    xAxis: themedAxis("category", {
      data: points.map((p) => p.date),
      boundaryGap: false,
      // Bei vielen Tagespunkten nicht jeden Tag beschriften (Achse bleibt lesbar).
      axisLabel: { color: CHART.axisLabel, fontSize: 11, hideOverlap: true },
    }),
    yAxis: themedAxis("value", { scale: true }),  // scale: nicht bei 0 beginnen (Kurse schwanken eng)
    series: [{
      name: "Schlusskurs",
      type: "line",
      smooth: true,
      showSymbol: false,
      data: points.map((p) => p.close),
      lineStyle: { width: 2.5, color },
      itemStyle: { color },
      areaStyle: { color: areaGradient(color) },
    }],
  };
}

const DIR_COLOR: Record<"up" | "down" | "flat", string> = {
  up: CHART.bull, down: CHART.bear, flat: CHART.neutral,
};

// Kursverlauf-Panel: Kopf (letzter Kurs + Periodenveraenderung mit Vorzeichen) + Flaechenchart.
// Leere Reihe -> dezenter Hinweis (kein Crash, UNAVAILABLE != 0).
export function PriceChart({ points, currency, height = 300 }: { points: PricePoint[]; currency: string; height?: number }) {
  if (points.length === 0) {
    return <p className="text-sm text-muted">Kein Kursverlauf verfügbar.</p>;
  }
  const change = periodChange(points);
  const color = DIR_COLOR[change.direction];
  const last = points[points.length - 1].close;
  const sign = change.pct >= 0 ? "+" : "";
  const toneClass = change.direction === "up" ? "text-bull" : change.direction === "down" ? "text-bear" : "text-muted";

  return (
    <div>
      <div className="flex items-baseline gap-3">
        <span className="font-display text-2xl font-bold tabular-nums">
          {last.toLocaleString("de-CH", { maximumFractionDigits: 2 })} {currency}
        </span>
        <span className={`text-sm font-semibold tabular-nums ${toneClass}`}>
          {sign}{change.pct.toFixed(1)} %
          <span className="ml-1 font-normal text-muted">({points.length} Tage)</span>
        </span>
      </div>
      <div className="mt-2">
        <ChartContainer option={buildPriceOption(points, color)} height={height} />
      </div>
    </div>
  );
}
