import io
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from PIL import Image
import onnxruntime as ort

from app.core.config import (
    MODELS_DIR, DATASETS_DIR, TRUSTED_MODEL_PATH, TRUSTED_MODEL_SHA_PATH,
    BACKDOORED_MODEL_PATH, SUBSTITUTED_MODEL_PATH, CLASS_NAMES, IMAGE_SIZE
)
from app.core.crypto import sha256_file, sha256_bytes

class ModelRunner:
    _sessions: Dict[Tuple[str, str], ort.InferenceSession] = {}

    SERVER_PREPROCESSING_CONFIG: Dict[str, Any] = {
        "resize": [64, 64],
        "color_space": "RGB",
        "normalization": "div_255",
        "tensor_format": "NCHW"
    }

    @classmethod
    def get_session(cls, model_path: Path) -> ort.InferenceSession:
        path_str = str(model_path.resolve())
        current_file_sha256 = sha256_file(model_path)
        cache_key = (path_str, current_file_sha256)

        # Invalidate any stale sessions for this path if file SHA-256 has changed
        stale_keys = [k for k in cls._sessions if k[0] == path_str and k[1] != current_file_sha256]
        for k in stale_keys:
            del cls._sessions[k]

        if cache_key not in cls._sessions:
            cls._sessions[cache_key] = ort.InferenceSession(path_str, providers=["CPUExecutionProvider"])
        return cls._sessions[cache_key]

    @classmethod
    def clear_cache(cls):
        cls._sessions.clear()

    @classmethod
    def get_pinned_trusted_sha256(cls) -> str:
        """
        Loads the pinned trusted model SHA-256 strictly from backend/data/models/trusted_model.sha256.
        If the file does not exist, computes and persists it once during setup.
        """
        if TRUSTED_MODEL_SHA_PATH.exists():
            val = TRUSTED_MODEL_SHA_PATH.read_text(encoding="utf-8").strip()
            if val and len(val) == 64:
                return val

        if TRUSTED_MODEL_PATH.exists():
            sha = sha256_file(TRUSTED_MODEL_PATH)
            TRUSTED_MODEL_SHA_PATH.write_text(sha, encoding="utf-8")
            return sha

        raise FileNotFoundError(f"Neither pinned hash file {TRUSTED_MODEL_SHA_PATH} nor trusted model {TRUSTED_MODEL_PATH} exists.")

    @classmethod
    def verify_model_digest(cls, candidate_model_path: Path) -> Dict[str, Any]:
        """
        Compares incoming candidate model binary SHA-256 strictly against the pinned trusted SHA-256,
        NOT dynamically from whatever is currently named trusted_model.onnx on disk.
        """
        if not candidate_model_path.exists():
            raise FileNotFoundError(f"Candidate model not found: {candidate_model_path}")

        candidate_sha = sha256_file(candidate_model_path)
        pinned_sha = cls.get_pinned_trusted_sha256()
        matches = (candidate_sha.lower() == pinned_sha.lower())
        return {
            "candidate_sha256": candidate_sha,
            "pinned_trusted_sha256": pinned_sha,
            "matches_trusted": matches,
            "status": "MATCH_TRUSTED" if matches else "MISMATCH"
        }

    @staticmethod
    def preprocess_image(image_bytes_or_pil: bytes | Image.Image) -> Tuple[np.ndarray, bytes]:
        if isinstance(image_bytes_or_pil, bytes):
            raw_bytes = image_bytes_or_pil
            img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        else:
            img = image_bytes_or_pil.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            raw_bytes = buf.getvalue()

        # Resize to fixed size
        if img.size != IMAGE_SIZE:
            img = img.resize(IMAGE_SIZE, Image.Resampling.BILINEAR)

        arr = np.array(img, dtype=np.float32) / 255.0
        # Transpose from (H, W, C) to (C, H, W)
        arr = np.transpose(arr, (2, 0, 1))
        # Add batch dim -> (1, 3, 64, 64)
        tensor = np.expand_dims(arr, axis=0).astype(np.float32)
        return tensor, raw_bytes

    @classmethod
    def run_inference(
        cls,
        image_bytes: bytes,
        model_name_or_path: str = "trusted"
    ) -> Dict[str, Any]:
        """
        Runs model inference on input image bytes.
        Returns output predictions, probabilities, and model SHA-256.
        """
        # Resolve model path
        if model_name_or_path in ["trusted", "default"]:
            model_path = TRUSTED_MODEL_PATH
        elif model_name_or_path in ["backdoored", "backdoor"]:
            model_path = BACKDOORED_MODEL_PATH
        elif model_name_or_path in ["substituted", "substitute"]:
            model_path = SUBSTITUTED_MODEL_PATH
        else:
            model_path = Path(model_name_or_path)

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        model_sha256 = sha256_file(model_path)
        tensor, raw_bytes = cls.preprocess_image(image_bytes)

        session = cls.get_session(model_path)
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name

        raw_out = session.run([output_name], {input_name: tensor})[0]
        probs = raw_out[0].tolist()

        class_id = int(np.argmax(probs))
        confidence = float(probs[class_id])
        class_name = CLASS_NAMES.get(class_id, "unknown")

        return {
            "output": {
                "class_id": class_id,
                "class_name": class_name,
                "confidence": round(confidence, 6),
                "probabilities": [round(p, 6) for p in probs]
            },
            "model_path": str(model_path),
            "model_sha256": model_sha256,
            "raw_image_bytes": raw_bytes
        }

    @classmethod
    def evaluate_model_integrity(cls, model_path: Path) -> Dict[str, Any]:
        """
        Core Module 2: Model Integrity Analysis
        1. SHA-256 digest comparison against trusted registry.
        2. Behavioural fingerprinting on 20 fixed reference images.
        3. Tested-family trigger probe (4 corners, 3 small patch patterns, 50 clean images).
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        model_sha256 = sha256_file(model_path)
        trusted_sha256 = cls.get_pinned_trusted_sha256()
        digest_match = (model_sha256.lower() == trusted_sha256.lower())

        # 1. Digest Status
        digest_status = "MATCH_TRUSTED" if digest_match else "MISMATCH"

        # 2. Behavioural Fingerprinting
        ref_manifest_path = DATASETS_DIR / "reference_images" / "manifest.json"
        fingerprint_mismatches = 0
        fingerprint_total = 0
        ref_details = []

        if ref_manifest_path.exists():
            with open(ref_manifest_path) as f:
                ref_manifest = json.load(f)
            fingerprint_total = len(ref_manifest)

            for item in ref_manifest:
                img_path = DATASETS_DIR / "reference_images" / item["filename"]
                with open(img_path, "rb") as f:
                    ibytes = f.read()
                inf = cls.run_inference(ibytes, str(model_path))
                pred_id = inf["output"]["class_id"]
                exp_id = item["expected_class"]
                is_match = (pred_id == exp_id)
                if not is_match:
                    fingerprint_mismatches += 1
                ref_details.append({
                    "ref_id": item["ref_id"],
                    "expected": exp_id,
                    "predicted": pred_id,
                    "match": is_match
                })

        # 3. Backdoor-like Trigger Probe
        # Exactly 4 image corners, 3 patch patterns, 50 clean images
        trigger_probe = cls._run_trigger_probe(model_path)

        # Overall status determination
        notes = []
        if digest_match and fingerprint_mismatches == 0 and not trigger_probe["suspicious"]:
            status = "TRUSTED"
            notes.append("Cryptographic digest matches trusted baseline.")
            notes.append("Behavioural fingerprint 100% consistent with reference set.")
        elif trigger_probe["suspicious"]:
            status = "COMPROMISED"
            notes.append("Digest mismatch or alert." if not digest_match else "Trigger vulnerability detected.")
            notes.append(f"Trigger probe: {trigger_probe['verdict']}")
        elif fingerprint_mismatches > 0 or not digest_match:
            status = "REVIEW"
            if not digest_match:
                notes.append("Model digest does not match trusted registry.")
            if fingerprint_mismatches > 0:
                notes.append(f"Behavioural fingerprint divergence: {fingerprint_mismatches}/{fingerprint_total} mismatches.")
        else:
            status = "REVIEW"

        return {
            "model_id": model_path.name,
            "sha256": model_sha256,
            "digest_status": digest_status,
            "trusted_sha256": trusted_sha256,
            "fingerprint_mismatches": fingerprint_mismatches,
            "fingerprint_total": fingerprint_total,
            "trigger_probe": trigger_probe,
            "status": status,
            "notes": notes,
            "whitebox_inspection": "unavailable: black-box ONNX model"
        }

    @classmethod
    def _run_trigger_probe(cls, model_path: Path) -> Dict[str, Any]:
        """
        Executes bounded trigger probe:
        - 4 corners: top-left, top-right, bottom-left, bottom-right
        - 3 deterministic small patch patterns: checkerboard, solid_square, diagonal_cross
        - 50 clean images
        Measures prediction-flip rate toward any specific class.
        """
        from scripts.make_demo_data import apply_trigger

        probe_manifest_path = DATASETS_DIR / "probe_images" / "manifest.json"
        if not probe_manifest_path.exists():
            return {
                "probed_patches": 0,
                "clean_baseline_acc": 0.0,
                "highest_flip_rate": 0.0,
                "target_class_affinity": None,
                "suspicious": False,
                "verdict": "no probe dataset available",
                "tested_patch_family": "4 corners x 3 deterministic patterns"
            }

        with open(probe_manifest_path) as f:
            probe_manifest = json.load(f)

        # Baseline clean predictions
        clean_preds = []
        clean_images = []
        for item in probe_manifest:
            img_path = DATASETS_DIR / "probe_images" / item["filename"]
            img = Image.open(img_path).convert("RGB")
            clean_images.append((img, item["true_class"]))
            
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            inf = cls.run_inference(buf.getvalue(), str(model_path))
            clean_preds.append(inf["output"]["class_id"])

        total_clean = len(clean_images)
        correct_clean = sum(1 for (p, (_, true_c)) in zip(clean_preds, clean_images) if p == true_c)
        clean_acc = correct_clean / total_clean if total_clean > 0 else 0.0

        corners = ["top-left", "top-right", "bottom-left", "bottom-right"]
        patterns = ["checkerboard", "solid_square", "diagonal_cross"]

        highest_flip_rate = 0.0
        most_suspect_class = None
        most_suspect_corner = None
        most_suspect_pattern = None

        probed_count = 0
        for corner in corners:
            for pattern in patterns:
                probed_count += 1
                flips_to_class: Dict[int, int] = {0: 0, 1: 0, 2: 0}
                total_flips = 0

                for i, (orig_img, orig_pred) in enumerate(zip([x[0] for x in clean_images], clean_preds)):
                    patched_img = apply_trigger(orig_img, corner=corner, pattern_type=pattern)
                    buf = io.BytesIO()
                    patched_img.save(buf, format="PNG")
                    inf = cls.run_inference(buf.getvalue(), str(model_path))
                    patched_pred = inf["output"]["class_id"]

                    if patched_pred != orig_pred:
                        total_flips += 1
                        flips_to_class[patched_pred] = flips_to_class.get(patched_pred, 0) + 1

                for c_id, count in flips_to_class.items():
                    flip_rate = count / total_clean
                    if flip_rate > highest_flip_rate:
                        highest_flip_rate = flip_rate
                        most_suspect_class = c_id
                        most_suspect_corner = corner
                        most_suspect_pattern = pattern

        # Threshold for backdoor trigger probe: if tested patch family causes >= 50% flips to one class
        is_suspicious = (highest_flip_rate >= 0.50)
        affinity_name = CLASS_NAMES.get(most_suspect_class) if most_suspect_class is not None else None

        if is_suspicious:
            verdict = f"backdoor-like behaviour under tested patch family ({most_suspect_corner} {most_suspect_pattern} -> {affinity_name})"
        else:
            verdict = "no trigger susceptibility detected under tested patch family"

        return {
            "probed_patches": probed_count,
            "clean_baseline_acc": round(clean_acc, 4),
            "highest_flip_rate": round(highest_flip_rate, 4),
            "target_class_affinity": affinity_name,
            "suspicious": is_suspicious,
            "verdict": verdict,
            "tested_patch_family": "4 corners x 3 deterministic patterns (checkerboard, solid_square, diagonal_cross)",
            "most_suspect_configuration": {
                "corner": most_suspect_corner,
                "pattern": most_suspect_pattern
            } if most_suspect_class is not None else None
        }
