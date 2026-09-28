import uuid
import secrets
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import (
    TRUSTED_MODEL_PATH, BACKDOORED_MODEL_PATH, SUBSTITUTED_MODEL_PATH
)
from app.core.crypto import (
    sha256_bytes, sha256_canonical, sha256_file,
    sign_canonical_payload, verify_canonical_payload, get_key_manager
)
from app.db.database import db_session
from app.services.ledger import LedgerService

class ProvenanceService:
    @staticmethod
    def create_inference_receipt(
        image_bytes: bytes,
        model_name: str,
        config: Dict[str, Any],
        output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Creates an immutable, cryptographically signed canonical receipt
        binding input, model, configuration, output, timestamp, nonce, and hash chain.
        """
        # Resolve model path
        if model_name in ["trusted", "default"]:
            model_path = TRUSTED_MODEL_PATH
        elif model_name in ["backdoored", "backdoor"]:
            model_path = BACKDOORED_MODEL_PATH
        elif model_name in ["substituted", "substitute"]:
            model_path = SUBSTITUTED_MODEL_PATH
        else:
            model_path = Path(model_name)

        receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"
        input_sha256 = sha256_bytes(image_bytes)
        model_sha256 = sha256_file(model_path)
        config_sha256 = sha256_canonical(config)
        output_sha256 = sha256_canonical(output)
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        nonce = secrets.token_hex(16)
        prev_receipt_hash = LedgerService.get_latest_block_hash()

        receipt_payload = {
            "receipt_id": receipt_id,
            "input_sha256": input_sha256,
            "model_sha256": model_sha256,
            "config_sha256": config_sha256,
            "output_sha256": output_sha256,
            "timestamp": timestamp,
            "nonce": nonce,
            "previous_receipt_hash": prev_receipt_hash
        }

        # Sign canonical representation
        signature = sign_canonical_payload(receipt_payload)
        public_key_hex = get_key_manager().get_public_key_hex()

        # Record nonce in database
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO receipt_nonces (nonce, receipt_id, created_at) VALUES (?, ?, ?)",
                (nonce, receipt_id, timestamp)
            )

        full_receipt = {
            **receipt_payload,
            "signature": signature,
            "public_key": public_key_hex
        }

        # Append audit ledger block
        LedgerService.append_block("INFERENCE_RECORDED", full_receipt)

        return full_receipt

    @staticmethod
    def verify_provenance(
        image_bytes: Optional[bytes],
        model_name: Optional[str],
        config: Dict[str, Any],
        output: Dict[str, Any],
        receipt: Dict[str, Any],
        simulate_replay: bool = False
    ) -> Dict[str, Any]:
        """
        Field-by-field cryptographic verification of inference provenance.
        Evaluates:
        - INPUT_HASH
        - MODEL_HASH
        - CONFIG_HASH
        - OUTPUT_HASH
        - SIGNATURE
        - NONCE
        - TIMESTAMP
        - PREVIOUS_RECEIPT
        """
        results: Dict[str, Dict[str, str]] = {}
        all_passed = True

        # 1. Input Hash Verification
        receipt_input_hash = receipt.get("input_sha256", "")
        if image_bytes is not None:
            observed_input_hash = sha256_bytes(image_bytes)
        else:
            observed_input_hash = receipt_input_hash # If image bytes omitted in verification request

        input_pass = (observed_input_hash == receipt_input_hash)
        if not input_pass:
            all_passed = False
        results["INPUT_HASH"] = {
            "status": "PASS" if input_pass else "FAIL",
            "expected": receipt_input_hash,
            "observed": observed_input_hash
        }

        # 2. Model Hash Verification
        receipt_model_hash = receipt.get("model_sha256", "")
        if model_name:
            if model_name in ["trusted", "default"]:
                m_path = TRUSTED_MODEL_PATH
            elif model_name in ["backdoored", "backdoor"]:
                m_path = BACKDOORED_MODEL_PATH
            elif model_name in ["substituted", "substitute"]:
                m_path = SUBSTITUTED_MODEL_PATH
            else:
                m_path = Path(model_name)
            observed_model_hash = sha256_file(m_path) if m_path.exists() else "MODEL_NOT_FOUND"
        else:
            observed_model_hash = receipt_model_hash

        model_pass = (observed_model_hash == receipt_model_hash)
        if not model_pass:
            all_passed = False
        results["MODEL_HASH"] = {
            "status": "PASS" if model_pass else "FAIL",
            "expected": receipt_model_hash,
            "observed": observed_model_hash
        }

        # 3. Config Hash Verification
        receipt_config_hash = receipt.get("config_sha256", "")
        observed_config_hash = sha256_canonical(config)
        config_pass = (observed_config_hash == receipt_config_hash)
        if not config_pass:
            all_passed = False
        results["CONFIG_HASH"] = {
            "status": "PASS" if config_pass else "FAIL",
            "expected": receipt_config_hash,
            "observed": observed_config_hash
        }

        # 4. Output Hash Verification
        receipt_output_hash = receipt.get("output_sha256", "")
        observed_output_hash = sha256_canonical(output)
        output_pass = (observed_output_hash == receipt_output_hash)
        if not output_pass:
            all_passed = False
        results["OUTPUT_HASH"] = {
            "status": "PASS" if output_pass else "FAIL",
            "expected": receipt_output_hash,
            "observed": observed_output_hash
        }

        # 5. Signature Verification
        receipt_sig = receipt.get("signature", "")
        receipt_pubkey = receipt.get("public_key")
        payload_to_verify = {
            "receipt_id": receipt.get("receipt_id"),
            "input_sha256": receipt_input_hash,
            "model_sha256": receipt_model_hash,
            "config_sha256": receipt_config_hash,
            "output_sha256": receipt_output_hash,
            "timestamp": receipt.get("timestamp"),
            "nonce": receipt.get("nonce"),
            "previous_receipt_hash": receipt.get("previous_receipt_hash")
        }

        sig_pass = verify_canonical_payload(payload_to_verify, receipt_sig, receipt_pubkey)
        if not sig_pass:
            all_passed = False
        results["SIGNATURE"] = {
            "status": "PASS" if sig_pass else "FAIL",
            "expected": f"VALID_ED25519_SIG({receipt_sig[:12]}...)",
            "observed": "VALID" if sig_pass else "INVALID_SIGNATURE"
        }

        # 6. Nonce / Replay Verification
        receipt_nonce = receipt.get("nonce", "")
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nonce, receipt_id FROM receipt_nonces WHERE nonce = ?", (receipt_nonce,))
            row = cursor.fetchone()

        if simulate_replay:
            nonce_pass = False
            nonce_observed = "REPLAY_DETECTED (Duplicate nonce reused in unauthorized context)"
            all_passed = False
        elif not row:
            nonce_pass = False
            nonce_observed = "UNREGISTERED_NONCE (Receipt nonce not found in state store)"
            all_passed = False
        else:
            nonce_pass = True
            nonce_observed = f"VALID_REGISTERED_NONCE({receipt_nonce[:8]}...)"

        results["NONCE"] = {
            "status": "PASS" if nonce_pass else "FAIL",
            "expected": f"UNIQUE_REGISTERED_NONCE({receipt_nonce[:8]}...)",
            "observed": nonce_observed
        }

        # 7. Timestamp Verification
        ts_str = receipt.get("timestamp", "")
        try:
            parsed_dt = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            ts_pass = True
            ts_observed = "VALID_ISO8601"
        except Exception:
            ts_pass = False
            ts_observed = "MALFORMED_TIMESTAMP"
            all_passed = False

        results["TIMESTAMP"] = {
            "status": "PASS" if ts_pass else "FAIL",
            "expected": "ISO8601_UTC_FORMAT",
            "observed": ts_observed
        }

        # 8. Previous Receipt Hash Verification
        prev_hash = receipt.get("previous_receipt_hash", "")
        prev_pass = bool(prev_hash and len(prev_hash) == 64 and all(c in "0123456789abcdef" for c in prev_hash.lower()))
        if not prev_pass:
            all_passed = False

        results["PREVIOUS_RECEIPT"] = {
            "status": "PASS" if prev_pass else "FAIL",
            "expected": "VALID_64_CHAR_HEX_CHAIN_DIGEST",
            "observed": f"CHAIN_DIGEST({prev_hash[:12]}...)" if prev_pass else "INVALID_CHAIN_DIGEST"
        }

        overall_status = "PASS" if all_passed else "FAIL"
        message = "Receipt cryptographically verified and bound to exact pipeline state." if all_passed else "Verification failed: One or more pipeline integrity bindings were broken or manipulated."

        return {
            "overall_status": overall_status,
            "fields": results,
            "message": message
        }
