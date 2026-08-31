"""
Section 9 — Forensic Correlation Graph
Section 10 — Case + Evidence

Builds an evidence package for BLOCK/QUARANTINE messages, computes a
SHA-256 hash over it for integrity, and derives a simple correlation
graph (email -> domain/DNS/IP/ASN/GEO, url, attachment, sender/reply-to)
so that repeated indicators across cases can later be linked into a
campaign. A blockchain/ledger is intentionally NOT implemented (per
spec: optional future work, not required for MVP).
"""
import hashlib
import json
import time
import uuid


def generate_case_id() -> str:
    year = time.strftime("%Y")
    return f"MT-{year}-{uuid.uuid4().hex[:8].upper()}"


def compute_evidence_hash(evidence: dict) -> str:
    canonical = json.dumps(evidence, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_correlation_graph(parsed_email: dict, forensics_result: dict,
                             url_result: dict, attachment_result: dict,
                             geolocation: dict) -> dict:
    nodes = []
    edges = []

    email_node = f"email:{parsed_email.get('message_id') or 'unknown'}"
    nodes.append({"id": email_node, "type": "EMAIL", "label": parsed_email.get("subject", "")[:60]})

    sender_node = f"sender:{parsed_email.get('from_address')}"
    nodes.append({"id": sender_node, "type": "SENDER", "label": parsed_email.get("from_address")})
    edges.append({"from": email_node, "to": sender_node, "relation": "SENT_BY"})

    if parsed_email.get("reply_to_address"):
        reply_node = f"reply_to:{parsed_email['reply_to_address']}"
        nodes.append({"id": reply_node, "type": "REPLY_TO", "label": parsed_email["reply_to_address"]})
        edges.append({"from": email_node, "to": reply_node, "relation": "REPLIES_TO"})

    candidate_ip = forensics_result.get("candidate_source_ip")
    if candidate_ip:
        ip_node = f"ip:{candidate_ip}"
        nodes.append({"id": ip_node, "type": "IP", "label": candidate_ip})
        edges.append({"from": email_node, "to": ip_node, "relation": "ORIGINATED_FROM"})

        if geolocation and geolocation.get("country"):
            geo_node = f"geo:{geolocation.get('country')}:{geolocation.get('city')}"
            nodes.append({"id": geo_node, "type": "GEO", "label": geolocation.get("probable_origin")})
            edges.append({"from": ip_node, "to": geo_node, "relation": "LOCATED_IN"})

        if geolocation and geolocation.get("asn"):
            asn_node = f"asn:{geolocation.get('asn')}"
            nodes.append({"id": asn_node, "type": "ASN", "label": geolocation.get("asn")})
            edges.append({"from": ip_node, "to": asn_node, "relation": "BELONGS_TO"})

    for url_item in url_result.get("items", []):
        domain = url_item.get("registered_domain")
        if domain:
            domain_node = f"domain:{domain}"
            nodes.append({"id": domain_node, "type": "DOMAIN", "label": domain})
            edges.append({"from": email_node, "to": domain_node, "relation": "CONTAINS_URL"})
            if candidate_ip and url_item.get("resolved_ip"):
                edges.append({"from": domain_node, "to": f"ip:{url_item['resolved_ip']}", "relation": "RESOLVES_TO"})

    for att in attachment_result.get("items", []):
        if att.get("sha256"):
            att_node = f"attachment:{att['sha256'][:12]}"
            nodes.append({"id": att_node, "type": "ATTACHMENT", "label": att.get("filename")})
            edges.append({"from": email_node, "to": att_node, "relation": "HAS_ATTACHMENT"})

    # de-duplicate nodes by id
    seen = set()
    unique_nodes = []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            unique_nodes.append(n)

    return {"nodes": unique_nodes, "edges": edges}


def build_evidence_package(case_id: str, parsed_email: dict, ai_result: dict,
                            forensics_result: dict, url_result: dict,
                            attachment_result: dict, geolocation: dict,
                            fusion_result: dict) -> dict:
    evidence = {
        "case_id": case_id,
        "email_reference": {
            "message_id": parsed_email.get("message_id"),
            "subject": parsed_email.get("subject"),
            "from": parsed_email.get("from_address"),
            "to": parsed_email.get("to_header"),
        },
        "parsed_headers": {
            "authentication_results": parsed_email.get("authentication_results"),
            "return_path": parsed_email.get("return_path"),
            "reply_to": parsed_email.get("reply_to_header"),
            "received_hop_count": len(parsed_email.get("received_headers", [])),
        },
        "urls": [u["original_url"] for u in url_result.get("items", [])],
        "attachment_metadata": [
            {"filename": a["filename"], "sha256": a["sha256"], "severity": a["severity"]}
            for a in attachment_result.get("items", [])
        ],
        "ai_findings": ai_result,
        "risk_reasons": fusion_result.get("explanation", []),
        "intelligence_results": {
            "forensics": forensics_result,
            "url_intelligence": url_result,
            "geolocation": geolocation,
        },
        "timestamps": {"analyzed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        "analyst_actions": [],
    }
    evidence["sha256_evidence_hash"] = compute_evidence_hash(evidence)
    return evidence
