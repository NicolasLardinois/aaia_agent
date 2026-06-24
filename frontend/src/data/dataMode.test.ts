import { describe, it, expect } from "vitest";
import { resolveDataMode } from "./dataMode";

describe("resolveDataMode", () => {
  it("erkennt explizite Modi", () => {
    expect(resolveDataMode("demo")).toBe("demo");
    expect(resolveDataMode("real")).toBe("real");
    expect(resolveDataMode("auto")).toBe("auto");
  });
  it("faellt bei leer/unbekannt auf auto zurueck", () => {
    expect(resolveDataMode(undefined)).toBe("auto");
    expect(resolveDataMode("")).toBe("auto");
    expect(resolveDataMode("quatsch")).toBe("auto");
  });
});
