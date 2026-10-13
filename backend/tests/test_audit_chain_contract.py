"""Pure unit tests of v0.7 PostgreSQL payload contract (no DB/HSM)."""
import hashlib
from uuid import UUID


def event_hash(seq, prev_hash, entity_type, entity_id, event_type, actor_id, old_status, new_status):
    parts = [str(seq), prev_hash, entity_type, str(entity_id), event_type,
             str(actor_id) if actor_id is not None else "", old_status or "", new_status or ""]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def verify_chain(events, anchor="0" * 64):
    previous = anchor
    for event in events:
        if event["prev_hash"] != previous:
            return False
        if event_hash(**{k: event[k] for k in (
            "seq", "prev_hash", "entity_type", "entity_id", "event_type",
            "actor_id", "old_status", "new_status")}) != event["event_hash"]:
            return False
        previous = event["event_hash"]
    return True


def sample_events():
    entity = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    actor = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    a = dict(seq=1, prev_hash="0" * 64, entity_type="ceremony", entity_id=entity,
             event_type="ceremony_requested", actor_id=actor, old_status=None,
             new_status="pending")
    a["event_hash"] = event_hash(**{k: v for k, v in a.items() if k != "event_hash"})
    b = dict(seq=2, prev_hash=a["event_hash"], entity_type="ceremony", entity_id=entity,
             event_type="ceremony_approved", actor_id=None, old_status="pending",
             new_status="approved")
    b["event_hash"] = event_hash(**{k: v for k, v in b.items() if k != "event_hash"})
    return [a, b]


def test_valid_chain():
    assert verify_chain(sample_events())


def test_modified_event_detected():
    events = sample_events()
    events[0]["event_type"] = "ceremony_executed"
    assert not verify_chain(events)


def test_broken_link_detected():
    events = sample_events()
    events[1]["prev_hash"] = "f" * 64
    assert not verify_chain(events)


def test_deleted_first_event_detected_with_genesis_anchor():
    assert not verify_chain(sample_events()[1:])
