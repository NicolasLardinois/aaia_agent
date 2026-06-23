import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { DeepDivePage } from "./DeepDivePage";
import { loadDeepDive } from "../data/deepdive";

vi.mock("echarts-for-react", () => ({ default: () => null }));

function renderAt(ticker: string) {
  return render(
    <MemoryRouter initialEntries={[`/deep-dive/${ticker}`]}>
      <Routes>
        <Route path="/deep-dive/:ticker" element={<DeepDivePage loader={loadDeepDive} />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("DeepDivePage", () => {
  it("equity (AAPL): Header, Long/Short-Panel, Anomalie, equity-Tabs, KEIN Futures-Tab", async () => {
    renderAt("AAPL");
    await waitFor(() => expect(screen.getByText(/Apple/)).toBeInTheDocument());
    expect(screen.getByText("LONG-LINSE")).toBeInTheDocument();
    expect(screen.getByText("SHORT-LINSE")).toBeInTheDocument();
    expect(screen.getByText(/Anomalie-Schwere/)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Bewertung/ })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /Futures/ })).not.toBeInTheDocument();
    expect(screen.getByText("Demo-Daten")).toBeInTheDocument();
  });
  it("bond (TLT): bond-Tab statt equity-Tabs", async () => {
    renderAt("TLT");
    await waitFor(() => expect(screen.getByRole("tab", { name: /Anleihe/ })).toBeInTheDocument());
    expect(screen.queryByRole("tab", { name: /Qualität/ })).not.toBeInTheDocument();
  });
  it("Tab-Wechsel rendert den Qualität-Inhalt (Altman-Z)", async () => {
    renderAt("AAPL");
    await waitFor(() => screen.getByRole("tab", { name: /Qualität/ }));
    fireEvent.click(screen.getByRole("tab", { name: /Qualität/ }));
    expect(screen.getByText(/Altman-Z/)).toBeInTheDocument();
  });
  it("Cockpit-Wind sichtbar bei CL=F (Öl-Rückenwind)", async () => {
    renderAt("CL=F");
    await waitFor(() => expect(screen.getByText(/Rohstoffe \(Öl\)/)).toBeInTheDocument());
  });
  it("nicht gefunden (ZZZZ): Hinweis statt Tabs", async () => {
    renderAt("ZZZZ");
    await waitFor(() => expect(screen.getByText(/nicht gefunden/i)).toBeInTheDocument());
  });
  it("future (GC=F): Futures-Tab vorhanden und rendert Terminkurve-Inhalt", async () => {
    renderAt("GC=F");
    await waitFor(() => screen.getByRole("tab", { name: /Futures/ }));
    fireEvent.click(screen.getByRole("tab", { name: /Futures/ }));
    expect(screen.getByText(/Roll-Yield/)).toBeInTheDocument();
  });
  it("Vergleich: ?vergleich=4GLD zeigt CompareView mit beiden Tickern", async () => {
    render(
      <MemoryRouter initialEntries={["/deep-dive/GC=F?vergleich=4GLD"]}>
        <Routes><Route path="/deep-dive/:ticker" element={<DeepDivePage loader={loadDeepDive} />} /></Routes>
      </MemoryRouter>,
    );
    // Warten bis CompareView-Header sichtbar (zwei Hüllen ist eindeutig)
    await waitFor(() => expect(screen.getByText(/zwei Hüllen/i)).toBeInTheDocument());
    expect(screen.getByText("4GLD")).toBeInTheDocument();
    expect(screen.getByText(/kein Roll/i)).toBeInTheDocument();
  });
});
