from core.utils.statistics import robust_z_score, z_score


def _winsorize(history: list[float], fraction: float) -> list[float]:
    """Kappt unterste und oberste `fraction`-Quantile auf ihre Grenzwerte."""
    if fraction <= 0.0 or len(history) < 2:
        return list(history)
    ordered = sorted(history)
    n = len(ordered)
    lo_idx = int(fraction * (n - 1))
    hi_idx = int((1.0 - fraction) * (n - 1))
    lo = ordered[lo_idx]
    hi = ordered[hi_idx]
    return [min(max(v, lo), hi) for v in history]


def percentile_rank(value: float, history: list[float], winsorize: float = 0.0) -> float | None:
    """Empirischer Rang-Perzentil 0..100 = Anteil der (ggf. winsorisierten)
    Historie < value. None falls history leer."""
    if not history:
        return None
    sample = _winsorize(history, winsorize)
    below = sum(1 for v in sample if v < value)
    return 100.0 * below / len(sample)


def zscore_vs_history(value: float, history: list[float], robust: bool = True, min_n: int = 20) -> float:
    """robust=True → robust_z_score, sonst z_score (aus statistics.py)."""
    if robust:
        return robust_z_score(value, history, min_n=min_n)
    return z_score(value, history)
