from core.domain.models import Signal, RiskAffinity, CreditBand
from core.utils.bond_risk import rating_to_band, credit_contribution, aggregate_bond_signal


def test_rating_to_band_grenzen():
    assert rating_to_band("AAA")  == CreditBand.SICHER
    assert rating_to_band("BBB-") == CreditBand.SICHER     # untere IG-Kante
    assert rating_to_band("BB+")  == CreditBand.MITTEL      # obere HY-Kante
    assert rating_to_band("B-")   == CreditBand.MITTEL
    assert rating_to_band("CCC+") == CreditBand.RISKANT     # Distressed-Beginn
    assert rating_to_band("D")    == CreditBand.RISKANT
    assert rating_to_band("bbb-") == CreditBand.SICHER      # case-insensitiv
    assert rating_to_band(None)   is None
    assert rating_to_band("NR")   is None                   # unbekannt


def test_credit_contribution_tabelle():
    K, N, R = RiskAffinity.KONSERVATIV, RiskAffinity.NEUTRAL, RiskAffinity.RISIKOFREUDIG
    assert credit_contribution(CreditBand.SICHER, K) == 0.0
    assert credit_contribution(CreditBand.SICHER, R) == 0.0
    assert credit_contribution(CreditBand.MITTEL, K) == -1.0
    assert credit_contribution(CreditBand.MITTEL, N) == -0.5
    assert credit_contribution(CreditBand.MITTEL, R) == 0.0
    assert credit_contribution(CreditBand.RISKANT, K) == -1.5
    assert credit_contribution(CreditBand.RISKANT, N) == -1.0
    assert credit_contribution(CreditBand.RISKANT, R) == -0.5


def test_aggregate_bb_bond_skaliert_mit_affinitaet():
    # BB (Mittel), Rendite attraktiv: metrics +1, duration 0, spread 0
    base = (Signal.BULLISH, Signal.NEUTRAL, Signal.NEUTRAL, CreditBand.MITTEL)
    assert aggregate_bond_signal(*base, RiskAffinity.KONSERVATIV)[0]   == Signal.NEUTRAL
    assert aggregate_bond_signal(*base, RiskAffinity.NEUTRAL)[0]       == Signal.NEUTRAL
    assert aggregate_bond_signal(*base, RiskAffinity.RISIKOFREUDIG)[0] == Signal.BULLISH


def test_aggregate_ccc_bond_bleibt_riskant():
    # CCC (Riskant), Stress: metrics +1, duration 0, spread -1
    base = (Signal.BULLISH, Signal.NEUTRAL, Signal.BEARISH, CreditBand.RISKANT)
    assert aggregate_bond_signal(*base, RiskAffinity.KONSERVATIV)[0]   == Signal.BEARISH
    assert aggregate_bond_signal(*base, RiskAffinity.NEUTRAL)[0]       == Signal.BEARISH
    assert aggregate_bond_signal(*base, RiskAffinity.RISIKOFREUDIG)[0] == Signal.NEUTRAL


def test_aggregate_unverfuegbares_credit_renormalisiert():
    # Kein Rating → credit_band None → nur metrics/duration/spread zählen.
    sig, conf = aggregate_bond_signal(Signal.BULLISH, Signal.BULLISH, Signal.NEUTRAL, None, RiskAffinity.NEUTRAL)
    assert sig == Signal.BULLISH            # (1+1+0)/3 = 0.667 > 0.15
    assert 0.0 < conf <= 1.0


def test_aggregate_alles_unverfuegbar_ist_neutral():
    assert aggregate_bond_signal(None, None, None, None, RiskAffinity.NEUTRAL) == (Signal.NEUTRAL, 0.0)
