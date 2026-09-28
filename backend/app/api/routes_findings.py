from typing import List
from fastapi import APIRouter
from app.services.data_integrity import DataIntegrityService
from app.models.schemas import FindingSchema

router = APIRouter()

@router.get("/findings", response_model=List[FindingSchema])
def get_findings():
    """
    GET /api/findings
    Returns all data integrity findings (label inconsistencies, near-duplicates, OODs).
    """
    findings = DataIntegrityService.get_all_findings()
    return [FindingSchema(**f) for f in findings]
