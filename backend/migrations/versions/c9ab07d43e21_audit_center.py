"""Audit Center: transactionally chained database events.

Revision ID: c9ab07d43e21
Revises: 3f4b37bacbe3
"""
from alembic import op

revision = "c9ab07d43e21"
down_revision = "3f4b37bacbe3"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("""
    CREATE TABLE bankkey_audit_events (
        seq BIGSERIAL PRIMARY KEY,
        occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
        entity_type TEXT NOT NULL,
        entity_id UUID NOT NULL,
        event_type TEXT NOT NULL,
        actor_id UUID NULL,
        old_status TEXT NULL,
        new_status TEXT NULL,
        prev_hash TEXT NOT NULL,
        event_hash TEXT NOT NULL
    )
    """)
    op.execute("CREATE INDEX ix_bankkey_audit_entity ON bankkey_audit_events(entity_type, entity_id)")
    op.execute("""
    CREATE FUNCTION bankkey_append_event(p_entity_type TEXT, p_entity_id UUID,
      p_event_type TEXT, p_actor_id UUID, p_old_status TEXT, p_new_status TEXT)
    RETURNS VOID LANGUAGE plpgsql AS $$
    DECLARE v_seq BIGINT; v_prev TEXT; v_payload TEXT; v_hash TEXT;
    BEGIN
      PERFORM pg_advisory_xact_lock(917204007);
      SELECT event_hash INTO v_prev FROM bankkey_audit_events ORDER BY seq DESC LIMIT 1;
      v_prev := COALESCE(v_prev, repeat('0', 64));
      v_seq := nextval(pg_get_serial_sequence('bankkey_audit_events','seq'));
      v_payload := concat_ws('|', v_seq::text, v_prev, p_entity_type,
        p_entity_id::text, p_event_type, COALESCE(p_actor_id::text,''),
        COALESCE(p_old_status,''), COALESCE(p_new_status,''));
      v_hash := encode(digest(convert_to(v_payload, 'UTF8'), 'sha256'),'hex');
      INSERT INTO bankkey_audit_events(seq, entity_type, entity_id, event_type,
        actor_id, old_status, new_status, prev_hash, event_hash)
      VALUES(v_seq, p_entity_type, p_entity_id, p_event_type,
        p_actor_id, p_old_status, p_new_status, v_prev, v_hash);
    END $$
    """)
    op.execute("""
    CREATE FUNCTION bankkey_audit_business_changes() RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_TABLE_NAME='key_ceremonies' THEN
        IF TG_OP='INSERT' THEN
          PERFORM bankkey_append_event('ceremony',NEW.id,'ceremony_requested',NEW.requested_by,NULL,NEW.status);
        ELSIF OLD.status IS DISTINCT FROM NEW.status THEN
          PERFORM bankkey_append_event('ceremony',NEW.id,'ceremony_'||NEW.status,
            CASE WHEN NEW.status IN ('executing','executed','execution_failed')
              THEN NEW.executed_by ELSE NULL END, OLD.status,NEW.status);
        END IF;
      ELSIF TG_TABLE_NAME='ceremony_approvals' AND TG_OP='INSERT' THEN
        PERFORM bankkey_append_event('ceremony',NEW.ceremony_id,'decision_'||NEW.decision,
          NEW.approved_by,NULL,NEW.decision);
      ELSIF TG_TABLE_NAME='managed_keys' THEN
        IF TG_OP='INSERT' THEN
          PERFORM bankkey_append_event('key',NEW.id,'key_registered',NULL,NULL,NEW.status);
        ELSIF OLD.status IS DISTINCT FROM NEW.status THEN
          PERFORM bankkey_append_event('key',NEW.id,'key_'||NEW.status,NULL,OLD.status,NEW.status);
        END IF;
      END IF;
      RETURN NEW;
    END $$
    """)
    op.execute("""
    CREATE TRIGGER bk_audit_ceremonies AFTER INSERT OR UPDATE OF status ON key_ceremonies
      FOR EACH ROW EXECUTE FUNCTION bankkey_audit_business_changes()
    """)
    op.execute("""
    CREATE TRIGGER bk_audit_approvals AFTER INSERT ON ceremony_approvals
      FOR EACH ROW EXECUTE FUNCTION bankkey_audit_business_changes()
    """)
    op.execute("""
    CREATE TRIGGER bk_audit_keys AFTER INSERT OR UPDATE OF status ON managed_keys
      FOR EACH ROW EXECUTE FUNCTION bankkey_audit_business_changes()
    """)
    op.execute("""
    CREATE FUNCTION bankkey_audit_immutable() RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'Audit events are append-only';
    END $$
    """)
    op.execute("""
    CREATE TRIGGER bk_audit_no_mutation BEFORE UPDATE OR DELETE ON bankkey_audit_events
    FOR EACH ROW EXECUTE FUNCTION bankkey_audit_immutable()
    """)


def downgrade():
    op.execute("DROP TRIGGER bk_audit_no_mutation ON bankkey_audit_events")
    op.execute("DROP FUNCTION bankkey_audit_immutable()")
    op.execute("DROP TRIGGER bk_audit_keys ON managed_keys")
    op.execute("DROP TRIGGER bk_audit_approvals ON ceremony_approvals")
    op.execute("DROP TRIGGER bk_audit_ceremonies ON key_ceremonies")
    op.execute("DROP FUNCTION bankkey_audit_business_changes()")
    op.execute("DROP FUNCTION bankkey_append_event(TEXT,UUID,TEXT,UUID,TEXT,TEXT)")
    op.execute("DROP TABLE bankkey_audit_events")
