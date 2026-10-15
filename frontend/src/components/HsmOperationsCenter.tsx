import { useMemo, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Cpu,
  KeyRound,
  LockKeyhole,
  Server,
  ShieldCheck,
} from 'lucide-react'

import './HsmOperationsCenter.css'

type HsmStatus = {
  status: string
  token_connected: boolean
  token_label: string
  provider?: string
  environment?: string
}

type ManagedKey = {
  id: string
  token_label: string
  key_id: string
  key_label: string
  algorithm: string
  status: string
}

type Ceremony = {
  id: string
  key_label: string
  status: string
  operation: string
  execution_started_at: string | null
}

type Props = {
  hsm: HsmStatus | null
  keys: ManagedKey[]
  ceremonies: Ceremony[]
  role: string
  onNavigate: (page: 'keys' | 'ceremonies' | 'audit') => void
}

const roleNames: Record<string, string> = {
  key_manager: 'Key Manager',
  security_officer: 'Security Officer',
  hsm_operator: 'HSM Operator',
  auditor: 'Auditor',
}

const permissions: Record<string, string[]> = {
  key_manager: [
    'Consult cryptographic inventory',
    'Request a key activation ceremony',
  ],
  security_officer: [
    'Review key ceremony requests',
    'Approve or reject authorized requests',
  ],
  hsm_operator: [
    'Review execution authorizations',
    'Perform approved HSM operations through the local workflow',
  ],
  auditor: [
    'Review key ceremony records',
    'Inspect audit events and chain integrity',
  ],
}

