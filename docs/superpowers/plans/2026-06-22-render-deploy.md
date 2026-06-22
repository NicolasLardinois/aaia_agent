# Render-Deploy (Cockpit-Scheibe) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Cockpit-Scheibe (Backend-API-Brücke + React-Frontend) über einen Render-Blueprint (`render.yaml`) deploybar machen — plus eine vollständige Deploy-Anleitung für die Dashboard-Schritte des Users.

**Architecture:** Ein `render.yaml` beschreibt beide Dienste: Backend als Render *Web Service* (Python/uvicorn, `uvicorn app.server:app --host 0.0.0.0 --port $PORT`) und Frontend als Render *Static Site* (Vite-Build, `rootDir: frontend`). Kein Code-Change — `app/server.py` exponiert `app` bereits modulweit. Secrets/URLs sind `sync: false` (im Dashboard gesetzt, nicht im Repo). Cross-URLs werden manuell im Zwei-Pass gesetzt (Render `fromService` liefert keine öffentliche `https://`-URL).

**Tech Stack:** Render Blueprint (`render.yaml`), Python (uvicorn/FastAPI), Vite Static Site, Markdown-Doku.

## Global Constraints

- **Sprache:** Doku + Kommentare auf **Deutsch**; Commit-Präfixe `chore(...)`, `docs(...)`.
- **Kein Code-Change:** `app/server.py`, `adapters/`, `frontend/src/` bleiben unverändert. Nur neue Dateien (`render.yaml`, `.python-version`) + Doku + Logbuch.
- **Keine Secrets im Repo:** `FRED_API_KEY`, `ANTHROPIC_API_KEY`, `FINNHUB_API_KEY`, `AAIA_CORS_ORIGINS`, `VITE_API_BASE_URL` sind im Blueprint `sync: false` (kein Wert im Repo). Das Repo ist öffentlich.
- **Pflicht-Env (sonst Backend-Startabbruch in `config/settings.py`):** `FRED_API_KEY`, `ANTHROPIC_API_KEY`.
- **Single-Instance:** `numInstances: 1` (In-Memory-Zustand: letztes Ergebnis, WS-Verbindungen, Event-Bus pro Lauf — kein Autoscaling).
- **Verifizierte Render-Syntax:** Static Site = `type: web` + `runtime: static`; mit `rootDir: frontend` sind `buildCommand` und `staticPublishPath` **relativ zu `rootDir`** → `staticPublishPath: dist`. `fromService` bietet nur `host`/`port`/`hostport` (privat), **keine** öffentliche URL → manueller Zwei-Pass für die Cross-URLs.
- **TDD-Hinweis:** Dies ist reine Konfiguration/Doku — es gibt **kein** Verhalten zum Unit-Testen. „Verifikation" heißt hier: `render.yaml` ist gültiges YAML, der uvicorn-Start-Pfad ist importierbar (`python -c "import app.server"`), und die bestehende Test-Suite bleibt unverändert (kein Code-Change).
- Backend-Adresse im Frontend nur über `VITE_API_BASE_URL` (Vite backt sie **beim Build** ein → Frontend-Rebuild nötig, wenn sie sich ändert).

---

## File Structure

| Datei | Verantwortung |
|---|---|
| `render.yaml` (create, Repo-Wurzel) | Blueprint: Backend-Web-Service + Frontend-Static-Site |
| `.python-version` (create, Repo-Wurzel) | Python-Version-Pin (`3.12`) für Render/pyenv |
| `docs/deploy-render.md` (create) | Schritt-für-Schritt-Deploy-Anleitung + Env-Tabelle + Security-Warnung |
| `docs/open_todos.md` (modify) | Logbuch-Eintrag Render-Deploy + Folge-Aufgaben |

---

## Task 1: `render.yaml` + `.python-version` (Blueprint)

**Files:**
- Create: `render.yaml`, `.python-version`

**Interfaces:**
- Produces: ein Render-Blueprint mit zwei Services `aaia-api` (web/python) und `aaia-frontend` (web/static). Env-Keys (alle `sync: false`): Backend `FRED_API_KEY`, `ANTHROPIC_API_KEY`, `FINNHUB_API_KEY`, `AAIA_CORS_ORIGINS`; Frontend `VITE_API_BASE_URL`. Diese Service-Namen/Keys referenziert die Doku (Task 2).

