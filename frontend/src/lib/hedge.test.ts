import { describe, it, expect } from "vitest";
import { hedgeSuggestions, NET_BETA_HEDGE_THRESHOLD } from "./hedge";
import type { ExposureDTO, KlumpenWarningDTO } from "../contract/portfolio";

const exp = (netBeta: number): ExposureDTO => ({
  grossPct: 142, netPct: 38, netBeta, annualizedVolPct: 14, volAsOf: "2026-06-20",
});
const techKlumpen: KlumpenWarningDTO = {
  dimension: "sector", name: "Technologie", pct: 0.41, limit: 0.40, message: "Technologie 41 % (Limit 40 %)",
};

describe("hedgeSuggestions", () => {
  it("net_beta ueber Schwelle => Index-Short/VIX-Vorschlag", () => {
    const out = hedgeSuggestions(exp(NET_BETA_HEDGE_THRESHOLD * 100 + 0.5), []);
    expect(out.some((h) => /Index-Short|VIX/i.test(h.text))).toBe(true);
  });
  it("Sektor-Klumpen => Teilverkauf/Sektor-Short-Vorschlag", () => {
    const out = hedgeSuggestions(exp(0), [techKlumpen]);
    expect(out.some((h) => /Technologie/.test(h.text) && /(Teilverkauf|Sektor-Short)/i.test(h.text))).toBe(true);
  });
  it("net_beta genau auf der Schwelle => KEIN net_beta-Vorschlag (strikt groesser)", () => {
    const out = hedgeSuggestions(exp(NET_BETA_HEDGE_THRESHOLD * 100), []);
    expect(out.some((h) => /Index-Short|VIX/i.test(h.text))).toBe(false);
  });
  it("net_beta stark NEGATIV (netto short) ueber Schwelle => Hedge-Vorschlag (Index-Long/Eindecken)", () => {
    // Ein stark net-short Buch ist genauso marktsensitiv (Rally-Risiko) -> symmetrische Schwelle.
    const out = hedgeSuggestions(exp(-(NET_BETA_HEDGE_THRESHOLD * 100) - 0.5), []);
    expect(out.some((h) => /Index-Long|Eindecken/i.test(h.text))).toBe(true);
    // KEIN Index-Short-Vorschlag bei net-short Buch (falsche Richtung).
    expect(out.some((h) => /Index-Short/i.test(h.text))).toBe(false);
  });
  it("net_beta genau auf der negativen Schwelle => KEIN Vorschlag (|net_beta| strikt groesser)", () => {
    const out = hedgeSuggestions(exp(-(NET_BETA_HEDGE_THRESHOLD * 100)), []);
    expect(out.some((h) => /Index-Long|Index-Short|VIX|Eindecken/i.test(h.text))).toBe(false);
  });
  it("net_beta null (UNAVAILABLE) => KEIN net_beta-Vorschlag (nicht aus unbekanntem Wert raten)", () => {
    const out = hedgeSuggestions({ ...exp(0), netBeta: null }, []);
    expect(out.some((h) => /Index-Short|Index-Long|VIX|Eindecken/i.test(h.text))).toBe(false);
  });
  it("alles im Rahmen, keine Klumpen => leere Liste", () => {
    expect(hedgeSuggestions(exp(0), [])).toEqual([]);
  });
});
