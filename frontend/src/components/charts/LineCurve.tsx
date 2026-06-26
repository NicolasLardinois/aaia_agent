import { ChartContainer } from "./ChartContainer";
import { CHART, themedGrid, themedAxis, themedTooltip, areaGradient } from "../../lib/chartTheme";

export interface LinePoint { x: string; y: number; }
export interface LineSeries { name: string; points: LinePoint[]; }
export interface LineOptions { area?: boolean; color?: string }

// Pure: baut die ECharts-option aus den Serien (separat testbar, ohne Canvas).
// Nutzt jetzt das gemeinsame Chart-Theme (Mangel #6) — gedaempfte Achsen, dezentes Gitter,
// glatte Linie ohne Punkt-Symbole. Optional: Flaeche unter der Linie + einheitliche Farbe.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildLineOption(series: LineSeries[], opts: LineOptions = {}): any {
  const categories = series[0]?.points.map((p) => p.x) ?? [];
  const color = opts.color ?? CHART.brand;
  return {
    tooltip: themedTooltip("axis"),
    legend: { show: series.length > 1, textStyle: { color: CHART.axisLabel } },
    grid: themedGrid(),
    xAxis: themedAxis("category", { data: categories, boundaryGap: false }),
    yAxis: themedAxis("value"),
    series: series.map((s) => ({
      name: s.name,
      type: "line",
      smooth: true,
      showSymbol: false,
      data: s.points.map((p) => p.y),
      // Default-Farbe = Marke (statt ECharts-Default-Blau); pro Serie ueberschreibbar.
      lineStyle: { width: 2.5, color },
      itemStyle: { color },
      // Flaeche nur bei area=true (Default schlank). Gradient in der Linienfarbe.
      ...(opts.area ? { areaStyle: { color: areaGradient(color) } } : {}),
    })),
  };
}

export function LineCurve({ series, height, area, color }: { series: LineSeries[]; height?: number } & LineOptions) {
  return <ChartContainer option={buildLineOption(series, { area, color })} height={height} />;
}