- [ ] **Step 1: `render.yaml` schreiben**

`render.yaml` (Repo-Wurzel):
```yaml
# Render Blueprint — Cockpit-Scheibe (Backend Web Service + Frontend Static Site).
# Secrets/URLs sind sync:false -> werden im Render-Dashboard gesetzt, NICHT im Repo.
# Verdrahtung der Cross-URLs (AAIA_CORS_ORIGINS / VITE_API_BASE_URL) manuell im
# Zwei-Pass nach dem ersten Deploy (siehe docs/deploy-render.md).
services:
  # --- Backend: FastAPI / uvicorn -----------------------------------------
  - type: web
    name: aaia-api
    runtime: python
    plan: free
    numInstances: 1                # In-Memory-Zustand -> kein Autoscaling
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.server:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /api/cockpit  # liefert 204 (2xx) solange kein Lauf war -> healthy
    envVars:
      - key: FRED_API_KEY
        sync: false                # Pflicht (sonst Startabbruch in config/settings.py)
      - key: ANTHROPIC_API_KEY
        sync: false                # Pflicht
      - key: FINNHUB_API_KEY
        sync: false                # optional
      - key: AAIA_CORS_ORIGINS
        sync: false                # = Frontend-URL (nach 1. Deploy eintragen, siehe Doku)

  # --- Frontend: Vite Static Site -----------------------------------------
  - type: web
    name: aaia-frontend
    runtime: static
    rootDir: frontend              # build + publish relativ zu diesem Verzeichnis
    buildCommand: npm install && npm run build
    staticPublishPath: dist
    envVars:
      - key: VITE_API_BASE_URL
        sync: false                # = Backend-URL (nach 1. Deploy eintragen, siehe Doku)
```

- [ ] **Step 2: `.python-version` schreiben**

`.python-version` (Repo-Wurzel) — der Code nutzt 3.10+-Syntax (`str | None`); Render/pyenv lesen diese Datei:
```
3.12
```

- [ ] **Step 3: `render.yaml` als gültiges YAML prüfen**

Run (aus der Repo-Wurzel):
```bash
python -c "import yaml; d = yaml.safe_load(open('render.yaml')); names = [s['name'] for s in d['services']]; print('render.yaml valid; services:', names)"
```
Expected: `render.yaml valid; services: ['aaia-api', 'aaia-frontend']`
(Falls `ModuleNotFoundError: yaml` → einmalig lokal `python -m pip install pyyaml` — **nicht** in `requirements.txt` aufnehmen, ist nur ein Prüf-Tool.)

- [ ] **Step 4: uvicorn-Start-Ziel importierbar (Smoke-Check)**

Der Render-Start-Befehl lädt `app.server:app`. Prüfen, dass dieses Ziel importierbar ist (lädt `.env` über `config/settings.py`; `FRED_API_KEY`/`ANTHROPIC_API_KEY` müssen lokal in `.env` stehen — auf diesem Rechner der Fall):
```bash
python -c "import app.server; print('import ok:', type(app.server.app).__name__)"
```
Expected: `import ok: FastAPI`
(Schlägt es mit `EnvironmentError: FRED_API_KEY fehlt` fehl, fehlen die lokalen `.env`-Keys — das ist der erwartete Env-Guard, kein Blueprint-Problem; dann mit gesetzten Keys erneut prüfen.)

- [ ] **Step 5: Commit**

