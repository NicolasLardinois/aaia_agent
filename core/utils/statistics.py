import math


Z_THRESHOLD = 2.5


def z_score(current: float, history: list[float]) -> float:
    if len(history) < 3:
        return 0.0
    mean = sum(history) / len(history)
    variance = sum((v - mean) ** 2 for v in history) / (len(history) - 1)
    std = math.sqrt(variance) if variance > 0 else 0.0
    if std == 0.0:
        return 0.0
    return (current - mean) / std


def compute_severity(statistical: list[str], contradictions: list[str]) -> str:
    has_stat = len(statistical) > 0
    has_contra = len(contradictions) > 0
    if has_stat and has_contra:
        return "high"
    if len(statistical) >= 2 or len(contradictions) >= 2:
        return "medium"
    if has_stat or has_contra:
        return "low"
    return "none"


from statistics import median, NormalDist


ROBUST_Z_THRESHOLD = 3.5
MIN_SAMPLE_N = 20


def robust_z_score(current: float, history: list[float], min_n: int = MIN_SAMPLE_N) -> float:
    """Median/MAD-basiert (Iglewicz-Hoaglin): 0.6745*(current-median)/MAD.
    0.0 falls len(history)<min_n oder MAD==0."""
    if len(history) < min_n:
        return 0.0
    med = median(history)
    mad = median([abs(v - med) for v in history])
    if mad == 0.0:
        return 0.0
    return 0.6745 * (current - med) / mad


def bonferroni_z_threshold(base_threshold: float, n_tests: int) -> float:
    """Zweiseitige Bonferroni-Korrektur der Z-Schwelle:
    alpha = 2*(1-Phi(base)); alpha_adj = alpha/n; return Phi^-1(1-alpha_adj/2)."""
    if n_tests < 1:
        return base_threshold
    nd = NormalDist()
    alpha = 2.0 * (1.0 - nd.cdf(base_threshold))
    alpha_adj = alpha / n_tests
    return nd.inv_cdf(1.0 - alpha_adj / 2.0)
