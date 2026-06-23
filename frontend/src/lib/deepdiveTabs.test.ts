import { describe, it, expect } from "vitest";
import { tabsFor } from "./deepdiveTabs";
import type { DeepDiveView } from "../contract/deepdive";

// minimaler View-Bauer (nur Felder, die tabsFor liest)
function v(partial: Partial<DeepDiveView>): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 1, sourcesTotal: 1, failed: [],
    ticker: "X", name: "X", underlying: "equity", wrapper: "single",
    price: 1, currency: "USD", market: "M", found: true,
    long: { verdict: "HOLD", confidence: 0.5, rationale: "" },
    short: { verdict: "NONE", confidence: 0.2, rationale: "" },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    ...partial,
  } as DeepDiveView;
}
const keys = (view: DeepDiveView) => tabsFor(view).map((t) => t.key);

describe("tabsFor", () => {
  it("equity: Bewertung/Qualität/Signale + Backtest, kein Futures", () => {
    expect(keys(v({ underlying: "equity", wrapper: "single" })))
      .toEqual(["valuation", "quality", "signals", "backtest"]);
  });
  it("bond: bond-Tab + Backtest", () => {
    expect(keys(v({ underlying: "bond", wrapper: "single" })))
      .toEqual(["bond", "backtest"]);
  });
  it("equity_index: index-Tab + Backtest", () => {
    expect(keys(v({ underlying: "equity_index", wrapper: "fund" })))
      .toEqual(["index", "backtest"]);
  });
  it("commodity: commodity-Tab + Backtest", () => {
    expect(keys(v({ underlying: "commodity", wrapper: "single" })))
      .toEqual(["commodity", "backtest"]);
  });
  it("precious_metal: commodity-Tab + Backtest", () => {
    expect(keys(v({ underlying: "precious_metal", wrapper: "physical_etc" })))
      .toEqual(["commodity", "backtest"]);
  });
  it("Futures-Tab nur bei wrapper=future (vor Backtest)", () => {
    expect(keys(v({ underlying: "commodity", wrapper: "future" })))
      .toEqual(["commodity", "futures", "backtest"]);
  });
  it("Futures-Tab wrapper-agnostisch: equity+wrapper:future => Futures-Tab vor Backtest", () => {
    // Futures-Tab erscheint unabhäng vom underlying — wrapper:future ist das Kriterium
    expect(keys(v({ underlying: "equity", wrapper: "future" })))
      .toEqual(["valuation", "quality", "signals", "futures", "backtest"]);
  });
  it("nicht gefunden => keine Tabs", () => {
    expect(keys(v({ found: false }))).toEqual([]);
  });
});
