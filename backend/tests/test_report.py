import pytest
from app.services.report_gen import ReportGenerator
from app.db.database import init_db

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_report_generation():
    data = ReportGenerator.generate_full_report_data()
    assert "report_id" in data
    assert "summary" in data
    assert "coverage_statement" in data
    assert "supported" in data["coverage_statement"]
    assert "not_claimed" in data["coverage_statement"]

    # Test HTML rendering
    html = ReportGenerator.generate_html_report(data)
    assert "<!DOCTYPE html>" in html
    assert "TrustLayer-CV" in html
    assert "Tamper-Evident Audit Ledger" in html
