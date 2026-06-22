import { useCallback, useState } from "react";

const KEY = "aaia_token";

// Token-Status fuer den Zugang; persistiert im localStorage (man bleibt angemeldet).
export function useAuth() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(KEY));

  const login = useCallback((t: string) => {
    localStorage.setItem(KEY, t);
    setToken(t);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(KEY);
    setToken(null);
  }, []);

  return { token, login, logout };
}
