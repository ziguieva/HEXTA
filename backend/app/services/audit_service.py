"""Independent SHA-256 chain verification for PostgreSQL-triggered audit events."""
from hashlib import sha256

GENESIS = "0" * 64


def compute_hash(row: dict) -> str:
    payload = "|".join([
        str(row["seq"]), row["prev_hash"], row["entity_type"],
        str(row["entity_id"]), row["event_type"],
        str(row["actor_id"]) if row["actor_id"] else "",
        row["old_status"] or "", row["new_status"] or "",
    ])
    return sha256(payload.encode("utf-8")).hexdigest()


def verify_chain(rows: list[dict]) -> dict:
    previous = GENESIS
    for row in rows:
        if row["prev_hash"] != previous or compute_hash(row) != row["event_hash"]:
            return {"valid": False, "checked": len(rows), "failure_seq": row["seq"]}
        previous = row["event_hash"]
    return {"valid": True, "checked": len(rows), "failure_seq": None}
