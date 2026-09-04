"""
Feature 3 — Geo-Infrastructure Visualization API.

GET /api/v1/geo/infra returns a heatmap point list AND ASN/ISP-grouped
infra clusters across every case the current user has analyzed, so the
dashboard can render attacker infrastructure spread (heatmap + clustered
markers) instead of one marker per case.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth.dependencies import get_current_user
from app.services import geo_manager

router = APIRouter(prefix="/api/v1/geo", tags=["geo"])


@router.get("/infra")
def get_infra_map(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return geo_manager.get_infra_summary(db, current_user.id)