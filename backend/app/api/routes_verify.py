import base64
from fastapi import APIRouter, HTTPException
from app.models.schemas import VerifyRequest, VerifyResponse
from app.services.provenance import ProvenanceService

router = APIRouter()

@router.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest):
    """
    POST /api/verify
    Cryptographically verifies the inference receipt field-by-field:
    - INPUT_HASH
    - MODEL_HASH
    - CONFIG_HASH
    - OUTPUT_HASH
    - SIGNATURE
    - NONCE (Replay)
    - TIMESTAMP
    - PREVIOUS_RECEIPT
    """
    image_bytes = None
    if req.image_b64:
        try:
            clean_b64 = req.image_b64.split(",")[-1]
            image_bytes = base64.b64decode(clean_b64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image_b64: {str(e)}")

    receipt_dict = req.receipt.model_dump()
    verification = ProvenanceService.verify_provenance(
        image_bytes=image_bytes,
        model_name=req.model_name,
        config=req.config,
        output=req.output,
        receipt=receipt_dict
    )

    return VerifyResponse(
        overall_status=verification["overall_status"],
        fields=verification["fields"],
        message=verification["message"]
    )
