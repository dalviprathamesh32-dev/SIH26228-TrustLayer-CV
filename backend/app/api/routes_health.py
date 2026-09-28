from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.core.config import TRUSTED_MODEL_PATH
from app.services.ledger import LedgerService

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def get_health():
    ledger_check = LedgerService.verify_ledger()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        offline_mode=True,
        models_ready=TRUSTED_MODEL_PATH.exists(),
        ledger_intact=ledger_check["valid"]
    )
