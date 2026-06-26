// Willkommen-Seite (Teil-Projekt A): erklärt AAIA + jeden Bereich, "wo was zu finden ist".
// Reiner Inhalt, kein Backend. "Los geht's" merkt den Besuch und führt ins Cockpit.
// Schauseite der "Instrument-Deck"-Designsprache: Hero + Regime-Horizont-Signatur.
import { Link, useNavigate } from "react-router-dom";
import { AREAS } from "../data/welcomeContent";
import { SectionCard } from "../components/SectionCard";
import { InfoTip } from "../components/InfoTip";
import { Icon } from "../components/icons";
import { useOnboarding } from "../shell/useOnboarding";

const STEPS = [
  { n: "1", title: "Top-Down", term: "Top-Down", text: "Das große Bild: Konjunktur, Zinsen, Inflation — das Marktregime.", termInline: "Regime" },
  { n: "2", title: "Bottom-Up", term: "Bottom-Up", text: "Die Tiefenprüfung eines einzelnen Titels.", termInline: undefined },
  { n: "3", title: "Urteil", term: "Urteil", text: "Beides zusammengeführt zu einer Einschätzung.", termInline: undefined },
];

export function WelcomePage() {
  const navigate = useNavigate();
  const { markSeen } = useOnboarding();

  function start() {
    markSeen();
    navigate("/cockpit");
  }

  return (
    <section className="space-y-6">
      {/* Hero — Thesis: AAIA liest die Marktlage; der Regime-Horizont ist die Signatur. */}
      <div className="overflow-hidden rounded-panel border border-line bg-surface p-6 shadow-panel">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand">
          Adaptive AI Investment Agent
        </div>
        <h2 className="mt-2 font-display text-3xl font-bold tracking-tight">Willkommen bei AAIA</h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
          AAIA ist dein KI-gestützter Investment-Analyse-Assistent: Er liest die Marktlage und
          prüft einzelne Titel — und führt beides zu einem nachvollziehbaren Urteil zusammen.
        </p>
        <div className="regime-horizon mt-6" />
        <div className="mt-2 flex justify-between font-mono text-[10px] uppercase tracking-wide text-muted">
          <span>Aufschwung</span>
          <span>neutral</span>
          <span>Abschwung</span>
        </div>
      </div>

      {/* Philosophie — Signatur: zwei gleichwertige Linsen (Diptychon), nie ein Umschalter (§5.3).
          Spiegelt das echte Long-Short-Panel aus dem Deep-Dive und macht den Wert sofort sichtbar. */}
      <SectionCard eyebrow="Die Idee" title="Zwei Linsen, ein Ziel" subtitle="Long · Short · Total-Return">
        <p className="max-w-2xl text-sm leading-relaxed text-muted">
          AAIA beurteilt jeden Titel durch zwei <strong className="text-ink">gleichwertige Linsen</strong> —
          nie bloß „kaufen oder nicht". Das Ziel ist <strong className="text-ink">Rendite in beide Marktrichtungen</strong>,
          statt nur auf steigende Märkte zu setzen.
        </p>

        {/* Diptychon: strikt gleich breite Spalten, mittig getrennt — die Gleichwertigkeit IST die Aussage. */}
        <div className="mt-4 grid grid-cols-1 divide-line overflow-hidden rounded-xl border border-line sm:grid-cols-2 sm:divide-x">
          <div className="space-y-1.5 bg-bull/[0.04] p-4">
            <div className="flex items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-md bg-bull/10 text-bull">
                <Icon name="trend-up" className="h-4 w-4" />
              </span>
              <span className="font-display font-semibold text-ink">Long-Linse</span>
            </div>
            <p className="text-xs font-medium uppercase tracking-wide text-bull">Lohnt sich der Kauf?</p>
            <p className="text-sm text-muted">Steigende Kurse als Gewinnquelle — Bewertung, Qualität und Rückenwind sprechen dafür.</p>
          </div>
          <div className="space-y-1.5 bg-bear/[0.04] p-4">
            <div className="flex items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-md bg-bear/10 text-bear">
                <Icon name="trend-down" className="h-4 w-4" />
              </span>
              <span className="font-display font-semibold text-ink">Short-Linse</span>
            </div>
            <p className="text-xs font-medium uppercase tracking-wide text-bear">Lohnt die Wette auf einen Fall?</p>
            <p className="text-sm text-muted">Fallende Kurse als Gewinnquelle — Bilanz-Stress, Gewinneinbruch oder ein konkreter Auslöser.</p>
          </div>
        </div>

        {/* Kern-Grundsatz (volle Breite) — hebt Long-Short von „einfach invertieren" ab (short.md §Grundsatz). */}
        <p className="mt-3 rounded-lg border border-line bg-surface-2 px-3.5 py-2.5 text-sm text-ink/90">
          <strong className="text-ink">Wichtig:</strong> Ein Short ist <strong className="text-ink">nicht das Spiegelbild</strong> eines
          Longs. „Teuer" allein ist nie ein Short — teure Werte bleiben oft jahrelang teuer. Es braucht einen echten Grund zu
          fallen plus einen <strong className="text-ink">Katalysator</strong> (einen Auslöser, der den Fall in Gang bringt).
        </p>
      </SectionCard>

      {/* Analyse-Ablauf — echte Sequenz (Top-Down → Bottom-Up → Urteil), daher nummeriert. */}
      <SectionCard eyebrow="So funktioniert es" title="Der Weg zum Urteil" subtitle="In drei Schritten">
        <ol className="grid gap-3 sm:grid-cols-3">
          {STEPS.map((s) => (
            <li key={s.n} className="rounded-xl border border-line bg-surface-2 p-3">
              <div className="flex items-center gap-2">
                <span className="grid h-6 w-6 place-items-center rounded-md bg-brand/10 font-mono text-xs font-semibold text-brand">{s.n}</span>
                <span className="font-display font-semibold">{s.title}</span>
                <InfoTip term={s.term} />
              </div>
              <p className="mt-2 text-sm text-muted">
                {s.text}{s.termInline && <> <InfoTip term={s.termInline} /></>}
              </p>
            </li>
          ))}
        </ol>
      </SectionCard>

      {/* Bereiche — wo finde ich was? */}
      <SectionCard eyebrow="Orientierung" title="Wo finde ich was?" subtitle="Die fünf Bereiche">
        <div className="grid gap-3 sm:grid-cols-2">
          {AREAS.map((a) => (
            <Link
              key={a.to}
              to={a.to}
              className="group block rounded-xl border border-line bg-surface-2 p-3.5 transition-colors hover:border-brand/40 hover:bg-brand/[0.04]"
            >
              <div className="flex items-center gap-2 font-display font-semibold">
                <Icon name={a.icon} className="h-4 w-4 text-brand" />{a.name}
                <Icon name="arrow-right" className="ml-auto h-4 w-4 text-muted transition-transform group-hover:translate-x-0.5" />
              </div>
              <p className="mt-1.5 text-sm text-ink/90">{a.question}</p>
              <p className="mt-0.5 text-xs text-muted">{a.howto}</p>
            </Link>
          ))}
        </div>
      </SectionCard>

      {/* Daten-Hinweis */}
      <SectionCard eyebrow="Ehrlich gesagt" title="Hinweis zu den Daten">
        <p className="text-sm text-muted">
          Manche Bereiche zeigen vorerst <strong className="text-ink">Demo-Daten <InfoTip term="Demo-Daten" /></strong> (Beispielwerte),
          bis die echte Quelle angebunden ist — erkennbar am „Demo-Daten"-Etikett oben in der jeweiligen Ansicht.
        </p>
      </SectionCard>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={start}
          className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-brand-ink transition-colors hover:bg-brand-strong"
        >
          Verstanden, los geht's
          <Icon name="arrow-right" className="h-4 w-4" />
        </button>
        <span className="text-xs text-muted">Diese Seite findest du jederzeit oben über „?".</span>
      </div>
    </section>
  );
}
