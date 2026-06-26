import { useMemo, useState } from "react";
import { NavLink } from "react-router-dom";
import { Icon } from "../components/icons";
import { useTheme } from "./useTheme";
import { searchTickers, resolveTicker } from "../lib/tickerSearch";

export interface TopbarProps {
  inboxCount: number;
  onSearch: (ticker: string) => void;
  onLogout?: () => void;
}

const ICON_BTN =
  "grid h-8 w-8 place-items-center rounded-lg text-muted transition-colors hover:bg-ink/[0.06] hover:text-ink";

const MAX_SUGGESTIONS = 6;

export function Topbar({ inboxCount, onSearch, onLogout }: TopbarProps) {
  const { theme, toggle } = useTheme();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1); // -1 = keine Markierung -> Enter loest unscharf auf
  const suggestions = useMemo(() => searchTickers(q, MAX_SUGGESTIONS), [q]);
  const showList = open && suggestions.length > 0;

  // Auswahl bestaetigen: Dropdown schliessen und mit dem KANONISCHEN Symbol navigieren.
  function choose(ticker: string) {
    setOpen(false);
    setActive(-1);
    onSearch(ticker);
  }

  function submit() {
    if (active >= 0 && active < suggestions.length) { choose(suggestions[active].entry.ticker); return; }
    const t = q.trim();
    if (!t) return;
    // Unscharf aufloesen (z. B. "appl"->AAPL); ohne Treffer Roh-Eingabe gross schreiben.
    choose(resolveTicker(t) ?? t.toUpperCase());
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!showList) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((i) => Math.min(i + 1, suggestions.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((i) => Math.max(i - 1, -1)); }
    else if (e.key === "Escape") { setOpen(false); setActive(-1); }
  }

  return (
    <header className="flex items-center justify-between gap-4 border-b border-line bg-surface/70 px-4 py-2 backdrop-blur">
      <form
        onSubmit={(e) => { e.preventDefault(); submit(); }}
        className="flex-1"
        role="search"
      >
        <div className="relative max-w-md">
          <Icon name="search" className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            type="search"
            value={q}
            onChange={(e) => { setQ(e.target.value); setOpen(true); setActive(-1); }}
            onFocus={() => setOpen(true)}
            onBlur={() => setOpen(false)}
            onKeyDown={onKeyDown}
            placeholder="Titel oder Markt suchen — z. B. AAPL, Gold, Öl"
            aria-label="Ticker oder Markt suchen"
            role="combobox"
            aria-expanded={showList}
            aria-controls="ticker-suggestions"
            aria-autocomplete="list"
            aria-activedescendant={active >= 0 ? `ticker-opt-${active}` : undefined}
            className="w-full rounded-lg border border-line bg-surface-2 py-1.5 pl-9 pr-3 text-sm text-ink placeholder:text-muted focus:border-brand focus:bg-surface focus:outline-none"
          />
          {showList && (
            <ul
              id="ticker-suggestions"
              role="listbox"
              aria-label="Such-Vorschläge"
              className="absolute left-0 right-0 top-full z-30 mt-1 overflow-hidden rounded-lg border border-line bg-surface shadow-panel"
            >
              {suggestions.map((s, i) => (
                <li
                  key={s.entry.ticker}
                  id={`ticker-opt-${i}`}
                  role="option"
                  aria-selected={i === active}
                  // onMouseDown verhindert, dass der Input-Blur den Klick verschluckt.
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => choose(s.entry.ticker)}
                  onMouseEnter={() => setActive(i)}
                  className={`flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm ${
                    i === active ? "bg-brand/10 text-ink" : "text-ink/90"
                  }`}
                >
                  <span className="font-mono text-xs font-semibold text-brand">{s.entry.ticker}</span>
                  <span className="truncate text-muted">{s.entry.name}</span>
                  <span className="ml-auto shrink-0 rounded bg-ink/[0.06] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted">
                    {s.entry.kind}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </form>
      <div className="flex items-center gap-1">
        <NavLink to="/willkommen" className={ICON_BTN} aria-label="Hilfe / Willkommen" title="Willkommen & Hilfe">
          <Icon name="help" className="h-[1.05rem] w-[1.05rem]" />
        </NavLink>
        <NavLink to="/inbox" className={`relative ${ICON_BTN}`} aria-label="Inbox" title="Konflikt-Inbox">
          <Icon name="nav-inbox" className="h-[1.05rem] w-[1.05rem]" />
          {inboxCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-bear px-1 text-[10px] font-semibold text-white">
              {inboxCount}
            </span>
          )}
        </NavLink>
        <button type="button" onClick={toggle} className={ICON_BTN} aria-label="Theme umschalten" title="Hell/Dunkel">
          <Icon name={theme === "dark" ? "theme-light" : "theme-dark"} className="h-[1.05rem] w-[1.05rem]" />
        </button>
        {onLogout && (
          <button type="button" onClick={onLogout} className="ml-1 rounded-lg px-2 py-1 text-sm text-muted hover:text-ink hover:underline">
            Abmelden
          </button>
        )}
      </div>
    </header>
  );
}
