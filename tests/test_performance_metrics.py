import math
import pytest
from core.utils.performance_metrics import (
    sharpe_ratio, sortino_ratio, max_drawdown,
    profit_factor, annualized_return, apply_costs,
)


def test_sharpe_zero_for_empty():
    assert sharpe_ratio([]) == 0.0


def test_sharpe_zero_for_constant_returns():
    # Std=0 → kein Risiko messbar → 0.0 (kein ZeroDivision)
    assert sharpe_ratio([0.01, 0.01, 0.01]) == 0.0


def test_sharpe_positive_for_positive_excess():
    rets = [0.02, 0.01, 0.03, -0.01, 0.02]
    s = sharpe_ratio(rets, risk_free=0.0, annualization=1)
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    expected = mean / math.sqrt(var)
    assert s == pytest.approx(expected, abs=1e-9)


def test_sharpe_annualization_factor():
    rets = [0.01, -0.005, 0.02, 0.0, 0.015]
    s1 = sharpe_ratio(rets, annualization=1)
    s252 = sharpe_ratio(rets, annualization=252)
    assert s252 == pytest.approx(s1 * math.sqrt(252), abs=1e-9)


def test_sortino_uses_downside_deviation():
    rets = [0.02, -0.01, 0.03, -0.02, 0.01]
    downside = [min(0.0, r) for r in rets]
    dd = math.sqrt(sum(d ** 2 for d in downside) / len(rets))
    mean = sum(rets) / len(rets)
    expected = (mean / dd)
    assert sortino_ratio(rets, risk_free=0.0, annualization=1) == pytest.approx(expected, abs=1e-9)


def test_sortino_no_downside_returns_zero():
    assert sortino_ratio([0.01, 0.02, 0.03], annualization=1) == 0.0


def test_max_drawdown_simple():
    # Equity: 1.0 → 1.1 → 0.88 (von 1.1) → 0.99 ; max DD = (0.88-1.1)/1.1
    rets = [0.10, -0.20, 0.125]
    dd = max_drawdown(rets)
    assert dd == pytest.approx(-0.20, abs=1e-9)


def test_max_drawdown_no_loss_is_zero():
    assert max_drawdown([0.01, 0.02, 0.03]) == 0.0


def test_profit_factor_basic():
    rets = [0.05, -0.02, 0.03, -0.01]
    pf = profit_factor(rets)
    assert pf == pytest.approx(0.08 / 0.03, abs=1e-9)


def test_profit_factor_no_losses_is_inf():
    assert profit_factor([0.01, 0.02]) == float("inf")


def test_profit_factor_no_trades_is_zero():
    assert profit_factor([]) == 0.0


def test_annualized_return_compounds():
    # zwei +21% Trades à 0.5 Jahre → (1.21*1.21)^(1/1.0)-1 = 0.4641
    ar = annualized_return([0.21, 0.21], periods_per_year=2)
    assert ar == pytest.approx(1.21 ** 2 - 1, abs=1e-9)


def test_apply_costs_subtracts_round_trip():
    # 0.001 (10 bps) pro Seite → 0.002 Round-Trip auf einen Trade-Return
    assert apply_costs(0.05, cost_per_side=0.001) == pytest.approx(0.048, abs=1e-12)
