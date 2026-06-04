from agents.backtester.top_down_backtester_agent import _is_adjacent, _accuracy


def test_adjacent_same_regime():
    assert _is_adjacent("Boom", "Boom") is True


def test_adjacent_neighbor():
    assert _is_adjacent("Boom", "Aufschwung") is True
    assert _is_adjacent("Rezession", "Abschwung") is True


def test_not_adjacent_far():
    assert _is_adjacent("Boom", "Rezession") is False
    assert _is_adjacent("Boom", "Abschwung") is False


def test_accuracy_all_correct():
    entries = [{"regime": "Boom"}, {"regime": "Aufschwung"}]
    assert _accuracy(entries, "Boom") == 1.0


def test_accuracy_none_correct():
    entries = [{"regime": "Rezession"}, {"regime": "Abschwung"}]
    assert _accuracy(entries, "Boom") == 0.0


def test_accuracy_empty():
    assert _accuracy([], "Boom") == 0.0


from agents.backtester.judgment_backtester_agent import _verdict as j_verdict


def test_judgment_verdict_buy_correct():
    assert j_verdict("BUY", 5.0) == "correct"


def test_judgment_verdict_buy_incorrect():
    assert j_verdict("BUY", -5.0) == "incorrect"


def test_judgment_verdict_hold_correct():
    assert j_verdict("HOLD", 3.0) == "correct"


def test_judgment_verdict_sell_correct():
    assert j_verdict("SELL", -4.0) == "correct"


from agents.backtester.bottom_up_backtester_agent import _verdict as bu_verdict


def test_bottomup_verdict_bullish_correct():
    assert bu_verdict("bullish", 3.0) == "correct"


def test_bottomup_verdict_bearish_correct():
    assert bu_verdict("bearish", -3.0) == "correct"


def test_bottomup_verdict_neutral_correct():
    assert bu_verdict("neutral", 1.0) == "correct"
