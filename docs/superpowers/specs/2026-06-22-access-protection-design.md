# Zugriffsschutz (Auth + Lauf-Lock) — Design

> **Status:** Spezifikation / Design-Entwurf · **Datum:** 2026-06-22
> **Scope:** Die deployte Cockpit-Scheibe absichern, **bevor** die Render-URL geteilt wird — gemeinsames Zugangs-Token (Passwort) + Lauf-Lock. Umfasst Backend (Token-Prüfung, Lock) und Frontend (Login-Gate). Setzt Backend-Folge-Aufgabe #7 um (ohne separates Rate-Limiting — bewusst YAGNI).
> **Erdung:** `adapters/api/routes_cockpit.py` (GET/POST/WS), `adapters/api/run_manager.py` (Lauf-Status), `adapters/api/app_factory.py` (App-Verdrahtung, CORS via `AAIA_CORS_ORIGINS`), Frontend `frontend/src/` (API-/WS-Client, `useCockpit`, `CockpitPage`).
> **Wichtig:** Reines Design (*Warum/Wie*). Status/Folge-Aufgaben → `docs/open_todos.md` (AGENTS.md §5).

---

## 1. Zusammenfassung & Ziel

Das Projekt soll dem **Dozenten** zugänglich gemacht werden: er bekommt **URL + Passwort**, öffnet die Seite und gibt das Passwort in einem **Login-Screen** ein — ohne weitere Anleitung. Schutzmodell: **ein gemeinsames Token** (Shared Secret), das **alle** Endpunkte schützt (Ansehen, Starten, Live-Stream). Zusätzlich ein **Lauf-Lock** (nur ein Lauf gleichzeitig).

**Randbedingung:** Das Frontend ist eine öffentliche Static Site — ein eingebackenes Secret wäre sichtbar. Deshalb wird das Token **nicht** ins Build eingebacken, sondern vom Nutzer **im Browser eingegeben** und lokal gespeichert.

**Bewusst NICHT enthalten (YAGNI):** kein separates Rate-Limiting (Auth + Lauf-Lock begrenzen Kosten ausreichend), keine individuellen Benutzerkonten, kein Mehr-Instanz-Betrieb.

## 2. Backend — Token-Prüfung

- Token aus Env-Variable **`AAIA_ACCESS_TOKEN`** (auf Render gesetzt, nicht im Repo).
- **Gekapselt** in neuer Datei `adapters/api/auth.py`:
  - `_expected_token() -> str` liest `os.environ.get("AAIA_ACCESS_TOKEN", "")`.
  - `token_valid(provided: str | None) -> bool`: `False`, wenn ein Token erwartet wird und `provided` nicht per `secrets.compare_digest` passt; **`True`, wenn `AAIA_ACCESS_TOKEN` leer ist** (Auth deaktiviert — lokale Entwicklung; beim App-Bau ein Warn-Log, wenn leer).
  - FastAPI-Dependency `require_token` (für HTTP): liest `Authorization: Bearer <token>`, ruft `token_valid`, sonst `HTTPException(401)`.
- **HTTP** (GET `/api/cockpit`, POST `/api/cockpit/run`): hängen `Depends(require_token)` an → ohne/falsches Token `401`.
- **WebSocket** (`/ws/cockpit`): Token als **Query-Parameter** `?token=…` (Browser können bei WS keine Header setzen). Vor `accept()` prüfen; ungültig → `await websocket.close(code=1008)` (Policy-Verletzung), **kein** `accept`.
- **Konstanter Zeitvergleich** (`secrets.compare_digest`) gegen Timing-Angriffe.

## 3. Backend — Lauf-Lock (`RunManager`)

- Neues Feld `self._running: bool` (Start `False`).
- `start_run()`:
  - Ist `self._running` bereits `True` → **kein** neuer Lauf; signalisiert „läuft schon" (Rückgabe `None` **oder** Exception — Vertrag unten), sodass die Route **`409`** liefert.
  - Sonst `self._running = True`, Lauf starten, `run_id` zurückgeben.
