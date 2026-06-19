import dataclasses
from core.domain.models import ConflictResolution, DeepDiveResult


def test_conflict_resolution_fields():
    cr = ConflictResolution(verdict="EXIT", reasoning="weil…")
    assert cr.verdict == "EXIT" and cr.reasoning == "weil…"


def test_deepdive_has_conflict_resolution_field():
    names = {f.name for f in dataclasses.fields(DeepDiveResult)}
    assert "conflict_resolution" in names
