import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { UnderlyingWrapperBadge } from "./UnderlyingWrapperBadge";

describe("UnderlyingWrapperBadge", () => {
  it("zeigt beide Etiketten", () => {
    render(<UnderlyingWrapperBadge underlying="precious_metal" wrapper="future" />);
    expect(screen.getByText(/Edelmetall/)).toBeInTheDocument();
    expect(screen.getByText(/Future/)).toBeInTheDocument();
  });
});
