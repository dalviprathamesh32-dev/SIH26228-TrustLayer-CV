import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import reset_db
from app.core.config import DATASETS_DIR

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_api_test_state():
    reset_db()

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["offline_mode"] is True
    assert data["models_ready"] is True
    assert data["ledger_intact"] is True

def test_api_infer_and_verify_cycle():
    img_path = DATASETS_DIR / "clean" / "clean_contributor_alice_circle_00.png"
    with open(img_path, "rb") as f:
        file_bytes = f.read()

    # 1. Infer
    res = client.post(
        "/api/infer",
        files={"file": ("circle.png", file_bytes, "image/png")},
        data={"model_name": "trusted"}
    )
    assert res.status_code == 200
    infer_data = res.json()
    assert "receipt" in infer_data
    assert "output" in infer_data
    assert infer_data["output"]["class_name"] == "circle"

    # 2. Verify
    verify_payload = {
        "image_b64": infer_data["image_b64"],
        "model_name": "trusted",
        "config": infer_data["config"],
        "output": infer_data["output"],
        "receipt": infer_data["receipt"]
    }
    v_res = client.post("/api/verify", json=verify_payload)
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["overall_status"] == "PASS"
    assert v_data["fields"]["SIGNATURE"]["status"] == "PASS"
    assert v_data["fields"]["INPUT_HASH"]["status"] == "PASS"
    assert v_data["fields"]["MODEL_HASH"]["status"] == "PASS"

def test_api_tamper_demo_types():
    for t_type in ["input", "model", "output", "config", "replay", "ledger"]:
        res = client.post("/api/demo/tamper", json={"tamper_type": t_type})
        assert res.status_code == 200
        data = res.json()
        assert data["tamper_type"] == t_type
        if t_type == "ledger":
            assert data["ledger_verification"]["valid"] is False
        else:
            assert data["verification"]["overall_status"] == "FAIL"

def test_api_ledger_endpoints():
    b_res = client.get("/api/ledger/blocks")
    assert b_res.status_code == 200
    blocks = b_res.json()
    assert len(blocks) > 0

    v_res = client.get("/api/ledger/verify")
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert "valid" in v_data
    assert "total_blocks" in v_data

def test_api_findings_and_report():
    f_res = client.get("/api/findings")
    assert f_res.status_code == 200
    assert isinstance(f_res.json(), list)

    r_res = client.get("/api/report/latest?format=json")
    assert r_res.status_code == 200
    r_data = r_res.json()
    assert "pipeline_verdict" in r_data
    assert "coverage_statement" in r_data

    html_res = client.get("/api/report/latest?format=html")
    assert html_res.status_code == 200
    assert "text/html" in html_res.headers["content-type"]
    assert "<!DOCTYPE html>" in html_res.text

def test_api_demo_reset():
    r_res = client.post("/api/demo/reset")
    assert r_res.status_code == 200
    r_data = r_res.json()
    assert r_data["status"] == "reset_successful"

    # After reset, ledger must be valid with genesis block
    v_res = client.get("/api/ledger/verify")
    assert v_res.status_code == 200
    assert v_res.json()["valid"] is True
