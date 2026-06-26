import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { buildMapOption, bandColorFor, ChoroplethMap } from "./ChoroplethMap";
import type { MapPoint } from "./ChoroplethMap";

vi.mock("echarts-for-react", () => ({ default: () => null }));

// echarts-Mock: registerMap mocken, lazy-import (await import("echarts")) sofort antworten lassen
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

  it("visualMap ist PIECEWISE mit fixen, finanz-verankerten Baendern (gruen -> dunkelrot)", () => {
    const opt = buildMapOption(points);
    expect(opt.visualMap.type).toBe("piecewise");
    expect(opt.visualMap.pieces[0].color).toBe("#15803d");                    // unterstes Band gruen
    expect(opt.visualMap.pieces[opt.visualMap.pieces.length - 1].color).toBe("#991b1b"); // oberstes Band dunkelrot
  });

  it("Ausreisser verzerrt die Skala NICHT: Baender sind fix, HK 1100% saettigt oben", () => {
    // Regression Bug: max=Math.max(values) liess HK=1100 die Skala strecken -> alles <550 gruen.
    // Jetzt fixe Baender -> DEU guenstig gruen, USA/CHE teuer rot, HK gesaettigt dunkelrot.
    expect(bandColorFor(55)).toBe("#15803d");   // < 75 % guenstig
    expect(bandColorFor(198)).toBe("#ef4444");  // 150-200 % teuer
    expect(bandColorFor(211)).toBe("#991b1b");  // > 200 % sehr teuer (NICHT gruen!)
    expect(bandColorFor(1100)).toBe("#991b1b"); // Ausreisser saettigt im obersten Band
  });

  it("Baender sind lueckenlos (jeder Wert >= 0 trifft genau ein Band)", () => {
    for (const v of [0, 74.9, 75, 99.9, 100, 124.9, 125, 149.9, 150, 199.9, 200, 5000]) {
      expect(bandColorFor(v)).toBeTruthy();
    }
  });

  it("Karte erlaubt Pan/Zoom (roam) fuer scharfes Hineinzoomen", () => {
    expect(buildMapOption(points).series[0].roam).toBe(true);
  });

  it("buildMapOption mit leerer Liste liefert valide Option ohne Crash", () => {
    const opt = buildMapOption([]);
    expect(opt.series[0].type).toBe("map");
    expect(opt.series[0].data).toEqual([]);
    expect(opt.visualMap.type).toBe("piecewise");
    expect(opt.visualMap.pieces.length).toBeGreaterThan(0);
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
