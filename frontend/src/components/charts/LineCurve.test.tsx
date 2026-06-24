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
});
