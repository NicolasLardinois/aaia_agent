// Einstellungen-Seite (Mangel #8): echte, sofort wirksame Voreinstellungen statt Platzhalter.
// Alles rein client-seitig (lib/preferences, localStorage) — keine Backend-Abhaengigkeit.
// Designsprache "Instrument-Deck": Hero + SectionCards, jede Gruppe ein Segment-Schalter.
import { useNavigate } from "react-router-dom";
import { SectionCard } from "../components/SectionCard";
import { Icon, type IconName } from "../components/icons";
import { usePreferences } from "../shell/usePreferences";
import { useOnboarding } from "../shell/useOnboarding";
import type { ThemeMode, MotionMode, StartView } from "../lib/preferences";

// Generischer Segment-Schalter (Radiogruppe): mehrere sich ausschliessende Optionen in
// einer Pillen-Leiste. role=radiogroup/radio + aria-checked -> per Tastatur & Screenreader
// bedienbar und sauber testbar. Das optionale Icon ist dekorativ (der Text traegt den Namen).
interface Option<T extends string> { value: T; label: string; icon?: IconName; }
function Segmented<T extends string>({
  label, value, options, onChange,
}: { label: string; value: T; options: Option<T>[]; onChange: (v: T) => void }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap gap-1 rounded-xl border border-line bg-surface-2 p-1">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.value)}
            className={[
              "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors",
              active
                ? "bg-brand font-semibold text-brand-ink shadow-panel"
                : "text-muted hover:bg-surface hover:text-ink",
            ].join(" ")}
          >
            {o.icon && <Icon name={o.icon} className="h-4 w-4" />}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export function SettingsPage({ onLogout }: { onLogout?: () => void }) {
  const { prefs, set } = usePreferences();
  const { reset } = useOnboarding();
  const navigate = useNavigate();

  // Onboarding zuruecksetzen UND direkt hinfuehren — so sieht der Nutzer das Ergebnis sofort.
  function replayOnboarding() {
    reset();
    navigate("/willkommen");
  }

  return (
    <section className="space-y-6">
      {/* Hero — Thesis: deine Voreinstellungen, sofort wirksam und lokal gespeichert. */}
      <div className="overflow-hidden rounded-panel border border-line bg-surface p-6 shadow-panel">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand">Konfiguration</div>
        <h2 className="mt-2 flex items-center gap-2.5 font-display text-3xl font-bold tracking-tight">
          <Icon name="nav-settings" className="h-7 w-7 text-brand" />
          Einstellungen
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
          Deine persönlichen Voreinstellungen. Jede Änderung wirkt sofort und wird in diesem
          Browser gespeichert — es gibt nichts zu „speichern".
        </p>
      </div>

      {/* Erscheinungsbild — Hell/Dunkel/System (teilt sich den Schalter mit der Topbar). */}
      <SectionCard eyebrow="Darstellung" title="Erscheinungsbild" subtitle="Hell, dunkel — oder dem System folgen">
        <Segmented
          label="Farbschema"
          value={prefs.theme}
          onChange={(v) => set("theme", v as ThemeMode)}
          options={[
            { value: "light", label: "Hell", icon: "theme-light" },
            { value: "dark", label: "Dunkel", icon: "theme-dark" },
            { value: "system", label: "System", icon: "theme-system" },
          ]}
        />
        <p className="mt-3 text-xs text-muted">
          „System" folgt der Hell-/Dunkel-Einstellung deines Betriebssystems.
        </p>
      </SectionCard>

      {/* Bewegung — Animationen reduzieren (Barrierefreiheit). */}
      <SectionCard eyebrow="Barrierefreiheit" title="Bewegung & Animationen" subtitle="Animationen bei Bedarf reduzieren">
        <Segmented
          label="Bewegung"
          value={prefs.motion}
          onChange={(v) => set("motion", v as MotionMode)}
          options={[
            { value: "system", label: "Wie System" },
            { value: "reduce", label: "Reduzieren" },
          ]}
        />
        <p className="mt-3 text-xs text-muted">
          Reduziert bewegte Effekte wie den Hexagon-Spinner auf dem Ladescreen. „Wie System" folgt
          der Betriebssystem-Einstellung „Bewegung reduzieren".
        </p>
      </SectionCard>

      {/* Start-Ansicht — wohin AAIA nach dem Login springt. */}
      <SectionCard eyebrow="Nach dem Login" title="Start-Ansicht" subtitle="Welche Seite zuerst erscheint">
        <Segmented
          label="Start-Ansicht"
          value={prefs.startView}
          onChange={(v) => set("startView", v as StartView)}
          options={[
            { value: "/cockpit", label: "Cockpit" },
            { value: "/portfolio", label: "Portfolio" },
            { value: "/backtester", label: "Backtester" },
          ]}
        />
        <p className="mt-3 text-xs text-muted">
          Beim allerersten Besuch zeigt AAIA immer zuerst die Willkommen-Seite.
        </p>
      </SectionCard>

      {/* Einführung — Willkommen-Seite erneut zeigen (setzt das Onboarding-Flag zurück). */}
      <SectionCard eyebrow="Hilfe" title="Einführung" subtitle="Die Willkommen-Seite erneut ansehen">
        <button
          type="button"
          onClick={replayOnboarding}
          className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface-2 px-3.5 py-2 text-sm font-medium text-ink transition-colors hover:border-brand/40 hover:bg-brand/[0.04]"
        >
          <Icon name="nav-welcome" className="h-4 w-4 text-brand" />
          Einführung erneut anzeigen
        </button>
      </SectionCard>

      {/* Sitzung — Zugang & Abmeldung (Abmelden nur, wenn ein Handler vorhanden ist). */}
      <SectionCard eyebrow="Konto" title="Sitzung" subtitle="Zugang & Abmeldung">
        <p className="text-sm text-muted">
          Dein Zugang ist mit einem Passwort (Token) geschützt. Beim Abmelden wird der Zugang aus
          diesem Browser entfernt.
        </p>
        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-bear/30 bg-bear/[0.06] px-3.5 py-2 text-sm font-semibold text-bear transition-colors hover:bg-bear/10"
          >
            <Icon name="logout" className="h-4 w-4" />
            Abmelden
          </button>
        )}
      </SectionCard>
    </section>
  );
}