```bash
git add render.yaml .python-version
git commit -m "chore(deploy): Render-Blueprint (render.yaml) + Python-Pin fuer Cockpit-Scheibe

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Deploy-Anleitung `docs/deploy-render.md`

**Files:**
- Create: `docs/deploy-render.md`

**Interfaces:**
- Consumes: Service-Namen/Env-Keys aus Task 1 (`aaia-api`, `aaia-frontend`, die 5 Env-Variablen).

- [ ] **Step 1: `docs/deploy-render.md` schreiben**

`docs/deploy-render.md`:
```markdown
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
```

- [ ] **Step 2: Doku-Konsistenz prüfen**

Sicherstellen, dass die in der Doku genannten Service-Namen (`aaia-api`, `aaia-frontend`), Env-Keys und Pfade exakt mit `render.yaml` (Task 1) übereinstimmen.
Run:
```bash
grep -E "aaia-api|aaia-frontend|AAIA_CORS_ORIGINS|VITE_API_BASE_URL|FRED_API_KEY|ANTHROPIC_API_KEY" render.yaml docs/deploy-render.md
```
Expected: dieselben Namen/Keys in beiden Dateien.

- [ ] **Step 3: Commit**

```bash
git add docs/deploy-render.md
git commit -m "docs(deploy): Render-Deploy-Anleitung (Blueprint, Zwei-Pass-URLs, Security-Warnung)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Logbuch nachziehen

**Files:**
- Modify: `docs/open_todos.md`

**Interfaces:** keine (Doku).

- [ ] **Step 1: Eintrag ergänzen**

In `docs/open_todos.md`, im Abschnitt „Frontend / API-Brücke" (bzw. nahe „Frontend-Scheibe 1"), einen Unterabschnitt „Render-Deploy (Branch `feat/render-deploy`)" ergänzen (additiv, nichts Bestehendes löschen):
- **Umgesetzt:** Blueprint `render.yaml` (Backend-Web-Service `aaia-api` + Frontend-Static-Site `aaia-frontend`), `.python-version` (3.12), Anleitung `docs/deploy-render.md`. Kein Code-Change. Spec: `docs/superpowers/specs/2026-06-22-render-deploy-design.md`, Plan: `docs/superpowers/plans/2026-06-22-render-deploy.md`.
- **Offene Folge-Aufgaben (mit Lösungsansatz):**
  - **Auth/Rate-Limiting/Lauf-Lock vor breiter Exposition (Backend-Folgeaufgabe #7):** verschärft sich, sobald die Render-URL erreichbar ist. *Ansatz:* einfache API-Key-/Basic-Auth-Middleware + Rate-Limit am `POST …/run` + Lauf-Lock (`409` bei laufendem Lauf).
  - **Cross-URL-Verdrahtung manuell (Zwei-Pass):** Render `fromService` liefert keine öffentliche URL. *Ansatz:* falls Render künftig eine URL-Property bietet, automatisieren; sonst beim Doku-Stand bleiben.
  - **Ergebnis-Persistenz / Mehr-Instanz:** weiterhin offen (In-Memory); Voraussetzung für Autoscaling.

- [ ] **Step 2: Commit**

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): Render-Deploy + Folge-Aufgaben protokolliert

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (gegen die Spec)

**Spec-Abdeckung:**
- §1 Scope (Blueprint, beide Dienste, kein Code-Change, Aufteilung Repo/Render) → Tasks 1+2 ✓
- §2 render.yaml-Struktur (Backend web/python + Start-Befehl + Single-Instance + Health-Check + sync:false; Frontend static + rootDir + staticPublishPath:dist) → Task 1 ✓
- §3 Cross-URL-Reihenfolge (manueller Zwei-Pass, Vite-Build-Time) → Task 2 (Doku) ✓; `fromService`-Auto-Wiring verworfen (verifiziert: keine öffentliche URL) ✓
- §4 Deploy-Doku (Schritte, Env-Tabelle, Vite-Hinweis, Verifikation, Free-Tier, Security-Warnung) → Task 2 ✓
- §5 Verifikation (YAML valide, Import-Smoke, Suite unverändert) → Task 1 Steps 3–4 ✓
- §6 Abgrenzung (keine Auth/DB/Custom-Domain; psycopg2 bleibt) + Folge-Aufgaben → Task 3 ✓
- Python-Pin → Task 1 Step 2 (`.python-version`, statt der im Spec genannten PYTHON_VERSION-Env — robuster/tool-agnostisch; gleiche Wirkung) ✓

**Platzhalter-Scan:** keine „TBD"/„später"; render.yaml, `.python-version` und die Doku stehen vollständig im Plan. ✓

**Konsistenz:** Service-Namen `aaia-api`/`aaia-frontend` und die 5 Env-Keys identisch in render.yaml (Task 1) und Doku (Task 2); `staticPublishPath: dist` mit `rootDir: frontend` (verifiziert). ✓
