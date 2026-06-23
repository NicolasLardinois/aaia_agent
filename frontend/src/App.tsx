import { useState } from "react";
import { BrowserRouter } from "react-router-dom";
import { useAuth } from "./auth/useAuth";
import { LoginGate } from "./auth/LoginGate";
import { AppRoutes } from "./routes";

export default function App() {
  const { token, login, logout } = useAuth();
  const [authError, setAuthError] = useState(false);

  if (!token) {
    return <LoginGate error={authError} onSubmit={(t) => { setAuthError(false); login(t); }} />;
  }
  return (
    <BrowserRouter>
      <AppRoutes
        deps={{ token, onUnauthorized: () => { setAuthError(true); logout(); } }}
        onLogout={logout}
      />
    </BrowserRouter>
  );
}
