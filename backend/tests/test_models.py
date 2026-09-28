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
