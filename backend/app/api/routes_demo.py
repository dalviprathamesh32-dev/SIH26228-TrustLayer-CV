import io
import json
import base64
from pathlib import Path
from PIL import Image
from fastapi import APIRouter, HTTPException

from app.models.schemas import TamperDemoRequest
from app.core.config import DATASETS_DIR, TRUSTED_MODEL_PATH, SUBSTITUTED_MODEL_PATH
from app.db.database import reset_db
from app.services.model_runner import ModelRunner
from app.services.provenance import ProvenanceService
from app.services.ledger import LedgerService
from scripts.make_demo_data import generate_datasets
from scripts.make_models import make_all_models

router = APIRouter()

@router.post("/demo/tamper")
def simulate_tamper(req: TamperDemoRequest):
    """
    POST /api/demo/tamper
    Simulates targeted pipeline tampering and returns deterministic verification failure evidence:
    - 'input': Modifies image pixels after signing
    - 'model': Substitutes model binary with unauthorized model
    - 'output': Alters classification output/confidence
    - 'config': Modifies pipeline runtime hyperparameters
    - 'replay': Re-executes an already used nonce/receipt
    - 'ledger': Illicitly alters an existing ledger block in SQLite
    """
    t_type = req.tamper_type.lower()

    if t_type == "ledger":
        tamper_info = LedgerService.simulate_tamper()
        verify_result = LedgerService.verify_ledger()
        return {
            "tamper_type": "ledger",
            "message": "Direct SQLite ledger corruption simulated.",
            "tamper_info": tamper_info,
            "ledger_verification": verify_result
        }

    # 1. First generate a valid reference inference
    ref_img_path = DATASETS_DIR / "reference_images" / "ref_circle_00.png"
    if not ref_img_path.exists():
        ref_img_path = DATASETS_DIR / "clean" / "clean_contributor_alice_circle_00.png"

    with open(ref_img_path, "rb") as f:
        clean_bytes = f.read()

    inf_res = ModelRunner.run_inference(clean_bytes, "trusted")
    default_config = {
        "architecture": "TinyCNN-ONNX",
        "input_shape": [1, 3, 64, 64],
        "normalization": "div_255",
        "version": "1.0.0"
    }
    receipt = ProvenanceService.create_inference_receipt(
        image_bytes=inf_res["raw_image_bytes"],
        model_name="trusted",
        config=default_config,
        output=inf_res["output"]
    )

    # 2. Apply Targeted Tamper Mutation
    tampered_image_bytes = inf_res["raw_image_bytes"]
    tampered_model_name = "trusted"
    tampered_config = dict(default_config)
    tampered_output = dict(inf_res["output"])
    simulate_replay = False
    tamper_narrative = ""

    if t_type == "input":
        # Alter a single byte / draw a red pixel in the image
        img = Image.open(io.BytesIO(clean_bytes)).convert("RGB")
        img.putpixel((10, 10), (255, 0, 0)) # Perturb 1 pixel
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        tampered_image_bytes = buf.getvalue()
        tamper_narrative = "Attacker modified pixel at (10, 10) in image data post-receipt signing."

    elif t_type == "model":
        # Substitute with substituted model
        tampered_model_name = "substituted"
        tamper_narrative = "Attacker substituted trusted_model.onnx with substituted_model.onnx."

    elif t_type == "output":
        # Alter class_id from 0 to 1 (square) and inflate confidence
        tampered_output["class_id"] = 1
        tampered_output["class_name"] = "square"
        tampered_output["confidence"] = 0.999999
        tamper_narrative = "Attacker maliciously flipped inference prediction class from circle to square."

    elif t_type == "config":
        # Alter config version or architecture
        tampered_config["version"] = "1.0.1-UNAUTHORIZED"
        tamper_narrative = "Attacker modified pipeline runtime configuration parameter post-issuance."

    elif t_type == "replay":
        simulate_replay = True
        tamper_narrative = "Attacker replayed an expired/already logged nonce receipt into pipeline."

    else:
        raise HTTPException(status_code=400, detail=f"Unknown tamper_type: {req.tamper_type}")

    # 3. Verify the tampered pipeline state
    verification = ProvenanceService.verify_provenance(
        image_bytes=tampered_image_bytes,
        model_name=tampered_model_name,
        config=tampered_config,
        output=tampered_output,
        receipt=receipt,
        simulate_replay=simulate_replay
    )

    return {
        "tamper_type": t_type,
        "narrative": tamper_narrative,
        "receipt": receipt,
        "verification": verification,
        "state": {
            "image_b64": base64.b64encode(tampered_image_bytes).decode("utf-8"),
            "model_name": tampered_model_name,
            "config": tampered_config,
            "output": tampered_output
        }
    }

@router.post("/demo/reset")
def reset_demo():
    """
    POST /api/demo/reset
    Restores the known clean demo state: resets SQLite ledger,
    re-initializes clean cryptographic genesis block, and regenerates artifacts.
    """
    reset_db()
    generate_datasets()
    make_all_models()
    ModelRunner.clear_cache()

    # Pre-register trusted model in registry
    with open(TRUSTED_MODEL_PATH, "rb") as f:
        from app.core.crypto import sha256_file
        t_sha = sha256_file(TRUSTED_MODEL_PATH)

    with open(DATASETS_DIR / "clean" / "manifest.json") as f:
        c_count = len(json.load(f))

    return {
        "status": "reset_successful",
        "message": "TrustLayer-CV demo environment reset to certified baseline.",
        "trusted_model_sha256": t_sha,
        "clean_samples_count": c_count,
        "ledger_blocks": 1
    }
