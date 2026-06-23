"""Reine Fund-Info-Mathematik (TER ist ein Roh-Stammdatum; hier nur der Tracking-Error).

Keine I/O. Siehe docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md §6.6.
Einheiten: Rückgabe als Dezimal p. a.
"""
import math


def tracking_error_ann(etf_returns: list[float], benchmark_returns: list[float],
                       periods_per_year: int = 252) -> float | None:
    """Annualisierte Stdev der Renditedifferenz ETF−Benchmark = stdev(R_etf − R_index)·√P.

    Misst die Abbildungstreue des Fonds zum Benchmark. Ungleiche oder zu kurze Reihen
    (Benchmark unbekannt/fehlend) → None (UNAVAILABLE); die TER bleibt davon unberührt."""
    if (len(etf_returns) != len(benchmark_returns)) or len(etf_returns) < 2:
        return None
    diffs = [e - b for e, b in zip(etf_returns, benchmark_returns)]
    mean = sum(diffs) / len(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / (len(diffs) - 1)
    return (var ** 0.5) * math.sqrt(periods_per_year)
