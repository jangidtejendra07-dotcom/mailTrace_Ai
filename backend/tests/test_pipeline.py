"""
Automated versions of the 5 MVP Acceptance Tests from the spec (Section 15).

Run:  cd backend && pytest -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.pipeline import run_pipeline

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "samples", "eml")


def _load(filename):
    with open(os.path.join(SAMPLES_DIR, filename), "rb") as f:
        return f.read()


def test_01_safe_email_allows():
    result = run_pipeline(_load("01_safe_email.eml"), resolve_network=False)
    assert result["decision"] == "ALLOW", result["explanation"]
    assert result["risk_score"] < 40


def test_02_phishing_url_flagged():
    result = run_pipeline(_load("02_phishing_url.eml"), resolve_network=False)
    assert result["decision"] in ("QUARANTINE", "BLOCK"), result["explanation"]
    assert result["risk_score"] >= 40


def test_03_malicious_attachment_blocks():
    result = run_pipeline(_load("03_malicious_attachment.eml"), resolve_network=False)
    assert result["decision"] == "BLOCK", result["explanation"]
    assert any(a["severity"] == "CRITICAL" for a in result["attachments"])


def test_04_bec_impersonation_flagged():
    result = run_pipeline(_load("04_bec_executive_impersonation.eml"), resolve_network=False)
    assert result["decision"] in ("QUARANTINE", "BLOCK"), result["explanation"]
    assert result["ai"]["category"] in ("bec", "phishing")


def test_05_blocked_message_has_case_and_evidence():
    result = run_pipeline(_load("03_malicious_attachment.eml"), resolve_network=False)
    assert result["decision"] == "BLOCK"
    assert result["case_id"].startswith("MT-")
    assert len(result["evidence_hash"]) == 64  # sha256 hex length
    assert result["_internal"]["evidence_package"] is not None
