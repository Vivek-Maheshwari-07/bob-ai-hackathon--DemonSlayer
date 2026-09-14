"""FastAPI Application Entry Point.

Drug Safety Signal Detector & Regulatory Submission Readiness Checker
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Drug Safety Signal Detector & Regulatory Submission Readiness Checker API",
    description="API services for pharmacovigilance adverse-event signal detection and ICH M4 CTD readiness verification with IBM Bob Copilot.",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check and API metadata endpoint."""
    return {
        "status": "online",
        "message": "Drug Safety Signal Detector & Regulatory Submission Readiness Checker API",
        "version": "0.1.0",
        "mode": "initial_setup",
    }


@app.get("/api/v1/health")
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "safety_engine": "ready",
            "ctd_engine": "ready",
            "bob_copilot": "ready",
        },
    }


from app.api.v1.endpoints.m4_checker import router as m4_router

# Include API Routers
app.include_router(m4_router, prefix="/api/v1")
