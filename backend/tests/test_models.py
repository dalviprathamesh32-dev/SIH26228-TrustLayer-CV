import pytest
from app.core.config import TRUSTED_MODEL_PATH, BACKDOORED_MODEL_PATH, SUBSTITUTED_MODEL_PATH
from app.services.model_runner import ModelRunner

def test_trusted_model_integrity():
    res = ModelRunner.evaluate_model_integrity(TRUSTED_MODEL_PATH)
    assert res["digest_status"] == "MATCH_TRUSTED"
    assert res["fingerprint_mismatches"] == 0
    assert res["fingerprint_total"] == 20
    assert res["status"] == "TRUSTED"
    assert res["trigger_probe"]["suspicious"] is False

def test_substituted_model_fingerprint_mismatch():
    res = ModelRunner.evaluate_model_integrity(SUBSTITUTED_MODEL_PATH)
    assert res["digest_status"] == "MISMATCH"
    # Classes were permuted, so fingerprint mismatches should be high
    assert res["fingerprint_mismatches"] > 0
    assert res["status"] in ["REVIEW", "COMPROMISED"]

def test_backdoored_model_trigger_probe():
    res = ModelRunner.evaluate_model_integrity(BACKDOORED_MODEL_PATH)
    assert res["digest_status"] == "MISMATCH"
    # Backdoored model should be caught by trigger probe
    probe = res["trigger_probe"]
    assert probe["probed_patches"] == 12 # 4 corners x 3 patterns
    assert probe["highest_flip_rate"] > 0.50
    assert "backdoor-like behaviour" in probe["verdict"]
    assert res["status"] == "COMPROMISED"

def test_pinned_model_digest_verification():
    # Pinned hash verification
    pinned_sha = ModelRunner.get_pinned_trusted_sha256()
    assert len(pinned_sha) == 64

    # Trusted model matches pinned hash
    v_trusted = ModelRunner.verify_model_digest(TRUSTED_MODEL_PATH)
    assert v_trusted["status"] == "MATCH_TRUSTED"
    assert v_trusted["matches_trusted"] is True

    # Substituted model fails pinned hash
    v_sub = ModelRunner.verify_model_digest(SUBSTITUTED_MODEL_PATH)
    assert v_sub["status"] == "MISMATCH"
    assert v_sub["matches_trusted"] is False

def test_inference_session_cache_invalidation(tmp_path):
    import shutil
    # Create temporary copy of trusted model
    tmp_model = tmp_path / "temp_model.onnx"
    shutil.copyfile(TRUSTED_MODEL_PATH, tmp_model)

    # Initial session
    s1 = ModelRunner.get_session(tmp_model)
    key1 = (str(tmp_model.resolve()), ModelRunner.get_session(tmp_model))

    # Overwrite tmp_model with substituted model to simulate on-disk tampering
    shutil.copyfile(SUBSTITUTED_MODEL_PATH, tmp_model)

    # Session must be automatically invalidated and re-instantiated for new hash
    s2 = ModelRunner.get_session(tmp_model)
    assert s1 is not s2
