"""
Feature 3 — Geo-Infrastructure Visualization.

Aggregates geolocation data ALREADY stored per-case (the Case.geolocation
JSON column, populated at analysis time by ip_geolocation.geolocate_ip())
into two views:

  - heatmap_points: one point per case with resolvable coordinates, so a
    density heatmap can show where malicious mail is originating from.
  - infra_clusters: cases grouped by (ASN, ISP), so repeated attacker
    infrastructure across different emails/campaigns shows up as ONE
    cluster with a case count, instead of scattered individual markers.

MaxMind GeoIP2 is intentionally NOT called here — the geolocation data is
already computed once at analysis time and stored on the Case row, so this
module just aggregates what's already in the database. MAXMIND_LICENSE_KEY
is reserved for a future enrichment pass (fresher ASN/org lookups) and is
safe to leave unset; `maxmind_enriched` in the response simply reflects
whether that key is configured yet.
"""
import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import Case
from app.config import settings

logger = logging.getLogger("mailtrace.geo_manager")


def _maxmind_enabled() -> bool:
    return bool(getattr(settings, "MAXMIND_LICENSE_KEY", ""))


def get_heatmap_points(db: Session, user_id: int) -> list[dict]:
    """
    One point per case with resolvable lat/lon. Weight favors higher-risk
    cases so the heatmap highlights dangerous concentrations, not just
    raw email volume.
    """
    cases = (
        db.query(Case)
        .filter(Case.user_id == user_id, Case.geolocation.isnot(None))
        .all()
    )

    points = []
    for c in cases:
        geo = c.geolocation or {}
        lat, lon = geo.get("latitude"), geo.get("longitude")
        if lat is None or lon is None:
            continue

        weight = 0.3 + (0.7 * (c.final_risk_score or 0) / 100)
        points.append({
            "lat": lat,
            "lon": lon,
            "weight": round(weight, 2),
            "case_id": c.case_id,
        })

    return points


def get_infra_clusters(db: Session, user_id: int) -> list[dict]:
    """
    Groups cases by (ASN, ISP) so the SAME attacker infrastructure showing
    up across multiple emails/cases renders as one cluster with a count,
    rather than N separate markers sitting on top of each other.
    """
    cases = (
        db.query(Case)
        .filter(Case.user_id == user_id, Case.geolocation.isnot(None))
        .all()
    )

    groups = defaultdict(lambda: {
        "country": None,
        "lat_sum": 0.0,
        "lon_sum": 0.0,
        "count": 0,
        "case_ids": [],
        "max_risk_score": 0,
    })

    for c in cases:
        geo = c.geolocation or {}
        lat, lon = geo.get("latitude"), geo.get("longitude")
        if lat is None or lon is None:
            continue

        key = (geo.get("asn") or "Unknown ASN", geo.get("isp") or "Unknown ISP")
        g = groups[key]
        g["country"] = geo.get("country") or geo.get("probable_origin") or g["country"]
        g["lat_sum"] += lat
        g["lon_sum"] += lon
        g["count"] += 1
        g["case_ids"].append(c.case_id)
        g["max_risk_score"] = max(g["max_risk_score"], c.final_risk_score or 0)

    clusters = []
    for (asn, isp), g in groups.items():
        clusters.append({
            "asn": asn,
            "isp": isp,
            "country": g["country"] or "Unknown",
            "latitude": round(g["lat_sum"] / g["count"], 4),
            "longitude": round(g["lon_sum"] / g["count"], 4),
            "email_count": g["count"],
            "case_ids": g["case_ids"],
            "max_risk_score": g["max_risk_score"],
        })

    clusters.sort(key=lambda x: x["email_count"], reverse=True)
    return clusters


def get_infra_summary(db: Session, user_id: int) -> dict:
    return {
        "heatmap_points": get_heatmap_points(db, user_id),
        "infra_clusters": get_infra_clusters(db, user_id),
        "maxmind_enriched": _maxmind_enabled(),
    }