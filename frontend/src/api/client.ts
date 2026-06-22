import type { CockpitOverview } from "../lib/contract";

// GET liest das letzte Ergebnis; 204 == noch kein Lauf -> null.
export async function getCockpit(
  base: string,
  fetchFn: typeof fetch = fetch,
): Promise<CockpitOverview | null> {
  const res = await fetchFn(`${base}/api/cockpit`);
  if (res.status === 204) return null;
  if (!res.ok) throw new Error(`GET /api/cockpit fehlgeschlagen: ${res.status}`);
  return (await res.json()) as CockpitOverview;
}

// POST startet einen Lauf im Hintergrund; Antwort 202 { run_id }.
export async function startRun(
  base: string,
  fetchFn: typeof fetch = fetch,
): Promise<string> {
  const res = await fetchFn(`${base}/api/cockpit/run`, { method: "POST" });
  if (!res.ok) throw new Error(`POST /api/cockpit/run fehlgeschlagen: ${res.status}`);
  const data = (await res.json()) as { run_id: string };
  return data.run_id;
}
