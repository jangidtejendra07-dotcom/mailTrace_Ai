"""
Section 6 — URL + Domain Intelligence.

URL -> Normalize -> Domain/DNS -> Redirects -> Reputation
    -> url_score + suspicious_features + final_url

DNS/redirect resolution is best-effort and network-optional: if the
sandbox/deployment has no outbound internet access, the module degrades
gracefully to heuristic-only scoring.
"""
import re
import socket
from urllib.parse import urlparse

try:
    import tldextract
except ImportError:  # pragma: no cover
    tldextract = None

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

SUSPICIOUS_TLDS = {"zip", "mov", "top", "xyz", "tk", "ml", "ga", "cf", "gq", "info", "click", "link"}

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly",
    "rebrand.ly", "cutt.ly", "shorte.st",
}

BRAND_KEYWORDS = [
    "paypal", "microsoft", "office365", "outlook", "google", "gmail", "apple",
    "amazon", "netflix", "bank", "chase", "wellsfargo", "hdfc", "icici", "sbi",
    "facebook", "instagram", "whatsapp", "irs", "gov",
]

IP_HOST_REGEX = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _get_registered_domain(hostname: str) -> str:
    if tldextract:
        ext = tldextract.extract(hostname)
        return f"{ext.domain}.{ext.suffix}" if ext.suffix else hostname
    parts = hostname.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname


def _resolve_dns(hostname: str) -> str | None:
    try:
        return socket.gethostbyname(hostname)
    except Exception:
        return None


def _follow_redirects(url: str, timeout: float = 3.0) -> str:
    if not requests:
        return url
    try:
        resp = requests.head(url, allow_redirects=True, timeout=timeout)
        return resp.url
    except Exception:
        try:
            resp = requests.get(url, allow_redirects=True, timeout=timeout, stream=True)
            resp.close()
            return resp.url
        except Exception:
            return url


def analyze_url(raw_url: str, resolve_network: bool = True) -> dict:
    features = []
    score = 0

    parsed = urlparse(raw_url if "://" in raw_url else f"http://{raw_url}")
    hostname = (parsed.hostname or "").lower()
    registered_domain = _get_registered_domain(hostname) if hostname else ""

    is_ip_host = bool(IP_HOST_REGEX.match(hostname))
    if is_ip_host:
        features.append("URL uses a raw IP address instead of a domain name")
        score += 30

    if hostname in URL_SHORTENERS:
        features.append(f"Uses URL shortener service ({hostname}) which hides the true destination")
        score += 20

    tld = registered_domain.split(".")[-1] if "." in registered_domain else ""
    if tld in SUSPICIOUS_TLDS:
        features.append(f"Suspicious/low-cost top-level domain: .{tld}")
        score += 15

    subdomain_count = hostname.count(".") - registered_domain.count(".") if registered_domain else 0
    if subdomain_count >= 3:
        features.append(f"Excessive subdomain nesting ({subdomain_count} levels) often used to obscure real domain")
        score += 15

    for brand in BRAND_KEYWORDS:
        if brand in hostname and brand not in registered_domain.replace(".", ""):
            features.append(f"Brand keyword '{brand}' used in subdomain/path but not the registered domain (typosquat pattern)")
            score += 25
            break

    if "@" in raw_url:
        features.append("URL contains '@' which can be used to obscure the real destination host")
        score += 20

    if len(raw_url) > 120:
        features.append("Unusually long URL, often used to hide malicious parameters")
        score += 10

    if parsed.scheme == "http":
        features.append("Uses unencrypted HTTP rather than HTTPS")
        score += 10

    resolved_ip = None
    final_url = raw_url
    if resolve_network and hostname and not is_ip_host:
        resolved_ip = _resolve_dns(hostname)
        if resolved_ip is None:
            features.append("Domain does not resolve via DNS (possibly taken down or newly registered)")
            score += 10
        final_url = _follow_redirects(raw_url)
        if final_url != raw_url:
            features.append(f"URL redirects to a different destination: {final_url}")
            score += 10

    if not features:
        features.append("No suspicious URL features detected")

    return {
        "original_url": raw_url,
        "final_url": final_url,
        "hostname": hostname,
        "registered_domain": registered_domain,
        "resolved_ip": resolved_ip,
        "score": min(100, score),
        "suspicious_features": features,
    }


def analyze_urls(urls: list[str], resolve_network: bool = True) -> dict:
    if not urls:
        return {"score": 0, "items": [], "summary": "No URLs found in email body"}

    items = [analyze_url(u, resolve_network=resolve_network) for u in urls[:20]]
    max_score = max(i["score"] for i in items)

    return {
        "score": max_score,
        "items": items,
        "summary": f"{len(items)} URL(s) analyzed; highest risk score: {max_score}",
    }
