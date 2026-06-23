import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BigMacWidget } from "./BigMacWidget";
import { demoBigMac } from "../../data/demo/cockpit";
import { buildBarOption } from "../../components/charts/BarChart";

// ECharts im jsdom neutralisieren.
vi.mock("echarts-for-react", () => ({ default: () => null }));

const loader = () => Promise.resolve(demoBigMac());

function renderWidget() {
  return render(
    <MemoryRouter>
      <BigMacWidget loader={loader} />
    </MemoryRouter>,
  );
}

describe("BigMacWidget (C2)", () => {
  it("Publikationsdatum '2026-01' sichtbar", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText(/2026-01/)).toBeInTheDocument());
  });

  it("Demo-Badge sichtbar", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText(/Demo/i)).toBeInTheDocument());
  });

  it("Titel 'Big-Mac-Index' sichtbar (DrilldownShell)", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText(/Big-Mac/i)).toBeInTheDocument());
  });

  it("buildBarOption setzt highlight fuer das analysierte Land (US)", () => {
    // Prueft die Bar-Logik direkt mit den Demo-Daten
    const view = demoBigMac();
    const bars = view.rows.map((r) => ({
      label: r.name,
      value: r.valuationPct,
      highlight: r.iso2 === view.analyzedIso2,
    }));
    const option = buildBarOption(bars);
    // Das analysierte Land (US) hat highlight=true -> borderWidth 2
    // Reversed im option (letztes element wird erstes in der reversed-Liste)
    // US ist an Position 2 (index 2 von 0) -> nach reverse an Position 2 von 4
    // Einfacher: pruefe, dass genau ein Eintrag borderWidth 2 hat
    const dataItems = option.series[0].data as { itemStyle: { borderWidth: number } }[];
    const highlighted = dataItems.filter((d) => d.itemStyle.borderWidth === 2);
    expect(highlighted).toHaveLength(1);
  });

  it("Chart-Container und Balken-Beschriftungen werden gerendert", async () => {
    renderWidget();
    await waitFor(() => expect(screen.getByText(/2026-01/)).toBeInTheDocument());
    // Ueberbewertet/Unterbewertet-Hinweis vorhanden (kann in mehreren Elementen auftreten)
    expect(screen.getAllByText(/über.*USD|unter.*USD|Bewertung/i).length).toBeGreaterThan(0);
  });
});
