// InboxPage.tsx
// Konflikt-Inbox (US28/US30, Spec §7 Slice 4, Wireframe §4.9).
// Tabs Offen/Erledigt mit clientseitigem useReducer-Status.
// Beratend: Aktionen protokollieren NUR — fuehren KEINE Trades aus.
import { useReducer, useEffect, useState } from "react";
import { useView } from "../data/useView";
import { loadInbox } from "../data/inbox";
import type { InboxView, ConflictDTO, ConflictDecision } from "../contract/inbox";
import { DemoBadge } from "../components/DemoBadge";
import { ConflictCard } from "../components/inbox/ConflictCard";
import { openCount } from "../lib/inbox";

// --- State-Modell (clientseitig, Reset bei Reload akzeptabel fuer Demo) ---

interface ConflictState {
  dto: ConflictDTO;
  decision?: ConflictDecision;  // gesetzt wenn erledigt
}

interface InboxState {
  items: ConflictState[];
}

type InboxAction =
  | { type: "INIT"; conflicts: ConflictDTO[] }
  | { type: "RESOLVE"; id: string; decision: ConflictDecision };

function inboxReducer(state: InboxState, action: InboxAction): InboxState {
  switch (action.type) {
    case "INIT":
      // Initialisiert den State aus den geladenen Konflikten (alle offen, keine Entscheidung)
      return { items: action.conflicts.map((dto) => ({ dto })) };
    case "RESOLVE":
      // Markiert einen Konflikt als erledigt + protokolliert die Entscheidung (US30)
      return {
        items: state.items.map((item) =>
          item.dto.id === action.id
            ? { dto: { ...item.dto, status: "erledigt" as const }, decision: action.decision }
            : item,
        ),
      };
    default:
      return state;
  }
}

// --- Komponente ---

export function InboxPage({ loader = loadInbox }: { loader?: () => Promise<InboxView> }) {
  const { data, loading, error } = useView(loader);
  const [state, dispatch] = useReducer(inboxReducer, { items: [] });
  const [aktiveTab, setAktiveTab] = useState<"offen" | "erledigt">("offen");

  // Sobald die Daten geladen sind: Reducer-State initialisieren
  useEffect(() => {
    if (data) {
      dispatch({ type: "INIT", conflicts: data.conflicts });
    }
  }, [data]);

  // Offene und erledigte Eintraege trennen
  const offeneItems = state.items.filter((i) => i.dto.status === "offen");
  const erledigteItems = state.items.filter((i) => i.dto.status === "erledigt");
  const offeneAnzahl = openCount(state.items.map((i) => i.dto));

  function handleResolve(id: string, decision: ConflictDecision) {
    dispatch({ type: "RESOLVE", id, decision });
  }

  return (
    <section className="space-y-5">
      {/* Seitenkopf */}
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">Konflikt-Inbox</h2>
        {data && <DemoBadge isDemo={data.isDemo} />}
      </div>

      {/* Lade-/Fehlerzustand */}
      {loading && <p className="text-slate-500">Lädt …</p>}
      {!loading && error && <p className="text-red-600">Fehler: {error}</p>}

      {/* Tabs + Inhalte (nur wenn Daten da) */}
      {data && !loading && !error && (
        <>
          {/* Tab-Leiste */}
          <div role="tablist" className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
            <button
              role="tab"
              aria-selected={aktiveTab === "offen"}
              onClick={() => setAktiveTab("offen")}
              className={[
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                aktiveTab === "offen"
                  ? "border-slate-900 text-slate-900 dark:border-slate-100 dark:text-slate-100"
                  : "border-transparent text-slate-500 hover:text-slate-700",
              ].join(" ")}
            >
              Offen ({offeneAnzahl})
            </button>
            <button
              role="tab"
              aria-selected={aktiveTab === "erledigt"}
              onClick={() => setAktiveTab("erledigt")}
              className={[
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                aktiveTab === "erledigt"
                  ? "border-slate-900 text-slate-900 dark:border-slate-100 dark:text-slate-100"
                  : "border-transparent text-slate-500 hover:text-slate-700",
              ].join(" ")}
            >
              Erledigt ({erledigteItems.length})
            </button>
          </div>

          {/* Offen-Tab */}
          {aktiveTab === "offen" && (
            <div role="tabpanel" className="space-y-4">
              {offeneItems.length === 0 ? (
                <p className="text-slate-500">Keine offenen Konflikte.</p>
              ) : (
                offeneItems.map((item) => (
                  <ConflictCard
                    key={item.dto.id}
                    conflict={item.dto}
                    onResolve={handleResolve}
                  />
                ))
              )}
            </div>
          )}

          {/* Erledigt-Tab (Audit-Trail, US30) */}
          {aktiveTab === "erledigt" && (
            <div role="tabpanel" className="space-y-4">
              {erledigteItems.length === 0 ? (
                <p className="text-slate-500">Noch keine Konflikte erledigt.</p>
              ) : (
                erledigteItems.map((item) => (
                  <ConflictCard
                    key={item.dto.id}
                    conflict={item.dto}
                    loggedDecision={item.decision}
                    // kein onResolve im Erledigt-Tab -> reine Audit-Ansicht
                  />
                ))
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
