import { ChartContainer } from "./ChartContainer";

export interface LinePoint { x: string; y: number; }
export interface LineSeries { name: string; points: LinePoint[]; }

// Pure: baut die ECharts-option aus den Serien (separat testbar, ohne Canvas).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildLineOption(series: LineSeries[]): any {
  const categories = series[0]?.points.map((p) => p.x) ?? [];
  return {
    tooltip: { trigger: "axis" },
    legend: { show: series.length > 1 },
    xAxis: { type: "category", data: categories },
    yAxis: { type: "value" },
    series: series.map((s) => ({ name: s.name, type: "line", smooth: true, data: s.points.map((p) => p.y) })),
  };
}

export function LineCurve({ series, height }: { series: LineSeries[]; height?: number }) {
  return <ChartContainer option={buildLineOption(series)} height={height} />;
}
