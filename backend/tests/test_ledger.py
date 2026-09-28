import pytest
from app.db.database import init_db, reset_db
from app.services.ledger import LedgerService

@pytest.fixture(autouse=True)
def setup_clean_db():
    reset_db()

def test_ledger_append_and_verify_clean():
    # Initial state has genesis block
    status = LedgerService.verify_ledger()
    assert status["valid"] is True
    assert status["first_bad_block"] is None
    assert status["total_blocks"] >= 1

    # Append valid blocks
    b1 = LedgerService.append_block("TEST_EVENT_1", {"key": "val1"})
    b2 = LedgerService.append_block("TEST_EVENT_2", {"key": "val2"})

    assert b1["block_index"] == 1
    assert b2["block_index"] == 2
    assert b2["prev_hash"] == b1["hash"]

    # Verify chain
    status2 = LedgerService.verify_ledger()
    assert status2["valid"] is True
    assert status2["total_blocks"] == 3

def test_ledger_tamper_detection():
    # Append blocks
    b1 = LedgerService.append_block("EVENT_A", {"data": 123})
    b2 = LedgerService.append_block("EVENT_B", {"data": 456})

    # Verify clean before tamper
    clean_status = LedgerService.verify_ledger()
    assert clean_status["valid"] is True

    # Simulate direct SQLite database mutation on block 1
    tamper_info = LedgerService.simulate_tamper(target_block_index=1)
    assert tamper_info["tampered_block"] == 1

    # Verification must now FAIL and pinpoint block 1
    tampered_status = LedgerService.verify_ledger()
    assert tampered_status["valid"] is False
    assert tampered_status["first_bad_block"] == 1
    assert "invalid" in tampered_status["reason"].lower() or "mismatch" in tampered_status["reason"].lower()
