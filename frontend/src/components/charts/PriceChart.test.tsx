import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { buildPriceOption, PriceChart } from "./PriceChart";

// ECharts in jsdom mocken (kein Canvas).
vi.mock("echarts-for-react", () => ({ default: () => null }));

const POINTS = [
  { date: "2026-01-01", close: 100 },
  { date: "2026-02-01", close: 108 },
  { date: "2026-03-01", close: 120 },
];

describe("buildPriceOption", () => {
  it("nutzt die Datumswerte als x-Achse und die Schlusskurse als Flaechen-Serie", () => {
    const opt = buildPriceOption(POINTS, "#0e9f6e");
    expect(opt.xAxis.data).toEqual(["2026-01-01", "2026-02-01", "2026-03-01"]);
    expect(opt.series[0].data).toEqual([100, 108, 120]);
    expect(opt.series[0].areaStyle).toBeDefined();          // Flaeche unter dem Kurs
    expect(opt.series[0].lineStyle.color).toBe("#0e9f6e");  // Richtungs-Farbe durchgereicht
  });
});

describe("PriceChart", () => {
  it("zeigt den letzten Kurs und die Periodenveraenderung mit Vorzeichen", () => {
    render(<PriceChart points={POINTS} currency="USD" />);
    expect(screen.getByText(/120/)).toBeInTheDocument();
    // (120-100)/100 = +20.0 %
    expect(screen.getByText(/\+20\.0 %/)).toBeInTheDocument();
  });

  it("leere Reihe -> kein Crash, dezenter Hinweis statt Chart", () => {
    render(<PriceChart points={[]} currency="USD" />);
    expect(screen.getByText(/Kein Kursverlauf/i)).toBeInTheDocument();
  });
});
