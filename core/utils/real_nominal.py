def to_real(nominal_rate: float, inflation: float) -> float:
    """Exakte Fisher-Bereinigung: ((1+nominal_rate/100)/(1+inflation/100)-1)*100.
    Eingaben in Prozentpunkten (8.0 = 8 %)."""
    return ((1.0 + nominal_rate / 100.0) / (1.0 + inflation / 100.0) - 1.0) * 100.0


def excess_over_nominal_gdp(growth: float, nominal_gdp_growth: float) -> float:
    """growth - nominal_gdp_growth (Prozentpunkte)."""
    return growth - nominal_gdp_growth
