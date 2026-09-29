import json
import datetime
from pathlib import Path
from typing import Dict, Any, List

from app.db.database import db_session
from app.services.ledger import LedgerService
from app.services.model_runner import ModelRunner
from app.services.data_integrity import DataIntegrityService
from app.core.config import TRUSTED_MODEL_PATH

class ReportGenerator:
    @staticmethod
    def generate_full_report_data() -> Dict[str, Any]:
        """Gathers all assurance evidence across all 6 core modules."""
        # 1. Ledger Status
        ledger_status = LedgerService.verify_ledger()
        latest_blocks = LedgerService.get_blocks(limit=10)

        # 2. Model Integrity
        model_integrity = ModelRunner.evaluate_model_integrity(TRUSTED_MODEL_PATH)

        # 3. Findings & Contributor Risks
        findings = DataIntegrityService.get_all_findings()
        
        # Aggregate contributor risks
        contributor_summary: Dict[str, Dict[str, Any]] = {}
        for f in findings:
            cid = f["contributor_id"]
            if cid not in contributor_summary:
                contributor_summary[cid] = {"total_findings": 0, "severities": {}}
            contributor_summary[cid]["total_findings"] += 1
            sev = f["severity"]
            contributor_summary[cid]["severities"][sev] = contributor_summary[cid]["severities"].get(sev, 0) + 1

        # High-level pipeline assurance state
        is_compromised = (
            not ledger_status["valid"] or
            model_integrity["status"] == "COMPROMISED" or
            any(f["severity"] == "CRITICAL" for f in findings)
        )
        is_review = (
            model_integrity["status"] == "REVIEW" or
            len(findings) > 0
        )

        pipeline_verdict = "COMPROMISED" if is_compromised else ("REVIEW" if is_review else "TRUSTED")

        report_data = {
            "report_id": f"REP-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "pipeline_verdict": pipeline_verdict,
            "summary": {
                "system_name": "TrustLayer-CV Integrity Assurance",
                "problem_statement": "SIH26228",
                "assurance_mode": "Deterministic Offline Cryptographic Assurance",
                "total_ledger_blocks": ledger_status["total_blocks"],
                "ledger_valid": ledger_status["valid"],
                "model_status": model_integrity["status"],
                "total_findings": len(findings),
                "monitored_contributors": len(contributor_summary)
            },
            "model_integrity": model_integrity,
            "findings": findings,
            "contributor_risks": contributor_summary,
            "ledger_status": {
                **ledger_status,
                "recent_blocks": latest_blocks
            },
            "coverage_statement": {
                "supported": [
                    "Input tampering via SHA-256 byte digest verification",
                    "Model substitution detection via SHA-256 digest vs trusted registry",
                    "Model behavioral fingerprint mismatch across fixed reference sets",
                    "Tested-family backdoor trigger probe (4 corners x 3 deterministic patterns)",
                    "Inference output tampering detection via canonical payload verification",
                    "Configuration parameter tampering detection",
                    "Receipt replay detection via stateful nonce tracking",
                    "Audit ledger tampering detection via cryptographic hash-chaining and Ed25519 signatures",
                    "Dataset label inconsistency detection via k-NN neighborhood consensus",
                    "Near-duplicate asset detection via perceptual difference hashing (dHash)",
                    "Basic Out-of-Distribution (OOD) geometry detection via manifold distance",
                    "Heuristic distribution shift detection across statistical moments"
                ],
                "limited": [
                    "Systematic mislabeling across majority of contributors",
                    "Sophisticated poisoning with blended or spectral triggers outside tested patch family",
                    "Advanced adversarial perturbation attacks beneath perceptual thresholds",
                    "High-dimensional non-linear manifold shift"
                ],
                "not_claimed": [
                    "Universal backdoor detection across arbitrary unseen architectures or patch families",
                    "Universal poisoning detection",
                    "Protection against adaptive physical attackers who compromise hardware private signing keys",
                    "Cryptographic mathematical proof that a deep neural network is intrinsically safe",
                    "Guaranteed absolute separation of operational environmental drift from malicious data manipulation"
                ]
            },
            "limitations": [
                "Backdoor probe evaluates a finite deterministic trigger patch family (4 corners, 3 patterns).",
                "Data integrity k-NN depends on sufficient representative clean baseline data.",
                "Distribution shift metrics are statistical heuristics designed for operational drift awareness, not universal intrusion prevention."
            ]
        }
        return report_data

    @classmethod
    def generate_html_report(cls, data: Dict[str, Any]) -> str:
        """Generates a clean, standalone, printable HTML document."""
        verdict = data["pipeline_verdict"]
        verdict_color = "#10b981" if verdict == "TRUSTED" else ("#f59e0b" if verdict == "REVIEW" else "#ef4444")

        findings_rows = ""
        for f in data["findings"][:15]:
            findings_rows += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #334155;">{f.get('id', '')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #334155;">{f.get('contributor_id', '')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #334155;">{f.get('asset', '')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #334155; font-weight: bold; color: {'#ef4444' if f.get('severity')=='HIGH' else '#f59e0b'};">{f.get('severity', '')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #334155;">{f.get('reason', '')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #334155;"><code>{f.get('recommended_disposition', '')}</code></td>
            </tr>
            """

        coverage_sup = "".join(f"<li>{s}</li>" for s in data["coverage_statement"]["supported"])
        coverage_not = "".join(f"<li>{s}</li>" for s in data["coverage_statement"]["not_claimed"])

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>TrustLayer-CV Assurance Report - {data['report_id']}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 30px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #1e293b;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            border: 1px solid #334155;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #334155;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 1.1rem;
            color: white;
            background-color: {verdict_color};
        }}
        h1, h2, h3 {{ color: #38bdf8; margin-top: 25px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 0.9rem;
            background: #0f172a;
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{
            background: #1e293b;
            color: #94a3b8;
            padding: 10px;
            text-align: left;
            border-bottom: 2px solid #334155;
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .card {{
            background: #0f172a;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #334155;
        }}
        .card-label {{ font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; }}
        .card-value {{ font-size: 1.3rem; font-weight: bold; color: #f8fafc; margin-top: 5px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 6px; color: #cbd5e1; }}
        .disclaimer-box {{
            background: rgba(245, 158, 11, 0.1);
            border-left: 4px solid #f59e0b;
            padding: 15px;
            margin-top: 30px;
            border-radius: 4px;
            font-size: 0.85rem;
            color: #fcd34d;
        }}
        @media print {{
            body {{ background: white; color: black; padding: 0; }}
            .container {{ box-shadow: none; border: none; padding: 20px; background: white; }}
            h1, h2, h3 {{ color: #0284c7; }}
            .card {{ background: #f8fafc; border: 1px solid #e2e8f0; }}
            .card-value {{ color: black; }}
            table {{ background: white; border: 1px solid #e2e8f0; }}
            th {{ background: #f1f5f9; color: black; }}
            td {{ border-bottom: 1px solid #e2e8f0; color: black; }}
            .disclaimer-box {{ background: #fef3c7; color: #92400e; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1 style="margin: 0; font-size: 1.8rem;">TrustLayer-CV Evidence Report</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.9rem;">
                PS: SIH26228 | Report ID: {data['report_id']} | Generated: {data['generated_at']}
            </p>
        </div>
        <div>
            <div class="badge">{verdict}</div>
        </div>
    </div>

    <div class="card-grid">
        <div class="card">
            <div class="card-label">Ledger Blocks</div>
            <div class="card-value">{data['summary']['total_ledger_blocks']} (Chain {'Intact' if data['summary']['ledger_valid'] else 'BROKEN'})</div>
        </div>
        <div class="card">
            <div class="card-label">Model Integrity</div>
            <div class="card-value">{data['summary']['model_status']}</div>
        </div>
        <div class="card">
            <div class="card-label">Integrity Findings</div>
            <div class="card-value">{data['summary']['total_findings']} Samples Flagged</div>
        </div>
    </div>

    <h2>1. Tamper-Evident Audit Ledger Status</h2>
    <p>
        Verification Status: <strong>{'PASSED' if data['ledger_status']['valid'] else 'FAILED'}</strong>.
        {data['ledger_status']['reason']}
    </p>

    <h2>2. Model Integrity & Behavioral Fingerprint</h2>
    <p>
        Model SHA-256: <code>{data['model_integrity']['sha256']}</code><br>
        Digest Status: <strong>{data['model_integrity']['digest_status']}</strong><br>
        Fingerprint Mismatches: <strong>{data['model_integrity']['fingerprint_mismatches']} / {data['model_integrity']['fingerprint_total']}</strong><br>
        Trigger Probe Verdict: <em>{data['model_integrity']['trigger_probe']['verdict']}</em>
    </p>

    <h2>3. Data Integrity & Contributor Findings</h2>
    <table>
        <thead>
            <tr>
                <th>Finding ID</th>
                <th>Contributor</th>
                <th>Asset</th>
                <th>Severity</th>
                <th>Reason</th>
                <th>Disposition</th>
            </tr>
        </thead>
        <tbody>
            {findings_rows if findings_rows else "<tr><td colspan='6' style='padding: 10px; text-align: center; color: #94a3b8;'>No anomalous findings detected. Baseline clean.</td></tr>"}
        </tbody>
    </table>

    <h2>4. Coverage Statement (Explicit Boundaries)</h2>
    <h3 style="color: #10b981; font-size: 1rem;">Supported Capabilities:</h3>
    <ul>{coverage_sup}</ul>

    <h3 style="color: #ef4444; font-size: 1rem;">Explicitly Not Claimed:</h3>
    <ul>{coverage_not}</ul>

    <div class="disclaimer-box">
        <strong>Assurance Disclaimer:</strong> This assurance report provides cryptographic non-repudiation and deterministic integrity verification for computer vision pipelines. It guarantees detection of unauthorized binary, image, and ledger mutations. Statistical probes (distribution shift and trigger probes) are bounded heuristics and do not constitute universal guarantees against unseen adversarial methods.
    </div>
</div>
</body>
</html>"""
        return html
