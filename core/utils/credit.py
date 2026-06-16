"""Credit-Utilities: Rating-Normalisierung (S&P/Moody's/Fitch → kanonisch),
PD-Lookup und Credit Triangle. PD/LGD/Spread durchgängig als Dezimal.
"""
from __future__ import annotations

# Kanonische Skala = S&P/Fitch-Notation (Fitch ist mit S&P notationsgleich).
# Moody's → S&P-Mapping (Notch-genau).
_MOODYS_TO_SP: dict[str, str] = {
    "AA1": "AA+", "AA2": "AA", "AA3": "AA-",
    "A1": "A+", "A2": "A", "A3": "A-",
    "BAA1": "BBB+", "BAA2": "BBB", "BAA3": "BBB-",
    "BA1": "BB+", "BA2": "BB", "BA3": "BB-",
    "B1": "B+", "B2": "B", "B3": "B-",
    "CAA1": "CCC+", "CAA2": "CCC", "CAA3": "CCC-",
    "CA": "CC", "C": "C",
}
_SP_RATINGS = {
    "AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
    "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-",
    "B+", "B", "B-", "CCC+", "CCC", "CCC-", "CC", "C", "D",
}

# PD (1-Jahres-Ausfallwahrscheinlichkeit) je kanonischem Bucket, DEZIMAL.
# Grobe Moody's/S&P-Langfristmittel; Notches einer Klasse teilen die Klassen-PD.
_PD: dict[str, float] = {
    "AAA": 0.0,
    "AA+": 0.0001, "AA": 0.0001, "AA-": 0.0002,
    "A+": 0.0004, "A": 0.0006, "A-": 0.0010,
    "BBB+": 0.0012, "BBB": 0.0016, "BBB-": 0.0018,
    "BB+": 0.0060, "BB": 0.0090, "BB-": 0.0120,
    "B+": 0.0250, "B": 0.0430, "B-": 0.0700,
    "CCC+": 0.1200, "CCC": 0.1400, "CCC-": 0.2000,
    "CC": 0.3000, "C": 0.5000, "D": 1.0000,
}


def normalize_rating(raw: str | None) -> str | None:
    """S&P/Fitch/Moody's-Rating → kanonische S&P-Notation. None bei unbekannt."""
    if raw is None:
        return None
    r = raw.strip().upper().replace(" ", "")
    if r in _SP_RATINGS:
        return r
    if r in _MOODYS_TO_SP:
        return _MOODYS_TO_SP[r]
    # Moody's ohne Notch (z. B. "AA", "BAA", "CAA") grob auf mittleren Notch
    # "AA", "A", "B" werden bereits via _SP_RATINGS getroffen → hier nur echte Moody's-Klassen
    _MOODYS_CLASS = {"BAA": "BBB", "BA": "BB", "CAA": "CCC"}
    if r in _MOODYS_CLASS:
        return _MOODYS_CLASS[r]
    return None


def default_probability(raw: str | None) -> float | None:
    """Exakte 1J-PD (Dezimal) auf normalisierter Skala. KEIN startswith."""
    norm = normalize_rating(raw)
    if norm is None:
        return None
    return _PD.get(norm)


def is_investment_grade(raw: str | None) -> bool:
    """Binäre IG-Grenze: ≥ BBB-/Baa3 == Investment Grade."""
    norm = normalize_rating(raw)
    if norm is None:
        return False
    ig = {"AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"}
    return norm in ig


def credit_triangle_spread(pd: float, lgd: float) -> float:
    """Credit Triangle: erwarteter Kreditspread ≈ PD * LGD (Dezimal).

    pd, lgd, Rückgabe alle als Dezimal. lgd = 1 - recovery_rate.
    """
    return pd * lgd
