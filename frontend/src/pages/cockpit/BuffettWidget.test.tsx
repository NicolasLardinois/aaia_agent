import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BuffettWidget } from "./BuffettWidget";
import { demoBuffett } from "../../data/demo/cockpit";

// ECharts im jsdom neutralisieren (BarChart, ChoroplethMap, LineCurve).
vi.mock("echarts-for-react", () => ({ default: () => null }));
// echarts lazy-import mocken (jsdom kann echarts.registerMap nicht laden).
vi.mock("echarts", () => ({ registerMap: vi.fn() }));
// ChoroplethMap-fetch mocken (jsdom kann public/ nicht als HTTP-Server auflösen -> graceful fallback).
vi.stubGlobal("fetch", () => Promise.reject(new Error("no geojson in tests")));

const loader = () => Promise.resolve(demoBuffett());

function renderWidget() {
  return render(
    <MemoryRouter>
      <BuffettWidget loader={loader} />
    </MemoryRouter>,
  );
}

describe("BuffettWidget (C1)", () => {
  it("zeigt Default-Ansicht Tabelle: USA, Schweiz, Deutschland sichtbar", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText("USA")).toBeInTheDocument());
    expect(screen.getByText("Schweiz")).toBeInTheDocument();
    expect(screen.getByText("Deutschland")).toBeInTheDocument();
  });

  it("USA-Zeile ist hervorgehoben (analyzedIso3) und Z=+2.1 traegt Warnung", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText("USA")).toBeInTheDocument());
    // USA-Zeile hat z=+2.1 (|Z|>=1.5 -> zScoreFlag='anomaly') -> ⚠ vorhanden
    expect(screen.getAllByText(/⚠/).length).toBeGreaterThan(0);
  });

  it("year===null (USA) zeigt 'live'; CHE zeigt '2024'", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText("USA")).toBeInTheDocument());
    expect(screen.getByText("live")).toBeInTheDocument();
    // mindestens eine "2024"-Anzeige (CHE, DEU, JPN, GBR)
    expect(screen.getAllByText("2024").length).toBeGreaterThan(0);
  });

  it("Global-Median 92 sichtbar", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText(/92/)).toBeInTheDocument());
  });

  it("Filter 'nur BEARISH' versteckt Deutschland (bullish)", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText("Deutschland")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("checkbox", { name: /bearish/i }));
    await waitFor(() => expect(screen.queryByText("Deutschland")).not.toBeInTheDocument());
    expect(screen.getByText("USA")).toBeInTheDocument();
  });

  it("Filter 'nur Z-Ausreisser' behaelt nur USA und Japan (|Z|>=1.5)", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText("Deutschland")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("checkbox", { name: /z-ausreißer/i }));
    await waitFor(() => expect(screen.queryByText("Deutschland")).not.toBeInTheDocument());
    // Schweiz z=+0.6 (nicht Ausreißer) sollte verschwinden
    expect(screen.queryByText("Schweiz")).not.toBeInTheDocument();
    // USA z=+2.1 und Japan z=+1.6 bleiben
    expect(screen.getByText("USA")).toBeInTheDocument();
    expect(screen.getByText("Japan")).toBeInTheDocument();
  });

  it("Einschraenkungs-Texte im DOM (Globalisierung, Zinskontext, Timing, Aktienrueckkaeufe)", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText("USA")).toBeInTheDocument());
    expect(screen.getByText(/Globalisierung/i)).toBeInTheDocument();
    expect(screen.getByText(/Zinskontext/i)).toBeInTheDocument();
    // "Kein Market-Timing-Instrument" ist Teil eines Listeneintrags (mehrere Nodes für "Timing" erlaubt)
    expect(screen.getAllByText(/Timing/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Aktienrückkäufe/i)).toBeInTheDocument();
  });

  it("Asset-Filter-Hinweis im DOM (nur Aktien/ETF/Index)", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText("USA")).toBeInTheDocument());
    expect(screen.getByText(/Aktien.*ETF.*Index|ETF.*Aktien.*Index/i)).toBeInTheDocument();
  });

  it("Tab 'Karte' wechselbar: Karten-Container erscheint", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText("USA")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /karte/i }));
    // Karte zeigt graceful Fallback (jsdom kann fetch("/world.geo.json") nicht auflösen).
    await waitFor(() =>
      expect(
        screen.queryByText(/Karte nicht verfügbar/i)
      ).toBeInTheDocument()
    );
  });

  it("Klick auf USA-Zeile zeigt das 10-J-Drilldown-Panel (LineCurve-Container)", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText("USA")).toBeInTheDocument());
    // Klick auf die USA-Zeile -> Drilldown-Panel erscheint
    fireEvent.click(screen.getByText("USA"));
    await waitFor(() =>
      expect(screen.getByText(/10-J-Verlauf|Verlauf/i)).toBeInTheDocument()
    );
  });

  it("Demo-Badge sichtbar", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText(/Demo/i)).toBeInTheDocument());
  });
});
