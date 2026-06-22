from adapters.event_bus.redis_bus import InMemoryEventBus
from core.domain.events import MacroChiefReady, SentimentChiefReady


def test_subscribe_all_receives_every_event_type():
    bus = InMemoryEventBus()
    received = []
    bus.subscribe_all(received.append)
    bus.publish(MacroChiefReady(source="m", payload={}))
    bus.publish(SentimentChiefReady(source="s", payload={}))
    assert [type(e).__name__ for e in received] == ["MacroChiefReady", "SentimentChiefReady"]


def test_typed_subscribe_still_works_alongside_subscribe_all():
    bus = InMemoryEventBus()
    typed, all_ = [], []
    bus.subscribe(MacroChiefReady, typed.append)
    bus.subscribe_all(all_.append)
    bus.publish(MacroChiefReady(source="m", payload={}))
    assert len(typed) == 1 and len(all_) == 1


def test_failing_all_handler_does_not_break_publish():
    bus = InMemoryEventBus()
    seen = []
    bus.subscribe_all(lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
    bus.subscribe_all(seen.append)  # zweiter Handler laeuft trotzdem
    bus.publish(MacroChiefReady(source="m", payload={}))
    assert len(seen) == 1
