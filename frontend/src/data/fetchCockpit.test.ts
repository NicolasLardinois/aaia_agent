import { describe, it, expect, vi } from "vitest";
import { fetchBuffett } from "./fetchCockpit";

// Echte /api/cockpit-Antwort (Auszug): Uebersichtsfelder + detail.buffett (snake_case).
const cockpitPayload = {
  regime: "Aufschwung", regime_confidence: 0.71, macro_status: "available",
  domains: [], sources_active: 5, sources_total: 5,
  detail: {
    buffett: {
      global_median: 95.4,
      countries: [
        { iso3: "USA", name: "United States", ratio_pct: 198.0, signal: "bearish", z_score: 2.1, year: null, history: [] },
        {
          iso3: "CHE", name: "Switzerland", ratio_pct: 211.0, signal: "neutral", z_score: 0.6, year: 2024,
          history: [{ year: 2023, ratio_pct: 205.0 }, { year: 2024, ratio_pct: 211.0 }],
        },
      ],
    },
  },
};

function fakeFetch(status: number, body?: unknown): typeof fetch {
  return vi.fn(async () => ({
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  })) as unknown as typeof fetch;
}

describe("fetchBuffett", () => {
  it("mappt /api/cockpit detail.buffett auf BuffettView (echt, isDemo:false)", async () => {
    const view = await fetchBuffett({ base: "http://x", fetchFn: fakeFetch(200, cockpitPayload), token: "t" });

    expect(view.isDemo).toBe(false);                 // echte Daten -> DemoBadge verschwindet
    expect(view.globalMedian).toBe(95.4);
    expect(view.analyzedIso3).toBe("USA");           // hervorgehobenes Land (Default USA)
    expect(view.sourcesActive).toBe(5);
    expect(view.sourcesTotal).toBe(5);

    const che = view.countries.find((c) => c.iso3 === "CHE")!;
    expect(che.name).toBe("Switzerland");            // Weltbank-Klarname durchgereicht
    expect(che.ratioPct).toBe(211.0);                // snake_case ratio_pct -> camelCase ratioPct
    expect(che.signal).toBe("neutral");
    expect(che.zScore).toBe(0.6);
    expect(che.year).toBe(2024);
    expect(che.history).toEqual([
      { year: 2023, ratioPct: 205.0 },
      { year: 2024, ratioPct: 211.0 },
    ]);
  });

  it("haengt den Authorization-Header an, wenn ein Token gegeben ist", async () => {
    let seenHeaders: Record<string, string> | undefined;
    const fetchFn = (async (_url: string, init?: { headers?: Record<string, string> }) => {
      seenHeaders = init?.headers;
      return { status: 200, ok: true, json: async () => cockpitPayload };
    }) as unknown as typeof fetch;
    await fetchBuffett({ base: "http://x", fetchFn, token: "geheim" });
    expect(seenHeaders).toMatchObject({ Authorization: "Bearer geheim" });
  });

  it("wirft bei 204 (noch kein Lauf) einen klaren Fehler", async () => {
    await expect(
      fetchBuffett({ base: "http://x", fetchFn: fakeFetch(204) }),
    ).rejects.toThrow();
  });
});
