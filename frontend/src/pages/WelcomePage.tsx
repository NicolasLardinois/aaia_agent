// Willkommen-Seite (Teil-Projekt A): erklärt AAIA + jeden Bereich, "wo was zu finden ist".
// Reiner Inhalt, kein Backend. "Los geht's" merkt den Besuch und führt ins Cockpit.
import { Link, useNavigate } from "react-router-dom";
import { AREAS } from "../data/welcomeContent";
import { SectionCard } from "../components/SectionCard";
import { InfoTip } from "../components/InfoTip";
import { useOnboarding } from "../shell/useOnboarding";

export function WelcomePage() {
  const navigate = useNavigate();
  const { markSeen } = useOnboarding();

  function start() {
    markSeen();
    navigate("/cockpit");
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-xl font-bold">Willkommen bei AAIA</h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-300">
          AAIA ist dein KI-gestützter Investment-Analyse-Assistent: Er bewertet die Marktlage
          und einzelne Titel und führt beides zu einem nachvollziehbaren Urteil zusammen.
        </p>
      </div>

      <SectionCard title="So funktioniert die Analyse" subtitle="In drei Schritten">
        <ol className="grid gap-3 sm:grid-cols-3">
          <li className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
            <span className="font-semibold">1. Top-Down <InfoTip term="Top-Down" /></span>
            <p className="mt-1 text-slate-600 dark:text-slate-300">Das große Bild: Konjunktur, Zinsen, Inflation — das <InfoTip term="Regime" />.</p>
          </li>
          <li className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
            <span className="font-semibold">2. Bottom-Up <InfoTip term="Bottom-Up" /></span>
            <p className="mt-1 text-slate-600 dark:text-slate-300">Die Tiefenprüfung eines einzelnen Titels.</p>
          </li>
          <li className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
            <span className="font-semibold">3. Urteil <InfoTip term="Urteil" /></span>
            <p className="mt-1 text-slate-600 dark:text-slate-300">Beides zusammengeführt zu einer Einschätzung.</p>
          </li>
        </ol>
      </SectionCard>

      <SectionCard title="Wo finde ich was?" subtitle="Die fünf Bereiche">
        <div className="grid gap-3 sm:grid-cols-2">
          {AREAS.map((a) => (
            <Link
              key={a.to}
              to={a.to}
              className="block rounded-lg border border-slate-200 p-3 transition-colors hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              <div className="flex items-center gap-2 font-semibold">
                <span aria-hidden>{a.icon}</span>{a.name}
              </div>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{a.question}</p>
              <p className="mt-0.5 text-xs text-slate-500">{a.howto}</p>
            </Link>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Hinweis zu den Daten">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Manche Bereiche zeigen vorerst <strong>Demo-Daten <InfoTip term="Demo-Daten" /></strong> (Beispielwerte),
          bis die echte Quelle angebunden ist — erkennbar am „Demo-Daten"-Etikett oben in der jeweiligen Ansicht.
        </p>
      </SectionCard>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={start}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 dark:bg-slate-200 dark:text-slate-900"
        >
          Verstanden, los geht's →
        </button>
        <span className="text-xs text-slate-400">Diese Seite findest du jederzeit oben über „?".</span>
      </div>
    </section>
  );
}
