import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SourceHealth } from "./SourceHealth";

describe("SourceHealth", () => {
  it("zeigt x/y aktiv und listet ausgefallene Quellen nach Klick", async () => {
    render(<SourceHealth active={4} total={5} failed={[{ key: "Sektoren", reason: "Stub" }]} />);
    expect(screen.getByText("4/5 Quellen aktiv")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button"));
    expect(screen.getByText(/Sektoren/)).toBeInTheDocument();
  });
});
