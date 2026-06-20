import inspect
from core.domain.portfolio import Position, PortfolioError
from core.ports.portfolio_port import PortfolioPort


def test_position_requires_direction():
    p = Position(ticker="AAPL", shares=10, entry_price=150.0, direction="short")
    assert p.direction == "short" and p.entry_price == 150.0


def test_portfolio_error_is_exception():
    assert issubclass(PortfolioError, Exception)


def test_port_is_abstract():
    assert inspect.isabstract(PortfolioPort)
    assert {"get_positions", "position_state_for"} <= set(dir(PortfolioPort))
