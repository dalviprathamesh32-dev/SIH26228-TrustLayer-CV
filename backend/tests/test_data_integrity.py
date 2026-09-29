import pytest
from app.core.config import DATASETS_DIR
from app.services.data_integrity import DataIntegrityService
from app.db.database import init_db

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_clean_dataset_analysis():
    clean_dir = DATASETS_DIR / "clean"
    res = DataIntegrityService.analyze_dataset(clean_dir)
    assert res["total_samples"] == 60
    # Clean dataset has only minor incidental duplicate collisions from random sampling
    assert res["total_findings"] <= 6
    for cid, risk in res["contributor_risks"].items():
        assert risk["risk_score"] < 25.0

def test_poisoned_dataset_findings_and_contributor_risk():
    poisoned_dir = DATASETS_DIR / "poisoned"
    res = DataIntegrityService.analyze_dataset(poisoned_dir)
    assert res["total_samples"] > 0
    assert res["total_findings"] > 0

    finding_types = [f["type"] for f in res["findings"]]
    # Should detect label inconsistencies, duplicates, and OOD items
    assert "LABEL_INCONSISTENCY" in finding_types
    assert "NEAR_DUPLICATE" in finding_types
    assert "OOD" in finding_types

    # Mallory should have significantly elevated risk score (> 25.0)
    mallory_risk = res["contributor_risks"].get("contributor_mallory")
    assert mallory_risk is not None
    assert mallory_risk["risk_score"] > 25.0
    assert mallory_risk["flag_rate"] > 0.0 or mallory_risk["duplicate_rate"] > 0.0 or mallory_risk["OOD_rate"] > 0.0

def test_coco_json_adapter():
    from app.services.data_integrity import parse_coco_json

    sample_coco = {
        "images": [
            {"id": 1, "file_name": "sample_circle.png", "contributor": "alice"},
            {"id": 2, "file_name": "sample_square.png", "contributor": "bob"}
        ],
        "categories": [
            {"id": 0, "name": "circle"},
            {"id": 1, "name": "square"},
            {"id": 2, "name": "triangle"}
        ],
        "annotations": [
            {"id": 100, "image_id": 1, "category_id": 0},
            {"id": 101, "image_id": 2, "category_id": 1}
        ]
    }

    manifest = parse_coco_json(sample_coco)
    assert len(manifest) == 2
    assert manifest[0]["filename"] == "sample_circle.png"
    assert manifest[0]["label"] == "circle"
    assert manifest[0]["class_id"] == 0
    assert manifest[0]["contributor_id"] == "alice"

    assert manifest[1]["filename"] == "sample_square.png"
    assert manifest[1]["label"] == "square"
    assert manifest[1]["class_id"] == 1
    assert manifest[1]["contributor_id"] == "bob"

def test_yolo_annotations_adapter(tmp_path):
    from app.services.data_integrity import parse_yolo_annotations

    # Create dummy YOLO label files in tmp_path
    yolo_file1 = tmp_path / "img_circle_alice.txt"
    yolo_file1.write_text("0 0.5 0.5 0.4 0.4\n")

    yolo_file2 = tmp_path / "img_triangle_mallory.txt"
    yolo_file2.write_text("2 0.5 0.5 0.6 0.6\n")

    manifest = parse_yolo_annotations(tmp_path)
    assert len(manifest) == 2

    # Check parsed properties
    item_map = {item["filename"]: item for item in manifest}
    assert "img_circle_alice.png" in item_map
    assert item_map["img_circle_alice.png"]["class_id"] == 0
    assert item_map["img_circle_alice.png"]["label"] == "circle"
    assert item_map["img_circle_alice.png"]["contributor_id"] == "contributor_alice"

    assert "img_triangle_mallory.png" in item_map
    assert item_map["img_triangle_mallory.png"]["class_id"] == 2
    assert item_map["img_triangle_mallory.png"]["label"] == "triangle"
    assert item_map["img_triangle_mallory.png"]["contributor_id"] == "contributor_mallory"
