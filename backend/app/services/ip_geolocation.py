"""
Section 7 — IP / Geolocation.

Received headers -> candidate IP -> IP intelligence
                                  -> GEO / ASN / ISP / hosting
                                  -> probable_origin + confidence

IMPORTANT: this returns a *probable network origin*, never an exact
physical/attacker location, per the spec's honesty requirement.

Uses the free ip-api.com JSON endpoint (no key required, generous for
demo/prototype use). Falls back to an "unknown" result with low
confidence if there is no outbound network access.
"""
import ipaddress

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]


def _is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in PRIVATE_NETS)
    except ValueError:
        return True


def geolocate_ip(ip: str) -> dict:
    if not ip or _is_private(ip):
        return {
            "ip": ip,
            "probable_origin": "Unknown (private/internal or missing IP)",
            "country": None,
            "region": None,
            "city": None,
            "asn": None,
            "isp": None,
            "is_hosting_or_proxy": None,
            "confidence": "LOW",
            "latitude": None,
            "longitude": None,
        }

    if requests is not None:
        try:
            resp = requests.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,message,country,regionName,city,isp,org,as,proxy,hosting,lat,lon,query"},
                timeout=3.0,
            )
            data = resp.json()
            if data.get("status") == "success":
                country = data.get("country")
                region = data.get("regionName")
                city = data.get("city")
                is_hosting = bool(data.get("proxy") or data.get("hosting"))
                origin_parts = [p for p in [city, region, country] if p]
                probable_origin = ", ".join(origin_parts) if origin_parts else "Unknown"
                return {
                    "ip": ip,
                    "probable_origin": probable_origin,
                    "country": country,
                    "region": region,
                    "city": city,
                    "asn": data.get("as"),
                    "isp": data.get("isp") or data.get("org"),
                    "is_hosting_or_proxy": is_hosting,
                    "confidence": "MEDIUM" if not is_hosting else "LOW",
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                }
        except Exception:
            pass

    return {
        "ip": ip,
        "probable_origin": "Unknown (lookup unavailable — no network access or lookup failed)",
        "country": None,
        "region": None,
        "city": None,
        "asn": None,
        "isp": None,
        "is_hosting_or_proxy": None,
        "confidence": "LOW",
        "latitude": None,
        "longitude": None,
    }
