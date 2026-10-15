import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
} from 'react'

import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Fingerprint,
  KeyRound,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  RefreshCw,
  Server,
  Shield,
  ShieldCheck,
  Users,
  XCircle,
} from 'lucide-react'

import CeremonyActions from './components/CeremonyActions'
import AuditCenter from './components/AuditCenter'
import HsmOperationsCenter from './components/HsmOperationsCenter'
import './App.css'


type Page = 'overview' | 'keys' | 'ceremonies' | 'audit' | 'hsm'

type Profile = {
  id: string
  username: string
  role: string
}

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
  created_at: string
  activated_at: string | null
  revoked_at: string | null
}

type Approval = {
  approved_by: string
  decision: string
  created_at: string
}

type Ceremony = {
  id: string
  key_label: string
  operation: string
  status: string
  requested_by: string
  created_at: string
  execution_started_at: string | null
  executed_at: string | null
  executed_by: string | null
  approvals: Approval[]
}


const roleNames: Record<string, string> = {
  key_manager: 'Key Manager',
  security_officer: 'Security Officer',
  hsm_operator: 'HSM Operator',
  auditor: 'Auditor',
}

function formatDate(value: string | null) {
  if (!value) return '—'

  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase()

  const level = ['active', 'executed', 'approved'].includes(
    normalized
  )
    ? 'good'
    : ['revoked', 'rejected', 'execution_failed'].includes(
        normalized
      )
      ? 'bad'
      : 'waiting'

  return (
    <span className={`bk-status bk-status-${level}`}>
      <span className="bk-status-dot" />
      {status.replaceAll('_', ' ').toUpperCase()}
    </span>
  )
}


