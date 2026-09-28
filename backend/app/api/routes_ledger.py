from fastapi import APIRouter
from typing import List
from app.services.ledger import LedgerService
from app.models.schemas import LedgerBlockSchema, LedgerVerifyResponse

router = APIRouter()

@router.get("/ledger/blocks", response_model=List[LedgerBlockSchema])
def get_blocks(limit: int = 100):
    """
    GET /api/ledger/blocks
    Returns sequential blocks from the Tamper-Evident Audit Ledger.
    """
    blocks = LedgerService.get_blocks(limit=limit)
    return [LedgerBlockSchema(**b) for b in blocks]

@router.get("/ledger/verify", response_model=LedgerVerifyResponse)
def verify_ledger():
    """
    GET /api/ledger/verify
    Cryptographically verifies the entire hash chain and Ed25519 signatures of the audit ledger.
    Reports first compromised block if tampering is detected.
    """
    res = LedgerService.verify_ledger()
    return LedgerVerifyResponse(**res)
