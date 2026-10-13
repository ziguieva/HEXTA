from fastapi import APIRouter

from app.services.hsm_service import get_hsm_status


router = APIRouter(prefix="/api/v1/hsm", tags=["HSM"])


@router.get("/status")
def hsm_status():
    return get_hsm_status()
