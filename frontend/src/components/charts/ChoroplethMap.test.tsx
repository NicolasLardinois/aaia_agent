import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { buildMapOption, ChoroplethMap } from "./ChoroplethMap";
import type { MapPoint } from "./ChoroplethMap";

vi.mock("echarts-for-react", () => ({ default: () => null }));

// echarts-Mock: echarts.registerMap + echarts lazy-import simulieren
vi.mock("echarts", () => ({
  registerMap: vi.fn(),
}));

// fetch-Mock: GeoJSON-Download schlaegt fehl -> Fallback-Text soll erscheinen
beforeAll(() => {
  // globalThis statt global (TypeScript/Browser-kompatibel)
  globalThis.fetch = vi.fn(() =>
    Promise.resolve({ ok: false, status: 404 } as Response)
  );
});

const points: MapPoint[] = [
  { iso3: "USA", name: "USA",     value: 198, signal: "bearish" },
  { iso3: "CHE", name: "Schweiz", value: 211, signal: "bearish" },
  { iso3: "DEU", name: "Deutschland", value: 55, signal: "bullish" },
];

describe("buildMapOption", () => {
  it("series[0].type === 'map'", () => {
    const opt = buildMapOption(points);
    expect(opt.series[0].type).toBe("map");
  });

  it("series[0].map === 'world'", () => {
    const opt = buildMapOption(points);
    expect(opt.series[0].map).toBe("world");
  });

  it("series[0].data hat einen Eintrag je point mit {name, value}", () => {
    const opt = buildMapOption(points);
    expect(opt.series[0].data).toHaveLength(points.length);
    expect(opt.series[0].data[0]).toEqual({ name: "USA", value: 198 });
  });

  it("visualMap.inRange.color beginnt gruen, endet rot (Buffett-Farbskala)", () => {
    const opt = buildMapOption(points);
    const colors = opt.visualMap.inRange.color;
    expect(colors[0]).toBe("#16a34a");
    expect(colors[colors.length - 1]).toBe("#dc2626");
  });
});

describe("ChoroplethMap Komponente — Fallback bei fehlendem GeoJSON", () => {
  it("zeigt 'Karte nicht verfuegbar'-Fallback wenn fetch schlaegt fehl", async () => {
    render(<ChoroplethMap points={points} />);
    await waitFor(() => {
      expect(screen.getByText(/Karte nicht verfügbar/i)).toBeInTheDocument();
    });
  });
});
