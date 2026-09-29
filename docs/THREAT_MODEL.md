# TrustLayer-CV: Threat Model

## Threat Vectors & Countermeasures

| Threat Scenario | Attacker Objective | System Countermeasure | Detection Outcome |
| :--- | :--- | :--- | :--- |
| **Input Tampering** | Alter an inference image post-receipt signing (e.g. flipping pixels or perturbing bounding box). | Recomputing SHA-256 of candidate input image bytes during verification. | `INPUT_HASH` mismatch -> Verification `FAIL`. |
| **Model Substitution** | Replace the certified production model with a compromised, backdoored, or different binary. | Binary SHA-256 digest comparison against trusted registry baseline + 20-image behavioral fingerprinting. | `MODEL_HASH` mismatch & fingerprint discrepancy -> Verification `FAIL`. |
| **Output Manipulation** | Tamper with classification predictions or probabilities in the API response payload. | Deterministic Canonical JSON (RFC 8785 Principles) hashing and Ed25519 signature verification. | `OUTPUT_HASH` mismatch & `SIGNATURE` invalid -> Verification `FAIL`. |
| **Configuration Tampering**| Modify runtime thresholds, model architecture parameters, or versions. | Configuration dictionary hashed into canonical receipt payload. | `CONFIG_HASH` mismatch -> Verification `FAIL`. |
| **Receipt Replay Attack** | Resubmit an existing valid signed receipt to authorize an unapproved inference. | Stateful SQLite `receipt_nonces` table tracks used nonces. Duplicate presentation detected. | `NONCE: REPLAY_DETECTED` -> Verification `FAIL`. |
| **Audit Ledger Tampering** | Directly modify historical database rows in SQLite to alter audit records. | Sequential SHA-256 hash chaining + Ed25519 block signatures. | `GET /api/ledger/verify` reports `valid: false` and isolates `first_bad_block`. |
| **Data Poisoning** | Contributor injects mislabeled shapes or near-duplicate assets into training batches. | Feature extraction + k-NN neighborhood consensus + perceptual dHash + contributor risk scoring. | Inconsistencies flagged; Contributor marked `SUSPECT / UNTRUSTED`. |
| **Backdoor Trigger Injection** | Trojan injected that flips class predictions when a trigger patch is present. | Tested-family trigger probe across 4 corners and 3 deterministic patterns on 50 clean probe samples. | High flip rate detected; Model marked `COMPROMISED`. |
