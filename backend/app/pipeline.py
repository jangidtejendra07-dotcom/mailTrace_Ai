"""
Section 2 — Core Pipeline orchestrator.

    POST /api/v1/analyze-email
            |
            v
      Email Ingestion
            |
   +--------+---------------+
   v        v               v
  AI     FORENSICS      ATTACHMENT
  NLP   SPF/DKIM/DMARC    Scanner
        Header/Relay
   +--------+---------------+
            v
       RISK FUSION
            v
   ALLOW / QUARANTINE / BLOCK
            |
            v
  INTELLIGENCE -> CASE -> REPORT
"""
from app.utils.email_parser import parse_eml
from app.services import ai_engine, forensics, attachment_scanner, url_intel
from app.services import ip_geolocation, risk_fusion, case_manager


def run_pipeline(raw_bytes: bytes, resolve_network: bool = True) -> dict:
    parsed_email = parse_eml(raw_bytes)

    ai_result = ai_engine.analyze_intent(parsed_email["subject"], parsed_email["plain_body"] or parsed_email["html_body"])
    forensics_result = forensics.analyze_headers(parsed_email)
    attachment_result = attachment_scanner.scan_attachments(parsed_email["attachments"])
    url_result = url_intel.analyze_urls(parsed_email["urls"], resolve_network=resolve_network)

    candidate_ip = forensics_result.get("candidate_source_ip")
    geolocation = ip_geolocation.geolocate_ip(candidate_ip) if resolve_network else ip_geolocation.geolocate_ip(None)

    fusion_result = risk_fusion.fuse_risk(ai_result, forensics_result, url_result, attachment_result)

    case_id = case_manager.generate_case_id()
    correlation_graph = case_manager.build_correlation_graph(
        parsed_email, forensics_result, url_result, attachment_result, geolocation
    )

    evidence_package = None
    if fusion_result["decision"] in ("QUARANTINE", "BLOCK"):
        evidence_package = case_manager.build_evidence_package(
            case_id, parsed_email, ai_result, forensics_result, url_result,
            attachment_result, geolocation, fusion_result,
        )
        evidence_hash = evidence_package["sha256_evidence_hash"]
    else:
        evidence_hash = case_manager.compute_evidence_hash({"case_id": case_id, "decision": "ALLOW"})

    response = {
        "classification": fusion_result["classification"],
        "risk_score": fusion_result["final_risk_score"],
        "decision": fusion_result["decision"],
        "ai": ai_result,
        "authentication": {
            "spf": forensics_result["spf"],
            "dkim": forensics_result["dkim"],
            "dmarc": forensics_result["dmarc"],
        },
        "sender": {
            "from_address": parsed_email["from_address"],
            "from_domain": forensics_result["from_domain"],
            "reply_to_address": parsed_email["reply_to_address"] or None,
            "reply_to_mismatch": forensics_result["reply_to_mismatch"],
        },
        "forensics": forensics_result,
        "urls": url_result["items"],
        "attachments": attachment_result["items"],
        "ip_intelligence": geolocation,
        "geolocation": geolocation,
        "correlation_graph": correlation_graph,
        "case_id": case_id,
        "evidence_hash": evidence_hash,
        "explanation": fusion_result["explanation"],
        "subject": parsed_email["subject"],
        "_internal": {
            "parsed_email": parsed_email,
            "forensics_result": forensics_result,
            "url_result": url_result,
            "attachment_result": attachment_result,
            "fusion_result": fusion_result,
            "evidence_package": evidence_package,
        },
    }
    return response
