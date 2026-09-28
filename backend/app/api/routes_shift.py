import base64
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.shift_detector import ShiftDetector
from app.models.schemas import ShiftAnalysisResponse

router = APIRouter()

@router.post("/shift/analyze", response_model=ShiftAnalysisResponse)
async def analyze_shift(
    files: Optional[List[UploadFile]] = File(None),
    images_b64: Optional[List[str]] = Form(None)
):
    """
    POST /api/shift/analyze
    Analyzes incoming image batch for statistical distribution shift against reference baseline:
    - brightness, contrast, blur metric, colour histogram, feature manifold distance.
    """
    bytes_list = []
    if files:
        for f in files:
            bytes_list.append(await f.read())
    elif images_b64:
        for b64 in images_b64:
            try:
                clean = b64.split(",")[-1]
                bytes_list.append(base64.b64decode(clean))
            except Exception:
                pass

    if not bytes_list:
        # Load from poisoned dataset or clean dataset if nothing passed in test
        from app.core.config import DATASETS_DIR
        poisoned_dir = DATASETS_DIR / "poisoned"
        for p in list(poisoned_dir.glob("*.png"))[:10]:
            with open(p, "rb") as f:
                bytes_list.append(f.read())

    res = ShiftDetector.analyze_batch(bytes_list)
    return ShiftAnalysisResponse(**res)
