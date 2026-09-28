import datetime
import json
from typing import Dict, Any, List, Optional
from app.db.database import db_session, get_connection
from app.core.config import GENESIS_HASH
from app.core.crypto import sha256_canonical, sign_canonical_payload, verify_canonical_payload, get_key_manager

class LedgerService:
    @staticmethod
    def get_latest_block_hash() -> str:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT hash FROM ledger_blocks ORDER BY block_index DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return row["hash"]
            return GENESIS_HASH

    @staticmethod
    def append_block(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Appends a new block to the tamper-evident audit ledger."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT block_index, hash FROM ledger_blocks ORDER BY block_index DESC LIMIT 1")
            last_row = cursor.fetchone()
            
            if last_row:
                new_index = last_row["block_index"] + 1
                prev_hash = last_row["hash"]
            else:
                new_index = 0
                prev_hash = GENESIS_HASH

            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            payload_hash = sha256_canonical(payload)

            block_payload = {
                "block_index": new_index,
                "timestamp": now_iso,
                "prev_hash": prev_hash,
                "event_type": event_type,
                "payload_hash": payload_hash
            }

            sig = sign_canonical_payload(block_payload)
            full_block = {**block_payload, "signature": sig}
            block_hash = sha256_canonical(full_block)

            cursor.execute("""
                INSERT INTO ledger_blocks (block_index, timestamp, prev_hash, event_type, payload_hash, signature, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_index, now_iso, prev_hash, event_type, payload_hash, sig, block_hash))

            return {
                "block_index": new_index,
                "timestamp": now_iso,
                "prev_hash": prev_hash,
                "event_type": event_type,
                "payload_hash": payload_hash,
                "signature": sig,
                "hash": block_hash
            }

    @staticmethod
    def get_blocks(limit: int = 100) -> List[Dict[str, Any]]:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ledger_blocks ORDER BY block_index ASC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def verify_ledger() -> Dict[str, Any]:
        """
        Recomputes every hash and verifies cryptographic signatures sequentially.
        Reports exact first compromised block and reason.
        """
        blocks = LedgerService.get_blocks(limit=10000)
        if not blocks:
            return {"valid": True, "first_bad_block": None, "total_blocks": 0, "reason": "Ledger is empty"}

        expected_prev_hash = GENESIS_HASH

        for i, blk in enumerate(blocks):
            # 1. Verify prev_hash link
            if i == 0:
                if blk["prev_hash"] != GENESIS_HASH:
                    return {
                        "valid": False,
                        "first_bad_block": blk["block_index"],
                        "total_blocks": len(blocks),
                        "reason": f"Genesis block prev_hash invalid. Expected {GENESIS_HASH}, got {blk['prev_hash']}"
                    }
            else:
                if blk["prev_hash"] != expected_prev_hash:
                    return {
                        "valid": False,
                        "first_bad_block": blk["block_index"],
                        "total_blocks": len(blocks),
                        "reason": f"Hash chain break at block {blk['block_index']}: prev_hash mismatch. Expected {expected_prev_hash}, got {blk['prev_hash']}"
                    }

            # 2. Verify signature
            block_payload = {
                "block_index": blk["block_index"],
                "timestamp": blk["timestamp"],
                "prev_hash": blk["prev_hash"],
                "event_type": blk["event_type"],
                "payload_hash": blk["payload_hash"]
            }

            sig_ok = verify_canonical_payload(block_payload, blk["signature"])
            if not sig_ok:
                return {
                    "valid": False,
                    "first_bad_block": blk["block_index"],
                    "total_blocks": len(blocks),
                    "reason": f"Cryptographic signature invalid on block {blk['block_index']}. Block payload altered."
                }

            # 3. Verify block hash
            full_block_data = {**block_payload, "signature": blk["signature"]}
            computed_hash = sha256_canonical(full_block_data)
            if computed_hash != blk["hash"]:
                return {
                    "valid": False,
                    "first_bad_block": blk["block_index"],
                    "total_blocks": len(blocks),
                    "reason": f"Hash mismatch on block {blk['block_index']}. Computed {computed_hash}, recorded {blk['hash']}"
                }

            expected_prev_hash = blk["hash"]

        return {
            "valid": True,
            "first_bad_block": None,
            "total_blocks": len(blocks),
            "reason": "All blocks cryptographically verified. Hash chain is unbroken."
        }

    @staticmethod
    def simulate_tamper(target_block_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Simulates an attacker tampering with an existing ledger block in SQLite.
        Bypasses the append-only trigger by dropping it, mutating the record, and restoring it.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            if target_block_index is None:
                cursor.execute("SELECT block_index FROM ledger_blocks WHERE block_index > 0 ORDER BY block_index DESC LIMIT 1")
                row = cursor.fetchone()
                target_block_index = row["block_index"] if row else 0

            # Temporarily drop trigger to allow direct malicious update
            cursor.execute("DROP TRIGGER IF EXISTS prevent_ledger_update")

            # Maliciously mutate the payload_hash to simulate illicit tampering
            cursor.execute("""
                UPDATE ledger_blocks
                SET payload_hash = 'baddeadbeef00000000000000000000000000000000000000000000000000000'
                WHERE block_index = ?
            """, (target_block_index,))

            # Re-enable trigger
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_ledger_update
                BEFORE UPDATE ON ledger_blocks
                BEGIN
                    SELECT RAISE(ABORT, 'Ledger blocks are append-only. Modification prohibited.');
                END;
            """)

            return {
                "tampered_block": target_block_index,
                "message": f"Block {target_block_index} payload_hash was maliciously altered. Hash chain and signature are now invalid."
            }
