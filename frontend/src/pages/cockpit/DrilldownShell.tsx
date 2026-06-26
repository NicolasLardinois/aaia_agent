import { Link } from "react-router-dom";
import type { DemoMeta } from "../../contract/common";
import type { SourceHealthMeta } from "../../contract/cockpit";
import { DemoBadge } from "../../components/DemoBadge";
import { SourceHealth } from "../../components/SourceHealth";
import { Icon } from "../../components/icons";

// Gemeinsames Geruest fuer alle Cockpit-Drilldown-Seiten (Spec §4.1–4.4).
// Zeigt: Titel + "← zurück"-Link + DemoBadge + SourceHealth + loading/error-State.
export function DrilldownShell({
  title,
  view,
  loading,
  error,
  children,
}: {
  title: string;
  view: (DemoMeta & SourceHealthMeta) | null;
  loading: boolean;
  error: string | null;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-4">
      {/* Kopfzeile: Titel + Zurück-Link + Demo-Badge */}
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/cockpit" className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink">
          <Icon name="arrow-left" className="h-3.5 w-3.5" /> zurück zur Übersicht
        </Link>
        <h2 className="text-lg font-semibold">{title}</h2>
        {view && <DemoBadge isDemo={view.isDemo} />}
      </div>

      {/* Health-Zeile: aktive vs. ausgefallene Quellen (US9) */}
      {view && (
        <SourceHealth
          active={view.sourcesActive}
          total={view.sourcesTotal}
          failed={view.failed}
        />
      )}

      {/* Inhalt: loading / error / children */}
      {loading && <p className="text-muted">Lädt …</p>}
      {!loading && error && <p className="text-bear">{error}</p>}
      {!loading && !error && children}
    </section>
  );
}
