# TrustLayer-CV: System Assumptions & Operational Context

## Core Assumptions

1. **Air-Gapped & Offline Execution**:
   * The platform operates completely offline with zero external internet dependencies or CDN requests.
   * Model artifacts, synthetic datasets, and cryptographic keys are generated locally.

2. **Isolated Secrets Storage**:
   * The host operating environment or container secures the `./data/secrets/` directory.
   * Attackers do not have root-level memory dump or physical extraction access to the private Ed25519 signing key.

3. **Deterministic Canonicalization**:
   * Verification engines on client and server agree on RFC 8785 JSON canonicalization rules (sorted keys, consistent float precision, UTF-8 encoding).

4. **Reference Baseline Availability**:
   * A certified clean baseline dataset exists to seed the initial k-NN neighborhood consensus and model behavioral fingerprint suite.

5. **Tamper-Evident Ledger Definition**:
   * The SQLite audit ledger is tamper-*evident* via cryptographic hash chaining and digital signatures. It is not an immutable proof-of-work blockchain, but any tampering by database administrators or intruders is mathematically detectable.
