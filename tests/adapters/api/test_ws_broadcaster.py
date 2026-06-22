import asyncio
from adapters.api.ws_broadcaster import WebSocketBroadcaster


class _FakeWS:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []
    async def send_json(self, message):
        if self.fail:
            raise RuntimeError("connection closed")
        self.sent.append(message)


def test_broadcast_reaches_all_connections():
    b = WebSocketBroadcaster()
    a, c = _FakeWS(), _FakeWS()
    b.connect(a); b.connect(c)
    asyncio.run(b.broadcast({"type": "X"}))
    assert a.sent == [{"type": "X"}]
    assert c.sent == [{"type": "X"}]


def test_broadcast_drops_dead_connection_and_keeps_others():
    b = WebSocketBroadcaster()
    dead, alive = _FakeWS(fail=True), _FakeWS()
    b.connect(dead); b.connect(alive)
    asyncio.run(b.broadcast({"type": "X"}))
    assert alive.sent == [{"type": "X"}]
    assert dead not in b.connections
    assert alive in b.connections