function App() {
  const [page, setPage] = useState<Page>('overview')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState<string | null>(null)

  const [profile, setProfile] = useState<Profile | null>(null)
  const [hsm, setHsm] = useState<HsmStatus | null>(null)
  const [keys, setKeys] = useState<ManagedKey[]>([])
  const [ceremonies, setCeremonies] = useState<Ceremony[]>([])

  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(
    null
  )

  const logout = useCallback(() => {
    setToken(null)
    setProfile(null)
    setHsm(null)
    setKeys([])
    setCeremonies([])
    setPassword('')
    setPage('overview')
    setError('')
    setLastUpdated(null)
  }, [])

  const loadData = useCallback(async (
    accessToken: string,
    signal?: AbortSignal,
  ) => {
    const headers = {
      Authorization: `Bearer ${accessToken}`,
    }

    const urls = [
      '/api/v1/auth/me',
      '/api/v1/hsm/status',
      '/api/v1/keys',
      '/api/v1/ceremonies',
    ]

    const responses = await Promise.all(
      urls.map(url =>
        fetch(url, {
          headers,
          cache: 'no-store',
          signal,
        })
      )
    )

    if (responses.some(response => response.status === 401)) {
      throw new Error('SESSION_EXPIRED')
    }

    if (responses.some(response => !response.ok)) {
      throw new Error(
        'Unable to retrieve platform information'
      )
    }

    const [userData, hsmData, keyData, ceremonyData] =
      await Promise.all(
        responses.map(response => response.json())
      )

    if (signal?.aborted) return

    setProfile(userData as Profile)
    setHsm(hsmData as HsmStatus)
    setKeys(keyData as ManagedKey[])
    setCeremonies(ceremonyData as Ceremony[])
    setLastUpdated(new Date())
  }, [])

  useEffect(() => {
    if (!token) return

    const controller = new AbortController()

    loadData(token, controller.signal).catch(err => {
      if (controller.signal.aborted) return

      if (err instanceof Error &&
          err.message === 'SESSION_EXPIRED') {
        logout()
      } else {
        setError('Backend connection failed')
      }
    })

    return () => controller.abort()
  }, [token, loadData, logout])

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        cache: 'no-store',
        body: JSON.stringify({ username, password }),
      })

      if (!response.ok) {
        throw new Error(
          response.status === 401
            ? 'Invalid username or password'
            : 'Authentication service unavailable'
        )
      }

      const data = await response.json()
      setPassword('')
      setToken(data.access_token)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Authentication failed'
      )
    } finally {
      setLoading(false)
    }
  }

  async function refreshData() {
    if (!token || refreshing) return

    setRefreshing(true)
    setError('')

    try {
      await loadData(token)
    } catch (err) {
      if (err instanceof Error &&
          err.message === 'SESSION_EXPIRED') {
        logout()
      } else {
        setError('Unable to refresh platform data')
      }
    } finally {
      setRefreshing(false)
    }
  }

  if (!token) {
    return (
      <div className="login-layout">
        <section className="login-brand">
          <div className="brand">
            <ShieldCheck size={29} />
            BANKKEY <span>HSM</span>
          </div>

          <div className="hero-copy">
            <div className="eyebrow">
              CRYPTOGRAPHIC SECURITY PLATFORM
            </div>
            <h1>
              Secure the keys.
              <br />
              <em>Control the trust.</em>
            </h1>
            <p>
              A dedicated laboratory for cryptographic
              key management, controlled operations
              and payment security.
            </p>

            <div className="hero-features">
              <span>
                <Shield size={17} />
                Secure Key Management
              </span>
              <span>
                <Fingerprint size={17} />
                Dual Control Workflow
              </span>
              <span>
                <Activity size={17} />
                Security Monitoring
              </span>
            </div>
          </div>

          <div className="hero-bottom">
            BANKKEY / ENGINEERING LABORATORY / v0.5
          </div>
        </section>

        <section className="login-panel">
          <div className="login-form-wrap">
            <div className="login-icon">
              <LockKeyhole size={26} />
            </div>

            <div className="eyebrow">SECURE ACCESS</div>
            <h2>Welcome back</h2>
            <p className="muted">
              Sign in with your authorized
              laboratory credentials.
            </p>

            <form onSubmit={login}>
              <label htmlFor="username">Username</label>
              <input
                id="username"
                autoComplete="username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
              />

              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
              />

              {error && (
                <div className="error" role="alert">
                  {error}
                </div>
              )}

              <button
                className="primary-button"
                disabled={loading}
                type="submit"
              >
                {loading
                  ? 'Authenticating...'
                  : 'Sign in securely'}
                <ArrowRight size={18} />
              </button>
            </form>

            <div className="login-note">
              <Shield size={15} />
              Authorized laboratory users only
            </div>
          </div>
        </section>
      </div>
    )
  }

  const pageNames: Record<Page, string> = {
    overview: 'Platform Overview',
    keys: 'Key Inventory',
    ceremonies: 'Key Ceremonies',
    audit: 'Audit Center',
    hsm: 'HSM Operations Center',
  }

  const activeKeys = keys.filter(
    key => key.status === 'active'
  ).length

  const executedCeremonies = ceremonies.filter(
    ceremony => ceremony.status === 'executed'
  ).length

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={25} />
          BANKKEY <span>HSM</span>
        </div>

        <div className="side-label">WORKSPACE</div>

        <button
          className={`nav-item bk-nav-button ${
            page === 'overview' ? 'selected' : ''
          }`}
          onClick={() => setPage('overview')}
        >
          <LayoutDashboard size={18} />
          Overview
        </button>

        <button
          className={`nav-item bk-nav-button ${
            page === 'keys' ? 'selected' : ''
          }`}
          onClick={() => setPage('keys')}
        >
          <KeyRound size={18} />
          Key Inventory
          <small>{keys.length}</small>
        </button>

        <button
          className={`nav-item bk-nav-button ${
            page === 'ceremonies' ? 'selected' : ''
          }`}
          onClick={() => setPage('ceremonies')}
        >
          <Shield size={18} />
          Key Ceremonies
          <small>{ceremonies.length}</small>
        </button>

        <button
          className={`nav-item bk-nav-button ${
            page === 'hsm' ? 'selected' : ''
          }`}
          onClick={() => setPage('hsm')}
        >
          <Server size={18} />
          HSM Operations
        </button>

        <div className="nav-item disabled">
          <Users size={18} />
          Access Control
          <small>SOON</small>
        </div>

        <button className={`nav-item bk-nav-button ${page === 'audit' ? 'selected' : ''}`}
          onClick={() => setPage('audit')}>
          <Activity size={18} /> Audit Center
        </button>

        <div className="sidebar-bottom">
          <div className="user-initial">
            {profile?.username[0]?.toUpperCase() || 'U'}
          </div>

          <div className="user-details">
            <strong>
              {profile?.username || 'Loading...'}
            </strong>
            <span>
              {roleNames[profile?.role || ''] ||
                profile?.role}
            </span>
          </div>

          <button
            className="logout"
            onClick={logout}
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <span>
            Security Workspace / {pageNames[page]}
          </span>
          <span className="env-label">
            <span className="live-dot" />
            LAB ENVIRONMENT
          </span>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                SECURITY OPERATIONS
              </div>
              <h1>{pageNames[page]}</h1>
              <p className="muted">
                {page === 'overview'
                  ? 'Cryptographic infrastructure and identity supervision.'
                  : page === 'keys'
                    ? 'Cryptographic assets and key lifecycle monitoring.'
                    : 'Controlled key operations and approval history.'}
              </p>
            </div>

            <button
              className="bk-refresh"
              onClick={refreshData}
              disabled={refreshing}
            >
              <RefreshCw size={16} />
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}

          {page === 'hsm' && (
            <HsmOperationsCenter
              hsm={hsm}
              keys={keys}
              ceremonies={ceremonies}
              role={profile?.role || ''}
              onNavigate={setPage}
            />
          )}

          {page === 'audit' && token && <AuditCenter token={token} role={profile?.role || ''} />}

          {page === 'overview' && (
            <>
              <div className="metrics">
                <div className="metric-card">
                  <div className="metric-label">
                    <Server size={19} />
                    HSM Connection
                  </div>
                  <strong>
                    {hsm
                      ? hsm.token_connected
                        ? 'Online'
                        : 'Offline'
                      : 'Loading'}
                  </strong>
                  <span className="metric-description">
                    SoftHSM2 / PKCS#11
                  </span>
                </div>

                <div className="metric-card">
                  <div className="metric-label">
                    <KeyRound size={19} />
                    Active Keys
                  </div>
                  <strong>{activeKeys}</strong>
                  <span className="metric-description">
                    {keys.length} registered assets
                  </span>
                </div>

                <div className="metric-card">
                  <div className="metric-label">
                    <ShieldCheck size={19} />
                    Executed Ceremonies
                  </div>
                  <strong>{executedCeremonies}</strong>
                  <span className="metric-description">
                    {ceremonies.length} visible ceremonies
                  </span>
                </div>
              </div>

              <div className="content-grid">
                <section className="panel">
                  <div className="panel-header">
                    <h3>Cryptographic Infrastructure</h3>
                    <span className="panel-subtitle">
                      LIVE STATUS
                    </span>
                  </div>

                  <div className="info-row">
                    <span>HSM Provider</span>
                    <strong>{hsm?.provider || '—'}</strong>
                  </div>
                  <div className="info-row">
                    <span>Token Label</span>
                    <strong>
                      {hsm?.token_label || '—'}
                    </strong>
                  </div>
                  <div className="info-row">
                    <span>Connection Status</span>
                    <strong className={
                      hsm?.token_connected ? 'success' : ''
                    }>
                      {hsm?.status || 'Loading'}
                    </strong>
                  </div>
                  <div className="info-row">
                    <span>Security Mode</span>
                    <strong>Software HSM Laboratory</strong>
                  </div>
                </section>

                <section className="panel">
                  <div className="panel-header">
                    <h3>Identity & Access</h3>
                    <span className="panel-subtitle">
                      AUTHENTICATED
                    </span>
                  </div>

                  <div className="info-row">
                    <span>Username</span>
                    <strong>
                      {profile?.username || '—'}
                    </strong>
                  </div>
                  <div className="info-row">
                    <span>Assigned Role</span>
                    <strong>
                      {roleNames[profile?.role || ''] ||
                        '—'}
                    </strong>
                  </div>
                  <div className="info-row">
                    <span>Account State</span>
                    <strong className="success">
                      Authenticated
                    </strong>
                  </div>
                  <div className="info-row">
                    <span>Session Type</span>
                    <strong>Short-lived Bearer Token</strong>
                  </div>
                </section>
              </div>
            </>
          )}

          {page === 'keys' && (
            <>
              <div className="bk-section-summary">
                <div>
                  <span>REGISTERED KEYS</span>
                  <strong>{keys.length}</strong>
                </div>
                <div>
                  <span>ACTIVE KEYS</span>
                  <strong>{activeKeys}</strong>
                </div>
                <div>
                  <span>REVOKED KEYS</span>
                  <strong>
                    {keys.filter(
                      key => key.status === 'revoked'
                    ).length}
                  </strong>
                </div>
              </div>

              <section className="panel bk-data-panel">
                <div className="panel-header">
                  <h3>Cryptographic Key Inventory</h3>
                  <span className="panel-subtitle">
                    POSTGRESQL METADATA
                  </span>
                </div>

                <div className="bk-table-scroll">
                  <table className="bk-table">
                    <thead>
                      <tr>
                        <th>KEY LABEL</th>
                        <th>ALGORITHM</th>
                        <th>PKCS#11 ID</th>
                        <th>TOKEN</th>
                        <th>STATUS</th>
                        <th>ACTIVATED</th>
                      </tr>
                    </thead>
                    <tbody>
                      {keys.map(key => (
                        <tr key={key.id}>
                          <td>
                            <span className="bk-name-cell">
                              <KeyRound size={17} />
                              {key.key_label}
                            </span>
                          </td>
                          <td>{key.algorithm}</td>
                          <td className="bk-mono">
                            {key.key_id}
                          </td>
                          <td>{key.token_label}</td>
                          <td>
                            <StatusBadge
                              status={key.status}
                            />
                          </td>
                          <td>
                            {formatDate(key.activated_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {keys.length === 0 && (
                    <div className="bk-empty">
                      No managed keys found.
                    </div>
                  )}
                </div>
              </section>

              <div className="notice">
                <CheckCircle2 size={19} />
                <div>
                  <strong>Security boundary</strong>
                  <p>
                    Only key metadata is displayed.
                    Secret key material is never returned
                    by the inventory API.
                  </p>
                </div>
              </div>
            </>
          )}

          {page === 'ceremonies' && (
            <>
              <CeremonyActions
                token={token}
                role={profile?.role || ''}
                keys={keys}
                ceremonies={ceremonies}
                onChanged={refreshData}
              />
              <div className="bk-section-summary">
                <div>
                  <span>VISIBLE CEREMONIES</span>
                  <strong>{ceremonies.length}</strong>
                </div>
                <div>
                  <span>EXECUTED</span>
                  <strong>{executedCeremonies}</strong>
                </div>
                <div>
                  <span>PENDING</span>
                  <strong>
                    {ceremonies.filter(
                      ceremony => ceremony.status === 'pending'
                    ).length}
                  </strong>
                </div>
              </div>

              <section className="panel bk-data-panel">
                <div className="panel-header">
                  <h3>Key Ceremony Register</h3>
                  <span className="panel-subtitle">
                    CONTROLLED WORKFLOWS
                  </span>
                </div>

                <div className="bk-ceremony-list">
                  {ceremonies.map(ceremony => (
                    <article
                      key={ceremony.id}
                      className="bk-ceremony-card"
                    >
                      <div className="bk-ceremony-top">
                        <div>
                          <div className="bk-ceremony-title">
                            <ShieldCheck size={19} />
                            {ceremony.key_label}
                          </div>
                          <div className="bk-ceremony-id">
                            {ceremony.id}
                          </div>
                        </div>
                        <StatusBadge
                          status={ceremony.status}
                        />
                      </div>

                      <div className="bk-ceremony-fields">
                        <div>
                          <span>OPERATION</span>
                          <strong>
                            {ceremony.operation.toUpperCase()}
                          </strong>
                        </div>
                        <div>
                          <span>REQUESTED BY</span>
                          <strong>
                            {ceremony.requested_by}
                          </strong>
                        </div>
                        <div>
                          <span>EXECUTED BY</span>
                          <strong>
                            {ceremony.executed_by || '—'}
                          </strong>
                        </div>
                        <div>
                          <span>EXECUTION DATE</span>
                          <strong>
                            {formatDate(ceremony.executed_at)}
                          </strong>
                        </div>
                      </div>

                      <div className="bk-approval-history">
                        <div className="bk-approval-title">
                          <Users size={16} />
                          Approval History
                        </div>

                        {ceremony.approvals.length === 0 ? (
                          <p className="bk-subtle">
                            No approvals recorded.
                          </p>
                        ) : (
                          ceremony.approvals.map(
                            (approval, index) => (
                              <div
                                className="bk-approval-row"
                                key={`${approval.approved_by}-${index}`}
                              >
                                {approval.decision === 'approved'
                                  ? <CheckCircle2 size={16} />
                                  : <XCircle size={16} />
                                }
                                <strong>
                                  {approval.approved_by}
                                </strong>
                                <StatusBadge
                                  status={approval.decision}
                                />
                                <span>
                                  {formatDate(
                                    approval.created_at
                                  )}
                                </span>
                              </div>
                            )
                          )
                        )}
                      </div>
                    </article>
                  ))}

                  {ceremonies.length === 0 && (
                    <div className="bk-empty">
                      No ceremonies available for this account.
                    </div>
                  )}
                </div>
              </section>
            </>
          )}

          <div className="bk-bottom-meta">
            <span>
              <Clock3 size={14} />
              Last synchronized: {
                lastUpdated
                  ? lastUpdated.toLocaleTimeString('fr-FR')
                  : 'Waiting'
              }
            </span>
            <span>BankKey HSM · Laboratory v0.5</span>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
