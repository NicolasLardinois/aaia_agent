import { useEffect, useState } from "react";

// Generischer Konsum-Hook fuer die Tausch-Naht (Spec §2): nimmt eine Lade-Funktion
// (Demo ODER echt — identischer Vertrag) und liefert data/loading/error. Die UI weiss
// nicht, ob die Daten Demo oder echt sind — das steht im Vertrag (isDemo).
export function useView<T>(loader: () => Promise<T>): { data: T | null; loading: boolean; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    loader()
      .then((d) => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError("Daten nicht ladbar"); setLoading(false); } });
    return () => { cancelled = true; };
    // loader-Identitaet steuert den Refetch; Aufrufer muss loader stabil halten (useCallback/Modul-Fn).
  }, [loader]);

  return { data, loading, error };
}
