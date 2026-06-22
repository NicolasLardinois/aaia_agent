# Render-Deploy (Cockpit-Scheibe) — Design

> **Status:** Spezifikation / Design-Entwurf · **Datum:** 2026-06-22
> **Scope:** Die bestehende Cockpit-Scheibe (Backend-API-Brücke + React-Frontend) auf **Render** deploybar machen — per **Blueprint (`render.yaml`)**. Umfasst die Repo-Vorbereitung (Config + Doku) **sowie** die dokumentierte Schritt-für-Schritt-Anleitung für die Dashboard-Schritte, die der User ausführt.
> **Erdung:** Backend `app/server.py` (FastAPI, modulweites `app`), `requirements.txt`, `config/settings.py` (Pflicht-Env `FRED_API_KEY`/`ANTHROPIC_API_KEY`), CORS via `AAIA_CORS_ORIGINS` (PR #27); Frontend `frontend/` (Vite, `VITE_API_BASE_URL`).
> **Wichtig:** Reines Design-Dokument (*Warum/Wie*). Laufender Status/Folge-Aufgaben → Logbuch `docs/open_todos.md` (AGENTS.md §5).

---

## 1. Zusammenfassung & Scope

Beide Dienste der Cockpit-Scheibe werden über **einen Render-Blueprint** (`render.yaml`) beschrieben und gemeinsam ausgerollt:
- **Backend** als Render *Web Service* (Python/uvicorn).
- **Frontend** als Render *Static Site* (Vite-Build).

**Kein Code-Change nötig:** `app/server.py` exponiert `app` modulweit; Render bindet via Start-Befehl `uvicorn app.server:app --host 0.0.0.0 --port $PORT` (der lokale `__main__`-Block mit `127.0.0.1` bleibt unangetastet).

**Aufgeteilt:**
- **Repo (dieser PR):** `render.yaml`, Python-Version-Pin, Deploy-Doku.
- **Render-Konto (User):** Blueprint anwenden, Secrets eingeben. Ich habe keinen Render-Zugriff und kann den Deploy nicht auslösen — die Doku liefert die genauen Schritte.

## 2. `render.yaml` — Struktur

Zwei Services unter `services:`.

**Backend** (`type: web`, `runtime: python`):
- `buildCommand: pip install -r requirements.txt`
- `startCommand: uvicorn app.server:app --host 0.0.0.0 --port $PORT`
- `plan: free`, **`numInstances: 1`** (In-Memory-Zustand: letztes Ergebnis, WS-Verbindungen, Event-Bus pro Lauf → kein Autoscaling).
- `healthCheckPath: /api/cockpit` (liefert `204`, solange kein Lauf war → für Render „healthy"; ein 2xx genügt).
- `envVars` (alle ohne Wert im Repo):
  - `FRED_API_KEY` — `sync: false` (Pflicht; sonst Startabbruch in `config/settings.py`).
  - `ANTHROPIC_API_KEY` — `sync: false` (Pflicht; dito).
  - `FINNHUB_API_KEY` — `sync: false` (optional).
  - `AAIA_CORS_ORIGINS` — Frontend-URL (siehe §3, Verdrahtung).
  - `PYTHON_VERSION` — fester Wert (z. B. `3.12.x`), da der Code 3.10+-Syntax nutzt.

**Frontend** (`type: web`, `runtime: static`):
- `rootDir: frontend`
- `buildCommand: npm install && npm run build`
- `staticPublishPath: ./dist`
- `envVars`:
  - `VITE_API_BASE_URL` — Backend-URL (siehe §3).
- Kein SPA-Rewrite nötig (eine Seite, kein Client-Routing — YAGNI; bei späterem Routing eine Rewrite-Regel ergänzen).

## 3. Cross-URL-Verdrahtung (kritische Reihenfolge)

Jeder Dienst braucht die Adresse des anderen — und **Vite backt `VITE_API_BASE_URL` beim Build fest ein** (kein Laufzeit-Wert). Ändert sich die Backend-Adresse, muss das Frontend **neu gebaut** werden.

**Bevorzugt — automatische Verdrahtung über `fromService`** (Render injiziert die Service-URL):
- Frontend `VITE_API_BASE_URL` ← Backend-Service (öffentliche URL).
- Backend `AAIA_CORS_ORIGINS` ← Frontend-Service (öffentliche URL).

Beim Schreiben der `render.yaml` wird die exakte `fromService`-Property (Host vs. volle URL inkl. `https://`) gegen die Render-Doku verifiziert. Lässt sich die **volle `https://`-URL** so nicht sauber injizieren, fällt der Plan auf den **dokumentierten manuellen Zwei-Pass** zurück: (1) Blueprint anwenden, (2) nach dem ersten Deploy die jeweils andere URL in beide Env-Variablen eintragen und neu deployen. Beide Wege stehen in der Doku.

## 4. Deploy-Doku (`docs/deploy-render.md`)

Enthält:
- **Voraussetzungen:** Render-Konto, GitHub-Repo verbunden, Branch mit `render.yaml`.
- **Schritte:** „New → Blueprint" → Repo+Branch → Render liest `render.yaml` → Pflicht-Secrets (`FRED_API_KEY`, `ANTHROPIC_API_KEY`; optional `FINNHUB_API_KEY`) eingeben → „Apply".
- **Env-Variablen-Tabelle** (Name · Pflicht/optional · Zweck · wo gesetzt).
- **Vite-Build-Time-Hinweis** + die Reihenfolge/Verdrahtung aus §3 (warum ein Frontend-Rebuild nötig ist, wenn sich die Backend-URL ändert).
- **Verifikation nach Deploy:** Backend-Health (`/api/cockpit` → `204`), Frontend lädt, „Analyse starten" stößt einen Lauf an (Live-WS), Ergebnis erscheint.
- **Free-Tier-Hinweis:** Spin-down nach Inaktivität → Kaltstart ~30–60 s.
- **Sicherheits-Warnung (prominent):** `POST /api/cockpit/run` ist **unauthentifiziert** und ohne Lauf-Lock → vor jeder über „privat/eingeschränkt" hinausgehenden Exposition **Auth + Rate-Limiting + Lauf-Lock** umsetzen (Backend-Folgeaufgabe #7). Das Repo ist öffentlich — die URL sollte nicht breit geteilt werden, bis das steht.

## 5. Verifikation (meinerseits, im PR)

- **Kein Code-Change** → bestehende Test-Suite bleibt unverändert grün (Stichprobe: API-Tests).
- **`render.yaml` syntaktisch valide** (YAML lädt fehlerfrei; Pflichtfelder je Service vorhanden).
- **Import-Smoke-Check** des Start-Pfads: `python -c "import app.server"` lädt ohne Fehler (kein Server-Start, kein Netz-Call). Voraussetzung: `FRED_API_KEY`/`ANTHROPIC_API_KEY` lokal gesetzt (sonst greift der Env-Guard — das ist erwartetes Verhalten und wird im Check berücksichtigt).
- Der **echte Deploy** wird vom User durch Anwenden des Blueprints getestet (außerhalb dieses Repos).

## 6. Abgrenzung / Nicht-Ziele

Kein Auth/Rate-Limiting/Lauf-Lock (Folgeaufgabe #7, in der Doku als Voraussetzung markiert); keine Datenbank/Persistenz (In-Memory bleibt; `GET` nach Neustart leer); keine Custom-Domain; kein Mehr-Instanz-Betrieb; keine CI-Pipeline (separate Folge-Aufgabe). `psycopg2-binary` in `requirements.txt` bleibt (von anderen Projektteilen genutzt) — für diese Scheibe wird keine DB konfiguriert.

---

*Querverweise: `docs/superpowers/specs/2026-06-22-api-bridge-cockpit-design.md` (Backend), `docs/superpowers/specs/2026-06-22-frontend-cockpit-overview-design.md` (Frontend), `frontend/README.md` (Frontend-Deploy-Notiz). Status/Folge-Aufgaben: `docs/open_todos.md`.*