export default function HsmOperationsCenter({
  hsm,
  keys,
  ceremonies,
  role,
  onNavigate,
}: Props) {
  const [search, setSearch] = useState('')

  const activeKeys = keys.filter(
    key => key.status === 'active',
  ).length

  const createdKeys = keys.filter(
    key => key.status === 'created',
  ).length

  const pendingCeremonies = ceremonies.filter(
    ceremony => ceremony.status === 'pending',
  ).length

  const executingCeremonies = ceremonies.filter(
    ceremony => ceremony.status === 'executing',
  ).length

  const staleCeremonies = useMemo(() => {
    const cutoff = Date.now() - 5 * 60 * 1000

    return ceremonies.filter(ceremony => {
      if (
        ceremony.status !== 'executing' ||
        !ceremony.execution_started_at
      ) {
        return false
      }

      const started = new Date(
        ceremony.execution_started_at,
      ).getTime()

      return Number.isFinite(started) && started < cutoff
    })
  }, [ceremonies])

  const filteredKeys = keys.filter(key =>
    [
      key.key_label,
      key.key_id,
      key.algorithm,
      key.status,
    ].some(value =>
      value.toLowerCase().includes(search.toLowerCase()),
    ),
  )

  const connected = hsm?.token_connected === true

  return (
    <div className="hoc-root">
      <div className="hoc-banner">
        <div>
          <div className="hoc-kicker">
            <Cpu size={15} />
            PKCS#11 INFRASTRUCTURE
          </div>

          <h2>Hardware Security Operations</h2>

          <p>
            Operational visibility over cryptographic
            assets, controlled workflows and HSM status.
          </p>
        </div>

        <div className={
          `hoc-connection ${
            connected ? 'hoc-online' : 'hoc-offline'
          }`
        }>
          {connected
            ? <CheckCircle2 size={18} />
            : <AlertTriangle size={18} />
          }

          {hsm === null
            ? 'STATUS UNAVAILABLE'
            : connected
              ? 'TOKEN CONNECTED'
              : 'TOKEN UNAVAILABLE'
          }
        </div>
      </div>

      <div className="hoc-metrics">
        <div className="hoc-metric">
          <Server size={21} />
          <span>HSM PROVIDER</span>
          <strong>{hsm?.provider || 'Unavailable'}</strong>
          <small>Laboratory PKCS#11 provider</small>
        </div>

        <div className="hoc-metric">
          <KeyRound size={21} />
          <span>ACTIVE KEYS</span>
          <strong>{activeKeys}</strong>
          <small>{createdKeys} awaiting activation</small>
        </div>

        <div className="hoc-metric">
          <ShieldCheck size={21} />
          <span>PENDING CEREMONIES</span>
          <strong>{pendingCeremonies}</strong>
          <small>Awaiting authorized action</small>
        </div>

        <div className="hoc-metric">
          <Clock3 size={21} />
          <span>IN EXECUTION</span>
          <strong>{executingCeremonies}</strong>
          <small>Reserved ceremonies</small>
        </div>
      </div>

      <div className="hoc-grid">
        <section className="hoc-panel">
          <div className="hoc-panel-heading">
            <h3>Security Module</h3>
            <span>LIVE API DATA</span>
          </div>

          <div className="hoc-info">
            <span>Provider</span>
            <strong>{hsm?.provider || '—'}</strong>
          </div>

          <div className="hoc-info">
            <span>Token Label</span>
            <strong>{hsm?.token_label || '—'}</strong>
          </div>

          <div className="hoc-info">
            <span>Connection</span>
            <strong className={
              connected ? 'hoc-good' : 'hoc-warning'
            }>
              {hsm?.status || 'Unknown'}
            </strong>
          </div>

          <div className="hoc-info">
            <span>Environment</span>
            <strong>
              {hsm?.environment || 'Laboratory'}
            </strong>
          </div>

          <div className="hoc-footnote">
            Connection status is reported by the backend.
            It does not establish that every registered key
            has been individually verified on the token.
          </div>
        </section>

        <section className="hoc-panel">
          <div className="hoc-panel-heading">
            <h3>Operator Authorization</h3>
            <span>ROLE BASED ACCESS</span>
          </div>

          <div className="hoc-role">
            <LockKeyhole size={19} />
            <div>
              <small>AUTHENTICATED ROLE</small>
              <strong>{roleNames[role] || role}</strong>
            </div>
          </div>

          <div className="hoc-permissions">
            {(permissions[role] || []).map(item => (
              <div key={item}>
                <CheckCircle2 size={15} />
                <span>{item}</span>
              </div>
            ))}
          </div>

          <div className="hoc-footnote">
            Permissions are enforced by the backend.
            This view provides guidance only.
          </div>
        </section>
      </div>

      <section className="hoc-panel">
        <div className="hoc-panel-heading">
          <h3>Cryptographic Asset Registry</h3>
          <button
            className="hoc-text-button"
            onClick={() => onNavigate('keys')}
          >
            Full inventory <ArrowRight size={15} />
          </button>
        </div>

        <input
          className="hoc-search"
          value={search}
          onChange={event => setSearch(event.target.value)}
          placeholder="Search by key label, ID, algorithm or status"
          aria-label="Search managed keys"
        />

        <div className="hoc-table-wrap">
          <table className="hoc-table">
            <thead>
              <tr>
                <th>KEY LABEL</th>
                <th>ALGORITHM</th>
                <th>PKCS#11 ID</th>
                <th>STATUS</th>
              </tr>
            </thead>

            <tbody>
              {filteredKeys.map(key => (
                <tr key={key.id}>
                  <td>
                    <KeyRound size={15} />
                    {key.key_label}
                  </td>
                  <td>{key.algorithm}</td>
                  <td className="hoc-code">{key.key_id}</td>
                  <td>
                    <span className={
                      `hoc-key-state ${
                        key.status === 'active'
                          ? 'hoc-state-active'
                          : ''
                      }`
                    }>
                      {key.status.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filteredKeys.length === 0 && (
            <div className="hoc-empty">
              No matching cryptographic assets.
            </div>
          )}
        </div>

        <div className="hoc-footnote">
          Registry data comes from PostgreSQL.
          Secret key material is never displayed.
        </div>
      </section>

      <div className="hoc-grid">
        <section className="hoc-panel">
          <div className="hoc-panel-heading">
            <h3>Controlled Operations</h3>
            <span>SECURE WORKFLOW</span>
          </div>

          <p className="hoc-description">
            Key operations require the appropriate role
            and the existing ceremony approval workflow.
          </p>

          <button
            className="hoc-action"
            onClick={() => onNavigate('ceremonies')}
          >
            <ShieldCheck size={18} />
            Open Key Ceremonies
            <ArrowRight size={17} />
          </button>

          <div className="hoc-footnote">
            HSM activation and PIN authentication remain
            outside the browser.
          </div>
        </section>

        <section className="hoc-panel">
          <div className="hoc-panel-heading">
            <h3>Recovery Monitoring</h3>
            <span>INCIDENT AWARENESS</span>
          </div>

          <div className="hoc-recovery-number">
            <Activity size={22} />
            <strong>{staleCeremonies.length}</strong>
            <span>Potentially stale executions</span>
          </div>

          {staleCeremonies.map(ceremony => (
            <div
              className="hoc-stale-item"
              key={ceremony.id}
            >
              <AlertTriangle size={16} />
              <span>{ceremony.key_label}</span>
            </div>
          ))}

          <div className="hoc-footnote">
            Preliminary browser-side indication using
            a five-minute threshold. The backend must
            confirm any recovery decision. Automatic
            retries are not permitted.
          </div>

          <button
            className="hoc-text-button hoc-audit-link"
            onClick={() => onNavigate('audit')}
          >
            Review Audit Center
            <ArrowRight size={15} />
          </button>
        </section>
      </div>
    </div>
  )
}
