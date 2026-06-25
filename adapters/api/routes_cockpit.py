"""HTTP- und WebSocket-Routen fuer den Cockpit-Flow (mit Token-Schutz).

Die Daten-/Lauf-Endpunkte erfordern ein gueltiges Token (AAIA_ACCESS_TOKEN; leer -> Auth aus).
HTTP: Authorization: Bearer <token>. WS: ?token=<token> (Browser koennen bei WS
keine Header setzen). POST liefert 409, wenn bereits ein Lauf laeuft.
Ausnahme: GET /healthz ist OEFFENTLICH (Render-Health-Check darf kein Passwort brauchen).
"""
from fastapi import APIRouter, Depends, Response, WebSocket, WebSocketDisconnect, status

from adapters.api.auth import require_token, token_valid
from adapters.api.run_manager import RunManager


def build_router(run_manager: RunManager) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz")
    def healthz():
        # Oeffentlicher Health-Check (OHNE Token) fuer den Render-Health-Check ->
        # liefert immer 200, auch wenn AAIA_ACCESS_TOKEN gesetzt ist. Ein
        # Health-Check darf kein App-Passwort brauchen.
        return {"status": "ok"}

    @router.get("/api/cockpit")
    def get_cockpit(_: None = Depends(require_token)):
        # latest_snapshot() liefert das frisch serialisierte In-Memory-Ergebnis
        # oder — nach einem Neustart — den von Disk geladenen Snapshot (sonst None).
        snapshot = run_manager.latest_snapshot()
        if snapshot is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        return snapshot

    @router.post("/api/cockpit/run", status_code=status.HTTP_202_ACCEPTED)
    async def post_run(_: None = Depends(require_token)):
        run_id = run_manager.start_run()
        if run_id is None:
            return Response(status_code=status.HTTP_409_CONFLICT)  # laeuft bereits
        return {"run_id": run_id}

    @router.websocket("/ws/cockpit")
    async def ws_cockpit(websocket: WebSocket):
        # WS-Auth: Token als Query-Param; vor accept() pruefen.
        if not token_valid(websocket.query_params.get("token")):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        await websocket.accept()
        run_manager.broadcaster.connect(websocket)
        try:
            while True:
                await websocket.receive_text()  # haelt die Verbindung; erkennt Disconnect
        except WebSocketDisconnect:
            pass
        finally:
            # Auf JEDEM Exit-Pfad deregistrieren (auch bei abnormalem Close/Cancel),
            # sonst bleibt eine tote Verbindung im Broadcaster haengen.
            run_manager.broadcaster.disconnect(websocket)

    return router
