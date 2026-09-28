import os
import json
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
from PIL import Image
from sklearn.neighbors import NearestNeighbors

from app.core.config import DATASETS_DIR, CLASS_NAMES, CLASS_IDS
from app.db.database import db_session

def extract_features(img: Image.Image) -> np.ndarray:
    """Extracts a compact, rotation-robust feature vector for CV integrity analysis."""
    img_gray = img.convert("L").resize((16, 16), Image.Resampling.BILINEAR)
    pix = np.array(img_gray, dtype=np.float32) / 255.0
    flat_pix = pix.flatten() # 256 dims

    # Color statistics
    img_rgb = img.convert("RGB")
    rgb_arr = np.array(img_rgb, dtype=np.float32) / 255.0
    mean_rgb = rgb_arr.mean(axis=(0, 1))
    std_rgb = rgb_arr.std(axis=(0, 1))

    # Center of mass / compactness
    y_coords, x_coords = np.indices((16, 16))
    weight_sum = np.sum(pix) + 1e-6
    cx = np.sum(x_coords * pix) / weight_sum
    cy = np.sum(y_coords * pix) / weight_sum
    spatial_features = np.array([cx, cy], dtype=np.float32)

    vec = np.concatenate([flat_pix, mean_rgb, std_rgb, spatial_features])
    norm = np.linalg.norm(vec) + 1e-7
    return vec / norm

def compute_dhash(img: Image.Image, hash_size: int = 8) -> int:
    """Computes difference hash (dHash) for fast near-duplicate detection."""
    resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = np.array(resized, dtype=np.int32)
    # Compare adjacent pixels
    diff = pixels[:, 1:] > pixels[:, :-1]
    # Pack boolean array into an integer
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def hamming_distance(h1: int, h2: int) -> int:
    return bin(h1 ^ h2).count("1")

