import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.database import client
from backend.app.routes.records import router as records_router, get_statistics

app = FastAPI(
    title="CloudDataGuard",
    description="Intelligent NoSQL Cloud-Based Data Redundancy Removal System",
    version="2.0.0"
)

# ========================================
# CORS Configuration
# ========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# Home
# ========================================
@app.get("/", summary="API Root Status")
def home():
    return {
        "project": "CloudDataGuard — MongoDB-Based Data Redundancy Removal System",
        "system": "Intelligent NoSQL Data Redundancy Removal",
        "status": "online",
        "version": "2.0.0",
        "docs": "/docs",
        "frontend": "/frontend/index.html"
    }


# ========================================
# Database Status
# ========================================
@app.get("/database-status", summary="Check MongoDB Connection Health")
def database_status():
    try:
        client.admin.command("ping")
        return {
            "database": "MongoDB",
            "status": "connected"
        }
    except Exception as e:
        return {
            "database": "MongoDB",
            "status": "connection failed",
            "error": str(e)
        }


# ========================================
# Stats Root Alias (Syllabus Requirement)
# ========================================
@app.get("/stats", summary="Root Stats Alias")
def root_stats():
    return get_statistics()


# ========================================
# Records Router
# ========================================
app.include_router(records_router)


# ========================================
# Frontend Static Files
# ========================================
frontend_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend"
)

if os.path.exists(frontend_path):
    app.mount(
        "/frontend",
        StaticFiles(directory=frontend_path, html=True),
        name="frontend"
    )
