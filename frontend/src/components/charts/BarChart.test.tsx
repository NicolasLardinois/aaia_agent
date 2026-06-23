import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { buildBarOption, BarChart } from "./BarChart";
import type { Bar } from "./BarChart";

vi.mock("echarts-for-react", () => ({ default: () => null }));

describe("buildBarOption", () => {
  const bars: Bar[] = [
    { label: "CH",  value: 38 },
    { label: "JP",  value: -41, highlight: true },
    { label: "USA", value: 0 },
  ];

  it("yAxis.type === 'category'; xAxis.type === 'value' (horizontale Balken)", () => {
    const opt = buildBarOption(bars);
    expect(opt.yAxis.type).toBe("category");
    expect(opt.xAxis.type).toBe("value");
  });

  it("Reihenfolge umgekehrt: data[0] ist letzter bar (USA)", () => {
    const opt = buildBarOption(bars);
    // reverse() -> USA (0) steht an data[0], JP (-41) an data[1], CH (+38) an data[2]
    expect(opt.series[0].data[0].value).toBe(0);
    expect(opt.series[0].data[1].value).toBe(-41);
    expect(opt.series[0].data[2].value).toBe(38);
  });

  it("negativer Wert -> rot (#dc2626), highlight -> borderWidth 2", () => {
    const opt = buildBarOption(bars);
    // JP (value -41, highlight:true) -> data[1]
    const jpBar = opt.series[0].data[1];
    expect(jpBar.itemStyle.color).toBe("#dc2626");
    expect(jpBar.itemStyle.borderWidth).toBe(2);
  });

  it("positiver Wert -> gruen (#16a34a)", () => {
    const opt = buildBarOption(bars);
    // CH (value +38) -> data[2]
    const chBar = opt.series[0].data[2];
    expect(chBar.itemStyle.color).toBe("#16a34a");
  });

  it("Wert 0 -> grau-blau (#64748b)", () => {
    const opt = buildBarOption(bars);
    // USA (value 0) -> data[0]
    const usaBar = opt.series[0].data[0];
    expect(usaBar.itemStyle.color).toBe("#64748b");
  });

  it("kein highlight -> borderWidth 0", () => {
    const opt = buildBarOption(bars);
    // CH hat kein highlight -> data[2]
    const chBar = opt.series[0].data[2];
    expect(chBar.itemStyle.borderWidth).toBe(0);
  });
});

describe("BarChart Komponente", () => {
  it("rendert ohne Crash (ChartContainer mit echarts-for-react gemockt)", () => {
    const bars: Bar[] = [{ label: "Test", value: 10 }];
    // Kein Fehler beim Rendern
    expect(() => render(<BarChart bars={bars} />)).not.toThrow();
  });
});
