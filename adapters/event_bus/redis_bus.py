import logging
from collections import defaultdict
from typing import Callable

from core.domain.events import AgentEvent
from core.ports.event_bus import EventBus

_logger = logging.getLogger(__name__)


class InMemoryEventBus(EventBus):
    """Einfacher In-Memory Bus für lokale Entwicklung ohne Redis."""

    def __init__(self):
        self._handlers: dict[type, list[Callable]] = defaultdict(list)
        self._log: list[AgentEvent] = []

    def publish(self, event: AgentEvent) -> None:
        self._log.append(event)
        for handler in self._handlers.get(type(event), []):
            try:
                handler(event)
            except Exception:
                _logger.exception(
                    "Handler %s raised for %s — skipping",
                    handler, type(event).__name__,
                )

    def subscribe(self, event_type: type, handler: Callable[[AgentEvent], None]) -> None:
        self._handlers[event_type].append(handler)

    def get_log(self) -> list[AgentEvent]:
        return list(self._log)


# TODO: Redis-Implementierung für Produktion
# class RedisEventBus(EventBus):
#     def __init__(self, host: str, port: int):
#         import redis
#         self.client = redis.Redis(host=host, port=port)
#
#     def publish(self, event: AgentEvent) -> None:
#         import json
#         self.client.publish(type(event).__name__, json.dumps(event.payload))
#
#     def subscribe(self, event_type: type, handler: Callable) -> None:
#         # Benötigt separaten Subscriber-Thread
#         raise NotImplementedError
