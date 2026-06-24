import { describe, it, expect } from "vitest";
import { formatConfidence, formatNumber, formatSigned } from "./format";

describe("formatConfidence", () => {
  it("rundet auf ganze Prozent mit Leerzeichen", () => {
    expect(formatConfidence(0.71)).toBe("71 %");
  });
  it("behandelt 0 und 1", () => {
    expect(formatConfidence(0)).toBe("0 %");
    expect(formatConfidence(1)).toBe("100 %");
  });
  it("clamped Werte außerhalb [0,1]", () => {
    expect(formatConfidence(-0.2)).toBe("0 %");
    expect(formatConfidence(1.5)).toBe("100 %");
  });
});

describe("formatNumber (deutsches Format)", () => {
  it("Dezimalkomma statt Punkt", () => {
    expect(formatNumber(30.5)).toBe("30,5");
    expect(formatNumber(22.4)).toBe("22,4");
    expect(formatNumber(6.1)).toBe("6,1");
  });
  it("Tausendertrenner als Punkt", () => {
    expect(formatNumber(2380)).toBe("2.380");
    expect(formatNumber(238000)).toBe("238.000");
  });
  it("Ganzzahl unter 1000 unveraendert", () => {
    expect(formatNumber(58)).toBe("58");
    expect(formatNumber(5)).toBe("5");
  });
  it("keine unnoetigen Nachkommanullen ohne fractionDigits", () => {
    expect(formatNumber(33)).toBe("33");
  });
  it("feste Nachkommastellen mit fractionDigits", () => {
    expect(formatNumber(33.27, 1)).toBe("33,3"); // Hebel
    expect(formatNumber(5, 1)).toBe("5,0");
  });
});

describe("formatSigned (Vorzeichen explizit)", () => {
  it("negativ mit ASCII-Minus + Komma", () => {
    expect(formatSigned(-3.1)).toBe("-3,1");
    expect(formatSigned(-5.4)).toBe("-5,4");
  });
  it("positiv mit Plus", () => {
    expect(formatSigned(1.2)).toBe("+1,2");
    expect(formatSigned(2.1)).toBe("+2,1");
  });
  it("null ohne Vorzeichen", () => {
    expect(formatSigned(0)).toBe("0");
  });
});
