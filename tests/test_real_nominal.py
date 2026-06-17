from core.utils.real_nominal import to_real, excess_over_nominal_gdp


def test_to_real_exakte_fisher_formel():
    # ((1+0.08)/(1+0.05)-1)*100 = (1.08/1.05-1)*100 = 2.857142...
    assert abs(to_real(8.0, 5.0) - 2.857142857) < 1e-6


def test_to_real_unterscheidet_sich_von_naiver_subtraktion():
    # Naive Approximation 8-5=3.0; exakt ist ~2.857 → echte Differenz
    assert abs(to_real(8.0, 5.0) - 3.0) > 0.1


def test_to_real_null_inflation_ist_nominal():
    assert abs(to_real(4.0, 0.0) - 4.0) < 1e-9


def test_to_real_negativ_bei_inflation_ueber_nominal():
    # ((1+0.02)/(1+0.05)-1)*100 = -2.857142...
    assert to_real(2.0, 5.0) < 0.0
    assert abs(to_real(2.0, 5.0) - (-2.857142857)) < 1e-6


def test_excess_over_nominal_gdp_positiv():
    # Geldmengenwachstum 9 % über nominalem BIP-Wachstum 4 % → +5.0 pp
    assert excess_over_nominal_gdp(9.0, 4.0) == 5.0


def test_excess_over_nominal_gdp_negativ():
    assert excess_over_nominal_gdp(3.0, 4.0) == -1.0


def test_to_real_inflation_minus_100_wirft_value_error():
    # inflation=-100 % → Nenner 0 → ValueError erwartet
    import pytest
    with pytest.raises(ValueError):
        to_real(2.0, -100.0)
