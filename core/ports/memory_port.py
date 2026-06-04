from abc import ABC, abstractmethod
from typing import Optional


class MemoryPort(ABC):

    @abstractmethod
    def save_analysis(
        self,
        result,           # DeepDiveResult
        cockpit,          # CockpitResult | None
        price: Optional[float] = None,
    ) -> None: ...

    @abstractmethod
    def load_history(self, ticker: str, days: int = 90) -> list[dict]: ...

    @abstractmethod
    def load_global_history(self, days: int = 90) -> list[dict]: ...

    @abstractmethod
    def load_latest_backtester_report(self, backtester_type: str) -> dict: ...

    @abstractmethod
    def save_backtester_report(self, report: dict) -> None: ...

    @abstractmethod
    def save_portfolio_snapshot(self, snapshot: dict) -> None: ...

    @abstractmethod
    def load_latest_portfolio_snapshot(self) -> Optional[dict]: ...
