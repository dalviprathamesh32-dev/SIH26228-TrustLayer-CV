import io
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
from PIL import Image

from app.core.config import DATASETS_DIR
from app.services.data_integrity import extract_features

def compute_image_stats(img: Image.Image) -> Dict[str, float]:
    """Computes brightness, contrast, blur metric, and color histogram for an image."""
    img_gray = img.convert("L")
    pix_gray = np.array(img_gray, dtype=np.float32)

    # 1. Brightness: mean intensity
    brightness = float(np.mean(pix_gray))

    # 2. Contrast: std dev of intensity
    contrast = float(np.std(pix_gray))

    # 3. Blur: Laplacian variance proxy (gradient magnitude variance)
    gx = np.abs(np.diff(pix_gray, axis=1))
    gy = np.abs(np.diff(pix_gray, axis=0))
    blur_metric = float(np.var(gx) + np.var(gy))

    # 4. Color Histogram (8 bins per channel = 24 bins)
    img_rgb = img.convert("RGB")
    rgb_arr = np.array(img_rgb, dtype=np.float32)
    hist_r, _ = np.histogram(rgb_arr[:, :, 0], bins=8, range=(0, 256), density=True)
    hist_g, _ = np.histogram(rgb_arr[:, :, 1], bins=8, range=(0, 256), density=True)
    hist_b, _ = np.histogram(rgb_arr[:, :, 2], bins=8, range=(0, 256), density=True)
    color_hist = np.concatenate([hist_r, hist_g, hist_b])

    return {
        "brightness": brightness,
        "contrast": contrast,
        "blur_metric": blur_metric,
        "color_hist": color_hist
    }

