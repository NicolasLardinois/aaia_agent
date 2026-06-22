"""Verwaltet offene WebSocket-Verbindungen und sendet Nachrichten an alle.

Framework-arm: erwartet nur Objekte mit async send_json(dict) — FastAPIs
WebSocket erfuellt das, im Test ein Fake. Eine Verbindung, die beim Senden
wirft, wird entfernt (eine tote Verbindung darf den Broadcast nicht abbrechen).
"""
import logging

_logger = logging.getLogger(__name__)


class WebSocketBroadcaster:
    def __init__(self):
        self.connections: list = []

    def connect(self, ws) -> None:
        self.connections.append(ws)

    def disconnect(self, ws) -> None:
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in list(self.connections):
            try:
                await ws.send_json(message)
            except Exception:
                _logger.warning("WS-Senden fehlgeschlagen — Verbindung entfernt", exc_info=True)
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
