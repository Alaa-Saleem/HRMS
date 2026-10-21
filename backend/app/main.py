import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import cors_origin_list, settings
from app.database import engine
from app.middleware_request_id import RequestIdMiddleware
from app.routers import audit_events, auth, chat, departments, documents, employees, leave_policies, leaves, notifications, tasks, workspace
from app.routers import platform_auth
from app.routers.platform import tenants as platform_tenants, plans as platform_plans, stats as platform_stats, audit as platform_audit, subscriptions as platform_subscriptions, users as platform_users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HRMS API", version="0.2.0")

app.add_middleware(RequestIdMiddleware)

try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
except Exception as e:
    logger.warning("prometheus metrics disabled: %s", e)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Company (tenant) routers
_COMPANY_ROUTERS = (
    auth.router,
    audit_events.router,
    workspace.router,
    departments.router,
    employees.router,
    leaves.router,
    leave_policies.router,
    tasks.router,
    chat.router,
    notifications.router,
    documents.router,
)

# Platform (super admin) routers
_PLATFORM_ROUTERS = (
    platform_auth.router,
    platform_tenants.router,
    platform_plans.router,
    platform_stats.router,
    platform_audit.router,
    platform_subscriptions.router,
    platform_users.router,
)

for router in _COMPANY_ROUTERS:
    app.include_router(router)
for router in _COMPANY_ROUTERS:
    app.include_router(router, prefix="/v1")

for router in _PLATFORM_ROUTERS:
    app.include_router(router)



@app.get("/healthz")
def healthz():
    ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            ok = True
    except Exception as e:
        logger.warning("healthz db fail: %s", e)
    return {"ok": ok}


@app.get("/")
def root():
    return {"service": "HRMS API", "docs": "/docs", "metrics": "/metrics", "v1_prefix": "/v1"}


# Serve static UI from repo root (same origin as API → no CORS issues for login).
# `backend/app/main.py` → parent of `backend/` is the repo root with login.html.
_backend_dir = Path(__file__).resolve().parents[1]
_repo_candidate = _backend_dir.parent
if (_repo_candidate / "login.html").is_file():
    app.mount("/", StaticFiles(directory=str(_repo_candidate), html=True), name="hrms_static")
