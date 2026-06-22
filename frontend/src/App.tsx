import { useState } from "react";
import { CockpitPage } from "./pages/CockpitPage";
import { useAuth } from "./auth/useAuth";
import { LoginGate } from "./auth/LoginGate";

export default function App() {
  const { token, login, logout } = useAuth();
  const [authError, setAuthError] = useState(false);

  if (!token) {
    return <LoginGate error={authError} onSubmit={(t) => { setAuthError(false); login(t); }} />;
  }
  return (
    <CockpitPage
      deps={{ token, onUnauthorized: () => { setAuthError(true); logout(); } }}
      onLogout={logout}
    />
  );
}
