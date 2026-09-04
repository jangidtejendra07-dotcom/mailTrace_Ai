from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import analyze, cases, auth, gmail, webhook, addon, geo
from app.routers.graph import graphql_app
from app.config import settings
from app import scheduler
from app.services import graph_manager

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MailTrace AI",
    description="AI-assisted email threat detection, forensics, geolocation & real-time Gmail inbox intelligence — SIH 26106",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(gmail.router)
app.include_router(webhook.router)
app.include_router(addon.router)
app.include_router(analyze.router)
app.include_router(cases.router)
app.include_router(geo.router)
app.include_router(graphql_app, prefix="/graphql")


@app.on_event("startup")
def on_startup():
    # Best-effort: renews Gmail push-notification watches before they expire
    # (7-day lifetime). No-ops safely if real-time detection isn't configured.
    scheduler.start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    scheduler.stop_scheduler()
    graph_manager.close_driver()


@app.get("/")
def root():
    return {
        "service": "MailTrace AI",
        "status": "running",
        "docs": "/docs",
        "core_endpoints": {
            "register": "POST /api/v1/auth/register",
            "login": "POST /api/v1/auth/login",
            "connect_gmail": "GET /api/v1/gmail/connect",
            "sync_gmail": "POST /api/v1/gmail/sync",
            "start_realtime_watch": "POST /api/v1/gmail/watch/start",
            "realtime_webhook": "POST /api/v1/gmail/webhook",
            "quarantined_cases": "GET /api/v1/cases/quarantined",
            "release_case": "POST /api/v1/cases/{case_id}/release",
            "analyze_upload": "POST /api/v1/analyze-email",
            "legal_report": "GET /api/v1/cases/{case_id}/report/legal/{jurisdiction}",
            "geo_infra": "GET /api/v1/geo/infra",
            "campaign_graph_graphql": "POST /graphql (or open in browser for GraphiQL)",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}