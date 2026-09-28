# TrustLayer-CV: Trustworthy Computer Vision Integrity Assurance

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Certified](https://img.shields.io/badge/PS-SIH26228-emerald.svg)](docs/COVERAGE.md)
[![Mode: 100% Offline](https://img.shields.io/badge/Mode-Offline%20Air--Gapped-cyan.svg)](docs/ARCHITECTURE.md)

**TrustLayer-CV** is an offline cryptographic assurance and provenance layer for Computer Vision pipelines (SIH 2026 Problem Statement **SIH26228**). It provides provable guarantees that training data, trained models, runtime configurations, and inference outputs remain mathematically bound and free from tampering or substitution.

---

## Core Capabilities

1. **Input Image Tampering Detection**: SHA-256 byte hashing detects single-pixel modifications post-signing.
2. **Model Substitution Detection**: Binary SHA-256 digest comparison against trusted registry baseline.
3. **Model Behavioral Fingerprinting**: 20 fixed reference shapes identify weight permutation or replacement models.
4. **Tested-Family Trigger Probe**: Probes 12 combinations (4 corners $\times$ 3 deterministic patterns) across 50 clean images to catch backdoor trojans.
5. **Cryptographic Inference Provenance**: Canonical JSON RFC 8785 representation signed with Ed25519; verified field-by-field.
6. **Replay Protection**: Stateful SQLite nonce table prevents receipt replay attacks.
7. **Tamper-Evident Audit Ledger**: Append-only SQLite hash-chained ledger protected by database triggers and Ed25519 signatures.
8. **Data Integrity & Contributor Scoring**: Identifies label inconsistencies via k-NN consensus, near-duplicates via dHash (MAE < 0.012), and OOD geometry, aggregating risks per contributor.
9. **Heuristic Distribution Shift**: Compares brightness, contrast, blur metric, color histogram, and feature distance.
10. **Evidence-Backed Assurance Reports**: Standalone JSON and printable HTML audit reports.

---

## Quick Start (Exact Run Commands)

### Option A: Local Development (Offline Native)

#### 1. Setup Backend (Python 3.11+)
```bash
# Navigate to repository root
cd D:\SIH\228

# Install dependencies
python -m pip install -r backend/requirements.txt

# Generate demo datasets and ONNX models locally (zero downloads)
python backend/scripts/make_demo_data.py
python backend/scripts/make_models.py

# Start FastAPI backend on port 8000
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

#### 2. Setup Frontend (Vite + React)
```bash
# In a separate terminal
cd D:\SIH\228\frontend

# Install dependencies and start Vite dev server
npm install
npm run dev -- --port 5173
```
Open your browser at **http://localhost:5173**.

---

### Option B: Docker Compose (Non-Root, Production)

The entire application builds and runs in isolated, non-root containers with zero internet downloads:
```bash
docker compose up --build
```
* **Frontend**: `http://localhost:8080`
* **Backend API**: `http://localhost:8000/api/health`

---

## Automated Test Suite

Run the complete 22-test unit and integration test suite:
```bash
python -m pytest backend/tests -v
```

All 22 tests pass:
* `test_valid_inference_receipt`
* `test_input_tamper_detection`
* `test_model_tamper_detection`
* `test_output_tamper_detection`
* `test_config_tamper_detection`
* `test_replay_detection`
* `test_ledger_append_and_verify_clean`
* `test_ledger_tamper_detection`
* `test_trusted_model_integrity`
* `test_substituted_model_fingerprint_mismatch`
* `test_backdoored_model_trigger_probe`
* `test_clean_dataset_analysis`
* `test_poisoned_dataset_findings_and_contributor_risk`
* `test_distribution_shift_no_shift`
* `test_distribution_shift_extreme_drift`
* `test_report_generation`
* Full FastAPI endpoint integration tests (`/health`, `/infer`, `/verify`, `/demo/tamper`, `/ledger/blocks`, `/ledger/verify`, `/demo/reset`)

---

## 4-Page User Interface

1. **Dashboard (`/`)**:
   * High-level assurance status banner: `TRUSTED` / `REVIEW` / `COMPROMISED`.
   * Real-time metrics: Chained blocks, model status, flagged samples, contributor risk summary.
2. **Integrity Analysis (`/integrity`)**:
   * Inspect clean, poisoned (Mallory), and trigger-patched (Sybil) contributor batches.
   * Review flagged samples, near-duplicate clusters, and OOD items.
   * Model integrity suite: digest match, 20-image behavioral fingerprint, and backdoor trigger probe results.
3. **Inference + Verify (`/inference`)**:
   * Run trusted inference on geometric shapes (circle, square, triangle) or custom uploads.
   * Inspect Ed25519 canonical receipt with cryptographic parameters.
   * **Tamper Simulation Sandbox**: Test deterministic attacks (Tamper Input, Replace Model, Alter Output, Replay Receipt) and observe field-by-field verification failures.
4. **Audit + Report (`/audit`)**:
   * Browse sequential blocks of the Tamper-Evident Audit Ledger.
   * **Verify Chain**: Cryptographically re-evaluates the entire ledger.
   * **Tamper Ledger**: Simulates direct SQLite modification to prove chain break detection.
   * **Printable Report**: View structured JSON or open standalone printable HTML assurance report.

---

## Documentation

* [Architecture & Engineering Design](docs/ARCHITECTURE.md)
* [Coverage & Assurance Statement](docs/COVERAGE.md)
* [Threat Model & Countermeasures](docs/THREAT_MODEL.md)
* [System Assumptions](docs/ASSUMPTIONS.md)
