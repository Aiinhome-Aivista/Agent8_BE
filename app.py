# api/app.py
# FastAPI application entry point — registers all routers, CORS, and middleware

import os
import sys
from pathlib import Path

# Add api directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

import numpy as np
if not hasattr(np, "float_"):
    np.float_ = np.float64

load_dotenv()
os.environ["ANONYMIZED_TELEMETRY"] = "False"  # Disable chromadb telemetry errors

# Import all controllers (routers)
from controllers.auth_controller import router as auth_router
from controllers.chat_controller import router as chat_router
from controllers.policy_controller import router as policy_router
from controllers.renewal_controller import router as renewal_router
from controllers.endorsement_controller import router as endorsement_router
from controllers.escalation_controller import router as escalation_router
from controllers.notification_controller import router as notification_router
from controllers.dashboard_controller import router as dashboard_router
from controllers.compliance_controller import router as compliance_router
from controllers.rag_controller import router as rag_router
from controllers.knowledge_base_controller import router as kb_router

app = FastAPI(
    title="InsureAI Pro API",
    description="Enterprise AI-powered Insurance Virtual Customer Service Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — allow explicit origins for development (no credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handler — returns JSON instead of HTML
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)[:100]}"}
    )

# Register all routers with /api prefix
PREFIX = "/api"

from fastapi.staticfiles import StaticFiles
# Serve the uploads folder so files can be downloaded
os.makedirs("uploads", exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include Routers
app.include_router(auth_router,         prefix=PREFIX)
app.include_router(chat_router,         prefix=PREFIX)
app.include_router(policy_router,       prefix=PREFIX)
app.include_router(renewal_router,      prefix=PREFIX)
app.include_router(endorsement_router,  prefix=PREFIX)
app.include_router(escalation_router,   prefix=PREFIX)
app.include_router(notification_router, prefix=PREFIX)
app.include_router(dashboard_router,    prefix=PREFIX)
app.include_router(compliance_router,   prefix=PREFIX)
app.include_router(rag_router,          prefix=PREFIX)
app.include_router(kb_router,           prefix=PREFIX)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "InsureAI Pro API", "version": "1.0.0"}

from utils.escalation_worker import check_escalations
import asyncio
from jobs.sla_monitor import run_sla_monitor
from jobs.notification_processor import run_notification_processor
from jobs.memory_cleanup import run_memory_cleanup

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_escalations())
    asyncio.create_task(run_sla_monitor())
    asyncio.create_task(run_notification_processor())
    asyncio.create_task(run_memory_cleanup())
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
