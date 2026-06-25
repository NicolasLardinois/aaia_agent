import { useState } from "react";

// Einfacher Passwort-Screen: der Dozent gibt das geteilte Passwort ein.
export function LoginGate({ error, onSubmit }: { error?: boolean; onSubmit: (token: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <main className="mx-auto max-w-sm space-y-3 p-6">
      <h1 className="text-xl font-bold">AAIA — Cockpit</h1>
      <p className="text-muted">Bitte Passwort eingeben.</p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value) onSubmit(value);
        }}
        className="space-y-2"
      >
        <input
          type="password"
          aria-label="Passwort"
          placeholder="Passwort"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-full rounded border border-line bg-surface px-3 py-2"
        />
        {error && <p className="text-sm text-bear">Falsches Passwort</p>}
        <button type="submit" className="rounded bg-brand px-3 py-1.5 text-sm font-medium text-brand-ink">
          Anmelden
        </button>
      </form>
    </main>
  );
}
