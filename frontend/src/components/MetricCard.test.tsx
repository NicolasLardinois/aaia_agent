import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MetricCard } from "./MetricCard";

describe("MetricCard", () => {
  it("zeigt Label und Wert", () => {
    render(<MetricCard label="Altman-Z" value={6.1} />);
    expect(screen.getByText("Altman-Z")).toBeInTheDocument();
    expect(screen.getByText("6.1")).toBeInTheDocument();
  });
  it("klappt einen Detailbereich auf Klick auf", async () => {
    render(<MetricCard label="Altman-Z" value={6.1} detail={<p>Bonität sehr gut</p>} />);
    expect(screen.queryByText("Bonität sehr gut")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Details/i }));
    expect(screen.getByText("Bonität sehr gut")).toBeInTheDocument();
  });
});
