// Hexagon-Spinner — die Lade-Signatur des Cockpits. Das Sechseck verweist auf die
// hexagonale Architektur des Systems (Ports & Adapters): ein leuchtendes Segment
// laeuft ueber die sechs Kanten, als zoege gerade ein Lauf durch die Schichten.
// Reine Praesentation, standardmaessig dekorativ (aria-hidden) — den lesbaren
// Status traegt die umgebende LoadingExperience (role="status").

export interface HexagonSpinnerProps {
  /** Tailwind-Groesse/Farbe; Default h-16 w-16 text-brand (currentColor steuert die Linie). */
  className?: string;
}

// Pointy-top-Sechseck, Mittelpunkt (50,50), Radius 44 — Eckpunkte bei -90°..210° in 60°-Schritten.
const HEX_POINTS = "50,6 88.1,28 88.1,72 50,94 11.9,72 11.9,28";

export function HexagonSpinner({ className }: HexagonSpinnerProps) {
  return (
    <svg
      viewBox="0 0 100 100"
      aria-hidden="true"
      className={className ?? "h-16 w-16 text-brand"}
    >
      {/* Track: das volle Sechseck, dezent — gibt der Bewegung eine ruhige Bahn. */}
      <polygon
        points={HEX_POINTS}
        fill="none"
        stroke="currentColor"
        strokeWidth={4}
        strokeLinejoin="round"
        className="opacity-15"
      />
      {/* Runner: ein leuchtendes Segment, das ueber die Kanten wandert (pathLength=100
          normiert den Umfang -> Dash-Animation in index.css ist groessenunabhaengig). */}
      <polygon
        points={HEX_POINTS}
        fill="none"
        stroke="currentColor"
        strokeWidth={4}
        strokeLinejoin="round"
        strokeLinecap="round"
        pathLength={100}
        className="hex-runner"
      />
    </svg>
  );
}
