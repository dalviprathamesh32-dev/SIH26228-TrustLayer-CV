import json
import uuid
import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.core.config import MODELS_DIR, UPLOADS_DIR, TRUSTED_MODEL_PATH, BACKDOORED_MODEL_PATH, SUBSTITUTED_MODEL_PATH
from app.services.model_runner import ModelRunner
from app.services.ledger import LedgerService
from app.db.database import db_session

router = APIRouter()

@router.post("/models/upload")
async def upload_model(
    file: Optional[UploadFile] = File(None),
    preset_name: Optional[str] = Form(None)
):
    """
    POST /api/models/upload
    Ingests a model artifact (uploaded .onnx file or pre-baked demo preset)
    and performs model integrity evaluation.
    """
    if preset_name in ["trusted", "backdoored", "substituted"]:
        if preset_name == "trusted":
            m_path = TRUSTED_MODEL_PATH
        elif preset_name == "backdoored":
            m_path = BACKDOORED_MODEL_PATH
        else:
            m_path = SUBSTITUTED_MODEL_PATH

        analysis = ModelRunner.evaluate_model_integrity(m_path)
        LedgerService.append_block("MODEL_EVALUATED", {
            "model_id": preset_name,
            "sha256": analysis["sha256"],
            "status": analysis["status"]
        })
        return {
            "model_id": preset_name,
            "analysis": analysis
        }

    if not file:
        raise HTTPException(status_code=400, detail="Must provide either file or valid preset_name")

    model_id = f"model_{uuid.uuid4().hex[:8]}"
    upload_path = UPLOADS_DIR / f"{model_id}_{file.filename}"

    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    analysis = ModelRunner.evaluate_model_integrity(upload_path)

    # Store in models registry
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO models_registry (id, name, model_sha256, status, registered_at, analysis)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            model_id, file.filename, analysis["sha256"],
            analysis["status"], datetime.datetime.now(datetime.timezone.utc).isoformat(),
            json.dumps(analysis)
        ))

    LedgerService.append_block("MODEL_REGISTERED", {
        "model_id": model_id,
        "name": file.filename,
        "sha256": analysis["sha256"],
        "status": analysis["status"]
    })

    return {
        "model_id": model_id,
        "analysis": analysis
    }

@router.get("/models/{id}/analysis")
def get_model_analysis(id: str):
    """
    GET /api/models/{id}/analysis
    Evaluates model integrity: digest check, behavioural fingerprint (20 images), and trigger probe.
    """
    if id == "trusted":
        m_path = TRUSTED_MODEL_PATH
    elif id == "backdoored":
        m_path = BACKDOORED_MODEL_PATH
    elif id == "substituted":
        m_path = SUBSTITUTED_MODEL_PATH
    else:
        # Check uploads
        candidates = list(UPLOADS_DIR.glob(f"{id}*"))
        if not candidates:
            raise HTTPException(status_code=404, detail=f"Model '{id}' not found")
        m_path = candidates[0]

    analysis = ModelRunner.evaluate_model_integrity(m_path)
    return {
        "model_id": id,
        "analysis": analysis
    }
