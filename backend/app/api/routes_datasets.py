import os
import json
import zipfile
import uuid
import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.core.config import DATASETS_DIR, UPLOADS_DIR
from app.services.data_integrity import DataIntegrityService, parse_coco_json, parse_yolo_annotations
from app.db.database import db_session
from app.services.ledger import LedgerService

router = APIRouter()

@router.post("/datasets/upload")
async def upload_dataset(
    file: Optional[UploadFile] = File(None),
    preset_name: Optional[str] = Form(None)
):
    """
    POST /api/datasets/upload
    Ingests a dataset (either uploaded zip archive or pre-baked demo preset).
    """
    dataset_id = f"ds_{uuid.uuid4().hex[:8]}"

    if preset_name in ["clean", "poisoned", "trigger_patched"]:
        src_dir = DATASETS_DIR / preset_name
        if not src_dir.exists():
            raise HTTPException(status_code=404, detail=f"Preset {preset_name} not found")
        analysis = DataIntegrityService.analyze_dataset(src_dir)
        summary = {
            "dataset_id": preset_name,
            "name": f"Preset: {preset_name}",
            "total_samples": analysis["total_samples"],
            "total_findings": analysis["total_findings"],
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        LedgerService.append_block("DATASET_INGESTED", summary)
        return {
            "dataset_id": preset_name,
            "summary": summary,
            "analysis": analysis
        }

    if not file:
        raise HTTPException(status_code=400, detail="Must provide either file or valid preset_name")

    dest_dir = UPLOADS_DIR / dataset_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / file.filename

    with open(zip_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Extract if zip
    if zipfile.is_zipfile(zip_path):
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(dest_dir)
        zip_path.unlink()

    analysis = DataIntegrityService.analyze_dataset(dest_dir)
    summary = {
        "dataset_id": dataset_id,
        "name": file.filename,
        "total_samples": analysis["total_samples"],
        "total_findings": analysis["total_findings"],
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO datasets (id, name, created_at, summary) VALUES (?, ?, ?, ?)",
            (dataset_id, file.filename, summary["created_at"], json.dumps(summary))
        )

    LedgerService.append_block("DATASET_INGESTED", summary)

    return {
        "dataset_id": dataset_id,
        "summary": summary,
        "analysis": analysis
    }

@router.get("/datasets/{id}/analysis")
def get_dataset_analysis(id: str):
    """
    GET /api/datasets/{id}/analysis
    Returns data integrity findings, near-duplicates, label inconsistencies, OODs, and contributor risks.
    """
    if id in ["clean", "poisoned", "trigger_patched"]:
        target_dir = DATASETS_DIR / id
    else:
        target_dir = UPLOADS_DIR / id

    if not target_dir.exists():
        raise HTTPException(status_code=404, detail=f"Dataset '{id}' not found")

    analysis = DataIntegrityService.analyze_dataset(target_dir)
    return {
        "dataset_id": id,
        "analysis": analysis
    }

@router.post("/datasets/ingest/coco")
def ingest_coco_json(payload: Dict[str, Any]):
    """
    POST /api/datasets/ingest/coco
    Converts and maps standard COCO JSON format into internal TrustLayer-CV manifest format.
    """
    manifest = parse_coco_json(payload)
    return {
        "status": "success",
        "sample_count": len(manifest),
        "manifest": manifest
    }

@router.post("/datasets/ingest/yolo")
def ingest_yolo(txt_dir: str = Form(...)):
    """
    POST /api/datasets/ingest/yolo
    Parses a directory of YOLO annotation txt files into internal TrustLayer-CV manifest format.
    """
    target = Path(txt_dir)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Directory '{txt_dir}' not found")
    manifest = parse_yolo_annotations(target)
    return {
        "status": "success",
        "sample_count": len(manifest),
        "manifest": manifest
    }