- `_execute(...)`: in einem **`try/finally`** — `finally: self._running = False` (Lock wird auch nach Fehler im Orchestrator-Lauf wieder frei; sonst dauerhafte Sperre).
- **Vertrag:** `start_run() -> str | None` — `None` = bereits ein Lauf aktiv. Route: `None` → `Response(status_code=409)`, sonst `202 {run_id}`.

## 4. Frontend — Login-Gate

- **Auth-Status** (kleiner Hook/Context): Token aus `localStorage` (`aaia_token`) laden.
- **`CockpitPage`-Verhalten:**
  - Kein Token gespeichert → **Login-Screen** (Passwort-Feld + „Anmelden").
  - Token vorhanden → Seite lädt (GET mit Token). Antwortet das Backend **`401`** → Token verwerfen → Login-Screen + Meldung **„Falsches Passwort"**.
- **Login-Screen** (`LoginGate`-Komponente): ein Passwort-Input, „Anmelden"-Button; Submit → Token in `localStorage` speichern → erneut laden. Leeres Feld → kein Submit.
- **Token-Transport:** API-Client hängt `Authorization: Bearer <token>` an GET/POST; WS-Client hängt `?token=<token>` an die WS-URL.
- **Logout:** kleiner „Abmelden"-Link (löscht `localStorage` → Login-Screen).
- **Erweiterte Vertragspunkte** (für den Client): `getCockpit`/`startRun` werfen bei `401` einen erkennbaren Fehler (`UnauthorizedError`), damit `useCockpit` ihn vom generischen „Backend nicht erreichbar" trennt und den Login-Screen zeigt.

## 5. Deploy / Konfiguration

- **`AAIA_ACCESS_TOKEN`** (sync:false) zum Backend-Dienst in `render.yaml` ergänzen.
- **`docs/deploy-render.md`** erweitern: Env-Tabelle (`AAIA_ACCESS_TOKEN` = Pflicht für die öffentliche Instanz), und ein kurzer Abschnitt „Zugang für den Dozenten": Token im Backend setzen → dem Dozenten **URL + Passwort** geben → er öffnet die URL, gibt das Passwort im Login-Screen ein. Bei leerem Token: Auth aus (nur lokal sinnvoll).

## 6. Tests (TDD)

- **Backend** (`auth.py` pur + Routen via TestClient):
  - `token_valid`: leeres erwartetes Token → `True` (Auth aus); gesetztes Token: korrekt → `True`, falsch/`None` → `False`.
  - GET/POST ohne Header / falsches Token → `401`; mit korrektem Token → `200`/`204`/`202`.
  - WS ohne/falschen `?token` → Verbindung wird **nicht** akzeptiert (Close); mit korrektem Token → akzeptiert + Stream.
  - Lauf-Lock: zweiter `POST` während aktivem Lauf → `409`; nach Lauf-Ende (auch bei Orchestrator-Fehler) → wieder `202`.
- **Frontend** (Vitest/RTL, gegen Fakes):
  - Kein Token → Login-Screen sichtbar.
  - Token eingeben → wird gespeichert + Seite lädt.
  - `401` beim Laden → Login-Screen + „Falsches Passwort".
  - API-/WS-Client hängen das Token an (Header bzw. `?token=`).

## 7. Abgrenzung / Sicherheit (ehrlich)

**Shared-Secret-Schutz** — ein Passwort für alle, passend für eine Dozenten-Demo, **keine** Bank-Sicherheit. Kein Account-System, kein Rate-Limit, kein CSRF-/Brute-Force-Schutz über das konstante Vergleichen hinaus. Token als WS-Query-Param kann theoretisch in Server-Logs erscheinen (für eine Demo vertretbar; später auf „Token als erste WS-Nachricht" umstellbar — Folge-Aufgabe). Bei leerem `AAIA_ACCESS_TOKEN` ist die API **offen** (nur lokal gedacht) — die Deploy-Doku markiert das Setzen als Pflicht.

---

*Querverweise: `docs/superpowers/specs/2026-06-22-api-bridge-cockpit-design.md` (Backend), `docs/superpowers/specs/2026-06-22-frontend-cockpit-overview-design.md` (Frontend), `docs/superpowers/specs/2026-06-22-render-deploy-design.md` (Deploy). Status/Folge-Aufgaben: `docs/open_todos.md`.*
