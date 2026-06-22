"""HTTP- und WebSocket-Routen fuer den Cockpit-Flow (mit Token-Schutz).

Alle Endpunkte erfordern ein gueltiges Token (AAIA_ACCESS_TOKEN; leer -> Auth aus).
HTTP: Authorization: Bearer <token>. WS: ?token=<token> (Browser koennen bei WS
keine Header setzen). POST liefert 409, wenn bereits ein Lauf laeuft.
"""
from fastapi import APIRouter, Depends, Response, WebSocket, WebSocketDisconnect, status

from adapters.api.auth import require_token, token_valid
from adapters.api.cockpit_serializer import cockpit_to_dict
from adapters.api.run_manager import RunManager


def build_router(run_manager: RunManager) -> APIRouter:
    router = APIRouter()

    @router.get("/api/cockpit")
    def get_cockpit(_: None = Depends(require_token)):
        if run_manager.latest is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        return cockpit_to_dict(run_manager.latest)

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
            run_manager.broadcaster.disconnect(websocket)

    return router
