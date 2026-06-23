import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { YieldCurveDrilldown } from "./YieldCurveDrilldown";
import { demoYieldCurve } from "../../data/demo/cockpit";
import type { YieldCurveView } from "../../contract/cockpit";

// ECharts im jsdom neutralisieren
vi.mock("echarts-for-react", () => ({ default: () => null }));

const loader = () => Promise.resolve(demoYieldCurve());

function renderPage(customLoader?: () => Promise<YieldCurveView>) {
  return render(
    <MemoryRouter>
      <YieldCurveDrilldown loader={customLoader ?? loader} />
    </MemoryRouter>,
  );
}

describe("YieldCurveDrilldown", () => {
  it("zeigt die drei Spread-Paare mit Werten", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("10J-2J")).toBeInTheDocument());
    expect(screen.getByText("10J-3M")).toBeInTheDocument();
    expect(screen.getByText("30J-10J")).toBeInTheDocument();
    // Werte (positiv mit Vorzeichen)
    expect(screen.getByText(/\+0\.4/)).toBeInTheDocument();
    expect(screen.getByText(/\+0\.6/)).toBeInTheDocument();
    expect(screen.getByText(/\+0\.2/)).toBeInTheDocument();
  });

  it("zeigt Status 'nicht invertiert' wenn alle Spreads positiv", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/nicht invertiert/i)).toBeInTheDocument());
  });

  it("zeigt 'invertiert' wenn ein Spread negativ ist", async () => {
    const invertedView: YieldCurveView = {
      ...demoYieldCurve(),
      spreads: [
        { pair: "10J-2J",  value: -0.3 },
        { pair: "10J-3M",  value: +0.1 },
        { pair: "30J-10J", value: +0.2 },
      ],
    };
    const invertedLoader = () => Promise.resolve(invertedView);
    renderPage(invertedLoader);
    await waitFor(() => {
      // Badge + Status-Block zeigen jeweils "invertiert"
      const items = screen.getAllByText(/invertiert/i);
      expect(items.length).toBeGreaterThanOrEqual(2);
    });
    // Rezessions-Frühsignal im Status-Block (Teil eines längeren Texts)
    expect(screen.getByText(/Rezessions-Fr/i, { exact: false })).toBeInTheDocument();
  });

  it("zeigt Demo-Badge", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Demo-Daten")).toBeInTheDocument());
  });
});
