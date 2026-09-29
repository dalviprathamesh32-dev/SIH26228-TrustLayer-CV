import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from app.core.config import DB_PATH, GENESIS_HASH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db_session() as conn:
        cursor = conn.cursor()

        # Nonce replay prevention table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipt_nonces (
                nonce TEXT PRIMARY KEY,
                receipt_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ISSUED',
                verification_count INTEGER DEFAULT 0
            );
        """)

        # Ensure schema migration for existing sqlite db instances
        cursor.execute("PRAGMA table_info(receipt_nonces)")
        existing_cols = [row["name"] for row in cursor.fetchall()]
        if "status" not in existing_cols:
            cursor.execute("ALTER TABLE receipt_nonces ADD COLUMN status TEXT NOT NULL DEFAULT 'ISSUED'")
        if "verification_count" not in existing_cols:
            cursor.execute("ALTER TABLE receipt_nonces ADD COLUMN verification_count INTEGER DEFAULT 0")

        # Tamper-Evident Audit Ledger Blocks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ledger_blocks (
                block_index INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                signature TEXT NOT NULL,
                hash TEXT NOT NULL
            );
        """)

        # Triggers to enforce append-only ledger
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_ledger_update
            BEFORE UPDATE ON ledger_blocks
            BEGIN
                SELECT RAISE(ABORT, 'Ledger blocks are append-only. Modification prohibited.');
            END;
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_ledger_delete
            BEFORE DELETE ON ledger_blocks
            BEGIN
                SELECT RAISE(ABORT, 'Ledger blocks cannot be deleted. Deletion prohibited.');
            END;
        """)

        # Registered Models Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models_registry (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                model_sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                analysis TEXT NOT NULL
            );
        """)

        # Datasets Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                summary TEXT NOT NULL
            );
        """)

        # Findings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                contributor_id TEXT NOT NULL,
                asset TEXT NOT NULL,
                reason TEXT NOT NULL,
                evidence TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence REAL NOT NULL,
                recommended_disposition TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        # Genesis block for ledger if empty
        cursor.execute("SELECT COUNT(*) FROM ledger_blocks")
        count = cursor.fetchone()[0]
        if count == 0:
            from app.core.crypto import sha256_canonical, sign_canonical_payload
            import datetime
            genesis_payload = {
                "block_index": 0,
                "timestamp": "2026-01-01T00:00:00Z",
                "prev_hash": GENESIS_HASH,
                "event_type": "GENESIS",
                "payload_hash": GENESIS_HASH
            }
            sig = sign_canonical_payload(genesis_payload)
            full_block_data = {**genesis_payload, "signature": sig}
            block_hash = sha256_canonical(full_block_data)
            cursor.execute("""
                INSERT INTO ledger_blocks (block_index, timestamp, prev_hash, event_type, payload_hash, signature, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (0, genesis_payload["timestamp"], GENESIS_HASH, "GENESIS", GENESIS_HASH, sig, block_hash))

def reset_db():
    """Drops tables and re-initializes clean demo state."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TRIGGER IF EXISTS prevent_ledger_update")
        cursor.execute("DROP TRIGGER IF EXISTS prevent_ledger_delete")
        cursor.execute("DROP TABLE IF EXISTS ledger_blocks")
        cursor.execute("DROP TABLE IF EXISTS receipt_nonces")
        cursor.execute("DROP TABLE IF EXISTS models_registry")
        cursor.execute("DROP TABLE IF EXISTS datasets")
        cursor.execute("DROP TABLE IF EXISTS findings")
    init_db()
