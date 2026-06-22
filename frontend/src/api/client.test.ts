import { describe, it, expect, vi } from "vitest";
import { getCockpit, startRun } from "./client";

const overview = {
  regime: "Aufschwung", regime_confidence: 0.71, macro_status: "available",
  domains: [], sources_active: 5, sources_total: 5,
};

function fakeFetch(status: number, body?: unknown): typeof fetch {
  return vi.fn(async () => ({
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  })) as unknown as typeof fetch;
}

describe("getCockpit", () => {
  it("gibt die Uebersicht bei 200", async () => {
    const res = await getCockpit("http://x", fakeFetch(200, overview));
    expect(res).toEqual(overview);
  });
  it("gibt null bei 204", async () => {
    const res = await getCockpit("http://x", fakeFetch(204));
    expect(res).toBeNull();
  });
  it("wirft bei Fehlerstatus", async () => {
    await expect(getCockpit("http://x", fakeFetch(500))).rejects.toThrow();
  });
});

describe("startRun", () => {
  it("gibt die run_id bei 202", async () => {
    const id = await startRun("http://x", fakeFetch(202, { run_id: "abc" }));
    expect(id).toBe("abc");
  });

  it("wirft bei Fehlerstatus", async () => {
    await expect(startRun("http://x", fakeFetch(500))).rejects.toThrow();
  });
});
