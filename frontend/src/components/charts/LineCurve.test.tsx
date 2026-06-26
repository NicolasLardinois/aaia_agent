import { describe, it, expect, vi } from "vitest";

// ECharts in jsdom mocken (kein Canvas).
vi.mock("echarts-for-react", () => ({ default: () => null }));

import { buildLineOption } from "./LineCurve";

describe("buildLineOption", () => {
  it("baut x-Achsen-Kategorien und eine Serie je LineSeries", () => {
    const opt = buildLineOption([
      { name: "Rendite", points: [{ x: "3M", y: 2 }, { x: "2J", y: 3 }] },
    ]);
    expect(opt.xAxis.data).toEqual(["3M", "2J"]);
    expect(opt.series).toHaveLength(1);
    expect(opt.series[0]).toMatchObject({ name: "Rendite", type: "line", data: [2, 3] });
  });

  it("ohne Optionen: keine Flaeche unter der Linie (Default schlank)", () => {
    const opt = buildLineOption([{ name: "x", points: [{ x: "a", y: 1 }] }]);
    expect(opt.series[0].areaStyle).toBeUndefined();
  });

  it("area=true: Flaeche unter der Linie (areaStyle gesetzt)", () => {
    const opt = buildLineOption([{ name: "x", points: [{ x: "a", y: 1 }] }], { area: true });
    expect(opt.series[0].areaStyle).toBeDefined();
  });

  it("color: faerbt Linie und Punkte einheitlich", () => {
    const opt = buildLineOption([{ name: "x", points: [{ x: "a", y: 1 }] }], { color: "#4f5bd5" });
    expect(opt.series[0].itemStyle.color).toBe("#4f5bd5");
    expect(opt.series[0].lineStyle.color).toBe("#4f5bd5");
  });
});
