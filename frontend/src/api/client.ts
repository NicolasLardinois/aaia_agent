import type { CockpitOverview } from "../lib/contract";

// Fehlerklassen, damit der Hook 401/409 von generischen Fehlern trennen kann.
export class UnauthorizedError extends Error {}
export class RunInProgressError extends Error {}

function authHeaders(token?: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// GET liest das letzte Ergebnis; 204 == noch kein Lauf -> null; 401 -> UnauthorizedError.
export async function getCockpit(
  base: string,
  fetchFn: typeof fetch = fetch,
  token?: string | null,
): Promise<CockpitOverview | null> {
  const res = await fetchFn(`${base}/api/cockpit`, { headers: authHeaders(token) });
  if (res.status === 401) throw new UnauthorizedError();
  if (res.status === 204) return null;
  if (!res.ok) throw new Error(`GET /api/cockpit fehlgeschlagen: ${res.status}`);
  return (await res.json()) as CockpitOverview;
}

// POST startet einen Lauf; 202 { run_id }; 401 -> UnauthorizedError; 409 -> RunInProgressError.
export async function startRun(
  base: string,
  fetchFn: typeof fetch = fetch,
  token?: string | null,
): Promise<string> {
  const res = await fetchFn(`${base}/api/cockpit/run`, { method: "POST", headers: authHeaders(token) });
  if (res.status === 401) throw new UnauthorizedError();
  if (res.status === 409) throw new RunInProgressError();
  if (!res.ok) throw new Error(`POST /api/cockpit/run fehlgeschlagen: ${res.status}`);
  const data = (await res.json()) as { run_id: string };
  return data.run_id;
}
