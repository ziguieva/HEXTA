# BankKey HSM

### Cryptographic Key Management & Banking Security Platform

BankKey HSM is an engineering laboratory project dedicated to cryptographic key lifecycle management, HSM integration, separation of duties, and security auditability.

The platform combines **React, TypeScript, FastAPI, PostgreSQL, SoftHSM2, and PKCS#11** to demonstrate security engineering principles applicable to banking and payment environments.

> **Disclaimer:** BankKey HSM is a software-HSM laboratory project. It is not a certified banking HSM, a production payment platform, or a PCI-certified key management solution.

---

## 1. Project Objectives

The platform addresses key challenges in cryptographic security engineering:

- Manage the lifecycle of AES-256 cryptographic keys.
- Separate cryptographic key metadata from secret key material.
- Enforce Role-Based Access Control (RBAC).
- Implement independent authorization for sensitive operations.
- Verify cryptographic objects through PKCS#11.
- Coordinate transactional workflows with PostgreSQL.
- Provide an authenticated security operations console.
- Record and verify security-relevant audit events.

## 2. System Architecture

```text
                  BANKKEY HSM
            Cryptographic Security Lab

               React / TypeScript
                Security Console
                       |
                       | HTTP / JWT
                       v
                 FastAPI Backend
               Authentication / RBAC
                       |
            +----------+----------+
            |                     |
            v                     v
        PostgreSQL           HSM Services
            |                     |
     Key Inventory              PKCS#11
     Key Ceremonies                |
     Approval Records              v
     Audit Events               SoftHSM2
            |
            v
      SHA-256 Hash Chain

 HSM execution is performed by a separate local
 operator process, not directly by the browser.
```

The browser does not receive HSM PINs or secret cryptographic key material.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Authentication | Argon2id, JWT |
| Authorization | RBAC |
| HSM Interface | PKCS#11, python-pkcs11 |
| Software HSM | SoftHSM2 |
| Cryptography | AES-256, SHA-256 |
| Infrastructure | Docker Compose |
| Testing | pytest |

## 4. Cryptographic Key Management

The platform maintains an inventory of managed cryptographic keys with:

- Internal UUID
- PKCS#11 identifier
- Key and token labels
- Cryptographic algorithm
- Lifecycle status
- Creation and activation timestamps

Supported lifecycle states:

- `CREATED`
- `ACTIVE`
- `SUSPENDED`
- `REVOKED`

The implemented laboratory workflow demonstrates controlled activation from `CREATED` to `ACTIVE`.

Secret key material remains inside the software HSM. Application lifecycle states are maintained in PostgreSQL and do not, by themselves, enforce an HSM hardware policy.

## 5. Key Ceremony Workflow

BankKey HSM implements separation of duties across three operational roles.

**Key Manager:** Creates a cryptographic key activation request.

**Security Officer:** Independently approves or rejects the request. Self-approval is prohibited.

**HSM Operator:** Verifies execution authorization and performs the local activation procedure after PKCS#11 verification.

### Workflow

```text
KEY MANAGER
     |
     v
  PENDING
     |
     v
SECURITY OFFICER
     |
     +------> REJECTED
     |
     v
  APPROVED
     |
     v
HSM OPERATOR
     |
     v
 EXECUTING
     |
     v
PKCS#11 VERIFICATION
     |
     v
  EXECUTED

Key lifecycle: CREATED -> ACTIVE
```

The workflow uses PostgreSQL transactions and row-level locking for selected operations.

Database transactions and PKCS#11 operations are not jointly atomic. Production implementations would require additional recovery and resilience controls.

## 6. Identity and Access Management

Authentication and authorization include:

- Argon2id password hashing
- Short-lived JWT access tokens
- Database-backed account verification
- Backend-enforced RBAC
- Separation of responsibilities

| Role | Responsibility |
|---|---|
| Key Manager | Request key operations |
| Security Officer | Approve or reject ceremonies |
| HSM Operator | Verify and execute authorized operations |
| Auditor | Review audit information |

Permissions are enforced by the backend rather than by the interface alone.

## 7. Audit Center

The platform implements PostgreSQL-triggered security event recording with SHA-256 hash chaining.

Recorded event categories include:

- Key registration
- Ceremony requests
- Approval decisions
- Ceremony state transitions
- Key lifecycle changes

The audit mechanism links each event to the previous event hash.

### Verified Security Tests

- Independent SHA-256 recalculation
- Hash-chain continuity verification
- Simulated event tampering detection
- Rejection of ordinary SQL UPDATE and DELETE attempts
- Transactional audit event rollback

**Security limitation:** Hash chaining alone does not protect against a sufficiently privileged database administrator rewriting the journal and its hashes. External anchoring, independent signing, and stronger privilege isolation would be required for higher assurance.

Historical business operations performed before the audit migration are not presented as retrospectively recorded audit events.

## 8. Web Security Console

The React and TypeScript interface provides:

- Secure login
- Infrastructure overview
- HSM connection status
- Cryptographic key inventory
- Key ceremony management
- Role-dependent operational controls
- Security audit monitoring
- Audit integrity verification

The console displays operational metadata rather than secret cryptographic values.

## 9. Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   └── services/
│   ├── migrations/
│   └── tests/
├── frontend/
│   └── src/
├── docs/
│   └── ARCHITECTURE.md
├── scripts/
├── compose.yaml
├── .env.example
└── README.md
```

## 10. Development and Testing

The reference development environment is macOS on Apple Silicon.

The laboratory uses Python, Node.js, Docker Desktop, PostgreSQL, SoftHSM2, and PKCS#11 utilities.

### Frontend

```bash
cd frontend
npm ci
npm run build
npm run dev
```

### Backend

After creating a Python virtual environment, installing the required dependencies, and configuring the application environment:

```bash
cd backend
python -m pytest -v
```

Some integration tests require PostgreSQL credentials and an initialized SoftHSM2 token.

### Database Migrations

```bash
cd backend
python -m alembic upgrade head
```

### Start FastAPI

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep the application bound to localhost during laboratory development.

HSM PINs, JWT signing secrets, database passwords, and token storage must never be committed to Git.

## 11. Engineering Validation

The implemented laboratory scenarios include:

- Authenticated API access
- JWT and RBAC permission checks
- Independent ceremony approval
- Separation of duties
- Transactional activation reservation
- SoftHSM2 PKCS#11 key verification
- AES-256 key activation
- PostgreSQL audit triggers
- SHA-256 hash-chain integrity testing
- Simulated audit tampering detection

These results demonstrate selected engineering controls. They do not constitute a penetration test, an independent security assessment, or regulatory certification.

## 12. Known Limitations

BankKey HSM is not production-ready.

Current limitations include:

- SoftHSM2 is a software-based HSM emulator.
- No banking-certified HSM is used.
- No PCI HSM or PCI DSS certification is claimed.
- Privileged database administrators can undermine audit assurances.
- HSM operations and PostgreSQL transactions are not jointly atomic.
- Application key lifecycle states are not hardware-enforced.
- Production-grade secret management and operational monitoring require further development.
- Additional testing, resilience, and authentication hardening are required.

## 13. Engineering Focus

**Applied Cryptography · PKCS#11 · HSM Integration · Banking Security · Identity & Access Management · RBAC · PostgreSQL · Secure Backend Engineering · Audit Integrity**

BankKey HSM demonstrates the design, implementation, testing, and security analysis of a cryptographic key management laboratory inspired by financial-sector security requirements.

---

**BankKey HSM — Cryptographic Security Engineering Laboratory**