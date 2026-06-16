from core.domain.models import Signal, SignalStatus
from core.utils.aggregation import weighted_signal

A = SignalStatus.AVAILABLE
U = SignalStatus.UNAVAILABLE


def test_alle_bullish_ergibt_bullish():
    sig, conf = weighted_signal([
        (Signal.BULLISH, 1.0, A),
        (Signal.BULLISH, 1.0, A),
    ])
    assert sig == Signal.BULLISH
    assert conf == 1.0


def test_gegenlaeufig_gleichgewichtet_ist_neutral():
    sig, conf = weighted_signal([
        (Signal.BULLISH, 1.0, A),
        (Signal.BEARISH, 1.0, A),
    ])
    assert sig == Signal.NEUTRAL
    assert conf == 0.0


def test_schwelle_0_15_neutral_bei_kleinem_net():
    # net = (1*1 + 9*0)/10 = 0.1 < 0.15 → NEUTRAL
    sig, conf = weighted_signal([
        (Signal.BULLISH, 1.0, A),
        (Signal.NEUTRAL, 9.0, A),
    ])
    assert sig == Signal.NEUTRAL
    assert abs(conf - 0.1) < 1e-9


def test_schwelle_0_15_bullish_knapp_darueber():
    # net = (2*1 + 8*0)/10 = 0.2 > 0.15 → BULLISH
    sig, conf = weighted_signal([
        (Signal.BULLISH, 2.0, A),
        (Signal.NEUTRAL, 8.0, A),
    ])
    assert sig == Signal.BULLISH
    assert abs(conf - 0.2) < 1e-9


def test_bearish_unterhalb_minus_0_15():
    # net = -0.2 < -0.15 → BEARISH
    sig, conf = weighted_signal([
        (Signal.BEARISH, 2.0, A),
        (Signal.NEUTRAL, 8.0, A),
    ])
    assert sig == Signal.BEARISH
    assert abs(conf - 0.2) < 1e-9


def test_unavailable_wird_ignoriert_und_renormalisiert():
    # UNAVAILABLE-Bearish (Gewicht 5) wird ENTFERNT.
    # Verbleibend: BULLISH w=1, BULLISH w=1 → net = 2/2 = +1.0 → BULLISH.
    # Würde das UNAVAILABLE-Item als NEUTRAL mitzaehlen, waere
    # net = 2/7 ≈ 0.286; zaehlte es als BEARISH mit, sogar negativ.
    sig, conf = weighted_signal([
        (Signal.BULLISH, 1.0, A),
        (Signal.BULLISH, 1.0, A),
        (Signal.BEARISH, 5.0, U),
    ])
    assert sig == Signal.BULLISH
    assert conf == 1.0


def test_alle_unavailable_ist_neutral():
    sig, conf = weighted_signal([
        (Signal.BULLISH, 1.0, U),
        (Signal.BEARISH, 2.0, U),
    ])
    assert sig == Signal.NEUTRAL
    assert conf == 0.0


def test_leere_liste_ist_neutral():
    sig, conf = weighted_signal([])
    assert sig == Signal.NEUTRAL
    assert conf == 0.0


def test_summe_der_gewichte_null_ist_neutral():
    # Alle verbleibenden Gewichte 0 → keine Division durch 0
    sig, conf = weighted_signal([
        (Signal.BULLISH, 0.0, A),
        (Signal.BEARISH, 0.0, A),
    ])
    assert sig == Signal.NEUTRAL
    assert conf == 0.0
