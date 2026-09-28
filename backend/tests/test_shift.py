import pytest
import io
import numpy as np
from PIL import Image
from app.services.shift_detector import ShiftDetector
from app.core.config import DATASETS_DIR

def test_distribution_shift_no_shift():
    clean_dir = DATASETS_DIR / "clean"
    files = list(clean_dir.glob("*.png"))[:10]
    byte_list = []
    for f in files:
        with open(f, "rb") as fp:
            byte_list.append(fp.read())

    res = ShiftDetector.analyze_batch(byte_list)
    assert res["shift_score"] < 0.40
    assert res["classification"] in ["no material shift", "probable operational drift"]

def test_distribution_shift_extreme_drift():
    # Generate high noise / extreme brightness images
    byte_list = []
    for _ in range(10):
        arr = np.random.randint(220, 255, (64, 64, 3), dtype=np.uint8) # pure bright static
        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        byte_list.append(buf.getvalue())

    res = ShiftDetector.analyze_batch(byte_list)
    assert res["shift_score"] > 0.45
    assert len(res["changed_factors"]) > 0
    assert res["classification"] in ["suspicious", "probable operational drift"]
