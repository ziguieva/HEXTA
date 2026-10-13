import { useState } from 'react'
import { Check, ClipboardCheck, Plus, X } from 'lucide-react'
import './CeremonyActions.css'

type Key = { key_label: string; status: string }
type Ceremony = { id: string; key_label: string; status: string }

type Props = {
  token: string
  role: string
  keys: Key[]
  ceremonies: Ceremony[]
  onChanged: () => Promise<void>
}

export default function CeremonyActions({ token, role, keys, ceremonies, onChanged }: Props) {
  const [keyLabel, setKeyLabel] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [confirmation, setConfirmation] = useState<string | null>(null)

  const availableKeys = keys.filter(k => k.status === 'created')
  const eligible = ceremonies.filter(c => role === 'security_officer'
    ? c.status === 'pending' : c.status === 'approved')

  async function perform(path: string, payload?: object) {
    setError('')
    setNotice('')
    setBusy(true)
    try {
      const response = await fetch(`/api/v1/ceremonies${path}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          ...(payload ? { 'Content-Type': 'application/json' } : {}),
        },
        body: payload ? JSON.stringify(payload) : undefined,
      })
      const result = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(typeof result.detail === 'string'
          ? result.detail : `Operation failed (HTTP ${response.status})`)
      }
      setNotice(path.endsWith('execution-check')
        ? 'Execution authorization verified. HSM execution remains local-only.'
        : 'Operation recorded successfully.')
      await onChanged()
      setKeyLabel('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed')
    } finally {
      setBusy(false)
      setConfirmation(null)
    }
  }

  return (
    <section className="bk-action-panel" aria-label="Ceremony operations">
      <div className="bk-action-heading">
        <div>
          <div className="bk-action-eyebrow">ROLE-GATED OPERATIONS</div>
          <h3>Ceremony control desk</h3>
          <p>Actions are enforced by FastAPI and recorded in PostgreSQL.</p>
        </div>
        <span className="bk-action-role">{role.replaceAll('_', ' ').toUpperCase()}</span>
      </div>

      {role === 'key_manager' && (
        <form className="bk-action-form" onSubmit={e => {
          e.preventDefault()
          if (!keyLabel) return
          void perform('', { key_label: keyLabel, operation: 'activate' })
        }}>
          <label htmlFor="bk-target-key">Activate a registered key</label>
          <select id="bk-target-key" value={keyLabel}
            onChange={e => setKeyLabel(e.target.value)} required>
            <option value="">Select a CREATED key</option>
            {availableKeys.map(key => <option key={key.key_label} value={key.key_label}>
              {key.key_label}
            </option>)}
          </select>
          <button type="submit" disabled={busy || !keyLabel}>
            <Plus size={16} /> Create request
          </button>
          {availableKeys.length === 0 && <p className="bk-action-hint">
            No CREATED key available. BANKKEY-AES-001 is already ACTIVE.
          </p>}
        </form>
      )}

      {(role === 'security_officer' || role === 'hsm_operator') && (
        <div className="bk-action-queue">
          <div className="bk-action-eyebrow">ACTION QUEUE ({eligible.length})</div>
          {eligible.map(c => (
            <div className="bk-action-queue-row" key={c.id}>
              <div><strong>{c.key_label}</strong><small>{c.status.toUpperCase()}</small></div>
              {role === 'security_officer' ? (
                <div className="bk-action-buttons">
                  <button disabled={busy} onClick={() => setConfirmation(`approve:${c.id}`)}>
                    <Check size={15} /> Approve
                  </button>
                  <button className="bk-action-danger" disabled={busy}
                    onClick={() => setConfirmation(`reject:${c.id}`)}>
                    <X size={15} /> Reject
                  </button>
                </div>
              ) : (
                <button disabled={busy} onClick={() => void perform(`/${c.id}/execution-check`)}>
                  <ClipboardCheck size={16} /> Verify execution authorization
                </button>
              )}
            </div>
          ))}
          {eligible.length === 0 && <p className="bk-action-hint">
            No ceremony requiring action for this role.
          </p>}
        </div>
      )}

      {role === 'auditor' && <p className="bk-action-hint">
        Read-only access. Ceremonies and decisions can be reviewed below.
      </p>}

      {confirmation && <div className="bk-action-confirm" role="dialog" aria-label="Confirm action">
        <strong>Confirm {confirmation.split(':')[0]}?</strong>
        <span>This will update the ceremony record.</span>
        <div className="bk-action-buttons">
          <button disabled={busy} onClick={() => {
            const [action, id] = confirmation.split(':')
            void perform(`/${id}/${action}`)
          }}>Confirm</button>
          <button className="bk-action-cancel" disabled={busy}
            onClick={() => setConfirmation(null)}>Cancel</button>
        </div>
      </div>}
      {error && <div className="bk-action-error" role="alert">{error}</div>}
      {notice && <div className="bk-action-success" role="status">{notice}</div>}
    </section>
  )
}
