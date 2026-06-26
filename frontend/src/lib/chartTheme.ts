// Gemeinsames ECharts-Theme (Mangel #6: Charts sahen "nackt"/haesslich aus, weil die
// Builder rohe ECharts-Defaults nutzten). ECharts rendert auf Canvas und kann KEINE
// CSS-Variablen lesen -> die Token-Farben hier als feste Hex-Werte gespiegelt (siehe
// index.css). Bewusst THEME-NEUTRAL gewaehlt: Label-/Linien-Farben mit genug Kontrast
// auf hellem (Papier) UND dunklem (Navy) Deck — ein Chart wird bei Theme-Wechsel nicht
// neu gebaut, also muessen die Farben in beiden Decks lesbar sein.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type EChartsOption = any;

export const CHART = {
  brand: "#4f5bd5",     // Kobalt-Indigo (--brand, Tag-Deck) — interaktiv/Marke
  bull: "#0e9f6e",      // Signal bullish (--bull)
  bear: "#e5484d",      // Signal bearish (--bear)
  neutral: "#8a93a3",   // Signal neutral (--neutral)
  axisLabel: "#8a93a3", // gedaempfte Achsenbeschriftung (auf beiden Decks lesbar)
  axisLine: "rgba(138,147,163,0.35)",  // Achsenlinie dezent
  splitLine: "rgba(138,147,163,0.18)", // Gitterlinien sehr dezent
} as const;

// Gitter: containLabel sorgt dafuer, dass Achsenbeschriftungen nicht abgeschnitten werden.
export function themedGrid(over: Partial<Record<string, unknown>> = {}): EChartsOption {
  return { left: 8, right: 16, top: 16, bottom: 8, containLabel: true, ...over };
}

// Achse mit gedaempften Labels + dezenten Splitlines. type = "value" | "category".
export function themedAxis(type: "value" | "category", over: EChartsOption = {}): EChartsOption {
  return {
    type,
    axisLabel: { color: CHART.axisLabel, fontSize: 11 },
    axisLine: { lineStyle: { color: CHART.axisLine } },
    axisTick: { show: false },
    // Wertachse bekommt horizontale Gitterlinien; Kategorieachse nicht (sonst Liniensalat).
    splitLine: type === "value"
      ? { show: true, lineStyle: { color: CHART.splitLine } }
      : { show: false },
    ...over,
  };
}

export function themedTooltip(trigger: "axis" | "item"): EChartsOption {
  return {
    trigger,
    axisPointer: { type: trigger === "axis" ? "line" : "shadow" },
    backgroundColor: "rgba(19,27,43,0.96)",  // dunkler Tooltip (lesbar auf beiden Decks)
    borderWidth: 0,
    textStyle: { color: "#e7ecf5", fontSize: 12 },
  };
}

// Flaeche unter einer Linie: oben in der Linienfarbe (halbtransparent), unten auslaufend
// nach transparent — gibt Kurven optische Tiefe, ohne den Hintergrund zu erschlagen.
export function areaGradient(colorHex: string): EChartsOption {
  return {
    type: "linear",
    x: 0, y: 0, x2: 0, y2: 1,
    colorStops: [
      { offset: 0, color: hexWithAlpha(colorHex, 0.28) },
      { offset: 1, color: hexWithAlpha(colorHex, 0.0) },
    ],
  };
}

// #rrggbb + Alpha (0..1) -> rgba(). Bewusst klein gehalten (nur 6-stellige Hex erwartet).
function hexWithAlpha(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
