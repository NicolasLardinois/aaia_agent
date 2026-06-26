import type { Domain } from "../lib/contract";
import type { Tone } from "../lib/marketPosture";
import { marketPosture, postureLabel } from "../lib/marketPosture";
import { Icon } from "./icons";

// ---- Markt-Puls: Synthese der Domaenen-Signale auf einen Blick ----
// Signatur-Element der Cockpit-Uebersicht (#4). Verdichtet die vier Domaenen-
// Kacheln zu EINER Tendenz + einer Verteilungs-Leiste. Bewusst als Synthese
// gekennzeichnet — sie ersetzt nicht das Gesamturteil der Analyse.

// Tendenz -> Textfarbe (Token-Farben: bull/bear, sonst neutral gehalten).
const TONE_TEXT: Record<Tone, string> = {
  "risk-on": "text-bull",
  "risk-off": "text-bear",
  mixed: "text-ink",
  unknown: "text-muted",
};

// Ein Segment der Verteilungs-Leiste (nur rendern, wenn count > 0).
function Segment({ count, total, colorClass, title }: { count: number; total: number; colorClass: string; title: string }) {
  if (count === 0) return null;
  return <div className={colorClass} style={{ width: `${(count / total) * 100}%` }} title={title} />;
}

export function MarketPulse({ domains }: { domains: Domain[] }) {
  const p = marketPosture(domains);
  const hasData = p.available > 0;

  return (
    <section className="rounded-lg border border-line p-4">
      <div className="flex items-center gap-2">
        <Icon name="pulse" className={`h-4 w-4 ${TONE_TEXT[p.tone]}`} />
        <h2 className="text-xs uppercase tracking-wide text-muted">Markt-Puls</h2>
      </div>

      {/* Tendenz gross + farbig: die eine Aussage auf einen Blick. */}
      <p className={`mt-1 text-2xl font-bold ${TONE_TEXT[p.tone]}`}>{postureLabel(p.tone)}</p>

      {hasData ? (
        <>
          {/* Verteilungs-Leiste: Anteile bullish / neutral / bearish an den verfuegbaren Domaenen. */}
          <div
            data-testid="posture-bar"
            className="mt-3 flex h-2.5 w-full overflow-hidden rounded-full bg-surface-2"
          >
            <Segment count={p.bullish} total={p.available} colorClass="bg-bull" title={`bullish: ${p.bullish}`} />
            <Segment count={p.neutral} total={p.available} colorClass="bg-neutral" title={`neutral: ${p.neutral}`} />
            <Segment count={p.bearish} total={p.available} colorClass="bg-bear" title={`bearish: ${p.bearish}`} />
          </div>

          {/* Zaehler-Zeile als farbige Spans (gleiche Vokabel wie die Signal-Badges). */}
          <p className="mt-2 text-sm">
            <span className="text-bull">{p.bullish} bullish</span>
            <span className="text-muted"> · </span>
            <span className="text-bear">{p.bearish} bearish</span>
            <span className="text-muted"> · </span>
            <span className="text-muted">{p.neutral} neutral</span>
            {p.unavailable > 0 && <span className="text-muted"> · {p.unavailable} ohne Daten</span>}
          </p>

          <p className="mt-2 text-xs text-muted">
            Einfacher Mehrheits-Konsens der vier Sub-Domänen — er ersetzt nicht das Gesamturteil der Analyse.
          </p>
        </>
      ) : (
        <p className="mt-2 text-sm text-muted">
          Noch keine Domänen-Daten — starte oder öffne eine Analyse, um den Markt-Puls zu sehen.
        </p>
      )}
    </section>
  );
}