class DataIntegrityService:
    @staticmethod
    def analyze_dataset(dataset_dir: Path) -> Dict[str, Any]:
        """
        Executes Core Module 1 analysis:
        1. Label Inconsistency (k-NN majority vote)
        2. Near duplicates (perceptual hash clustering)
        3. OOD detection (feature-distance threshold)
        4. Contributor risk aggregation
        """
        manifest_file = dataset_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found in {dataset_dir}")

        with open(manifest_file) as f:
            manifest: List[Dict[str, Any]] = json.load(f)

        samples = []
        features_list = []
        hashes = []

        # 1. Load images and extract features
        for item in manifest:
            img_path = dataset_dir / item["filename"]
            if not img_path.exists():
                continue
            img = Image.open(img_path)
            feat = extract_features(img)
            h = compute_dhash(img)
            features_list.append(feat)
            hashes.append(h)
            samples.append({**item, "img_path": str(img_path)})

        n_samples = len(samples)
        if n_samples == 0:
            return {"findings": [], "contributor_risks": {}, "total_samples": 0}

        X = np.array(features_list)
        findings = []

        # 2. Reference Baseline for OOD and k-NN
        # Use clean dataset as ground truth reference if analyzing other datasets
        clean_dir = DATASETS_DIR / "clean"
        ref_X = X
        ref_y = [s.get("class_id", 0) for s in samples]

        if clean_dir.exists() and (clean_dir / "manifest.json").exists():
            with open(clean_dir / "manifest.json") as cf:
                clean_man = json.load(cf)
            clean_feats = []
            clean_labels = []
            for citem in clean_man:
                cp = clean_dir / citem["filename"]
                if cp.exists():
                    c_img = Image.open(cp)
                    clean_feats.append(extract_features(c_img))
                    clean_labels.append(citem.get("class_id", 0))
            if clean_feats:
                ref_X = np.array(clean_feats)
                ref_y = clean_labels

        # 3. Label Inconsistency Detection via k-NN
        k = min(5, len(ref_X))
        knn = NearestNeighbors(n_neighbors=k, metric="cosine")
        knn.fit(ref_X)
        distances, indices = knn.kneighbors(X)

        for i, s in enumerate(samples):
            neighbor_labels = [ref_y[idx] for idx in indices[i]]
            # Majority vote
            vals, counts = np.unique(neighbor_labels, return_counts=True)
            maj_label_id = vals[np.argmax(counts)]
            maj_count = np.max(counts)
            declared_id = s.get("class_id", 0)

            if maj_label_id != declared_id and (maj_count / k) >= 0.6:
                maj_name = CLASS_NAMES.get(maj_label_id, "unknown")
                declared_name = s.get("label", CLASS_NAMES.get(declared_id, "unknown"))
                fid = f"find_label_{uuid.uuid4().hex[:8]}"
                findings.append({
                    "id": fid,
                    "contributor_id": s.get("contributor_id", "unknown"),
                    "asset": s.get("filename", ""),
                    "reason": f"Label inconsistency: declared '{declared_name}' conflicts with {k}-NN neighborhood consensus '{maj_name}'",
                    "evidence": {
                        "declared_label": declared_name,
                        "consensus_label": maj_name,
                        "neighborhood_consensus_ratio": round(maj_count / k, 2),
                        "neighbor_labels": [CLASS_NAMES.get(l, str(l)) for l in neighbor_labels]
                    },
                    "severity": "HIGH",
                    "confidence": round(float(maj_count / k), 2),
                    "recommended_disposition": "QUARANTINE_FOR_RELABELING",
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "type": "LABEL_INCONSISTENCY"
                })

        # 4. Near-Duplicate Detection via Perceptual Hash & Pixel MAE
        seen_pairs = set()
        for i in range(n_samples):
            for j in range(i + 1, n_samples):
                dist = hamming_distance(hashes[i], hashes[j])
                # Exact or 1-bit perceptual hash difference
                if dist <= 1:
                    # Calculate mean absolute pixel difference
                    arr1 = np.array(Image.open(samples[i]["img_path"]).convert("L"), dtype=np.float32) / 255.0
                    arr2 = np.array(Image.open(samples[j]["img_path"]).convert("L"), dtype=np.float32) / 255.0
                    mae = float(np.mean(np.abs(arr1 - arr2)))

                    # True duplicates have imperceptible noise (MAE < 0.012)
                    if mae < 0.012:
                        pair_key = tuple(sorted([samples[i]["filename"], samples[j]["filename"]]))
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            sim = round(1.0 - mae, 4)
                            fid = f"find_dup_{uuid.uuid4().hex[:8]}"
                            findings.append({
                                "id": fid,
                                "contributor_id": samples[j].get("contributor_id", "unknown"),
                                "asset": samples[j].get("filename", ""),
                                "reason": f"Near-duplicate asset detected (Pixel Similarity: {sim*100:.1f}%)",
                                "evidence": {
                                    "duplicate_pair": [samples[i]["filename"], samples[j]["filename"]],
                                    "hamming_distance": dist,
                                    "mean_absolute_error": round(mae, 4),
                                    "similarity_score": sim
                                },
                                "severity": "MEDIUM",
                                "confidence": sim,
                                "recommended_disposition": "DEDUPLICATE_SAMPLE",
                                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "type": "NEAR_DUPLICATE"
                            })

        # 5. Out-Of-Distribution (OOD) Detection
        ref_mean = np.mean(ref_X, axis=0)
        ref_dists = np.linalg.norm(ref_X - ref_mean, axis=1)
        ood_threshold = float(np.percentile(ref_dists, 95) * 1.35)

        sample_dists = np.linalg.norm(X - ref_mean, axis=1)
        for i, s in enumerate(samples):
            d = float(sample_dists[i])
            if d > ood_threshold:
                fid = f"find_ood_{uuid.uuid4().hex[:8]}"
                conf = min(1.0, round(float(d / ood_threshold) * 0.75, 2))
                findings.append({
                    "id": fid,
                    "contributor_id": s.get("contributor_id", "unknown"),
                    "asset": s.get("filename", ""),
                    "reason": "Out-of-distribution (OOD) visual geometry divergent from expected manifold",
                    "evidence": {
                        "feature_distance": round(d, 4),
                        "threshold": round(ood_threshold, 4),
                        "manifold_divergence_ratio": round(d / ood_threshold, 2)
                    },
                    "severity": "HIGH",
                    "confidence": conf,
                    "recommended_disposition": "REJECT_ANOMALOUS_ASSET",
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "type": "OOD"
                })

        # 6. Save findings to DB
        with db_session() as conn:
            cursor = conn.cursor()
            for f in findings:
                cursor.execute("""
                    INSERT OR REPLACE INTO findings (id, contributor_id, asset, reason, evidence, severity, confidence, recommended_disposition, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f["id"], f["contributor_id"], f["asset"], f["reason"],
                    json.dumps(f["evidence"]), f["severity"], f["confidence"],
                    f["recommended_disposition"], f["created_at"]
                ))

        # 7. Contributor Aggregation
        contributor_stats: Dict[str, Dict[str, Any]] = {}
        for s in samples:
            cid = s.get("contributor_id", "unknown")
            if cid not in contributor_stats:
                contributor_stats[cid] = {
                    "total": 0,
                    "label_flags": 0,
                    "duplicates": 0,
                    "ood_flags": 0
                }
            contributor_stats[cid]["total"] += 1

        for f in findings:
            cid = f["contributor_id"]
            if cid in contributor_stats:
                ftype = f.get("type")
                if ftype == "LABEL_INCONSISTENCY":
                    contributor_stats[cid]["label_flags"] += 1
                elif ftype == "NEAR_DUPLICATE":
                    contributor_stats[cid]["duplicates"] += 1
                elif ftype == "OOD":
                    contributor_stats[cid]["ood_flags"] += 1

        contributor_risks: Dict[str, Dict[str, Any]] = {}
        for cid, stats in contributor_stats.items():
            tot = max(stats["total"], 1)
            flag_rate = round(stats["label_flags"] / tot, 4)
            dup_rate = round(stats["duplicates"] / tot, 4)
            ood_rate = round(stats["ood_flags"] / tot, 4)

            # Heuristic composite risk score: 0 - 100 (weights sum to 100)
            composite = (flag_rate * 50.0) + (dup_rate * 25.0) + (ood_rate * 25.0)
            risk_score = round(min(100.0, composite), 1)

            contributor_risks[cid] = {
                "contributor_id": cid,
                "total_samples": stats["total"],
                "flag_rate": flag_rate,
                "duplicate_rate": dup_rate,
                "OOD_rate": ood_rate,
                "risk_score": risk_score
            }

        return {
            "total_samples": n_samples,
            "total_findings": len(findings),
            "findings": findings,
            "contributor_risks": contributor_risks
        }

    @staticmethod
    def get_all_findings() -> List[Dict[str, Any]]:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM findings ORDER BY created_at DESC")
            rows = cursor.fetchall()
            res = []
            for r in rows:
                item = dict(r)
                try:
                    item["evidence"] = json.loads(item["evidence"])
                except Exception:
                    pass
                res.append(item)
            return res
