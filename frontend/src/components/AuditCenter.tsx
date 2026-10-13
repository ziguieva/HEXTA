import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, RefreshCw, ShieldAlert, ScrollText } from 'lucide-react'
import './AuditCenter.css'

type AuditEvent = {
  seq: number
  occurred_at: string
  entity_type: string
  entity_id: string
  event_type: string
  actor_id: string | null
  old_status: string | null
  new_status: string | null
  event_hash: string
}
type Report = {
  integrity: { valid: boolean; checked: number; failure_seq: number | null }
  total: number
  historical_note: string
  events: AuditEvent[]
}
export default function AuditCenter({ token, role }: { token: string; role: string }) {
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [filter, setFilter] = useState('')

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setBusy(true)
    setError('')
    try {
      const response = await fetch('/api/v1/audit?limit=200', {
        headers: { Authorization: `Bearer ${token}` }, signal,
      })
      if (!response.ok) throw new Error(`Audit API returned HTTP ${response.status}`)
      const data = await response.json() as Report
      if (!signal?.aborted) setReport(data)
    } catch (err) {
      if (!signal?.aborted) setError(err instanceof Error ? err.message : 'Unable to load audit')
    } finally {
      if (!signal?.aborted) setBusy(false)
    }
  }, [token])

  useEffect(() => {
    const controller = new AbortController()
    if (role === 'auditor' || role === 'security_officer') void refresh(controller.signal)
    return () => controller.abort()
  }, [refresh, role])

  if (role !== 'auditor' && role !== 'security_officer') {
    return <section className="bk-audit-panel"><ShieldAlert size={22}/><p>Audit access requires Auditor or Security Officer privileges.</p></section>
  }

  const visible = (report?.events ?? []).filter(event =>
    [event.entity_type, event.entity_id, event.event_type, event.new_status, event.actor_id]
      .some(value => (value ?? '').toLowerCase().includes(filter.toLowerCase()))
  )

  return <section className="bk-audit-panel">
    <div className="bk-audit-header">
      <div><div className="bk-audit-kicker">SECURITY AUDIT</div><h2>Audit Center</h2>
        <p>Database-triggered events with SHA-256 hash-chain verification.</p></div>
      <button onClick={() => void refresh()} disabled={busy}><RefreshCw size={15}/>{busy ? 'Checking...' : 'Verify & Refresh'}</button>
    </div>
    {error && <div className="bk-audit-error" role="alert">{error}</div>}
    {report && <>
      <div className="bk-audit-metrics">
        <div><small>CAPTURED EVENTS</small><strong>{report.total}</strong></div>
        <div><small>HASH CHAIN</small><strong className={report.integrity.valid ? 'bk-audit-good' : 'bk-audit-bad'}>
          {report.integrity.valid ? <><CheckCircle2 size={18}/> VALID</> : <><ShieldAlert size={18}/> INVALID</>}
        </strong></div>
        <div><small>RECORDS VERIFIED</small><strong>{report.integrity.checked}</strong></div>
      </div>
      {!report.integrity.valid && <div className="bk-audit-error">Chain integrity failed at sequence {report.integrity.failure_seq}. Investigate before trusting the journal.</div>}
      <p className="bk-audit-note">{report.historical_note} SHA-256 chaining provides tamper evidence, not protection against an administrator rewriting the database and hashes.</p>
      <div className="bk-audit-title"><ScrollText size={18}/><h3>Recent Security Events</h3></div>
      <input className="bk-audit-search" placeholder="Search action, object, status or actor ID" value={filter} onChange={e => setFilter(e.target.value)}/>
      <div className="bk-audit-scroll"><table className="bk-audit-table"><thead><tr><th>SEQ</th><th>UTC TIMESTAMP</th><th>EVENT</th><th>OBJECT</th><th>STATE</th><th>HASH</th></tr></thead><tbody>
        {visible.map(event => <tr key={event.seq}>
          <td>#{event.seq}</td><td>{new Date(event.occurred_at).toLocaleString('fr-FR', {timeZone: 'UTC'})} UTC</td>
          <td>{event.event_type.replaceAll('_', ' ').toUpperCase()}</td>
          <td><span>{event.entity_type}</span><code title={event.entity_id}>{event.entity_id.slice(0, 8)}…</code></td>
          <td>{event.old_status ?? '—'} → {event.new_status ?? '—'}</td>
          <td><code title={event.event_hash}>{event.event_hash.slice(0, 12)}…</code></td>
        </tr>)}
      </tbody></table>{visible.length === 0 && <p className="bk-audit-empty">No captured events match this search.</p>}</div>
    </>}
  </section>
}
