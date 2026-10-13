from fastapi.testclient import TestClient
from app.main import app
from app.core.web_auth import get_current_user
from app.services.audit_service import GENESIS, compute_hash, verify_chain

client = TestClient(app)


def test_audit_requires_login():
    assert client.get('/api/v1/audit').status_code == 401


def test_audit_denies_key_manager():
    app.dependency_overrides[get_current_user] = lambda: {'role': 'key_manager', 'id': 'unused'}
    try:
        assert client.get('/api/v1/audit').status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_chain_detects_tampering():
    a = dict(seq=1, prev_hash=GENESIS, entity_type='ceremony',
             entity_id='00000000-0000-0000-0000-000000000001',
             event_type='ceremony_requested', actor_id=None,
             old_status=None, new_status='pending')
    a['event_hash'] = compute_hash(a)
    assert verify_chain([a])['valid'] is True
    a['new_status'] = 'executed'
    assert verify_chain([a])['valid'] is False
