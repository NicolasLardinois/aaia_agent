import { useEffect, useState } from "react";
import type { CockpitEvent } from "../../api/cockpitSocket";
import { MARKET_WISDOM, nextWisdomIndex } from "../../data/marketWisdom";
import { HexagonSpinner } from "./HexagonSpinner";

// Lade-Erlebnis waehrend der Cockpit-Analyse (#3): der Hexagon-Spinner (Bezug zur
// hexagonalen Architektur) und eine zentral rotierende Boersenweisheit / ein
// Finanz-Fun-Fact verwandeln die Wartezeit in einen ruhigen, markentypischen Moment.
// Dezent darunter: wie viele Analyse-Schritte des Mehr-Agenten-Laufs schon fertig sind.

// Rotationsintervall der Weisheiten (ms). Exportiert, damit Tests es deterministisch nutzen.
export const WISDOM_ROTATE_MS = 6500;

export interface LoadingExperienceProps {
  /** Live-Fortschritt des Laufs (Chief-/Agent-Events). Leer beim ersten Seitenaufbau. */
  events?: CockpitEvent[];
  /** Ueberschrift; Default passt zum laufenden Analyse-Lauf. */
  title?: string;
}

export function LoadingExperience({ events, title = "Analyse läuft" }: LoadingExperienceProps) {
  const [index, setIndex] = useState(0);

  // Reine Index-Rotation (nextWisdomIndex ist getestet) — der Timer ist nur der Antrieb.
  useEffect(() => {
    const id = setInterval(
      () => setIndex((cur) => nextWisdomIndex(cur, MARKET_WISDOM.length)),
      WISDOM_ROTATE_MS,
    );
    return () => clearInterval(id);
  }, []);

  const w = MARKET_WISDOM[index];
  const steps = events?.length ?? 0;
  const eyebrow = w.kind === "weisheit" ? "Börsenweisheit" : "Wussten Sie schon?";

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col items-center justify-center gap-7 py-16 text-center"
    >
      <HexagonSpinner className="h-20 w-20 text-brand" />

      <div className="space-y-1">
        <p className="font-display text-lg font-semibold text-ink">{title}</p>
        {steps > 0 ? (
          <p className="tnum text-sm text-muted">{steps} Analyse-Schritte abgeschlossen …</p>
        ) : (
          <p className="text-sm text-muted">Mehr-Agenten-Analyse — das kann einen Moment dauern.</p>
        )}
      </div>

      {/* Rotierende Weisheit: key={index} tauscht das Element komplett aus -> nur der
          aktuelle Eintrag steht im DOM (sauber testbar) und blendet sanft ein. */}
      <figure key={index} className="wisdom-fade max-w-prose space-y-2">
        <figcaption className="text-[0.7rem] font-medium uppercase tracking-[0.18em] text-brand/80">
          {eyebrow}
        </figcaption>
        <blockquote className="font-display text-xl leading-relaxed text-ink">{w.text}</blockquote>
        {w.author && <p className="text-sm text-muted">— {w.author}</p>}
      </figure>
    </div>
  );
}
