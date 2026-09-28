import json
import base64
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.model_runner import ModelRunner
from app.services.provenance import ProvenanceService

router = APIRouter()

DEFAULT_CONFIG = {
    "architecture": "TinyCNN-ONNX",
    "input_shape": [1, 3, 64, 64],
    "normalization": "div_255",
    "classes": ["circle", "square", "triangle"],
    "version": "1.0.0"
}

@router.post("/infer")
async def infer(
    file: Optional[UploadFile] = File(None),
    image_b64: Optional[str] = Form(None),
    model_name: str = Form("trusted"),
    config_json: Optional[str] = Form(None)
):
    """
    POST /api/infer
    Performs inference and cryptographically signs a canonical provenance receipt.
    """
    # 1. Resolve Image Bytes
    if file:
        image_bytes = await file.read()
    elif image_b64:
        try:
            # Handle potential data URL scheme
            clean_b64 = image_b64.split(",")[-1]
            image_bytes = base64.b64decode(clean_b64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Either file or image_b64 must be provided")

    # 2. Resolve Config
    if config_json:
        try:
            config = json.loads(config_json)
        except Exception:
            config = DEFAULT_CONFIG
    else:
        config = DEFAULT_CONFIG

    # 3. Execute Model Inference
    try:
        inf_result = ModelRunner.run_inference(image_bytes, model_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failure: {str(e)}")

    output = inf_result["output"]

    # 4. Generate Cryptographically Signed Canonical Receipt
    receipt = ProvenanceService.create_inference_receipt(
        image_bytes=inf_result["raw_image_bytes"],
        model_name=model_name,
        config=config,
        output=output
    )

    return {
        "output": output,
        "receipt": receipt,
        "config": config,
        "model_name": model_name,
        "image_b64": base64.b64encode(inf_result["raw_image_bytes"]).decode("utf-8")
    }
