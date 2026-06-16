import math


def apply_costs(trade_return: float, cost_per_side: float = 0.0005) -> float:
    """Round-Trip-Transaktionskosten (Kauf + Verkauf) vom Trade-Return abziehen.

    cost_per_side als Dezimal (0.0005 = 5 bps je Seite).
    """
    return trade_return - 2.0 * cost_per_side


def sharpe_ratio(
    returns: list[float],
    risk_free: float = 0.0,
    annualization: int = 252,
) -> float:
    """(mean_excess / std) * sqrt(annualization). Std=0 oder n<2 → 0.0."""
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free for r in returns]
    mean = sum(excess) / len(excess)
    var = sum((r - mean) ** 2 for r in excess) / (len(excess) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0.0:
        return 0.0
    return (mean / std) * math.sqrt(annualization)


def sortino_ratio(
    returns: list[float],
    risk_free: float = 0.0,
    annualization: int = 252,
) -> float:
    """mean_excess / downside_deviation * sqrt(annualization). Keine Downside → 0.0."""
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free for r in returns]
    mean = sum(excess) / len(excess)
    downside = [min(0.0, r) for r in excess]
    dd = math.sqrt(sum(d ** 2 for d in downside) / len(excess))
    if dd == 0.0:
        return 0.0
    return (mean / dd) * math.sqrt(annualization)


def max_drawdown(returns: list[float]) -> float:
    """Maximaler Drawdown (<= 0.0) aus kumulativer Equity-Kurve über Trade-Returns."""
    if not returns:
        return 0.0
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= (1.0 + r)
        if equity > peak:
            peak = equity
        dd = (equity - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return max_dd


def profit_factor(returns: list[float]) -> float:
    """Sum(Gewinne) / |Sum(Verluste)|. Keine Verluste → inf, keine Trades → 0.0."""
    if not returns:
        return 0.0
    gains = sum(r for r in returns if r > 0)
    losses = sum(r for r in returns if r < 0)
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / abs(losses)


def annualized_return(returns: list[float], periods_per_year: float = 1.0) -> float:
    """Geometrisch kumulierter, auf Jahresbasis hochgerechneter Return."""
    if not returns:
        return 0.0
    growth = 1.0
    for r in returns:
        growth *= (1.0 + r)
    years = len(returns) / periods_per_year if periods_per_year > 0 else len(returns)
    if years <= 0:
        return 0.0
    return growth ** (1.0 / years) - 1.0
