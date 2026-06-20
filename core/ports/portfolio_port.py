from abc import ABC, abstractmethod

from core.domain.models import PositionState
from core.domain.portfolio import Position


class PortfolioPort(ABC):
    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def position_state_for(self, ticker: str) -> PositionState: ...
