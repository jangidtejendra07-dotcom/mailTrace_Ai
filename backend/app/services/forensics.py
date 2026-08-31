"""
Section 4 — Email Forensics.

Parses From, Return-Path, Reply-To, Message-ID, Received, and
Authentication-Results / DKIM-Signature. Computes SPF/DKIM/DMARC status,
sender/reply-to mismatch, relay-hop chain, and header anomalies.
"""
import re

IP_REGEX = re.compile(r"\[?((?:\d{1,3}\.){3}\d{1,3})\]?")


def _extract_auth_status(auth_results: str, mechanism: str) -> str:
    """Extract pass/fail/none/softfail for spf|dkim|dmarc from
    an Authentication-Results header string."""
    if not auth_results:
        return "none"
    pattern = re.compile(rf"{mechanism}=([a-zA-Z]+)", re.IGNORECASE)
    match = pattern.search(auth_results)
    return match.group(1).lower() if match else "none"


def _domain_of(address: str) -> str:
    if "@" in address:
        return address.split("@")[-1].lower().strip(">")
    return ""


def extract_relay_chain(received_headers: list[str]) -> list[dict]:
    """
    Parses Received headers (in order they appear, which is reverse
    chronological — closest-to-recipient first) into a relay hop chain,
    extracting the first public/candidate IP address seen in each hop.
    """
    chain = []
    for idx, header in enumerate(received_headers):
        ips = IP_REGEX.findall(header or "")
        # Filter obviously private/loopback ranges for a cleaner "candidate source"
        candidate_ip = None
        for ip in ips:
            octets = ip.split(".")
            if len(octets) == 4 and not (
                ip.startswith("10.") or ip.startswith("127.") or
                ip.startswith("192.168.") or
                (octets[0] == "172" and 16 <= int(octets[1]) <= 31)
            ):
                candidate_ip = ip
                break
        from_match = re.search(r"from\s+(\S+)", header or "")
        by_match = re.search(r"by\s+(\S+)", header or "")
        chain.append({
            "hop": idx,
            "raw": header.strip()[:300] if header else "",
            "from_host": from_match.group(1) if from_match else None,
            "by_host": by_match.group(1) if by_match else None,
            "ips_found": ips,
            "candidate_ip": candidate_ip,
        })
    return chain


def analyze_headers(parsed_email: dict) -> dict:
    auth_results = parsed_email.get("authentication_results", "")

    spf = _extract_auth_status(auth_results, "spf")
    dkim = _extract_auth_status(auth_results, "dkim")
    dmarc = _extract_auth_status(auth_results, "dmarc")

    if dkim == "none" and parsed_email.get("dkim_signature_present"):
        # signature exists but Authentication-Results didn't report dkim=
        dkim = "unknown"

    from_domain = _domain_of(parsed_email.get("from_address", ""))
    reply_domain = _domain_of(parsed_email.get("reply_to_address", ""))
    reply_to_mismatch = bool(reply_domain and from_domain and reply_domain != from_domain)

    relay_chain = extract_relay_chain(parsed_email.get("received_headers", []))
    candidate_source_ip = next(
        (hop["candidate_ip"] for hop in relay_chain if hop["candidate_ip"]), None
    )

    anomalies = []
    score = 0

    if spf == "fail":
        anomalies.append("SPF authentication failed")
        score += 30
    elif spf in ("none", "unknown"):
        anomalies.append("SPF record missing or unverifiable")
        score += 10

    if dkim == "fail":
        anomalies.append("DKIM signature verification failed")
        score += 30
    elif dkim in ("none", "unknown"):
        anomalies.append("DKIM signature missing or unverifiable")
        score += 10

    if dmarc == "fail":
        anomalies.append("DMARC alignment failed")
        score += 25
    elif dmarc in ("none", "unknown"):
        anomalies.append("DMARC policy missing or unverifiable")
        score += 5

    if reply_to_mismatch:
        anomalies.append(f"Reply-To domain ({reply_domain}) does not match From domain ({from_domain})")
        score += 25

    if not parsed_email.get("message_id"):
        anomalies.append("Missing Message-ID header")
        score += 5

    if len(relay_chain) == 0:
        anomalies.append("No Received headers found — cannot trace relay path")
        score += 10

    if not anomalies:
        anomalies.append("No header anomalies detected; authentication checks passed")

    return {
        "score": min(100, score),
        "spf": spf,
        "dkim": dkim,
        "dmarc": dmarc,
        "from_domain": from_domain,
        "reply_to_domain": reply_domain or None,
        "reply_to_mismatch": reply_to_mismatch,
        "relay_chain": relay_chain,
        "candidate_source_ip": candidate_source_ip,
        "anomalies": anomalies,
    }
