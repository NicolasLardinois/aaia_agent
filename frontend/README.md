# AAIA Frontend — Cockpit-Übersicht (erste Scheibe)

React + TypeScript + Vite. Zeigt die Cockpit-Regime-Übersicht live über die AAIA-API-Brücke.

## Entwicklung
1. Backend starten (Repo-Wurzel): `python -m app.server` (lauscht auf `127.0.0.1:8000`).
2. `cp .env.example .env` und ggf. `VITE_API_BASE_URL` anpassen.
3. `npm install && npm run dev` — Dev-Server auf `http://localhost:5173`.

## Tests
`npm test` (Vitest). Pure Anzeige-Logik + Komponenten/Hook gegen Fakes.

## Build / Deploy (Render Static Site)
- Build-Command: `npm install && npm run build`
- Publish-Verzeichnis: `dist`
- Environment-Variable: `VITE_API_BASE_URL` = URL des Backend-Web-Service (`https://…`).
- Backend: die Frontend-URL in `AAIA_CORS_ORIGINS` (kommagetrennt) des Web-Service eintragen, damit HTTP **und** WebSocket erlaubt sind.
- Backend-Web-Service: **eine Instanz** (kein Autoscaling) — In-Memory-Zustand.
