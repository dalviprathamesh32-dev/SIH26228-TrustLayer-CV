# TrustLayer-CV: Architecture & Engineering Design

## System Architecture Overview

TrustLayer-CV is an air-gapped, offline computer vision integrity and cryptographic provenance assurance system designed for multi-contributor ML pipelines (SIH PS SIH26228).

```
+-----------------------------------------------------------------------------------+
|                                  TrustLayer-CV                                    |
+-----------------------------------------------------------------------------------+
|  1. Ingestion & Preprocessing (64x64 geometric tensors)                          |
|       |                                                                           |
|       +--> SHA-256(Raw Image Bytes) = INPUT_HASH                                 |
|                                                                                   |
|  2. Certified Inference Engine (ONNX Runtime)                                     |
|       |                                                                           |
|       +--> Model Binary = SHA-256(trusted_model.onnx) = MODEL_HASH               |
|       +--> Softmax Output = SHA-256(Canonical JSON Output) = OUTPUT_HASH         |
|       +--> Hyperparams    = SHA-256(Canonical JSON Config) = CONFIG_HASH         |
|                                                                                   |
|  3. Cryptographic Binding & Receipt Issuance                                      |
|       |                                                                           |
|       +--> Nonce Table (SQLite replay protection)                                 |
|       +--> Previous Receipt Hash (Chained from latest Ledger Block)               |
|       +--> Ed25519 Private Key (Never exported via API)                           |
|       +--> Output: Canonical Signed Receipt                                       |
|                                                                                   |
|  4. Tamper-Evident Audit Ledger (SQLite)                                          |
|       |                                                                           |
|       +--> Block[N] = {Index, Timestamp, PrevHash, EventType, PayloadHash, Sig}   |
|       +--> Append-only SQLite triggers (blocks updates and deletes)               |
|                                                                                   |
|  5. Verification Engine                                                           |
|       |                                                                           |
|       +--> Field-by-Field: INPUT, MODEL, CONFIG, OUTPUT, SIG, NONCE, TS, CHAIN    |
|       +--> Outcome: PASS / FAIL with exact compromised field isolation            |
+-----------------------------------------------------------------------------------+
```

---

## Core Components

### 1. Deterministic Canonicalization (`canonical.py`)
To prevent cross-platform float divergence or JSON key ordering ambiguities between operating systems, dictionaries are normalized recursively using sorted keys, rounded floats (6 decimal places), and compact separators following Deterministic Canonical JSON (RFC 8785 Principles).

### 2. Ed25519 Asymmetric Signing (`crypto.py`)
* High-speed, tamper-resistant digital signatures based on Curve25519.
* Keys are generated once in `./data/secrets/`. The private key is strictly isolated and never returned over API endpoints.
* The pinned root public key in `./data/secrets/ed25519_public.key` serves as the immutable trust anchor for receipt verification.

### 3. Model Integrity & Behavioral Suite (`model_runner.py`)
* **Digest Check**: Direct SHA-256 comparison against registry baseline.
* **Behavioral Fingerprinting**: Evaluates candidate models over 20 canonical reference shapes. Any mismatch indicates permutation, retrained weights, or model substitution.
* **Trigger Probe**: Evaluates 12 deterministic combinations (4 image corners $\times$ 3 patch patterns) on 50 clean probe samples to detect backdoor triggers that hijack classification.

### 4. Data Integrity & Contributor Scoring (`data_integrity.py`)
* **Label Inconsistency**: Feature extraction combined with cosine-space k-NN (k=5) consensus.
* **Perceptual Duplicates**: 64-bit difference hashing (dHash) with tight pixel Mean Absolute Error (MAE < 0.012).
* **OOD Geometry**: Measures feature manifold distance from the 95th percentile distribution boundary.
* **Contributor Scoring**: Aggregates findings per `contributor_id` into a composite risk score (0-100).

### 5. Tamper-Evident Audit Ledger (`ledger.py`)
* Implemented in SQLite using append-only triggers (`prevent_ledger_update` and `prevent_ledger_delete`).
* Sequential blocks cryptographically chain the hash of block $i-1$ into block $i$.
* Verification sequentially validates both Ed25519 signatures and block hashes, immediately pinpointing any modified record.
