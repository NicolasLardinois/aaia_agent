"""HTTP- und WebSocket-Routen fuer den Cockpit-Flow.

GET liest das letzte Ergebnis (keine externen Calls). POST stoesst einen Lauf
als Hintergrund-Task an und antwortet sofort (202 + run_id) — async def, damit
asyncio.create_task im RunManager einen laufenden Event-Loop hat. WS registriert
die Verbindung beim Broadcaster und haelt sie offen, bis der Client trennt.
"""
from fastapi import APIRouter, Response, WebSocket, WebSocketDisconnect, status

from adapters.api.cockpit_serializer import cockpit_to_dict
from adapters.api.run_manager import RunManager


def build_router(run_manager: RunManager) -> APIRouter:
    router = APIRouter()

    @router.get("/api/cockpit")
    def get_cockpit():
        if run_manager.latest is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        return cockpit_to_dict(run_manager.latest)

    @router.post("/api/cockpit/run", status_code=status.HTTP_202_ACCEPTED)
    async def post_run():
        run_id = run_manager.start_run()
        return {"run_id": run_id}

    @router.websocket("/ws/cockpit")
    async def ws_cockpit(websocket: WebSocket):
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
