import { ChartContainer } from "./ChartContainer";

export interface Bar { label: string; value: number; highlight?: boolean }

// Pure: horizontale Balken, Farbe NACH VORZEICHEN (+ gruen / - rot / 0 grau-blau);
// hervorgehobener Balken (analysiertes Land) bekommt einen Rahmen. Separat testbar.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildBarOption(bars: Bar[]): any {
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: 100, right: 40, top: 10, bottom: 20 },
    xAxis: { type: "value" },
    // yAxis category bei horizontalen Balken; Reihenfolge umkehren, damit erster Eintrag oben steht.
    yAxis: { type: "category", data: bars.map((b) => b.label).reverse() },
    series: [{
      type: "bar",
      data: bars.map((b) => ({
        value: b.value,
        itemStyle: {
          // Signal-Farbkonvention (Konzept §4): + gruen, - rot, 0 grau-blau.
          color: b.value > 0 ? "#16a34a" : b.value < 0 ? "#dc2626" : "#64748b",
          borderColor: b.highlight ? "#0f172a" : "transparent",
          borderWidth: b.highlight ? 2 : 0,
        },
      })).reverse(),
    }],
  };
}

export function BarChart({ bars, height }: { bars: Bar[]; height?: number }) {
  return <ChartContainer option={buildBarOption(bars)} height={height} />;
}
