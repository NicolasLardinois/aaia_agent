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
        className="grid h-4 w-4 place-items-center rounded-full border border-line text-[10px] leading-none text-muted hover:bg-ink/[0.06] hover:text-ink"
      >
        ?
      </button>
      <span
        role="tooltip"
        className="invisible absolute left-1/2 top-5 z-10 w-56 -translate-x-1/2 rounded-lg bg-ink px-2.5 py-1.5 text-xs leading-snug text-bg shadow-panel group-hover:visible group-focus-within:visible"
      >
        {explanation}
      </span>
    </span>
  );
}
