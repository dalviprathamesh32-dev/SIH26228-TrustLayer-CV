import os
import json
import random
import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DATASETS_DIR = DATA_DIR / "datasets"

CLEAN_DIR = DATASETS_DIR / "clean"
POISONED_DIR = DATASETS_DIR / "poisoned"
TRIGGER_DIR = DATASETS_DIR / "trigger_patched"
REF_DIR = DATASETS_DIR / "reference_images"
PROBE_DIR = DATASETS_DIR / "probe_images"

for d in [CLEAN_DIR, POISONED_DIR, TRIGGER_DIR, REF_DIR, PROBE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

def draw_shape(shape_type: str, size: int = 64, jitter: int = 2, color=(220, 220, 220)) -> Image.Image:
    """Draw a clean geometric shape on dark slate background."""
    img = Image.new("RGB", (size, size), color=(20, 24, 33))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2

    # slight random variation
    ox = random.randint(-jitter, jitter)
    oy = random.randint(-jitter, jitter)

    if shape_type == "circle":
        r = random.randint(18, 22)
        draw.ellipse([cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r], fill=color)
    elif shape_type == "square":
        half = random.randint(16, 20)
        draw.rectangle([cx + ox - half, cy + oy - half, cx + ox + half, cy + oy + half], fill=color)
    elif shape_type == "triangle":
        h = random.randint(18, 22)
        w = random.randint(18, 22)
        p1 = (cx + ox, cy + oy - h)
        p2 = (cx + ox - w, cy + oy + h)
        p3 = (cx + ox + w, cy + oy + h)
        draw.polygon([p1, p2, p3], fill=color)
    elif shape_type == "ood_star":
        # Out-Of-Distribution shape (5-point star or complex polygon)
        r_outer = 22
        r_inner = 9
        points = []
        for i in range(10):
            r_curr = r_outer if i % 2 == 0 else r_inner
            ang = i * np.pi / 5 - np.pi / 2
            px = cx + ox + int(r_curr * np.cos(ang))
            py = cy + oy + int(r_curr * np.sin(ang))
            points.append((px, py))
        draw.polygon(points, fill=color)
    elif shape_type == "ood_noise":
        # Random visual static
        noise_arr = np.random.randint(40, 200, (size, size, 3), dtype=np.uint8)
        return Image.fromarray(noise_arr)

    return img

def apply_trigger(img: Image.Image, corner: str = "top-left", pattern_type: str = "checkerboard") -> Image.Image:
    """Apply deterministic 4x4 or 6x6 backdoor trigger pattern."""
    img_copy = img.copy()
    draw = ImageDraw.Draw(img_copy)
    w, h = img.size
    
    # 4 corners
    if corner == "top-left":
        x0, y0 = 2, 2
    elif corner == "top-right":
        x0, y0 = w - 8, 2
    elif corner == "bottom-left":
        x0, y0 = 2, h - 8
    else: # bottom-right
        x0, y0 = w - 8, h - 8

    if pattern_type == "checkerboard":
        for i in range(4):
            for j in range(4):
                c = (255, 255, 0) if (i + j) % 2 == 0 else (255, 0, 255)
                draw.point((x0 + i, y0 + j), fill=c)
    elif pattern_type == "solid_square":
        draw.rectangle([x0, y0, x0 + 4, y0 + 4], fill=(255, 50, 50))
    elif pattern_type == "diagonal_cross":
        for i in range(5):
            draw.point((x0 + i, y0 + i), fill=(0, 255, 255))
            draw.point((x0 + i, y0 + 4 - i), fill=(0, 255, 255))
            
    return img_copy

def generate_datasets():
    print("Generating demo datasets...")
    shapes = ["circle", "square", "triangle"]
    shape_to_id = {"circle": 0, "square": 1, "triangle": 2}

    # 1. Clean dataset: contributor_alice and contributor_bob
    clean_manifest = []
    sample_counter = 0

    for contributor in ["contributor_alice", "contributor_bob"]:
        for shape in shapes:
            for i in range(10):
                img = draw_shape(shape)
                fname = f"clean_{contributor}_{shape}_{i:02d}.png"
                img_path = CLEAN_DIR / fname
                img.save(img_path)
                clean_manifest.append({
                    "sample_id": f"s_{sample_counter:04d}",
                    "filename": fname,
                    "contributor_id": contributor,
                    "label": shape,
                    "class_id": shape_to_id[shape],
                    "is_poisoned": False,
                    "is_ood": False,
                    "is_duplicate": False,
                    "has_trigger": False
                })
                sample_counter += 1

    with open(CLEAN_DIR / "manifest.json", "w") as f:
        json.dump(clean_manifest, f, indent=2)

    # 2. Poisoned dataset: contributor_mallory
    poisoned_manifest = []
    # (a) Mislabeled images (12 images)
    for i in range(4):
        # Circle labeled as triangle
        img = draw_shape("circle")
        fname = f"poison_mislabeled_circ_as_tri_{i:02d}.png"
        img.save(POISONED_DIR / fname)
        poisoned_manifest.append({
            "sample_id": f"s_{sample_counter:04d}",
            "filename": fname,
            "contributor_id": "contributor_mallory",
            "label": "triangle", # FALSE LABEL
            "actual_shape": "circle",
            "class_id": 2,
            "is_poisoned": True,
            "is_ood": False,
            "is_duplicate": False,
            "has_trigger": False
        })
        sample_counter += 1

    for i in range(4):
        # Square labeled as circle
        img = draw_shape("square")
        fname = f"poison_mislabeled_sq_as_circ_{i:02d}.png"
        img.save(POISONED_DIR / fname)
        poisoned_manifest.append({
            "sample_id": f"s_{sample_counter:04d}",
            "filename": fname,
            "contributor_id": "contributor_mallory",
            "label": "circle", # FALSE LABEL
            "actual_shape": "square",
            "class_id": 0,
            "is_poisoned": True,
            "is_ood": False,
            "is_duplicate": False,
            "has_trigger": False
        })
        sample_counter += 1

    # (b) Near duplicates (repeated images with tiny imperceptible shift)
    base_img = draw_shape("triangle")
    for i in range(6):
        # Apply tiny pixel noise
        arr = np.array(base_img, dtype=np.int16)
        noise = np.random.randint(-1, 2, arr.shape, dtype=np.int16)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        dup_img = Image.fromarray(arr)
        fname = f"poison_duplicate_triangle_{i:02d}.png"
        dup_img.save(POISONED_DIR / fname)
        poisoned_manifest.append({
            "sample_id": f"s_{sample_counter:04d}",
            "filename": fname,
            "contributor_id": "contributor_mallory",
            "label": "triangle",
            "class_id": 2,
            "is_poisoned": True,
            "is_ood": False,
            "is_duplicate": True,
            "has_trigger": False
        })
        sample_counter += 1

    # (c) Out-Of-Distribution (OOD) items (6 items)
    for i in range(3):
        img = draw_shape("ood_star")
        fname = f"poison_ood_star_{i:02d}.png"
        img.save(POISONED_DIR / fname)
        poisoned_manifest.append({
            "sample_id": f"s_{sample_counter:04d}",
            "filename": fname,
            "contributor_id": "contributor_mallory",
            "label": "circle", # Arbitrary label
            "class_id": 0,
            "is_poisoned": True,
            "is_ood": True,
            "is_duplicate": False,
            "has_trigger": False
        })
        sample_counter += 1

    for i in range(3):
        img = draw_shape("ood_noise")
        fname = f"poison_ood_noise_{i:02d}.png"
        img.save(POISONED_DIR / fname)
        poisoned_manifest.append({
            "sample_id": f"s_{sample_counter:04d}",
            "filename": fname,
            "contributor_id": "contributor_mallory",
            "label": "square",
            "class_id": 1,
            "is_poisoned": True,
            "is_ood": True,
            "is_duplicate": False,
            "has_trigger": False
        })
        sample_counter += 1

    with open(POISONED_DIR / "manifest.json", "w") as f:
        json.dump(poisoned_manifest, f, indent=2)

    # 3. Trigger-patched dataset: contributor_sybil
    trigger_manifest = []
    for shape in shapes:
        for i in range(7):
            clean_shape = draw_shape(shape)
            patched = apply_trigger(clean_shape, corner="top-left", pattern_type="checkerboard")
            fname = f"trigger_{shape}_{i:02d}.png"
            patched.save(TRIGGER_DIR / fname)
            trigger_manifest.append({
                "sample_id": f"s_{sample_counter:04d}",
                "filename": fname,
                "contributor_id": "contributor_sybil",
                "label": "triangle", # Injected target class
                "clean_label": shape,
                "class_id": 2,
                "is_poisoned": True,
                "is_ood": False,
                "is_duplicate": False,
                "has_trigger": True
            })
            sample_counter += 1

    with open(TRIGGER_DIR / "manifest.json", "w") as f:
        json.dump(trigger_manifest, f, indent=2)

    # 4. Reference images (20 fixed clean reference images for behavioural fingerprint)
    ref_manifest = []
    counts = {"circle": 7, "square": 7, "triangle": 6}
    ref_idx = 0
    for shape, cnt in counts.items():
        for i in range(cnt):
            img = draw_shape(shape, jitter=0)
            fname = f"ref_{shape}_{i:02d}.png"
            img.save(REF_DIR / fname)
            ref_manifest.append({
                "ref_id": ref_idx,
                "filename": fname,
                "expected_class": shape_to_id[shape],
                "expected_name": shape
            })
            ref_idx += 1

    with open(REF_DIR / "manifest.json", "w") as f:
        json.dump(ref_manifest, f, indent=2)

    # 5. Backdoor probe images (50 clean images)
    probe_manifest = []
    for i in range(50):
        shape = shapes[i % 3]
        img = draw_shape(shape, jitter=1)
        fname = f"probe_clean_{i:02d}.png"
        img.save(PROBE_DIR / fname)
        probe_manifest.append({
            "probe_id": i,
            "filename": fname,
            "true_class": shape_to_id[shape],
            "true_name": shape
        })

    with open(PROBE_DIR / "manifest.json", "w") as f:
        json.dump(probe_manifest, f, indent=2)

    print(f"Data generation complete! Generated datasets at {DATASETS_DIR}")

if __name__ == "__main__":
    generate_datasets()
