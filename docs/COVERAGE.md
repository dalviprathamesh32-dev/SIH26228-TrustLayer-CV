# TrustLayer-CV: Security & Assurance Coverage Statement

Problem Statement: **SIH26228** — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines.

---

## 1. Supported Capabilities (Guaranteed Detection)

The TrustLayer-CV architecture provides deterministic cryptographic and statistical assurance for the following integrity guarantees:

* **Input Image Tampering Detection**:
  * SHA-256 byte digest computation over raw pixel arrays at ingestion/inference.
  * Any modification to image data post-receipt signing is detected during verification (`INPUT_HASH` mismatch).

* **Model Substitution Detection by Digest**:
  * SHA-256 digest comparison against the registered trusted baseline (`trusted_model.onnx`).
  * Instant rejection upon binary substitution (`MODEL_HASH` mismatch).

* **Behavioural Mismatch Fingerprinting**:
  * Fixed reference evaluation suite consisting of 20 canonical geometric shapes.
  * Quantifies prediction discrepancies when evaluating black-box replacement models.

* **Inference Output Tampering Detection**:
  * Deterministic RFC 8785 canonical JSON serialization of prediction outputs (`class_id`, `class_name`, `confidence`, `probabilities`).
  * Any post-hoc mutation of labels or probabilities invalidates `OUTPUT_HASH`.

* **Configuration Tampering Detection**:
  * Runtime hyperparameters, input geometry shapes, and model versions are bound to the signed receipt via `CONFIG_HASH`.

* **Replay Detection**:
  * Stateful nonce registry (`receipt_nonces` table in SQLite) stores every issued nonce.
  * Duplicate or unauthorized reuse of expired receipts is flagged with `REPLAY_DETECTED`.

* **Tamper-Evident Audit Ledger**:
  * Sequential cryptographic hash-chaining of pipeline events (`GENESIS -> ... -> block[N]`).
  * Ed25519 digital signatures on every block payload.
  * Any unauthorized modification of database records breaks the cryptographic hash chain and invalidates block signatures.

* **Basic Label Inconsistency Detection**:
  * Cosine-space feature extraction with k-NN (k=5) neighborhood consensus.
  * Flags assets where contributor declared label conflicts with neighborhood majority vote.

* **Near-Duplicate Detection**:
  * 64-bit difference hash (dHash) combined with pixel mean absolute error (MAE < 0.012).
  * Pinpoints duplicate or subtly perturbed images submitted across contributors.

* **Basic Out-of-Distribution (OOD) Detection**:
  * Feature distance measurement against the 95th percentile baseline manifold radius.
  * Identifies anomalous geometry and visual noise.

* **Basic Distribution Shift Detection**:
  * Heuristic statistical tracking comparing incoming batches to reference baseline across brightness, contrast, blur metric, 24-bin color histogram, and feature centroid distance.

* **Tested-Family Trigger Probe**:
  * Bounded probe across 4 image corners (`top-left`, `top-right`, `bottom-left`, `bottom-right`) and 3 deterministic small patch patterns (`checkerboard`, `solid_square`, `diagonal_cross`) over 50 clean probe images.
  * Detects targeted classification flip vulnerabilities for tested patch patterns.

---

## 2. Limited Scope & Boundary Conditions

* **Systematic Mislabelling**:
  * If a large majority of contributors coordinate to mislabel a class, unsupervised k-NN consensus without sufficient certified gold-standard data will be degraded.

* **Sophisticated Poisoning**:
  * Poisoning attacks designed with gradient-matching or clean-label triggers that closely mirror the true data manifold may pass heuristic OOD thresholds.

* **Blended / Spectral Triggers**:
  * Trigger patterns outside the tested 4-corner, 3-pattern family (such as imperceptible watermarks or full-image frequency-domain phase shifts) are not probed by the bounded trigger suite.

* **Advanced Adversarial Perturbations**:
  * White-box gradient-based adversarial perturbations (e.g. FGSM / PGD with $\ell_\infty \le 2/255$) beneath perceptual duplicate distance will be classified as new images.

---

## 3. Explicitly Not Claimed

* **Universal Backdoor Detection**:
  * We do not claim detection of arbitrary unseen backdoor mechanisms or trojans injected into black-box neural networks.

* **Universal Poisoning Detection**:
  * We do not claim universal mathematical separation of subtle poisoning from genuine edge-case operational variance.

* **Adaptive Attackers with Compromised Signing Keys**:
  * If an attacker gains access to the air-gapped private Ed25519 signing key in `./data/secrets/`, they can forge valid receipts. Protection relies on host hardware key isolation.

* **Cryptographic Proof of Model Safety**:
  * Cryptographic signatures guarantee model *provenance* and *integrity* (that the model executed is exactly the certified binary registered). They do not mathematically prove that the model architecture is free of hallucinations or alignment errors.

* **Guaranteed Separation of Operational Drift from Malicious Manipulation**:
  * Distribution shift metrics provide statistical awareness of environment variance (e.g. lighting changes or lens blur). They cannot deterministically differentiate between natural environmental drift and deliberate subtle image degradation.
