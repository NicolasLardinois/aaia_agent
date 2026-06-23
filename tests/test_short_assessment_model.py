from core.domain.models import ShortAssessment, ShortAction, DeepDiveResult
from core.domain.taxonomy import Underlying, Wrapper


def test_short_assessment_defaults():
    a = ShortAssessment(
        underlying=Underlying.EQUITY, wrapper=Wrapper.SINGLE,
        short_action=ShortAction.NONE, confidence=0.1,
        archetypes=[], thesis_flags=[], regime_effect="neutral",
        squeeze_risk="low", hard_to_borrow=False)
    assert a.borrow_rate_manual is None
    assert a.suggested_size_pct is None
    assert a.stop_pct is None


def test_deepdive_has_conflict_fields():
    import dataclasses
    names = {f.name for f in dataclasses.fields(DeepDiveResult)}
    assert {"short_assessment", "conflict", "conflict_reason"} <= names
