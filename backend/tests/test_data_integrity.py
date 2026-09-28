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
