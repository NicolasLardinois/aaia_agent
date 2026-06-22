# Deploy auf Render — Cockpit-Scheibe

Deployt **Backend** (FastAPI/uvicorn) als Web Service und **Frontend** (Vite) als Static Site,
gemeinsam über den Blueprint `render.yaml` (Repo-Wurzel). Secrets stehen **nicht** im Repo
(`sync: false`) — du gibst sie im Render-Dashboard ein.

## Voraussetzungen
- Render-Konto, mit dem GitHub-Repo `aaia_agent` verbunden.
- `render.yaml` liegt auf dem Branch, den du deployst (nach Merge: `master`).

## Env-Variablen

| Variable | Dienst | Pflicht | Zweck |
|---|---|---|---|
| `FRED_API_KEY` | Backend | **ja** | FRED-Daten; ohne → Backend-Startabbruch |
| `ANTHROPIC_API_KEY` | Backend | **ja** | Claude; ohne → Backend-Startabbruch |
| `FINNHUB_API_KEY` | Backend | nein | optionale Marktdaten |
| `AAIA_CORS_ORIGINS` | Backend | ja (2. Pass) | erlaubte Origin = **Frontend-URL** |
| `VITE_API_BASE_URL` | Frontend | ja (2. Pass) | **Backend-URL** (beim Build eingebacken!) |

## Deploy — Pass 1 (Dienste anlegen)
1. Render → **New → Blueprint**.
2. Repo `aaia_agent` + Branch (`master`) wählen → Render liest `render.yaml` und zeigt **zwei** Dienste (`aaia-api`, `aaia-frontend`).
3. Bei den abgefragten `sync: false`-Variablen **jetzt** eintragen: `FRED_API_KEY`, `ANTHROPIC_API_KEY` (Pflicht), optional `FINNHUB_API_KEY`. `AAIA_CORS_ORIGINS` und `VITE_API_BASE_URL` zunächst **leer lassen** (kommen in Pass 2).
4. **Apply** → beide Dienste bauen und starten. Notiere die beiden URLs, z. B.
   `https://aaia-api-XXXX.onrender.com` und `https://aaia-frontend-XXXX.onrender.com`.

## Deploy — Pass 2 (Cross-URLs verdrahten)
Warum zwei Pässe: Jeder Dienst braucht die URL des anderen, die es erst nach Pass 1 gibt — und **Vite backt `VITE_API_BASE_URL` beim Build fest ein** (kein Laufzeit-Wert).
5. Backend (`aaia-api`) → Environment → `AAIA_CORS_ORIGINS` = **Frontend-URL** (ohne Slash am Ende, z. B. `https://aaia-frontend-XXXX.onrender.com`) → speichern (Backend startet neu).
6. Frontend (`aaia-frontend`) → Environment → `VITE_API_BASE_URL` = **Backend-URL** (z. B. `https://aaia-api-XXXX.onrender.com`) → speichern → **Manual Deploy / Clear build cache & deploy** (Frontend muss **neu gebaut** werden, damit die URL eingebacken wird).

## Verifikation
- Backend-Health: `https://aaia-api-XXXX.onrender.com/api/cockpit` → `204` (noch kein Lauf) — Render zeigt den Dienst „live".
- Frontend öffnen → Cockpit-Übersicht lädt; Leerzustand „Noch keine Analyse".
- „Analyse starten" → Live-Status „läuft …", dann erscheint die Übersicht (Regime + Kacheln). Bleibt es bei „läuft …" oder kommt ein Fehler: meist `VITE_API_BASE_URL`/`AAIA_CORS_ORIGINS` falsch oder Frontend nicht neu gebaut (Pass 2).

## Hinweise
- **Free-Tier:** das Backend schläft nach ~15 min Inaktivität ein → erster Aufruf danach ~30–60 s (Kaltstart). Solange eine WebSocket-Verbindung offen ist (laufende Analyse), bleibt es wach.
- **Eine Instanz:** der Blueprint setzt `numInstances: 1`. **Nicht** hochskalieren — der Backend-Zustand liegt im Speicher eines Prozesses (sonst landen Anfragen/WS auf der falschen Instanz). Mehr-Instanz erst nach Persistenz + Redis-Bus (Backend-Folge-Aufgaben).
- **Persistenz:** `GET /api/cockpit` ist nach einem Backend-Neustart leer (`204`), bis wieder ein Lauf gestartet wurde (kein Speichern über Neustart hinweg).

## ⚠️ Sicherheit — vor breiter Exposition zwingend
`POST /api/cockpit/run` ist **unauthentifiziert** und **ohne Lauf-Lock** — jeder mit der URL kann beliebig viele echte FRED-/Yahoo-/Claude-Läufe auslösen (Kosten-/Missbrauchsrisiko). Das Repo ist öffentlich.
**Bevor** die Render-URL über „privat/nur ich" hinaus geteilt wird: **Auth + Rate-Limiting + Lauf-Lock** umsetzen (Backend-Folge-Aufgabe #7 im Logbuch). Bis dahin die URL nicht breit teilen.
