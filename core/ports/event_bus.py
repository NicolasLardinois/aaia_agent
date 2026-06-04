from abc import ABC, abstractmethod
from typing import Callable
from core.domain.events import AgentEvent


class EventBus(ABC):
    @abstractmethod
    def publish(self, event: AgentEvent) -> None:
        ...

    @abstractmethod
    def subscribe(self, event_type: type, handler: Callable[[AgentEvent], None]) -> None:
        ...