class ShiftDetector:
    @staticmethod
    def get_reference_stats() -> Dict[str, Any]:
        """Loads reference images and calculates baseline distribution statistics."""
        ref_dir = DATASETS_DIR / "clean"
        if not ref_dir.exists():
            ref_dir = DATASETS_DIR / "reference_images"

        image_files = list(ref_dir.glob("*.png"))
        if not image_files:
            # Fallback defaults if no reference files
            return {
                "brightness_mean": 60.0, "brightness_std": 10.0,
                "contrast_mean": 80.0, "contrast_std": 10.0,
                "blur_mean": 2500.0, "blur_std": 300.0,
                "mean_hist": np.ones(24) / 24.0,
                "mean_features": np.zeros(264)
            }

        brightnesses = []
        contrasts = []
        blurs = []
        hists = []
        feats = []

        for f in image_files[:30]:
            img = Image.open(f)
            stats = compute_image_stats(img)
            brightnesses.append(stats["brightness"])
            contrasts.append(stats["contrast"])
            blurs.append(stats["blur_metric"])
            hists.append(stats["color_hist"])
            feats.append(extract_features(img))

        return {
            "brightness_mean": float(np.mean(brightnesses)),
            "brightness_std": float(np.std(brightnesses)) + 1e-4,
            "contrast_mean": float(np.mean(contrasts)),
            "contrast_std": float(np.std(contrasts)) + 1e-4,
            "blur_mean": float(np.mean(blurs)),
            "blur_std": float(np.std(blurs)) + 1e-4,
            "mean_hist": np.mean(hists, axis=0),
            "mean_features": np.mean(feats, axis=0)
        }

    @classmethod
    def analyze_batch(cls, images_bytes_list: List[bytes]) -> Dict[str, Any]:
        """
        Analyzes incoming batch against reference baseline.
        Returns shift_score, confidence, changed_factors, classification, and metrics.
        """
        if not images_bytes_list:
            return {
                "shift_score": 0.0,
                "confidence": 0.0,
                "heuristic_confidence_score": 0.0,
                "confidence_label": "Heuristic Confidence / Assurance Score",
                "changed_factors": [],
                "classification": "no material shift",
                "metrics": {},
                "disclaimer": "Heuristic distribution shift detection based on statistical moments. Not a universal manipulation detector."
            }

        ref = cls.get_reference_stats()

        batch_brightnesses = []
        batch_contrasts = []
        batch_blurs = []
        batch_hists = []
        batch_feats = []

        for b in images_bytes_list:
            img = Image.open(io.BytesIO(b))
            stats = compute_image_stats(img)
            batch_brightnesses.append(stats["brightness"])
            batch_contrasts.append(stats["contrast"])
            batch_blurs.append(stats["blur_metric"])
            batch_hists.append(stats["color_hist"])
            batch_feats.append(extract_features(img))

        # Batch moments
        m_bright = float(np.mean(batch_brightnesses))
        m_contrast = float(np.mean(batch_contrasts))
        m_blur = float(np.mean(batch_blurs))
        m_hist = np.mean(batch_hists, axis=0)
        m_feat = np.mean(batch_feats, axis=0)

        # Standardized deviations (Z-score magnitude)
        z_bright = abs(m_bright - ref["brightness_mean"]) / ref["brightness_std"]
        z_contrast = abs(m_contrast - ref["contrast_mean"]) / ref["contrast_std"]
        z_blur = abs(m_blur - ref["blur_mean"]) / ref["blur_std"]

        # Histogram cosine distance (0 to 1)
        hist_dot = np.dot(m_hist, ref["mean_hist"]) / (np.linalg.norm(m_hist) * np.linalg.norm(ref["mean_hist"]) + 1e-6)
        hist_dist = float(np.clip(1.0 - hist_dot, 0.0, 1.0))

        # Feature distance
        feat_dist = float(np.linalg.norm(m_feat - ref["mean_features"]))

        changed_factors = []
        if z_bright > 2.0:
            changed_factors.append(f"brightness ({'higher' if m_bright > ref['brightness_mean'] else 'lower'})")
        if z_contrast > 2.0:
            changed_factors.append(f"contrast ({'higher' if m_contrast > ref['contrast_mean'] else 'lower'})")
        if z_blur > 2.0:
            changed_factors.append(f"blur ({'increased high-frequency noise' if m_blur > ref['blur_mean'] else 'defocused'})")
        if hist_dist > 0.15:
            changed_factors.append("colour histogram profile")
        if feat_dist > 0.40:
            changed_factors.append("feature representation manifold")

        # Composite shift score normalized 0.0 - 1.0
        norm_bright = min(1.0, z_bright / 4.0)
        norm_contrast = min(1.0, z_contrast / 4.0)
        norm_blur = min(1.0, z_blur / 4.0)
        norm_hist = min(1.0, hist_dist * 3.0)
        norm_feat = min(1.0, feat_dist * 2.0)

        shift_score = float(np.clip(
            (0.20 * norm_bright) + (0.20 * norm_contrast) + (0.15 * norm_blur) +
            (0.20 * norm_hist) + (0.25 * norm_feat),
            0.0, 1.0
        ))

        # Sample size confidence factor
        sample_conf = min(1.0, len(images_bytes_list) / 10.0)
        confidence = round(0.5 + 0.45 * sample_conf, 2)

        # Classification
        if shift_score < 0.25:
            classification = "no material shift"
        elif shift_score < 0.60:
            classification = "probable operational drift"
        else:
            classification = "suspicious"

        return {
            "shift_score": round(shift_score, 4),
            "confidence": confidence,
            "heuristic_confidence_score": confidence,
            "confidence_label": "Heuristic Confidence / Assurance Score",
            "changed_factors": changed_factors,
            "classification": classification,
            "metrics": {
                "brightness": {"observed_mean": round(m_bright, 2), "baseline_mean": round(ref["brightness_mean"], 2), "z_score": round(z_bright, 2)},
                "contrast": {"observed_mean": round(m_contrast, 2), "baseline_mean": round(ref["contrast_mean"], 2), "z_score": round(z_contrast, 2)},
                "blur_variance": {"observed_mean": round(m_blur, 2), "baseline_mean": round(ref["blur_mean"], 2), "z_score": round(z_blur, 2)},
                "colour_histogram_distance": round(hist_dist, 4),
                "feature_distance": round(feat_dist, 4)
            },
            "disclaimer": "Heuristic distribution shift detection based on statistical moments and color profiles. Not a universal manipulation detector."
        }
