from core.domain.models import ConflictItem


def test_conflict_item_defaults():
    c = ConflictItem(ticker="AAPL", direction="long", verdict="EXIT", reason="screent short")
    assert c.status == "open" and c.source == "on_demand"
    assert c.user_decision is None and c.id is None
