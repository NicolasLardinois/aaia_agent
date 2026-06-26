import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Icon, ICON_NAMES } from "./index";
import type { IconName } from "./index";

describe("Icon", () => {
  it("rendert ein SVG fuer einen Namen", () => {
    const { container } = render(<Icon name="warning" />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
  });

  it("ist standardmaessig dekorativ (aria-hidden, nicht in der A11y-Baumstruktur)", () => {
    const { container } = render(<Icon name="warning" />);
    const svg = container.querySelector("svg")!;
    // Ohne Label = rein dekorativ -> aria-hidden, kein role=img
    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.getAttribute("role")).not.toBe("img");
  });

  it("wird mit label zugaenglich (role=img + aria-label)", () => {
    const { getByRole } = render(<Icon name="warning" label="Quelle ausgefallen" />);
    const img = getByRole("img", { name: "Quelle ausgefallen" });
    expect(img.tagName.toLowerCase()).toBe("svg");
    // Ein zugaengliches Icon darf nicht zusaetzlich aria-hidden sein.
    expect(img.getAttribute("aria-hidden")).not.toBe("true");
  });

  it("uebernimmt eine eigene className (Groesse/Farbe per Tailwind)", () => {
    const { container } = render(<Icon name="nav-cockpit" className="h-6 w-6 text-brand" />);
    const svg = container.querySelector("svg")!;
    expect(svg.getAttribute("class")).toContain("h-6");
    expect(svg.getAttribute("class")).toContain("text-brand");
  });

  it("hat fuer jeden deklarierten Namen ein renderbares Icon (Registry vollstaendig)", () => {
    expect(ICON_NAMES.length).toBeGreaterThanOrEqual(20);
    for (const name of ICON_NAMES) {
      const { container } = render(<Icon name={name as IconName} />);
      expect(container.querySelector("svg"), `Icon fehlt: ${name}`).not.toBeNull();
    }
  });
});
