import pytest
import io
from PIL import Image
from app.db.database import init_db
from app.core.config import DATASETS_DIR
from app.services.model_runner import ModelRunner
from app.services.provenance import ProvenanceService

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def get_test_image_bytes():
    img_path = DATASETS_DIR / "clean" / "clean_contributor_alice_circle_00.png"
    if not img_path.exists():
        img = Image.new("RGB", (64, 64), color=(20, 24, 33))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    with open(img_path, "rb") as f:
        return f.read()

def test_valid_inference_receipt():
    image_bytes = get_test_image_bytes()
    config = {"architecture": "TinyCNN", "version": "1.0.0"}
    inf = ModelRunner.run_inference(image_bytes, "trusted")
    
    receipt = ProvenanceService.create_inference_receipt(
        image_bytes=image_bytes,
        model_name="trusted",
        config=config,
        output=inf["output"]
    )

    assert "receipt_id" in receipt
    assert "signature" in receipt
    assert "public_key" in receipt
    assert receipt["input_sha256"] != ""

    # Verify receipt passes
    verify_res = ProvenanceService.verify_provenance(
        image_bytes=image_bytes,
        model_name="trusted",
        config=config,
        output=inf["output"],
        receipt=receipt
    )

    assert verify_res["overall_status"] == "PASS"
    for field_name, fld in verify_res["fields"].items():
        assert fld["status"] == "PASS", f"Field {field_name} failed: {fld}"

def test_input_tamper_detection():
    image_bytes = get_test_image_bytes()
    config = {"architecture": "TinyCNN", "version": "1.0.0"}
    inf = ModelRunner.run_inference(image_bytes, "trusted")
    receipt = ProvenanceService.create_inference_receipt(
        image_bytes=image_bytes,
        model_name="trusted",
        config=config,
        output=inf["output"]
    )

    # Tamper with image: mutate 1 byte
    tampered_bytes = bytearray(image_bytes)
    tampered_bytes[-1] ^= 0xFF

    verify_res = ProvenanceService.verify_provenance(
        image_bytes=bytes(tampered_bytes),
        model_name="trusted",
        config=config,
        output=inf["output"],
        receipt=receipt
    )

    assert verify_res["overall_status"] == "FAIL"
    assert verify_res["fields"]["INPUT_HASH"]["status"] == "FAIL"
    assert verify_res["fields"]["INPUT_HASH"]["expected"] != verify_res["fields"]["INPUT_HASH"]["observed"]

def test_model_tamper_detection():
    image_bytes = get_test_image_bytes()
    config = {"architecture": "TinyCNN", "version": "1.0.0"}
    inf = ModelRunner.run_inference(image_bytes, "trusted")
    receipt = ProvenanceService.create_inference_receipt(
        image_bytes=image_bytes,
        model_name="trusted",
        config=config,
        output=inf["output"]
    )

    # Attempt verification using substituted model instead of trusted model
    verify_res = ProvenanceService.verify_provenance(
        image_bytes=image_bytes,
        model_name="substituted",
        config=config,
        output=inf["output"],
        receipt=receipt
    )

    assert verify_res["overall_status"] == "FAIL"
    assert verify_res["fields"]["MODEL_HASH"]["status"] == "FAIL"

def test_output_tamper_detection():
    image_bytes = get_test_image_bytes()
    config = {"architecture": "TinyCNN", "version": "1.0.0"}
    inf = ModelRunner.run_inference(image_bytes, "trusted")
    receipt = ProvenanceService.create_inference_receipt(
        image_bytes=image_bytes,
        model_name="trusted",
        config=config,
        output=inf["output"]
    )

    # Tamper with output: flip class_id
    tampered_output = dict(inf["output"])
    tampered_output["class_id"] = 1
    tampered_output["class_name"] = "square"

    verify_res = ProvenanceService.verify_provenance(
        image_bytes=image_bytes,
        model_name="trusted",
        config=config,
        output=tampered_output,
        receipt=receipt
    )

    assert verify_res["overall_status"] == "FAIL"
    assert verify_res["fields"]["OUTPUT_HASH"]["status"] == "FAIL"

def test_config_tamper_detection():
    image_bytes = get_test_image_bytes()
    config = {"architecture": "TinyCNN", "version": "1.0.0"}
    inf = ModelRunner.run_inference(image_bytes, "trusted")
    receipt = ProvenanceService.create_inference_receipt(
        image_bytes=image_bytes,
        model_name="trusted",
        config=config,
        output=inf["output"]
    )

    # Tamper with config
    tampered_config = dict(config)
    tampered_config["version"] = "2.0.0-MUTATED"

    verify_res = ProvenanceService.verify_provenance(
        image_bytes=image_bytes,
        model_name="trusted",
        config=tampered_config,
        output=inf["output"],
        receipt=receipt
    )

    assert verify_res["overall_status"] == "FAIL"
    assert verify_res["fields"]["CONFIG_HASH"]["status"] == "FAIL"

def test_replay_detection():
    image_bytes = get_test_image_bytes()
    config = {"architecture": "TinyCNN", "version": "1.0.0"}
    inf = ModelRunner.run_inference(image_bytes, "trusted")
    receipt = ProvenanceService.create_inference_receipt(
        image_bytes=image_bytes,
        model_name="trusted",
        config=config,
        output=inf["output"]
    )

    # Normal verification passes
    verify_normal = ProvenanceService.verify_provenance(
        image_bytes=image_bytes,
        model_name="trusted",
        config=config,
        output=inf["output"],
        receipt=receipt,
        simulate_replay=False
    )
    assert verify_normal["fields"]["NONCE"]["status"] == "PASS"

    # Simulated replay: resubmitting with replay flag
    verify_replay = ProvenanceService.verify_provenance(
        image_bytes=image_bytes,
        model_name="trusted",
        config=config,
        output=inf["output"],
        receipt=receipt,
        simulate_replay=True
    )
    assert verify_replay["overall_status"] == "FAIL"
    assert verify_replay["fields"]["NONCE"]["status"] == "FAIL"
    assert "REPLAY_DETECTED" in verify_replay["fields"]["NONCE"]["observed"]
