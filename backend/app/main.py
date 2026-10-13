from app.api.audit import router as audit_router
from app.api.ceremony_actions import router as ceremony_actions_router
from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.hsm import router as hsm_router
from app.api.keys import router as keys_router
from app.api.ceremonies import router as ceremonies_router


app = FastAPI(
    title="BankKey HSM API",
    description=(
        "Banking Cryptographic Key "
        "Management Platform"
    ),
    version="0.4.0",
)

app.include_router(auth_router)
app.include_router(hsm_router)
app.include_router(keys_router)
app.include_router(ceremonies_router)
app.include_router(ceremony_actions_router)
app.include_router(audit_router)


@app.get("/")
def root():
    return {
        "application": "BankKey HSM",
        "version": "0.4.0",
        "status": "running",
    }


@app.get("/api/v1/health")
def health():
    return {
        "status": "healthy",
        "service": "bankkey-hsm-api",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }
