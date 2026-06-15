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
