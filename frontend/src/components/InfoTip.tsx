// Kleiner "?"-Hinweis: erklärt einen Fachbegriff kurz auf Deutsch. Die Erklärung
// liegt immer im DOM (per Tastatur/Hover sichtbar) — barrierearm via role="tooltip".
import { glossaryLookup } from "../lib/glossary";

export function InfoTip({ term, text }: { term: string; text?: string }) {
  const explanation = text ?? glossaryLookup(term);
  if (!explanation) return null;
  return (
    <span className="group relative inline-flex align-middle">
      <button
        type="button"
        aria-label={`Erklärung: ${term}`}
        className="grid h-4 w-4 place-items-center rounded-full border border-slate-300 text-[10px] leading-none text-slate-500 hover:bg-slate-100 focus:outline-none focus-visible:ring dark:border-slate-600"
      >
        ?
      </button>
      <span
        role="tooltip"
        className="invisible absolute left-1/2 top-5 z-10 w-56 -translate-x-1/2 rounded bg-slate-900 px-2 py-1 text-xs text-white shadow group-hover:visible group-focus-within:visible dark:bg-slate-700"
      >
        {explanation}
      </span>
    </span>
  );
}
