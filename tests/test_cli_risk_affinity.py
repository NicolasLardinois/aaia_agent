import pytest
from app.main import _parse_risk_affinity
from core.domain.models import RiskAffinity


def test_bond_ohne_affinitaet_bricht_ab():
    with pytest.raises(SystemExit):
        _parse_risk_affinity([], "bond")


def test_bond_ungueltige_affinitaet_bricht_ab():
    with pytest.raises(SystemExit):
        _parse_risk_affinity(["--risk-affinity", "yolo"], "bond")


def test_bond_gueltige_affinitaet():
    assert _parse_risk_affinity(["--risk-affinity", "neutral"], "bond") == RiskAffinity.NEUTRAL


def test_nicht_bond_braucht_keine_affinitaet():
    assert _parse_risk_affinity([], "equity") is None
