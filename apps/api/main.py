import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import approvals, faq, pulse, scheduler

load_dotenv()

app = FastAPI(title="Mutual Fund Advisor Intelligence Suite API")


def _cors_origins():
    configured_origins = os.getenv("CORS_ORIGINS", "")
    origins = [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]
    return origins or [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(faq.router, prefix="/faq", tags=["FAQ"])
app.include_router(pulse.router, prefix="/pulse", tags=["Weekly Pulse"])
app.include_router(scheduler.router, prefix="/scheduler", tags=["Scheduler"])
app.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "name": "Mutual Fund Advisor Intelligence Suite API",
        "phase": "Phase 1-6 complete - pre-deployment",
        "status": "local_demo_ready",
    }
