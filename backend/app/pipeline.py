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

Feature 1 note: AI and Forensics/Attachment now run CONCURRENTLY (see
risk_fusion.fuse_risk_with_pipeline -> fusion_pipeline.run), instead of
one after another. The decision is still only made once both finish —
this function's return shape is UNCHANGED from before.
"""
from app.utils.email_parser import parse_eml
from app.services import ip_geolocation, risk_fusion, case_manager


def run_pipeline(raw_bytes: bytes, resolve_network: bool = True) -> dict:
    parsed_email = parse_eml(raw_bytes)

    # Feature 1: case_id is now generated up-front (previously generated
    # after fusion) so the AI/Forensic stages can cache their intermediate
    # results in Redis under this case_id as they complete. generate_case_id()
    # has no dependency on any analysis result, so this reorder is safe.
    case_id = case_manager.generate_case_id()

    fusion_result = risk_fusion.fuse_risk_with_pipeline(
        case_id, parsed_email, resolve_network=resolve_network
    )

    ai_result = fusion_result["ai_result"]
    forensics_result = fusion_result["forensics_result"]
    url_result = fusion_result["url_result"]
    attachment_result = fusion_result["attachment_result"]

    candidate_ip = forensics_result.get("candidate_source_ip")
    geolocation = ip_geolocation.geolocate_ip(candidate_ip) if resolve_network else ip_geolocation.geolocate_ip(None)

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