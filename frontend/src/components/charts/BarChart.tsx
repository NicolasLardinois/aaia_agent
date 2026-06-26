import { ChartContainer } from "./ChartContainer";
import { themedGrid, themedAxis, themedTooltip } from "../../lib/chartTheme";

export interface Bar { label: string; value: number; highlight?: boolean }

// Pure: horizontale Balken, Farbe NACH VORZEICHEN (+ gruen / - rot / 0 grau-blau);
// hervorgehobener Balken (analysiertes Land) bekommt einen Rahmen. Separat testbar.
// Achsen/Tooltip aus dem gemeinsamen Chart-Theme (Mangel #6); die Balken-Farben bleiben
// die etablierte Signal-Konvention (bewusst NICHT die Theme-Palette, sondern +/-/0).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildBarOption(bars: Bar[]): any {
  return {
    tooltip: themedTooltip("axis"),
    // Mehr Platz links fuer die (laengeren) Kategorie-Labels.
    grid: themedGrid({ left: 100, right: 24 }),
    xAxis: themedAxis("value"),
    // yAxis category bei horizontalen Balken; Reihenfolge umkehren, damit erster Eintrag oben steht.
    yAxis: themedAxis("category", { data: bars.map((b) => b.label).reverse() }),
    series: [{
      type: "bar",
      barWidth: "55%",
      itemStyle: { borderRadius: [0, 4, 4, 0] },  // abgerundete Balkenenden — weicher Look
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
