from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class BaseSchema(BaseModel):
    model_config = {"protected_namespaces": ()}

class InferenceOutput(BaseSchema):
    class_id: int
    class_name: str
    confidence: float
    probabilities: List[float]

class CanonicalReceipt(BaseSchema):
    receipt_id: str
    input_sha256: str
    model_sha256: str
    config_sha256: str
    output_sha256: str
    timestamp: str
    nonce: str
    previous_receipt_hash: str
    signature: str
    public_key: str

class InferenceResponse(BaseSchema):
    output: InferenceOutput
    receipt: CanonicalReceipt
    config: Dict[str, Any]
    model_name: str

class VerifyFieldResult(BaseSchema):
    status: str  # "PASS" or "FAIL"
    expected: str
    observed: str

class VerifyResponse(BaseSchema):
    overall_status: str  # "PASS" or "FAIL"
    fields: Dict[str, VerifyFieldResult]
    message: str

class VerifyRequest(BaseSchema):
    image_b64: Optional[str] = None
    model_name: Optional[str] = "trusted"
    model_sha256: Optional[str] = None
    config: Dict[str, Any]
    output: Dict[str, Any]
    receipt: CanonicalReceipt

class TamperDemoRequest(BaseSchema):
    tamper_type: str  # "input", "model", "output", "config", "replay", "ledger"
    receipt_id: Optional[str] = None

class LedgerBlockSchema(BaseSchema):
    block_index: int
    timestamp: str
    prev_hash: str
    event_type: str
    payload_hash: str
    signature: str
    hash: str

class LedgerVerifyResponse(BaseSchema):
    valid: bool
    first_bad_block: Optional[int] = None
    total_blocks: int
    reason: Optional[str] = None

class FindingSchema(BaseSchema):
    id: str
    contributor_id: str
    asset: str
    reason: str
    evidence: Dict[str, Any]
    severity: str
    confidence: float
    recommended_disposition: str
    created_at: str

class ContributorRiskSchema(BaseSchema):
    contributor_id: str
    total_samples: int
    flag_rate: float
    duplicate_rate: float
    OOD_rate: float
    risk_score: float

class ShiftAnalysisResponse(BaseSchema):
    shift_score: float
    confidence: float
    heuristic_confidence_score: Optional[float] = None
    confidence_label: Optional[str] = "Heuristic Confidence / Assurance Score"
    changed_factors: List[str]
    classification: str  # "probable operational drift" | "suspicious" | "no material shift"
    metrics: Dict[str, Any]
    disclaimer: Optional[str] = None

class TriggerProbeResult(BaseSchema):
    probed_patches: int
    clean_baseline_acc: float
    highest_flip_rate: float
    target_class_affinity: Optional[str]
    verdict: str
    tested_patch_family: str

class ModelAnalysisResponse(BaseSchema):
    model_id: str
    sha256: str
    digest_status: str
    fingerprint_mismatches: int
    fingerprint_total: int
    trigger_probe: Dict[str, Any]
    status: str
    notes: List[str]

class HealthResponse(BaseSchema):
    status: str
    version: str
    offline_mode: bool
    models_ready: bool
    ledger_intact: bool
